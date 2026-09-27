"""台本（YAML）から縦型ショート動画（1080x1920 / mp4）を作る。

使い方:
  python shorts-maker/make_video.py shorts-maker/scripts/001_switch2_accessories.yaml --out out
  python shorts-maker/make_video.py shorts-maker/scripts/*.yaml --tts silent   # 音声なしで見た目だけ確認

読み上げは VOICEVOX エンジン（http://localhost:50021）を使う。
GitHub Actions ではワークフローが自動で起動するので、何も準備しなくてよい。

画面は3種類:
  title  : 放射状の背景に大きなタイトル（白・赤・黄の文字）、下にイラスト
  rank   : 上に「番号＋名前」、その下に説明の枠（青→紫→緑→赤の枠が1つずつ出る）、下に画像
  ending : 放射状の背景に大きな白文字
"""

import argparse
import glob
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import wave

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
FPS = 30
SAMPLE_RATE = 24000
LINE_GAP = 0.15   # ナレーションとナレーションの間の無音（秒）
SCENE_GAP = 0.35  # シーンとシーンの間の無音（秒）

# ───────────── 見た目の設定 ─────────────

RAY_YELLOW = (255, 226, 0)
RAY_ORANGE = (255, 171, 0)
RAY_COUNT = 12                # オレンジの光線の本数
RAY_WIDTH = 0.45              # オレンジの光線の太さ（1本ぶんの角度に対する割合）
RAY_CENTER = (W // 2, 945)
# 枠の色。台本で color を書かなければ 青→紫→緑→赤 の順に使う
BOX_COLORS = {
    "blue": (0, 0, 255),
    "purple": (220, 0, 255),
    "green": (60, 255, 0),
    "red": (255, 0, 0),
}
BOX_ORDER = ["blue", "purple", "green", "red"]
BOX_LEFT = 78          # 枠の左端
BOX_GAP = 18           # 枠と枠のすきま
BOX_PAGE_BOTTOM = 1300  # 枠がここより下にはみ出す時は、枠を消して上から並べ直す
POP_STEPS = [(0.5, 0.1), (0.8, 0.1)]  # 見出しがポンと出る動き: (大きさ, 秒) の順に表示してから等倍
SPIN = 10               # 背景が回る速さ（度/秒）。台本の spin で変えられる。0 で止まる、マイナスで逆回り
BGM_VOLUME = 0.12       # BGM の音量（台本の bgm_volume で変えられる）
BGM_FADE = (0.5, 2.0)   # BGM のフェードイン・フェードアウト（秒）
RAKUTEN_API = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

# 文字のスタイル: (上の色, 下の色) のグラデーション
STYLES = {
    "white": ((255, 255, 255), (255, 255, 255)),
    "red": ((240, 20, 20), (70, 0, 0)),
    "yellow": ((255, 250, 90), (240, 190, 0)),
}

DISPLAY_FONT = os.path.join(HERE, "fonts", "MPLUSRounded1c-Black.ttf")  # タイトル・順位・締め
BOX_FONT = os.path.join(HERE, "fonts", "NotoSansJP-Black.ttf")          # 枠の中の文字
# fonts/ に display.ttf / box.ttf を置くと、そのフォントに差し替わる
for _name, _var in (("display", "DISPLAY_FONT"), ("box", "BOX_FONT")):
    for _ext in (".ttf", ".otf", ".ttc"):
        _p = os.path.join(HERE, "fonts", _name + _ext)
        if os.path.exists(_p):
            globals()[_var] = _p

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# ───────────── 読み上げ ─────────────

def tts_voicevox(text, cfg):
    base = cfg["voicevox_url"].rstrip("/")
    speaker = cfg["speaker"]
    q = urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(f"{base}/audio_query?{q}", method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        query = json.load(r)
    query["speedScale"] = cfg["speed"]
    query["prePhonemeLength"] = 0.05
    query["postPhonemeLength"] = 0.05
    query["outputSamplingRate"] = SAMPLE_RATE
    query["outputStereo"] = False
    req = urllib.request.Request(
        f"{base}/synthesis?speaker={speaker}",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    with wave.open(io.BytesIO(data)) as w:
        return w.readframes(w.getnframes())


def voicevox_names(cfg):
    """話者ID → キャラクター名 の表（クレジット用）。取れなければ空。"""
    try:
        with urllib.request.urlopen(cfg["voicevox_url"].rstrip("/") + "/speakers", timeout=30) as r:
            return {st["id"]: sp["name"] for sp in json.load(r) for st in sp["styles"]}
    except Exception:
        return {}


def tts_silent(text, cfg):
    # 見た目の確認用。1文字あたり約0.12秒の無音を返す
    seconds = max(1.2, len(text) * 0.12 / cfg["speed"])
    return b"\x00\x00" * int(seconds * SAMPLE_RATE)


def silence(seconds):
    return b"\x00\x00" * int(seconds * SAMPLE_RATE)


# ───────────── 描画の部品 ─────────────

def sunburst(angle=0.0):
    """黄色とオレンジの放射状の背景。angle（度）だけ回した絵を返す。

    縁がギザギザしないよう、2倍の大きさで描いてから縮める。
    """
    k = 2
    img = Image.new("RGB", (W * k, H * k), RAY_YELLOW)
    d = ImageDraw.Draw(img)
    cx, cy = RAY_CENTER[0] * k, RAY_CENTER[1] * k
    r = math.hypot(W, H) * k
    step = 2 * math.pi / RAY_COUNT
    for i in range(RAY_COUNT):
        mid = i * step + math.radians(2 + angle)
        a0, a1 = mid - step * RAY_WIDTH / 2, mid + step * RAY_WIDTH / 2
        d.polygon([(cx, cy),
                   (cx + r * math.cos(a0), cy + r * math.sin(a0)),
                   (cx + r * math.cos(a1), cy + r * math.sin(a1))], fill=RAY_ORANGE)
    return img.resize((W, H), Image.LANCZOS).convert("RGBA")


def canvas():
    """文字や画像を描く透明な画面。背景はあとで動画にするときに下に敷く。"""
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def text_layer(text, fnt, style="white", tracking=-0.04, squeeze=1.0, outline="auto"):
    """縁取り・グラデーション・影つきの文字を1枚の透過画像にして返す。

    white : 白文字＋太い黒縁＋影
    red / yellow : グラデーション文字＋細い白縁＋黒いぼかし縁
    """
    size = fnt.size
    pad = int(size * 0.35)
    # 1文字ずつ置いて字間を詰める
    advances = [fnt.getlength(ch) for ch in text]
    track = size * tracking
    width = int(sum(advances) + track * (len(text) - 1)) + pad * 2
    height = int(size * 1.35) + pad * 2
    mask = Image.new("L", (width, height), 0)
    md = ImageDraw.Draw(mask)
    x = pad
    for ch, adv in zip(text, advances):
        md.text((x, pad), ch, font=fnt, fill=255)
        x += adv + track

    def grow(m, px):
        return m.filter(ImageFilter.MaxFilter(px * 2 + 1)) if px > 0 else m

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if style == "white":
        black = grow(mask, max(2, int(size * 0.085)) // 1)
        shadow = black.filter(ImageFilter.GaussianBlur(size * 0.06))
        layer.paste((0, 0, 0, 170), (int(size * 0.05), int(size * 0.06)), shadow)
        layer.paste((0, 0, 0, 255), (0, 0), black)
        layer.paste((255, 255, 255, 255), (0, 0), mask)
    else:
        white = grow(mask, max(2, int(size * 0.055)))
        glow = grow(white, max(2, int(size * 0.07))).filter(ImageFilter.GaussianBlur(size * 0.08))
        layer.paste((0, 0, 0, 255), (0, 0), glow)
        layer.paste((255, 255, 255, 255), (0, 0), white)
        top, bottom = STYLES[style]
        grad = Image.new("RGBA", (1, height))
        for y in range(height):
            t = min(1, max(0, (y - pad) / (size * 1.1)))
            grad.putpixel((0, y), tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)) + (255,))
        layer.paste(grad.resize((width, height)), (0, 0), mask)
    if squeeze != 1.0:
        layer = layer.resize((int(width * squeeze), height), Image.LANCZOS)
    bbox = layer.getbbox()
    return layer.crop(bbox) if bbox else layer


def fitted_layer(text, font_path, max_width, max_size, min_size=40, **kw):
    """幅に収まる一番大きいサイズで文字を作る。"""
    size = max_size
    while True:
        layer = text_layer(text, font(font_path, size), **kw)
        if layer.width <= max_width or size <= min_size:
            return layer
        size = max(min_size, int(size * max_width / layer.width) - 2)


def paste_center(img, layer, center_x, top):
    img.alpha_composite(layer, (int(center_x - layer.width / 2), int(top)))


def fetch(url, timeout=60, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (shorts-maker)", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def rakuten_search(keyword):
    """楽天市場の商品検索APIで一番上の商品を探す。(画像URLの候補, アフィリエイトURL) を返す。

    環境変数（GitHub では Secrets）:
      RAKUTEN_APP_ID       アプリID（必須）
      RAKUTEN_ACCESS_KEY   アクセスキー（必須）
      RAKUTEN_AFFILIATE_ID アフィリエイトID（あれば link にアフィリエイトURLが入る）
      RAKUTEN_ORIGIN       アプリ登録で入れたサイトのURL（403 になる時に必要）
    """
    env = os.environ
    if not (env.get("RAKUTEN_APP_ID") and env.get("RAKUTEN_ACCESS_KEY")):
        print("    ※ image_search には RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY の設定が必要です（README 参照）")
        return None, None
    params = {"applicationId": env["RAKUTEN_APP_ID"], "accessKey": env["RAKUTEN_ACCESS_KEY"],
              "keyword": keyword, "hits": 1, "imageFlag": 1, "format": "json"}
    if env.get("RAKUTEN_AFFILIATE_ID"):
        params["affiliateId"] = env["RAKUTEN_AFFILIATE_ID"]
    headers = {"accessKey": env["RAKUTEN_ACCESS_KEY"]}
    if env.get("RAKUTEN_ORIGIN"):
        origin = env["RAKUTEN_ORIGIN"].rstrip("/")
        headers.update({"Origin": origin, "Referer": origin + "/"})
    try:
        items = json.loads(fetch(RAKUTEN_API + "?" + urllib.parse.urlencode(params), headers=headers))["Items"]
    except urllib.error.HTTPError as e:
        print(f"    ※ 楽天の検索に失敗しました（{keyword}）: {e} {e.read()[:200].decode(errors='ignore')}")
        return None, None
    except Exception as e:
        print(f"    ※ 楽天の検索に失敗しました（{keyword}）: {e}")
        return None, None
    if not items:
        print(f"    ※ 楽天で商品が見つかりませんでした: {keyword}")
        return None, None
    item = items[0].get("Item", items[0])
    small = item["mediumImageUrls"][0]
    small = small["imageUrl"] if isinstance(small, dict) else small
    print(f"    楽天の商品: {item['itemName'][:40]}")
    # APIの画像は128px。URLの _ex を変えると大きい画像が取れるので、まずそちらを試す
    big = small.replace("_ex=128x128", "_ex=600x600")
    return [big, small] if big != small else [small], item.get("affiliateUrl") or item.get("itemUrl")


def load_image(scene, image_dir):
    """シーンの画像を読み込む。

    image        : images/ に置いたファイル名、または画像のURL
    image_search : 楽天市場で探すキーワード（image がない時だけ使う）。link が空ならリンクも入れる
    """
    name = scene.get("image") or ""
    if not name and scene.get("image_search"):
        urls, link = rakuten_search(scene["image_search"])
        if link and not scene.get("link"):
            scene["link"] = link
        for url in urls or []:
            try:
                return Image.open(io.BytesIO(fetch(url))).convert("RGBA")
            except Exception as e:
                print(f"    ※ 楽天の画像を取れませんでした（{url}）: {e}")
        return None
    if not name:
        return None
    try:
        if name.startswith(("http://", "https://")):
            data = fetch(name)
        else:
            path = os.path.join(image_dir, name)
            if not os.path.exists(path):
                print(f"    ※ 画像が見つかりません: images/{name}")
                return None
            data = open(path, "rb").read()
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"    ※ 画像を読み込めませんでした（{name}）: {e}")
        return None


def draw_pr_badge(img):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 150, 130, 200], radius=10, fill=(255, 255, 255, 235),
                        outline=(0, 0, 0), width=3)
    d.text((85, 175), "PR", font=font(BOX_FONT, 30), fill=(20, 20, 20), anchor="mm")


