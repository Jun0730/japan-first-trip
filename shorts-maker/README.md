# ショート動画メーカー

台本（YAML）を書くと、縦型ショート動画（1080×1920 / mp4）を自動で作る。
読み上げは VOICEVOX（ずんだもん）。YouTube ショートと TikTok の両方にそのまま使える。

## 動画の作り方（1クリック）

1. GitHub のリポジトリページで **Actions** タブを開く
2. 左の一覧から **ショート動画を作る** を選ぶ
3. **Run workflow** → 緑の **Run workflow** ボタンを押す
4. 数分待って、完了した実行を開き、下の **Artifacts** にある `shorts-videos` をダウンロード

台本・画像・BGM を GitHub 上で編集してコミットした時も、自動で動画が作られる。

ダウンロードした zip の中身:

| ファイル | 使い道 |
|---|---|
| `001_xxx.mp4` | 投稿する動画 |
| `001_xxx.txt` | 概要欄・キャプションにそのまま貼る文（PR表記・商品リンク・ハッシュタグ・クレジット入り） |
| `001_xxx_thumb.png` | サムネイル（タイトル画面） |

## 台本の書き方

`scripts/` に YAML ファイルを置く。見本は `scripts/001_switch2_accessories.yaml`。

画面は3種類（黄色とオレンジの放射状の背景。ゆっくり回る）:

| 種類 | 画面 | 書くこと |
|---|---|---|
| `type: title` | 大きなタイトル（ポンと出る）＋下にイラスト | `lines` に1行ずつ。`style` は `white`（白）/ `red`（赤）/ `yellow`（黄）。`size` で大きさ（例: `150`） |
| `rank: 数字` | 上に「番号＋名前」（ポンと出る）、説明の枠が1つずつ出て、下に画像 | `name`、`boxes`（枠の中は `\|` で改行）、`image`、`link` |
| `type: ending` | 最後の呼びかけ（全部同じ大きさの白文字） | `lines` と `narration` |

枠のルール:

- 枠の色は **青 → 紫 → 緑 → 赤** の順。変えたい時は枠に `color: blue` / `purple` / `green` / `red`
- 枠が画像の上まで増えたら、枠を消して上から並べ直す。区切りを自分で決めたい時は、新しい画面の最初の枠に `page: true`
- 名前が長い時は `name: バンジョーとカズーイの大冒険|ガレージ大作戦` のように `|` で見出しを2行にできる

- `title`: 投稿するときのタイトル（概要欄の文に入る）
- `yomi` / `name_yomi` / `narration`: 読み上げ用。読み間違える時だけ書けばよい
- `rank_yomi`: 見出しの読み方。ふつうは「5、キャリングケース」。ランキング風にしたい時は `rank_yomi: "第{n}位、{name}"`
- `image`: `images/` に置いた画像のファイル名、または画像のURL（なければ名前を大きく表示）
- `image_search`: 楽天市場で探すキーワード。一番上の商品の画像を自動で使う（下の「商品画像」参照）
- `link`: アフィリエイトリンク（概要欄の文に入る）
- `rakuten_affiliate_id`: 楽天アフィリエイトID。台本の最初に1回書くと、`link` に貼った楽天の商品ページ（`https://item.rakuten.co.jp/...`）が自動でアフィリエイトリンクになる
- `spin`: 背景が回る速さ（度/秒、ふつうは `10`）。`0` で止まる、マイナスで逆回り

## フォント

`fonts/` に入っているフォントを使う（どちらも SIL Open Font License で商用利用可）。

- `MPLUSRounded1c-Black.ttf`（M PLUS Rounded 1c Black）: タイトル・順位・最後の画面
- `NotoSansJP-Black.ttf`（Noto Sans JP Black）: 枠の中の文字

別のフォントにしたい時は、`fonts/display.ttf`（タイトル用）や `fonts/box.ttf`（枠用）という名前で置くと差し替わる。

## BGM

