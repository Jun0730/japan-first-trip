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

画面は3種類（黄色とオレンジの放射状の背景）:

| 種類 | 画面 | 書くこと |
|---|---|---|
| `type: title` | 大きなタイトル | `lines` に1行ずつ。`style` は `white`（白）/ `red`（赤）/ `yellow`（黄） |
| `rank: 数字` | 上に「順位＋名前」、青枠→紫枠の順に説明が出て、下に画像 | `name`、`boxes`（枠の中は `|` で改行）、`image`、`link` |
| `type: ending` | 最後の呼びかけ | `lines` と `narration` |

- `title`: 投稿するときのタイトル（概要欄の文に入る）
- `yomi` / `name_yomi` / `narration`: 読み上げ用。読み間違える時だけ書けばよい
- `image`: `images/` に置いた画像のファイル名（なければ名前を大きく表示）
- `link`: アフィリエイトリンク（概要欄の文に入る）

## フォント

`fonts/` に入っているフォントを使う（どちらも SIL Open Font License で商用利用可）。

- `MPLUSRounded1c-Black.ttf`（M PLUS Rounded 1c Black）: タイトル・順位・最後の画面
- `NotoSansJP-Black.ttf`（Noto Sans JP Black）: 枠の中の文字

別のフォントにしたい時は、`fonts/display.ttf`（タイトル用）や `fonts/box.ttf`（枠用）という名前で置くと差し替わる。

## BGM・画像

- `bgm/` に mp3 を1つ置くと、小さい音量で自動で流れる（`bgm_volume: 0.12` で調整可）
- `images/` に商品画像を置き、台本の `image:` にファイル名を書く
- 画像は **自分で撮った写真** か、アフィリエイトの規約で使用が許されている商品画像を使うこと

## 声を変える

台本に `speaker: 番号` を書く（例: 3=ずんだもん、2=四国めたん、13=青山龍星、11=玄野武宏）。
キャラクターごとに利用規約があるので確認すること。クレジットは概要欄の文に自動で入る
（ずんだもん以外を使う時は台本に `credit: 音声：VOICEVOX:キャラ名` を書く）。

## 手元のPCで作る場合

```bash
pip install -r shorts-maker/requirements.txt   # ffmpeg も別途インストール
# VOICEVOX アプリを起動しておく
python shorts-maker/make_video.py shorts-maker/scripts/001_switch2_accessories.yaml --out out
# 音声なしで見た目だけ確認
python shorts-maker/make_video.py shorts-maker/scripts/*.yaml --tts silent --out out
```