# ───────────── 画面 ─────────────

def scaled(layer, k):
    """文字を k 倍に縮める（k が 1 以上ならそのまま）。"""
    if k >= 1.0:
        return layer
    return layer.resize((max(1, int(layer.width * k)), max(1, int(layer.height * k))), Image.LANCZOS)


def paste_scaled(img, layer, center_x, top, k):
    """等倍の時と同じ中心に、k 倍に縮めた文字を置く（ポンと出る動き用）。"""
    small = scaled(layer, k)
    img.alpha_composite(small, (int(center_x - small.width / 2),
                                int(top + (layer.height - small.height) / 2)))


def paste_bottom(img, image, max_w, max_h, margin, max_area=None):
    """画像を下ぞろえ・左右中央に置く。max_area を渡すと面積（ピクセル数）もそこまでにする。"""
    s = min(max_w / image.width, max_h / image.height)
    if max_area:
        s = min(s, math.sqrt(max_area / (image.width * image.height)))
    pic = image.resize((int(image.width * s), int(image.height * s)), Image.LANCZOS)
    img.alpha_composite(pic, ((W - pic.width) // 2, H - margin - pic.height))


def render_title(lines, image=None, pop=1.0):
    """タイトル画面。行ごとに文字の大きさを幅いっぱいに合わせる。下にイラスト。"""
    img = canvas()
    if image:
        paste_bottom(img, image, 1060, 430, 28)
    layers = []
    for line in lines:
        if isinstance(line, str):
            line = {"text": line}
        layers.append(fitted_layer(line["text"], DISPLAY_FONT, 1040, line.get("size", 190),
                                   style=line.get("style", "white"), tracking=-0.06))
    gap = 18
    area_top, area_bottom = 300, (1340 if image else 1700)
    total = sum(l.height for l in layers) + gap * (len(layers) - 1)
    scale = min(1.0, (area_bottom - area_top) / total)
    if scale < 1.0:
        layers = [scaled(l, scale) for l in layers]
        total = sum(l.height for l in layers) + gap * (len(layers) - 1)
    y = area_top + (area_bottom - area_top - total) / 2
    for layer in layers:
        paste_scaled(img, layer, W / 2, y, pop)
        y += layer.height + gap
    return img


def render_ending(lines):
    """締めの画面。全部の行を同じ大きさの白文字で、真ん中よりやや上に並べる。"""
    img = canvas()
    texts = [l if isinstance(l, str) else l["text"] for l in lines]
    size = 150
    while True:
        layers = [text_layer(t, font(DISPLAY_FONT, size), style="white", tracking=-0.06) for t in texts]
        pitch = int(size * 1.53)
        if (max(l.width for l in layers) <= 1000 and pitch * len(layers) <= 1700) or size <= 60:
            break
        size -= 6
    top = 885 - pitch * len(layers) / 2
    for i, layer in enumerate(layers):
        paste_center(img, layer, W / 2, top + i * pitch + (pitch - layer.height) / 2)
    return img


def box_layer(text, border):
    """白い四角に色つきの枠。「|」で改行、文字は左ぞろえ。"""
    fnt = font(BOX_FONT, 80)
    lines = text.split("|")
    while max(fnt.getlength(l) for l in lines) > 880 and fnt.size > 44:
        fnt = font(BOX_FONT, fnt.size - 2)
    pad_x, pad_y, line_h, bw = 20, 4, int(fnt.size * 1.47), 9
    width = int(max(fnt.getlength(l) for l in lines)) + pad_x * 2 + bw * 2
    height = line_h * len(lines) + pad_y * 2 + bw * 2
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, width - 1, height - 1], fill=border)
    d.rectangle([bw, bw, width - bw - 1, height - bw - 1], fill=(255, 255, 255))
    y = bw + pad_y
    for line in lines:
        d.text((bw + pad_x, y + line_h / 2), line, font=fnt, fill=(0, 0, 0), anchor="lm")
        y += line_h
    return layer


