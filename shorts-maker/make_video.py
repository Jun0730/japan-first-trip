"""台本（YAML）から縦型ショート動画（1080x1920 / mp4）を作る。

使い方:
  python shorts-maker/make_video.py shorts-maker/scripts/001_switch2_accessories.yaml --out out
  python shorts-maker/make_video.py shorts-maker/scripts/*.yaml --tts silent   # 音声なしで見た目だけ確認

読み上げは VOICEVOX エンジン（http://localhost:50021）を使う。
GitHub Actions ではワークフローが自動で起動するので、何も準備しなくてよい。
"""

import argparse
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import wave

import yaml
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
FPS = 30
SAMPLE_RATE = 24000
LINE_GAP = 0.15   # 字幕と字幕の間の無音（秒）
SCENE_GAP = 0.35  # シーンとシーンの間の無音（秒）

# 色
BG_TOP = (14, 17, 38)
BG_BOTTOM = (38, 20, 70)
YELLOW = (255, 214, 10)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RANK_COLORS = {1: (230, 40, 60), 2: (140, 150, 170), 3: (205, 127, 50)}
RANK_DEFAULT = (60, 120, 230)

FONT_CANDIDATES = [
    os.environ.get("FONT_PATH", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if p and os.path.exists(p)), None)
if FONT_PATH is None:
    sys.exit("日本語フォントが見つかりません。環境変数 FONT_PATH にフォントのパスを指定してください。")

_font_cache = {}


def font(size):
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(FONT_PATH, size)
    return _font_cache[size]


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


def tts_silent(text, cfg):
    # 見た目の確認用。1文字あたり約0.12秒の無音を返す
    seconds = max(1.2, len(text) * 0.12 / cfg["speed"])
    return b"\x00\x00" * int(seconds * SAMPLE_RATE)


def silence(seconds):
    return b"\x00\x00" * int(seconds * SAMPLE_RATE)


# ───────────── 描画 ─────────────

NO_LINE_START = set("、。，．・！？!?）」』】ー～…ぁぃぅぇぉっゃゅょァィゥェォッャュョ")


def wrap(text, fnt, max_width):
    """日本語を1文字ずつ折り返す（行頭に句読点が来ないようにする）。"""
    lines, cur = [], ""
    for ch in text:
        if fnt.getlength(cur + ch) <= max_width or not cur:
            cur += ch
        elif ch in NO_LINE_START:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def fit_font(text, max_width, start, minimum, max_lines=1):
    size = start
    while size > minimum:
        if len(wrap(text, font(size), max_width)) <= max_lines:
            break
        size -= 4
    return font(size)


def draw_text_block(d, text, fnt, center_x, top, fill, stroke, stroke_width, max_width, line_gap=1.18):
    y = top
    for line in wrap(text, fnt, max_width):
        d.text((center_x, y), line, font=fnt, fill=fill, anchor="ma",
               stroke_width=stroke_width, stroke_fill=stroke)
        y += int(fnt.size * line_gap)
    return y


_background = None


def background():
    global _background
    if _background is None:
        img = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H
            c = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
            d.line([(0, y), (W, y)], fill=c)
        # うっすら斜めのライン模様
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for x in range(-H, W, 90):
            od.line([(x, H), (x + H, 0)], fill=(255, 255, 255, 14), width=3)
        _background = Image.alpha_composite(img, overlay)
    return _background.copy()