- `bgm/` に mp3（wav / m4a / ogg も可）を置くと、声の後ろで小さく流れる。動画より短い曲はくり返す
- 最初は0.5秒でフェードイン、最後は2秒でフェードアウトする
- 何曲か置いた時は台本に `bgm: ファイル名` で選ぶ（書かなければ名前順で最初の1曲）。`bgm: none` で無し
- 音量は `bgm_volume: 0.12`（大きくするなら 0.2 くらい）
- クレジット表記が必要な曲は `bgm_credit: "BGM：曲名 / 作者名"` と書くと概要欄の文に入る
- 使う曲は、商用利用・YouTube/TikTok での利用が許されているフリー音源にすること（DOVA-SYNDROME、甘茶の音楽工房など。サイトごとの規約を確認）

## 商品画像

画像の指定は3通り。上のものが優先される。

楽天の商品なら、楽天市場の商品ページの画像を右クリック →「画像アドレスをコピー」して `image:` に貼るのが手軽（楽天のアプリ登録はいらない）。
`https://thumbnail.image.rakuten.co.jp/@0_mall/お店/cabinet/...jpg?_ex=600x600` の形にすると大きい画像が取れる。

1. `image: case.jpg` … `images/` に置いた画像（自分で撮った写真など）
2. `image: https://...` … 画像のURL（使用が許されている画像だけ）
3. `image_search: Nintendo Switch 2 キャリングケース` … 楽天市場で検索して、一番上の商品の画像を使う。
   `link` が空なら、その商品のアフィリエイトリンクも概要欄に自動で入る

`image_search` を使うには楽天ウェブサービスの登録が必要（無料）:

1. https://webservice.rakuten.co.jp/ でアプリを登録し、**アプリID** と **アクセスキー** をもらう
   （2026年5月に新しいAPIに変わったので、それより前に登録したIDは使えない）
2. GitHub のリポジトリで **Settings → Secrets and variables → Actions → New repository secret** から登録:

| 名前 | 中身 |
|---|---|
| `RAKUTEN_APP_ID` | アプリID |
| `RAKUTEN_ACCESS_KEY` | アクセスキー |
| `RAKUTEN_AFFILIATE_ID` | 楽天アフィリエイトID（任意。あると link がアフィリエイトリンクになる） |
| `RAKUTEN_ORIGIN` | アプリ登録で入れたサイトのURL（任意。検索が 403 になる時に入れる） |

- 検索で出た商品名は Actions のログに出るので、違う商品になっていないか確認すること
- 楽天の画像は楽天の商品ページへのリンクと一緒に使うのが規約。`link` を別のお店にする時は `image_search` を使わないこと

## 声を変える

台本全体・シーンごと・枠ごとに `speaker: 番号` を書ける（例: 3=ずんだもん、2=四国めたん、13=青山龍星、11=玄野武宏）。
細かく書いた方が優先される（枠 → シーン → 台本全体）。`speed: 1.2` で読む速さも同じように変えられる。

```yaml
speaker: 3              # 台本全体はずんだもん
scenes:
  - rank: 5
    name: キャリングケース
    name_speaker: 13    # 見出しの読み上げだけ青山龍星
    boxes:
      - text: 本体が大きくなって|カバンの中でぶつけがち
      - text: 7.9インチの画面に|傷ついたら泣くで
        speaker: 2      # この枠だけ四国めたん
  - type: ending
    narration:
      - { text: みんなはどれ買った？, speaker: 2 }   # タイトル・締めは1行ずつ指定できる
```

使った声は全部、概要欄のクレジット（`音声：VOICEVOX:ずんだもん、VOICEVOX:四国めたん`）に自動で入る。
キャラクターごとに利用規約があるので確認すること。

## 手元のPCで作る場合

```bash
pip install -r shorts-maker/requirements.txt   # ffmpeg も別途インストール
# VOICEVOX アプリを起動しておく
python shorts-maker/make_video.py shorts-maker/scripts/001_switch2_accessories.yaml --out out
# 音声なしで見た目だけ確認
python shorts-maker/make_video.py shorts-maker/scripts/*.yaml --tts silent --out out
```