def rank_label(rank, name):
    """名前が日本語なら全角数字、英字なら半角数字＋スペース（例: 「１メタル…」「3 FRONT…」）。"""
    if name[:1].isascii():
        return f"{rank} "
    return str(rank).translate(str.maketrans("0123456789", "０１２３４５６７８９"))


def header_layers(scene):
    """「番号＋名前」の見出し。名前に「|」を入れると2行に分かれる。"""
    parts = scene["name"].split("|")
    parts[0] = rank_label(scene["rank"], parts[0]) + parts[0]
    return [fitted_layer(p, DISPLAY_FONT, 1000, 96, style="red", tracking=-0.14) for p in parts]


def box_pages(scene, box_top):
    """枠を画面ごとに分ける。枠に page: true を書くか、下にはみ出しそうな時に並べ直す。"""
    pages, y = [], box_top
    for i, box in enumerate(scene.get("boxes", [])):
        layer = box_layer(box["text"], BOX_COLORS[box.get("color") or BOX_ORDER[i % len(BOX_ORDER)]])
        if not pages or (pages[-1] and (box.get("page") or y + layer.height > BOX_PAGE_BOTTOM)):
            pages.append([])
            y = box_top
        pages[-1].append((layer, y))
        y += layer.height + BOX_GAP
    return pages


