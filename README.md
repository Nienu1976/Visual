# visualquiz

漢字ビジュアルクイズ自動生成ツール

[![CI](https://github.com/YOUR_USERNAME/visualquiz/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/visualquiz/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 概要

漢字をテーマにした3種類のビジュアルクイズを **MP4動画** として自動生成します。
生成した動画はそのまま **PowerPoint (.pptx)** に埋め込めます。

| 機能 | 説明 |
|------|------|
| ① フラッシュクイズ | 漢字熟語を部分的にフラッシュしながら段階的に表示 |
| ② 歌詞クイズ | 歌詞の漢字のみ／漢字以外のみを表示してクイズ化 |
| ③ スライドパズル | 漢字1文字ずつのスライドパズルをA*で自動解答アニメーション |

---

## インストール

### 前提条件

- Python 3.10 以上
- ffmpeg（動画エンコードに必要）

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows（管理者権限のPowerShell）
choco install ffmpeg
```

### pip インストール

```bash
pip install visualquiz
```

### ソースからインストール

```bash
git clone https://github.com/YOUR_USERNAME/visualquiz.git
cd visualquiz
pip install -e .
```

---

## 使い方

### 機能① フラッシュクイズ

```bash
# 1つの熟語
visualquiz flash 桜花

# 複数まとめて
visualquiz flash 桜花 雷雨 日本 漢字 -o output/flash_quiz/

# PowerPointにも自動埋め込み
visualquiz flash 春夏秋冬 --pptx

# アニメーションモード指定（random/scan_h/scan_v/radial）
visualquiz flash 日本語 --mode scan_h --stages 10
```

### 機能② 歌詞クイズ

```bash
# 漢字のみ表示（デフォルト）
visualquiz lyrics assets/samples/sample_lyrics.txt

# 漢字以外のみ表示
visualquiz lyrics lyrics.txt --mode non_kanji

# タイトル付き・正解なし
visualquiz lyrics lyrics.txt --title "春の小川" --no-answer

# PowerPointに埋め込み
visualquiz lyrics lyrics.txt --pptx
```

歌詞ファイル形式（UTF-8テキスト）:
```
春の小川はさらさらいくよ
岸のすみれやれんげの花に

春の小川はさらさらいくよ
```
（空行が段落区切り = ページ区切りになります）

### 機能③ スライドパズル

```bash
# 漢字列を入力（文字数+1マスのグリッドが自動生成）
visualquiz puzzle 日本語

# シャッフル手数・完成表示時間を調整
visualquiz puzzle 春夏秋冬 --shuffle-steps 50 --complete-duration 5

# PowerPointに埋め込み
visualquiz puzzle 漢字学習 --pptx
```

### 一括生成

```bash
# 全機能をまとめて生成してPPTXにまとめる
visualquiz all \
  -w 桜花 雷雨 日本 \
  -l assets/samples/sample_lyrics.txt \
  -p 春夏秋冬 \
  --pptx \
  -o output/
```

### MP4 → PPTX 変換

```bash
visualquiz pptx output/flash.mp4 output/puzzle.mp4 -o output/quiz.pptx
```

### デモ生成

```bash
visualquiz demo
# output/demo/ に各クイズのサンプルMP4とPPTXが生成されます
```

---

## オプション一覧

### `visualquiz flash`

| オプション | デフォルト | 説明 |
|---|---|---|
| `--stages` | 8 | マスク解除の段階数 |
| `--mode` | random | アニメーションモード（random/scan_h/scan_v/radial） |
| `--font-size` | 280 | 文字サイズ（px） |
| `--stage-duration` | 0.6 | 各段階の表示時間（秒） |
| `--answer-duration` | 2.5 | 正解表示の時間（秒） |
| `--pptx` | False | PPTXにも自動埋め込み |

### `visualquiz lyrics`

| オプション | デフォルト | 説明 |
|---|---|---|
| `--mode` | kanji_only | kanji_only / non_kanji |
| `--title` | "" | タイトルスライドのテキスト |
| `--font-size` | 52 | 文字サイズ（px） |
| `--page-duration` | 4.0 | 各ページの表示時間（秒） |
| `--no-answer` | False | 正解表示を省略 |

### `visualquiz puzzle`

| オプション | デフォルト | 説明 |
|---|---|---|
| `--shuffle-steps` | 80 | シャッフル手数 |
| `--move-duration` | 0.25 | 1手の移動アニメーション時間（秒） |
| `--complete-duration` | 3.0 | 完成後の表示時間（秒） |

---

## フォントについて

初回実行時に自動でシステムフォントを探索します。
見つからない場合は `assets/fonts/` に漢字対応フォント（NotoSerifCJK等）を配置してください。

```bash
# Noto Serif CJK を手動で配置する場合
cp /path/to/NotoSerifCJKjp-Regular.otf assets/fonts/
```

---

## 開発

```bash
# 開発依存のインストール
pip install -e ".[dev]"

# テスト実行
pytest

# Linting
ruff check visualquiz/ tests/
```

---

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照。
