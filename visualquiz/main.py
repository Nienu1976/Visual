"""visualquiz CLIエントリーポイント。"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from visualquiz import __version__


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """漢字ビジュアルクイズ自動生成ツール。

    \b
    使い方:
        visualquiz flash 桜花 -o output/flash.mp4
        visualquiz lyrics lyrics.txt -o output/lyrics.mp4
        visualquiz puzzle 日本語学習 -o output/puzzle.mp4
        visualquiz all -w 桜花 雷雨 日本 -l lyrics.txt -p 漢字 -o output/
    """
    pass


# ─────────────────────────────────────────────
# 機能①：フラッシュクイズ
# ─────────────────────────────────────────────
@cli.command("flash")
@click.argument("words", nargs=-1, required=True)
@click.option("-o", "--output", default="output/flash.mp4", show_default=True, help="出力MP4パス（複数ワードはディレクトリ指定）")
@click.option("--stages", default=8, show_default=True, help="マスク解除の段階数")
@click.option("--mode", default="random", show_default=True,
              type=click.Choice(["random", "scan_h", "scan_v", "radial"]),
              help="フラッシュのアニメーションモード")
@click.option("--font-size", default=280, show_default=True, help="文字サイズ（px）")
@click.option("--stage-duration", default=0.6, show_default=True, help="各段階の表示時間（秒）")
@click.option("--answer-duration", default=2.5, show_default=True, help="正解表示の時間（秒）")
@click.option("--pptx", is_flag=True, help="PPTXにも自動埋め込む")
def cmd_flash(
    words: tuple[str, ...],
    output: str,
    stages: int,
    mode: str,
    font_size: int,
    stage_duration: float,
    answer_duration: float,
    pptx: bool,
) -> None:
    """漢字フラッシュクイズMP4を生成する。

    \b
    例:
        visualquiz flash 桜花
        visualquiz flash 桜花 雷雨 日本 -o output/flash_quiz/
        visualquiz flash 桜花 --pptx
    """
    from visualquiz.quiz1_flash.flash_generator import (
        FlashConfig,
        FlashMode,
        generate_flash_quiz,
        generate_flash_quiz_batch,
    )

    config = FlashConfig(
        stages=stages,
        mode=FlashMode(mode),
        font_size=font_size,
        stage_duration=stage_duration,
        answer_duration=answer_duration,
    )

    output_path = Path(output)

    if len(words) == 1:
        out = output_path if output_path.suffix == ".mp4" else output_path / f"flash_{words[0]}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        result = generate_flash_quiz(words[0], out, config)
        click.echo(f"✓ 生成完了: {result}")
        mp4_files = [result]
    else:
        out_dir = output_path if not output_path.suffix else output_path.parent
        mp4_files = generate_flash_quiz_batch(list(words), out_dir, config)
        for f in mp4_files:
            click.echo(f"✓ 生成完了: {f}")

    if pptx:
        _embed_to_pptx(mp4_files, output_path, "flash")


# ─────────────────────────────────────────────
# 機能②：歌詞クイズ
# ─────────────────────────────────────────────
@cli.command("lyrics")
@click.argument("lyrics_file", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", default="output/lyrics.mp4", show_default=True, help="出力MP4パス")
@click.option("--mode", default="kanji_only", show_default=True,
              type=click.Choice(["kanji_only", "non_kanji"]),
              help="kanji_only=漢字のみ表示 / non_kanji=漢字以外のみ表示")
@click.option("--title", default="", help="タイトルスライドのテキスト")
@click.option("--font-size", default=52, show_default=True, help="歌詞の文字サイズ（px）")
@click.option("--page-duration", default=4.0, show_default=True, help="各ページの表示時間（秒）")
@click.option("--no-answer", is_flag=True, help="正解表示を省略する")
@click.option("--pptx", is_flag=True, help="PPTXにも自動埋め込む")
def cmd_lyrics(
    lyrics_file: Path,
    output: str,
    mode: str,
    title: str,
    font_size: int,
    page_duration: float,
    no_answer: bool,
    pptx: bool,
) -> None:
    """歌詞クイズMP4を生成する。

    \b
    例:
        visualquiz lyrics lyrics.txt
        visualquiz lyrics lyrics.txt --mode non_kanji --title "桜の歌"
        visualquiz lyrics lyrics.txt --no-answer
    """
    from visualquiz.quiz2_lyrics.lyrics_video import (
        LyricsConfig,
        LyricsMode,
        generate_lyrics_quiz_from_file,
    )

    config = LyricsConfig(
        mode=LyricsMode(mode),
        title=title,
        font_size=font_size,
        page_duration=page_duration,
        show_answer=not no_answer,
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = generate_lyrics_quiz_from_file(lyrics_file, output_path, config)
    click.echo(f"✓ 生成完了: {result}")

    if pptx:
        _embed_to_pptx([result], output_path, "lyrics")


# ─────────────────────────────────────────────
# 機能③：スライドパズル
# ─────────────────────────────────────────────
@cli.command("puzzle")
@click.argument("kanji_string")
@click.option("-o", "--output", default="output/puzzle.mp4", show_default=True, help="出力MP4パス")
@click.option("--shuffle-steps", default=80, show_default=True, help="シャッフル手数")
@click.option("--move-duration", default=0.25, show_default=True, help="1手の移動時間（秒）")
@click.option("--complete-duration", default=3.0, show_default=True, help="完成後の表示時間（秒）")
@click.option("--pptx", is_flag=True, help="PPTXにも自動埋め込む")
def cmd_puzzle(
    kanji_string: str,
    output: str,
    shuffle_steps: int,
    move_duration: float,
    complete_duration: float,
    pptx: bool,
) -> None:
    """漢字スライドパズルクイズMP4を生成する。

    \b
    例:
        visualquiz puzzle 日本語
        visualquiz puzzle 漢字学習 --shuffle-steps 50
        visualquiz puzzle 春夏秋冬 --pptx
    """
    from visualquiz.quiz3_puzzle.puzzle_video import PuzzleConfig, generate_puzzle_quiz

    config = PuzzleConfig(
        shuffle_steps=shuffle_steps,
        move_duration=move_duration,
        complete_duration=complete_duration,
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = generate_puzzle_quiz(kanji_string, output_path, config)
    click.echo(f"✓ 生成完了: {result}")

    if pptx:
        _embed_to_pptx([result], output_path, "puzzle")


# ─────────────────────────────────────────────
# まとめてPPTX生成
# ─────────────────────────────────────────────
@cli.command("pptx")
@click.argument("mp4_files", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", default="output/quiz.pptx", show_default=True, help="出力PPTXパス")
@click.option("--titles", multiple=True, help="スライドタイトル（MP4と同数指定）")
def cmd_pptx(
    mp4_files: tuple[Path, ...],
    output: str,
    titles: tuple[str, ...],
) -> None:
    """MP4ファイル群をPowerPointスライドに埋め込む。

    \b
    例:
        visualquiz pptx output/flash.mp4 output/puzzle.mp4 -o output/quiz.pptx
    """
    from visualquiz.common.pptx_builder import embed_videos_to_pptx

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    slide_titles = list(titles) if titles else None
    result = embed_videos_to_pptx(list(mp4_files), output_path, slide_titles)
    click.echo(f"✓ PPTX生成完了: {result}")


# ─────────────────────────────────────────────
# 一括生成コマンド
# ─────────────────────────────────────────────
@cli.command("all")
@click.option("-w", "--words", multiple=True, help="フラッシュクイズの熟語")
@click.option("-l", "--lyrics", type=click.Path(exists=True, path_type=Path), help="歌詞テキストファイル")
@click.option("-p", "--puzzle", "puzzle_str", default="", help="スライドパズルの漢字列")
@click.option("-o", "--output-dir", default="output", show_default=True, help="出力ディレクトリ")
@click.option("--pptx", is_flag=True, help="全MP4をPPTXにまとめる")
def cmd_all(
    words: tuple[str, ...],
    lyrics: Path | None,
    puzzle_str: str,
    output_dir: str,
    pptx: bool,
) -> None:
    """全クイズをまとめて生成する。

    \b
    例:
        visualquiz all -w 桜花 雷雨 -l lyrics.txt -p 春夏秋冬 --pptx
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_mp4s: list[Path] = []

    if words:
        from visualquiz.quiz1_flash.flash_generator import (
            FlashConfig,
            generate_flash_quiz_batch,
        )
        mp4s = generate_flash_quiz_batch(list(words), out_dir / "flash")
        all_mp4s.extend(mp4s)

    if lyrics:
        from visualquiz.quiz2_lyrics.lyrics_video import (
            LyricsConfig,
            generate_lyrics_quiz_from_file,
        )
        out = out_dir / "lyrics.mp4"
        mp4 = generate_lyrics_quiz_from_file(lyrics, out, LyricsConfig())
        all_mp4s.append(mp4)
        click.echo(f"✓ 歌詞クイズ: {mp4}")

    if puzzle_str:
        from visualquiz.quiz3_puzzle.puzzle_video import PuzzleConfig, generate_puzzle_quiz
        out = out_dir / f"puzzle_{puzzle_str}.mp4"
        mp4 = generate_puzzle_quiz(puzzle_str, out, PuzzleConfig())
        all_mp4s.append(mp4)
        click.echo(f"✓ パズル: {mp4}")

    if pptx and all_mp4s:
        from visualquiz.common.pptx_builder import embed_videos_to_pptx
        pptx_path = out_dir / "visualquiz.pptx"
        embed_videos_to_pptx(all_mp4s, pptx_path)
        click.echo(f"✓ PPTX: {pptx_path}")