def render_rank(scene, visible_boxes, image, pop=1.0):
    img = canvas()
    heads = header_layers(scene)

    # 画像は枠の後ろ（枠が重なってもよい）。見出しが出きってから表示する
    if pop >= 1.0:
        if image:
            paste_bottom(img, image, 900, 1080, 15, max_area=520_000)
        else:
            # 画像がない時は名前を大きく出す
            name = fitted_layer(scene["name"].replace("|", ""), DISPLAY_FONT, 980, 170,
                                style="red", tracking=-0.04)
            paste_center(img, name, W / 2, 1450 - name.height / 2)

    y = 212
    for head in heads:
        paste_scaled(img, head, W / 2, y, pop)
        y += head.height

    # 今の画面の枠だけを表示（前の画面の枠は消える）
    shown = 0
    for page in box_pages(scene, y + 30):
        if shown + len(page) >= visible_boxes:
            for layer, top in page[:visible_boxes - shown]:
                img.alpha_composite(layer, (BOX_LEFT, int(top)))
            break
        shown += len(page)
    return img


# ───────────── 台本 → 画面とナレーションの並び ─────────────

def rank_yomi(scene, script):
    template = script.get("rank_yomi", "{n}、{name}")
    return template.format(n=scene["rank"], name=scene.get("name_yomi") or scene["name"].replace("|", ""))


