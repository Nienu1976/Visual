"""ビジュアル漢字クイズ生成ツール - Gradio Webアプリ。

起動: python app.py
ブラウザで http://localhost:7860 が自動的に開きます。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import gradio as gr

# ── 出力先ディレクトリ（セッション間で共有） ──────────────────────────
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════
#  機能①：フラッシュクイズ
# ══════════════════════════════════════════════════════════════════

def run_flash(
    words_text: str,
    flash_duration: float,
    hold_duration: float,
    answer_duration: float,
    progress=gr.Progress(track_tqdm=True),
) -> tuple[str | None, str | None, str]:
    """フラッシュクイズMP4を生成して (動画パス, ダウンロードパス, ステータス) を返す。"""
    from visualquiz.quiz1_flash.flash_generator import FlashConfig, generate_flash_quiz_batch

    words = [w.strip() for w in words_text.splitlines() if w.strip()]
    if not words:
        return None, None, "❌ 熟語を1つ以上入力してください"

    progress(0, desc="KanjiVG書き順データを取得中...")
    out_dir = OUTPUT_DIR / "flash"
    config = FlashConfig(
        flash_duration=flash_duration,
        hold_duration=hold_duration,
        answer_duration=answer_duration,
    )

    try:
        mp4_files = []
        for i, word in enumerate(words):
            progress((i + 0.5) / len(words), desc=f"{word} を生成中...")
            cfg = FlashConfig(
                flash_duration=flash_duration,
                hold_duration=hold_duration,
                answer_duration=answer_duration,
                question_label=f"Q{i+1}" if len(words) > 1 else "",
            )
            from visualquiz.quiz1_flash.flash_generator import generate_flash_quiz
            out = out_dir / f"flash_{i+1:03d}_{word}.mp4"
            out.parent.mkdir(parents=True, exist_ok=True)
            generate_flash_quiz(word, out, cfg)
            mp4_files.append(out)
            progress((i + 1) / len(words), desc=f"{word} 完了")

        # 複数ある場合は連結
        if len(mp4_files) == 1:
            final_path = mp4_files[0]
        else:
            final_path = _concat_videos(mp4_files, out_dir / "flash_all.mp4")

        progress(1.0, desc="完了")
        return str(final_path), str(final_path), f"✅ 生成完了: {len(words)}問"

    except Exception as e:
        return None, None, f"❌ エラー: {e}"


# ══════════════════════════════════════════════════════════════════
#  機能②：歌詞クイズ
# ══════════════════════════════════════════════════════════════════

def run_lyrics(
    lyrics_text: str,
    lyrics_file,
    mode: str,
    title: str,
    page_duration: float,
    show_answer: bool,
    progress=gr.Progress(track_tqdm=True),
) -> tuple[str | None, str | None, str]:
    from visualquiz.quiz2_lyrics.lyrics_video import LyricsConfig, LyricsMode, generate_lyrics_quiz

    # ファイルアップロードを優先
    if lyrics_file is not None:
        lyrics = Path(lyrics_file).read_text(encoding="utf-8")
    else:
        lyrics = lyrics_text.strip()

    if not lyrics:
        return None, None, "❌ 歌詞を入力またはファイルをアップロードしてください"

    progress(0.2, desc="生成中...")
    config = LyricsConfig(
        mode=LyricsMode(mode),
        title=title,
        page_duration=page_duration,
        show_answer=show_answer,
    )

    mode_label = "kanji" if mode == "kanji_only" else "non_kanji"
    out = OUTPUT_DIR / f"lyrics_{mode_label}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        generate_lyrics_quiz(lyrics, out, config)
        progress(1.0, desc="完了")
        return str(out), str(out), "✅ 生成完了"
    except Exception as e:
        return None, None, f"❌ エラー: {e}"


# ══════════════════════════════════════════════════════════════════
#  機能③：スライドパズル
# ══════════════════════════════════════════════════════════════════

def run_puzzle(
    kanji_str: str,
    shuffle_steps: int,
    move_duration: float,
    complete_duration: float,
    progress=gr.Progress(track_tqdm=True),
) -> tuple[str | None, str | None, str]:
    from visualquiz.quiz3_puzzle.puzzle_video import PuzzleConfig, generate_puzzle_quiz

    kanji_str = kanji_str.strip()
    if not kanji_str:
        return None, None, "❌ 漢字文字列を入力してください"
    if len(kanji_str) < 2:
        return None, None, "❌ 2文字以上入力してください（空きスペース用に1マス必要）"

    progress(0.1, desc="パズルを生成中...")
    config = PuzzleConfig(
        shuffle_steps=shuffle_steps,
        move_duration=move_duration,
        complete_duration=complete_duration,
    )
    out = OUTPUT_DIR / f"puzzle_{kanji_str}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        progress(0.3, desc="A*で解法を計算中...")
        generate_puzzle_quiz(kanji_str, out, config)
        progress(1.0, desc="完了")
        return str(out), str(out), f"✅ 生成完了: {len(kanji_str)}文字パズル"
    except Exception as e:
        return None, None, f"❌ エラー: {e}"


# ══════════════════════════════════════════════════════════════════
#  PPTX 生成
# ══════════════════════════════════════════════════════════════════

def run_pptx(
    flash_video: str | None,
    lyrics_video: str | None,
    puzzle_video: str | None,
    progress=gr.Progress(track_tqdm=True),
) -> tuple[str | None, str]:
    from visualquiz.common.pptx_builder import embed_videos_to_pptx

    mp4s = [p for p in [flash_video, lyrics_video, puzzle_video] if p and Path(p).exists()]
    if not mp4s:
        return None, "❌ 先に各クイズを生成してください"

    progress(0.5, desc="PowerPointを生成中...")
    out = OUTPUT_DIR / "visualquiz.pptx"
    try:
        embed_videos_to_pptx([Path(p) for p in mp4s], out)
        progress(1.0, desc="完了")
        return str(out), f"✅ PPTX生成完了 ({len(mp4s)}スライド)"
    except Exception as e:
        return None, f"❌ エラー: {e}"


# ══════════════════════════════════════════════════════════════════
#  ユーティリティ
# ══════════════════════════════════════════════════════════════════

def _concat_videos(paths: list[Path], output: Path) -> Path:
    """複数MP4を1本に連結する。"""
    try:
        from moviepy import VideoFileClip, concatenate_videoclips
    except ImportError:
        from moviepy.editor import VideoFileClip, concatenate_videoclips

    clips = [VideoFileClip(str(p)) for p in paths]
    final = concatenate_videoclips(clips)
    output.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(output), codec="libx264", audio=False,
                          logger=None, ffmpeg_params=["-pix_fmt", "yuv420p"])
    for c in clips:
        c.close()
    final.close()
    return output


# ══════════════════════════════════════════════════════════════════
#  Gradio UI 定義
# ══════════════════════════════════════════════════════════════════

_CSS = """
#title { text-align: center; margin-bottom: 8px; }
.status-ok  { color: #4ade80; font-weight: bold; }
.status-err { color: #f87171; font-weight: bold; }
.generate-btn { min-width: 160px; }
"""

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="blue",
        neutral_hue="slate",
    ),
    title="ビジュアル漢字クイズ",
    css=_CSS,
) as demo:

    # ─── タイトル ───────────────────────────────────────────────
    gr.Markdown("# 🎴 ビジュアル漢字クイズ生成ツール", elem_id="title")
    gr.Markdown(
        "書き順ストローク・歌詞マスク・スライドパズルの3種類のクイズ動画を自動生成します。",
        elem_id="title"
    )

    # ─── 生成済みファイルのパス（タブ間で共有する State） ────────
    flash_mp4_state = gr.State(None)
    lyrics_mp4_state = gr.State(None)
    puzzle_mp4_state = gr.State(None)

    with gr.Tabs():

        # ══ タブ①：フラッシュクイズ ══════════════════════════════
        with gr.TabItem("① フラッシュクイズ（書き順）"):
            gr.Markdown(
                "### 書き順ストロークをランダムにフラッシュ → だんだん文字が完成するクイズ\n"
                "KanjiVG（CC BY-SA 3.0）の書き順データを使用します。初回はダウンロードが発生します。"
            )
            with gr.Row():
                with gr.Column(scale=1, min_width=280):
                    flash_input = gr.Textbox(
                        label="熟語（1行1単語）",
                        placeholder="桜花\n雷雨\n日本語",
                        lines=5,
                    )
                    with gr.Accordion("⚙️ 詳細設定", open=False):
                        flash_duration_sl = gr.Slider(
                            0.1, 1.0, value=0.35, step=0.05,
                            label="フラッシュ時間（秒）"
                        )
                        hold_duration_sl = gr.Slider(
                            0.05, 0.5, value=0.2, step=0.05,
                            label="確定後の静止時間（秒）"
                        )
                        answer_duration_sl = gr.Slider(
                            1.0, 6.0, value=3.0, step=0.5,
                            label="正解表示時間（秒）"
                        )
                    flash_btn = gr.Button("🎬 生成", variant="primary", elem_classes="generate-btn")
                    flash_status = gr.Textbox(label="ステータス", interactive=False, lines=1)

                with gr.Column(scale=2):
                    flash_video_out = gr.Video(label="プレビュー", height=400)
                    flash_dl = gr.File(label="📥 MP4ダウンロード")

            flash_btn.click(
                run_flash,
                inputs=[flash_input, flash_duration_sl, hold_duration_sl, answer_duration_sl],
                outputs=[flash_video_out, flash_dl, flash_status],
            ).then(
                lambda v: v,
                inputs=[flash_dl],
                outputs=[flash_mp4_state],
            )

        # ══ タブ②：歌詞クイズ ════════════════════════════════════
        with gr.TabItem("② 歌詞クイズ"):
            gr.Markdown(
                "### 歌詞の「漢字のみ」または「漢字以外のみ」を表示してクイズ化\n"
                "空行で段落（＝ページ）を区切ります。"
            )
            with gr.Row():
                with gr.Column(scale=1, min_width=300):
                    lyrics_file_in = gr.File(
                        label="📄 歌詞ファイル（UTF-8テキスト）",
                        file_types=[".txt"],
                    )
                    lyrics_text_in = gr.Textbox(
                        label="または直接入力",
                        placeholder="春の小川はさらさらいくよ\n岸のすみれやれんげの花に\n\n（空行でページ区切り）",
                        lines=8,
                    )
                    lyrics_mode = gr.Radio(
                        choices=[("漢字のみ表示", "kanji_only"), ("漢字以外のみ表示", "non_kanji")],
                        value="kanji_only",
                        label="表示モード",
                    )
                    lyrics_title = gr.Textbox(label="タイトル（省略可）", placeholder="春の小川")
                    with gr.Accordion("⚙️ 詳細設定", open=False):
                        page_duration_sl = gr.Slider(
                            1.0, 10.0, value=4.0, step=0.5,
                            label="1ページの表示時間（秒）"
                        )
                        show_answer_cb = gr.Checkbox(value=True, label="各ページ後に正解を表示する")
                    lyrics_btn = gr.Button("🎬 生成", variant="primary", elem_classes="generate-btn")
                    lyrics_status = gr.Textbox(label="ステータス", interactive=False, lines=1)

                with gr.Column(scale=2):
                    lyrics_video_out = gr.Video(label="プレビュー", height=400)
                    lyrics_dl = gr.File(label="📥 MP4ダウンロード")

            lyrics_btn.click(
                run_lyrics,
                inputs=[lyrics_text_in, lyrics_file_in, lyrics_mode, lyrics_title,
                        page_duration_sl, show_answer_cb],
                outputs=[lyrics_video_out, lyrics_dl, lyrics_status],
            ).then(
                lambda v: v,
                inputs=[lyrics_dl],
                outputs=[lyrics_mp4_state],
            )

        # ══ タブ③：スライドパズル ════════════════════════════════
        with gr.TabItem("③ スライドパズル"):
            gr.Markdown(
                "### 漢字1文字ずつのスライドパズルをA*最短手数で自動解答\n"
                "入力した文字数＋1マス（空きスペース）のグリッドが自動生成されます。"
            )
            with gr.Row():
                with gr.Column(scale=1, min_width=280):
                    puzzle_input = gr.Textbox(
                        label="漢字文字列",
                        placeholder="春夏秋冬（4文字 → 5マス）",
                        max_lines=1,
                    )
                    gr.Markdown(
                        "- 3文字 → 2×2グリッド\n"
                        "- 4〜8文字 → 3×3グリッド等\n"
                        "- 文字数が多いほど解法探索に時間がかかります"
                    )
                    with gr.Accordion("⚙️ 詳細設定", open=False):
                        shuffle_sl = gr.Slider(
                            10, 150, value=80, step=10,
                            label="シャッフル手数（大きいほど難しい）"
                        )
                        move_dur_sl = gr.Slider(
                            0.1, 0.6, value=0.25, step=0.05,
                            label="タイル移動アニメーション時間（秒）"
                        )
                        complete_dur_sl = gr.Slider(
                            1.0, 6.0, value=3.0, step=0.5,
                            label="完成後の表示時間（秒）"
                        )
                    puzzle_btn = gr.Button("🎬 生成", variant="primary", elem_classes="generate-btn")
                    puzzle_status = gr.Textbox(label="ステータス", interactive=False, lines=1)

                with gr.Column(scale=2):
                    puzzle_video_out = gr.Video(label="プレビュー", height=400)
                    puzzle_dl = gr.File(label="📥 MP4ダウンロード")

            puzzle_btn.click(
                run_puzzle,
                inputs=[puzzle_input, shuffle_sl, move_dur_sl, complete_dur_sl],
                outputs=[puzzle_video_out, puzzle_dl, puzzle_status],
            ).then(
                lambda v: v,
                inputs=[puzzle_dl],
                outputs=[puzzle_mp4_state],
            )

        # ══ タブ④：PowerPoint出力 ════════════════════════════════
        with gr.TabItem("📊 PowerPoint 出力"):
            gr.Markdown(
                "### 生成した動画をPowerPointスライドにまとめる\n"
                "各タブで動画を生成してから実行してください。"
            )
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**含めるスライド（生成済みのものが自動で選ばれます）**")
                    pptx_btn = gr.Button("📊 PowerPoint生成", variant="primary", size="lg")
                    pptx_status = gr.Textbox(label="ステータス", interactive=False, lines=1)
                with gr.Column():
                    pptx_dl = gr.File(label="📥 PPTXダウンロード")

            pptx_btn.click(
                run_pptx,
                inputs=[flash_mp4_state, lyrics_mp4_state, puzzle_mp4_state],
                outputs=[pptx_dl, pptx_status],
            )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        open_browser=True,
        show_error=True,
    )