def draw_title(img, title):
    """タイトルを描く。【】の部分は黄色。「|」を入れた所で改行する。"""
    d = ImageDraw.Draw(img)
    if "】" in title:
        head, rest = title.split("】", 1)
        head += "】"
    else:
        head, rest = "", title
    y = 150
    if head:
        f = fit_font(head, 980, 84, 48)
        d.text((W // 2, y), head, font=f, fill=YELLOW, anchor="ma", stroke_width=8, stroke_fill=BLACK)
        y += int(f.size * 1.25)
    parts = [p for p in rest.split("|") if p]
    size = min(fit_font(p, 1000, 80, 52, max_lines=2 if len(parts) == 1 else 1).size for p in parts)
    for part in parts:
        y = draw_text_block(d, part, font(size), W // 2, y, WHITE, BLACK, 8, 1000)


def draw_pr_badge(img):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 50, 150, 110], radius=12, fill=(255, 255, 255, 235))
    d.text((95, 80), "PR", font=font(40), fill=(20, 20, 20), anchor="mm")


def draw_card(img, scene, image_dir):
    """中央のカード。画像があれば画像、なければ見出し＋一言。"""
    box = (70, 700, W - 70, 1230)
    d = ImageDraw.Draw(img)
    rank = scene.get("rank")

    # ランクと見出し（カードの上）
    if rank:
        color = RANK_COLORS.get(rank, RANK_DEFAULT)
        label = f"第{rank}位"
        f = font(92)
        tw = f.getlength(label)
        d.rounded_rectangle([W // 2 - tw / 2 - 40, 500, W // 2 + tw / 2 + 40, 630], radius=30, fill=color)
        d.text((W // 2, 565), label, font=f, fill=WHITE, anchor="mm", stroke_width=4, stroke_fill=BLACK)

    image_file = scene.get("image") or ""
    path = os.path.join(image_dir, image_file) if image_file else ""
    if path and os.path.exists(path):
        src = Image.open(path).convert("RGB")
        bw, bh = box[2] - box[0], box[3] - box[1]
        scale = min(bw / src.width, bh / src.height)
        src = src.resize((int(src.width * scale), int(src.height * scale)), Image.LANCZOS)
        d.rounded_rectangle(box, radius=36, fill=(255, 255, 255))
        img.paste(src, (box[0] + (bw - src.width) // 2, box[1] + (bh - src.height) // 2))
        # 画像の下に商品名
        f = fit_font(scene.get("heading", ""), 940, 56, 36)
        d.text((W // 2, box[3] + 20), scene.get("heading", ""), font=f, fill=WHITE, anchor="ma",
               stroke_width=6, stroke_fill=BLACK)
        return

    d.rounded_rectangle(box, radius=36, fill=(255, 255, 255, 240))
    heading = scene.get("heading", "")
    point = scene.get("point", "")
    hf = fit_font(heading, 880, 110, 56, max_lines=2)
    h_lines = wrap(heading, hf, 880)
    pf = fit_font(point, 860, 64, 40, max_lines=2) if point else None
    p_lines = wrap(point, pf, 860) if point else []
    content_h = len(h_lines) * int(hf.size * 1.18) + (30 + len(p_lines) * int(pf.size * 1.3) if point else 0)
    y = box[1] + (box[3] - box[1] - content_h) // 2
    y = draw_text_block(d, heading, hf, W // 2, y, (25, 25, 45), None, 0, 880)
    if point:
        y += 30
        # 黄色マーカー風の下線
        for line in p_lines:
            lw = pf.getlength(line)
            d.rectangle([W // 2 - lw / 2 - 10, y + pf.size * 0.62, W // 2 + lw / 2 + 10, y + pf.size * 1.12],
                        fill=YELLOW)
            d.text((W // 2, y), line, font=pf, fill=(200, 30, 50), anchor="ma")
            y += int(pf.size * 1.3)


def draw_subtitle(img, text):
    d = ImageDraw.Draw(img)
    f = fit_font(text, 980, 70, 54, max_lines=3)
    draw_text_block(d, text, f, W // 2, 1300, WHITE, BLACK, 10, 980, line_gap=1.22)


def render_frame(title, scene, line_text, image_dir):
    img = background()
    draw_pr_badge(img)
    draw_title(img, title)
    draw_card(img, scene, image_dir)
    draw_subtitle(img, line_text)
    return img.convert("RGB")


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
    name = script.get("bgm")
    if name:
        path = os.path.join(HERE, "bgm", name)
        return path if os.path.exists(path) else None
    files = sorted(glob.glob(os.path.join(HERE, "bgm", "*.mp3")) + glob.glob(os.path.join(HERE, "bgm", "*.wav")))
    return files[0] if files else None


def write_caption(script, out_txt):
    lines = [script["title"].replace("|", ""), "", "※本動画はアフィリエイト広告（PR）を含みます", ""]
    ranked = sorted([s for s in script["scenes"] if s.get("rank")], key=lambda s: s["rank"])
    if ranked:
        lines.append("▼紹介した商品")
        for s in ranked:
            lines.append(f"{s['rank']}位 {s['heading']}")
            lines.append(f"  {s.get('link') or '（リンクをここに貼る）'}")
        lines.append("")
    if script.get("credit"):
        lines += [script["credit"], ""]
    lines.append(" ".join(script.get("hashtags", [])))
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build(script_path, out_dir, cfg):
    with open(script_path, encoding="utf-8") as f:
        script = yaml.safe_load(f)
    name = os.path.splitext(os.path.basename(script_path))[0]
    image_dir = os.path.join(HERE, "images")
    tts = tts_voicevox if cfg["tts"] == "voicevox" else tts_silent
    cfg = {**cfg, "speaker": script.get("speaker", cfg["speaker"]), "speed": script.get("speed", cfg["speed"])}
    if cfg["tts"] == "voicevox" and "credit" not in script:
        script["credit"] = f"音声：VOICEVOX:{cfg['speaker_name']}"

    os.makedirs(out_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix=f"{name}_")
    audio = bytearray()
    concat = []
    thumb = None
    n = 0
    total_lines = sum(len(s["lines"]) for s in script["scenes"])
    for si, scene in enumerate(script["scenes"]):
        for li, line in enumerate(scene["lines"]):
            text = line["text"] if isinstance(line, dict) else str(line)
            yomi = (line.get("yomi") if isinstance(line, dict) else None) or text
            n += 1
            print(f"  [{n}/{total_lines}] {text}", flush=True)
            pcm = tts(yomi, cfg)
            last_in_scene = li == len(scene["lines"]) - 1
            pcm += silence(SCENE_GAP if last_in_scene else LINE_GAP)
            audio += pcm
            seconds = len(pcm) / 2 / SAMPLE_RATE
            frame = os.path.join(work, f"{n:03d}.png")
            render_frame(script["title"], scene, text, image_dir).save(frame)
            concat.append((frame, seconds))
            if scene.get("rank") == 1 and thumb is None:
                thumb = frame

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

    out_mp4 = os.path.join(out_dir, f"{name}.mp4")
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", list_path,
           "-i", wav_path]
    bgm = find_bgm(script)
    if bgm:
        vol = script.get("bgm_volume", 0.12)
        cmd += ["-stream_loop", "-1", "-i", bgm,
                "-filter_complex",
                f"[2:a]volume={vol}[b];[1:a][b]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out_mp4]
    subprocess.run(cmd, check=True)

    # サムネイル用に1位のシーン（なければ最初）の画像も書き出す
    shutil.copy(thumb or concat[0][0], os.path.join(out_dir, f"{name}_thumb.png"))
    write_caption(script, os.path.join(out_dir, f"{name}.txt"))
    shutil.rmtree(work, ignore_errors=True)

    total = sum(s for _, s in concat)
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