def voice_of(*sources):
    """読み上げの声。枠 → シーン → 台本 の順に、先に書いてある speaker / speed を使う。"""
    voice = {}
    for src in sources:
        for key in ("speaker", "speed"):
            if isinstance(src, dict) and key in src and key not in voice:
                voice[key] = src[key]
    return voice


def timeline(script, image_dir):
    """画面とナレーションを順番に返す。1つずつ次の内容の dict:

    render : 画面を作る関数（pop = 文字の大きさ 0〜1 を受け取る）
    text   : 読み上げる文
    voice  : {"speaker": 話者ID, "speed": 速さ}（書いてないものは入らない）
    last   : シーンの最後か
    pop    : 見出しをポンと出すか
    """
    for scene in script["scenes"]:
        kind = scene.get("type", "rank" if "rank" in scene else "title")
        image = load_image(scene, image_dir)
        if kind == "rank":
            head = {"text": rank_yomi(scene, script)}
            if "name_speaker" in scene:
                head["speaker"] = scene["name_speaker"]
            items = [(lambda pop=1.0, s=scene, im=image: render_rank(s, 0, im, pop), head)]
            for i, box in enumerate(scene.get("boxes", [])):
                line = {**box, "text": box.get("yomi") or box["text"].replace("|", "")}
                items.append((lambda pop=1.0, s=scene, n=i + 1, im=image: render_rank(s, n, im, pop), line))
        else:
            narration = scene.get("narration") or ["".join(
                (l if isinstance(l, str) else l["text"]) for l in scene["lines"])]
            if isinstance(narration, (str, dict)):
                narration = [narration]
            if kind == "ending":
                render = lambda pop=1.0, s=scene: render_ending(s["lines"])
            else:
                render = lambda pop=1.0, s=scene, im=image: render_title(s["lines"], im, pop)
            items = [(render, n if isinstance(n, dict) else {"text": n}) for n in narration]
        for i, (render, line) in enumerate(items):
            yield {"render": render, "text": line["text"], "voice": voice_of(line, scene, script),
                   "last": i == len(items) - 1, "pop": i == 0 and kind != "ending"}