# ─────────────────────────────────────────────
# サンプル生成（デモ用）
# ─────────────────────────────────────────────
@cli.command("demo")
@click.option("-o", "--output-dir", default="output/demo", show_default=True)
def cmd_demo(output_dir: str) -> None:
    """サンプルデータでデモ動画を生成する。"""
    from visualquiz.quiz1_flash.flash_generator import FlashConfig, generate_flash_quiz_batch
    from visualquiz.quiz2_lyrics.lyrics_video import LyricsConfig, generate_lyrics_quiz
    from visualquiz.quiz3_puzzle.puzzle_video import PuzzleConfig, generate_puzzle_quiz

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_mp4s: list[Path] = []

    # フラッシュクイズ
    demo_words = ["桜花", "雷雨", "日本", "漢字"]
    click.echo("--- 機能① フラッシュクイズ ---")
    mp4s = generate_flash_quiz_batch(demo_words, out_dir / "flash")
    all_mp4s.extend(mp4s)

    # 歌詞クイズ
    demo_lyrics = (
        "春の小川はさらさらいくよ\n"
        "岸のすみれやれんげの花に\n"
        "にほひめでたく色うつくしく\n"
        "咲けよ咲けよとささやきながら\n"
        "\n"
        "春の小川はさらさらいくよ\n"
        "えびやめだかや小鮒の群れに\n"
        "今日も一日ひなたでおよぎ\n"
        "遊べ遊べとささやきながら\n"
    )
    click.echo("--- 機能② 歌詞クイズ（漢字のみ） ---")
    lconfig = LyricsConfig(title="春の小川")
    mp4 = generate_lyrics_quiz(demo_lyrics, out_dir / "lyrics_kanji.mp4", lconfig)
    all_mp4s.append(mp4)
    click.echo(f"✓ {mp4}")

    click.echo("--- 機能② 歌詞クイズ（漢字以外のみ） ---")
    from visualquiz.quiz2_lyrics.lyrics_video import LyricsMode
    lconfig2 = LyricsConfig(title="春の小川", mode=LyricsMode.NON_KANJI_ONLY)
    mp4 = generate_lyrics_quiz(demo_lyrics, out_dir / "lyrics_non_kanji.mp4", lconfig2)
    all_mp4s.append(mp4)
    click.echo(f"✓ {mp4}")

    # スライドパズル
    click.echo("--- 機能③ スライドパズル ---")
    pconfig = PuzzleConfig(shuffle_steps=40)
    mp4 = generate_puzzle_quiz("春夏秋冬", out_dir / "puzzle.mp4", pconfig)
    all_mp4s.append(mp4)
    click.echo(f"✓ {mp4}")

    # PPTX生成
    from visualquiz.common.pptx_builder import embed_videos_to_pptx
    pptx_path = out_dir / "demo_quiz.pptx"
    embed_videos_to_pptx(all_mp4s, pptx_path)
    click.echo(f"\n✓ デモPPTX生成完了: {pptx_path}")


def _embed_to_pptx(mp4_files: list[Path], base_path: Path, prefix: str) -> None:
    """MP4ファイルをPPTXに埋め込むヘルパー。"""
    from visualquiz.common.pptx_builder import embed_videos_to_pptx
    pptx_path = base_path.parent / f"{prefix}_quiz.pptx"
    result = embed_videos_to_pptx(mp4_files, pptx_path)
    click.echo(f"✓ PPTX生成完了: {result}")


if __name__ == "__main__":
    cli()