# ───────────── 動画を組み立てる ─────────────

def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg が見つかりません。")


def find_bgm(script):
    """BGM のファイル。台本の bgm にファイル名、なければ bgm/ の最初の1つ。bgm: none で無し。"""
    name = script.get("bgm")
    if name in ("none", False):
        return None
    if name:
        path = os.path.join(HERE, "bgm", name)
        if not os.path.exists(path):
            print(f"  ※ BGM が見つかりません: bgm/{name}")
            return None
        return path
    files = sorted(f for ext in ("mp3", "wav", "m4a", "ogg") for f in glob.glob(os.path.join(HERE, "bgm", "*." + ext)))
    return files[0] if files else None


def write_background(work, spin):
    """回る背景を連番画像にする。光線は同じ形のくり返しなので、1本ぶん回るところまで作ってループさせる。"""
    period = 360 / RAY_COUNT
    frames = 1 if not spin else max(1, round(FPS * period / abs(spin)))
    step = 0 if not spin else math.copysign(period / frames, spin)
    for i in range(frames):
        sunburst(i * step).convert("RGB").save(os.path.join(work, f"bg_{i:03d}.png"))
    return os.path.join(work, "bg_%03d.png")


def affiliate_link(link, script):
    """楽天の商品ページのURLを、自分のアフィリエイトリンクにする。

    台本の rakuten_affiliate_id（または環境変数 RAKUTEN_AFFILIATE_ID）がある時だけ。
    """
    aff = script.get("rakuten_affiliate_id") or os.environ.get("RAKUTEN_AFFILIATE_ID")
    if not (aff and link and link.startswith("https://item.rakuten.co.jp/")):
        return link
    q = urllib.parse.quote(link, safe="")
    return f"https://hb.afl.rakuten.co.jp/hgc/{aff}/?pc={q}&m={q}"


def write_caption(script, out_txt):
    lines = [script["title"], "", "※本動画はアフィリエイト広告（PR）を含みます", ""]
    ranked = sorted([s for s in script["scenes"] if s.get("rank")], key=lambda s: s["rank"])
    if ranked:
        lines.append("▼紹介した商品")
        for s in ranked:
            lines.append(f"{s['rank']}位 {s['name'].replace('|', '')}")
            lines.append(f"  {affiliate_link(s.get('link'), script) or '（リンクをここに貼る）'}")
        lines.append("")
    for key in ("credit", "bgm_credit"):
        if script.get(key):
            lines.append(script[key])
    if script.get("credit") or script.get("bgm_credit"):
        lines.append("")
    lines.append(" ".join(script.get("hashtags", [])))
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build(script_path, out_dir, cfg):
    with open(script_path, encoding="utf-8") as f:
        script = yaml.safe_load(f)
    name = os.path.splitext(os.path.basename(script_path))[0]
    image_dir = os.path.join(HERE, "images")
    tts = tts_voicevox if cfg["tts"] == "voicevox" else tts_silent

    os.makedirs(out_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix=f"{name}_")
    audio = bytearray()
    concat = []
    items = list(timeline(script, image_dir))
    speakers = []
    thumb = None
    for n, item in enumerate(items, 1):
        voice = {"speaker": cfg["speaker"], "speed": cfg["speed"], **item["voice"]}
        if voice["speaker"] not in speakers:
            speakers.append(voice["speaker"])
        print(f"  [{n}/{len(items)}] ({voice['speaker']}) {item['text']}", flush=True)
        pcm = tts(item["text"], {**cfg, **voice}) + silence(SCENE_GAP if item["last"] else LINE_GAP)
        audio += pcm
        seconds = len(pcm) / 2 / SAMPLE_RATE
        # 見出しは小さい→大きいと数コマ見せてから等倍にする（合計の長さは音声と同じ）
        steps = POP_STEPS if item["pop"] else []
        for k, (size, dur) in enumerate(steps + [(1.0, seconds - sum(d for _, d in steps))]):
            frame = os.path.join(work, f"{n:03d}_{k}.png")
            img = item["render"](size)
            if script.get("pr", True):
                draw_pr_badge(img)
            img.save(frame)
            concat.append((frame, dur))
        thumb = thumb or frame

    # クレジット: 使った声を全部書く
    if cfg["tts"] == "voicevox" and "credit" not in script:
        names = voicevox_names(cfg)
        default = {cfg["speaker"]: cfg["speaker_name"]}
        chars = []
        for sp in speakers:
            ch = names.get(sp) or default.get(sp) or f"話者{sp}"
            if ch not in chars:
                chars.append(ch)
        script["credit"] = "音声：" + "、".join(f"VOICEVOX:{c}" for c in chars)

    wav_path = os.path.join(work, "voice.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(audio))

    list_path = os.path.join(work, "frames.txt")
    with open(list_path, "w") as f:
        for frame, seconds in concat:
            f.write(f"file '{frame}'\nduration {seconds:.3f}\n")
        f.write(f"file '{concat[-1][0]}'\n")  # concat の仕様で最後のフレームをもう一度書く

    total = sum(s for _, s in concat)
    spin = script.get("spin", SPIN)
    bg_pattern = write_background(work, spin)

    # 入力: 0=文字や画像（透明）, 1=背景（ループ）, 2=声, 3=BGM
    out_mp4 = os.path.join(out_dir, f"{name}.mp4")
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", list_path,
           "-stream_loop", "-1", "-framerate", str(FPS), "-i", bg_pattern,
           "-i", wav_path]
    video = (f"[1:v]fps={FPS},format=rgba[bg];[0:v]fps={FPS},format=rgba[fg];"
             f"[bg][fg]overlay=format=auto,format=yuv420p[v]")
    bgm = find_bgm(script)
    if bgm:
        vol = script.get("bgm_volume", BGM_VOLUME)
        fade_in, fade_out = BGM_FADE
        cmd += ["-stream_loop", "-1", "-i", bgm]
        audio_f = (f";[3:a]volume={vol},afade=t=in:d={fade_in},"
                   f"afade=t=out:st={max(0, total - fade_out):.3f}:d={fade_out}[b];"
                   f"[2:a][b]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
        print(f"  BGM: {os.path.basename(bgm)}")
    else:
        audio_f = ";[2:a]anull[a]"
    cmd += ["-filter_complex", video + audio_f, "-map", "[v]", "-map", "[a]",
            "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out_mp4]
    subprocess.run(cmd, check=True)

    # サムネイル用にタイトル画面を書き出す（背景を敷く）
    cover = sunburst()
    cover.alpha_composite(Image.open(thumb))
    cover.convert("RGB").save(os.path.join(out_dir, f"{name}_thumb.png"))
    write_caption(script, os.path.join(out_dir, f"{name}.txt"))
    shutil.rmtree(work, ignore_errors=True)

    print(f"完成: {out_mp4}（{total:.1f}秒）")
    if total > 60:
        print("  ※60秒を超えています。TikTokは問題ありませんが、短い方が最後まで見られやすいです。")


def main():
    p = argparse.ArgumentParser(description="台本からショート動画を作る")
    p.add_argument("scripts", nargs="+", help="台本の YAML ファイル")
    p.add_argument("--out", default="out", help="出力フォルダ")
    p.add_argument("--tts", choices=["voicevox", "silent"], default="voicevox")
    p.add_argument("--voicevox-url", default=os.environ.get("VOICEVOX_URL", "http://localhost:50021"))
    p.add_argument("--speaker", type=int, default=int(os.environ.get("VOICEVOX_SPEAKER", 3)),
                   help="VOICEVOX の話者ID（3=ずんだもん）")
    p.add_argument("--speaker-name", default=os.environ.get("VOICEVOX_SPEAKER_NAME", "ずんだもん"),
                   help="概要欄のクレジットに書く名前")
    p.add_argument("--speed", type=float, default=1.15, help="読み上げ速度")
    a = p.parse_args()
    cfg = {"tts": a.tts, "voicevox_url": a.voicevox_url, "speaker": a.speaker,
           "speaker_name": a.speaker_name, "speed": a.speed}

    paths = [f for s in a.scripts for f in sorted(glob.glob(s))]
    if not paths:
        sys.exit("台本が見つかりません: " + " ".join(a.scripts))
    for path in paths:
        print(f"▶ {path}")
        build(path, a.out, cfg)


if __name__ == "__main__":
    main()
