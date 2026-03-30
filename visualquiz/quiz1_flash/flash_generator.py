"""漢字フラッシュクイズ動画ジェネレーター（書き順ストローク版）。

KanjiVGの書き順データをもとに1ストロークずつランダムに表示し、
だんだん文字が完成していくアニメーションMP4を生成する。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from visualquiz.common.font_manager import get_font_path
from visualquiz.common.video_exporter import frames_to_mp4, repeat_frame
from visualquiz.quiz1_flash.kanjivg import get_strokes
from visualquiz.quiz1_flash.stroke_renderer import (
    StrokeStyle,
    make_default_style,
    render_kanji_tile,
)


@dataclass
class FlashConfig:
    """フラッシュクイズの生成設定。"""
    width: int = 1280
    height: int = 720
    fps: int = 30

    # 色設定
    bg_color: tuple[int, int, int] = (13, 17, 23)          # 背景（ダークネイビー）
    tile_bg_color: tuple[int, int, int] = (248, 248, 244)  # 漢字タイル背景（オフホワイト）
    stroke_color: tuple[int, int, int] = (40, 40, 40)      # 確定ストローク色
    flash_color: tuple[int, int, int] = (220, 50, 50)      # フラッシュ色（赤）
    answer_color: tuple[int, int, int] = (218, 165, 32)    # 正解色（ゴールド）
    tile_border_color: tuple[int, int, int] = (180, 180, 180)

    # タイミング（秒）
    intro_duration: float = 0.8      # 最初の空白表示
    flash_duration: float = 0.35     # 新ストロークのフラッシュ表示時間
    hold_duration: float = 0.2       # フラッシュ後の静止時間
    answer_duration: float = 3.0     # 正解表示時間

    # レイアウト
    tile_gap: int = 30               # タイル間の余白（px）
    tile_padding: int = 60           # 上下左右の余白（px）
    label_size: int = 32             # ラベルフォントサイズ
    question_label: str = ""         # 問題番号ラベル（例："Q1"）


def generate_flash_quiz(
    word: str,
    output_path: Path | str,
    config: FlashConfig | None = None,
) -> Path:
    """漢字フラッシュクイズMP4を生成する。

    Args:
        word: クイズにする漢字熟語（1文字以上）
        output_path: 出力MP4ファイルパス
        config: 生成設定

    Returns:
        生成したMP4ファイルのPath
    """
    if config is None:
        config = FlashConfig()

    font_path = get_font_path()

    # 各文字のストロークデータを取得
    char_strokes: list[list[str]] = []
    for char in word:
        strokes = get_strokes(char)
        char_strokes.append(strokes)

    # ストロークが1つもない場合はフォールバック
    total_strokes = sum(len(s) for s in char_strokes)
    if total_strokes == 0:
        return _generate_fallback(word, output_path, config, font_path)

    # タイルサイズを計算
    tile_size = _calc_tile_size(len(word), config)

    # ランダムな表示順（char_idx, stroke_idx）を生成
    all_refs: list[tuple[int, int]] = []
    for ci, strokes in enumerate(char_strokes):
        for si in range(len(strokes)):
            all_refs.append((ci, si))
    random.shuffle(all_refs)

    # フレーム生成
    frames: list[np.ndarray] = []
    revealed: list[set[int]] = [set() for _ in range(len(word))]

    # 冒頭：全マスク状態
    blank = _render_frame(word, char_strokes, revealed, tile_size, config, font_path)
    frames.extend(repeat_frame(blank, config.intro_duration, config.fps))

    # ストロークを1本ずつランダムにフラッシュ
    for ci, si in all_refs:
        revealed[ci].add(si)

        # フラッシュフレーム（新ストロークを赤でハイライト）
        flash_frame = _render_frame(
            word, char_strokes, revealed, tile_size, config, font_path,
            highlight=(ci, si)
        )
        frames.extend(repeat_frame(flash_frame, config.flash_duration, config.fps))

        # 確定フレーム（通常色に戻す）
        normal_frame = _render_frame(
            word, char_strokes, revealed, tile_size, config, font_path
        )
        frames.extend(repeat_frame(normal_frame, config.hold_duration, config.fps))

    # 正解フレーム（全ストロークをゴールドで表示）
    answer_frame = _render_frame(
        word, char_strokes, revealed, tile_size, config, font_path,
        answer_mode=True
    )
    frames.extend(repeat_frame(answer_frame, config.answer_duration, config.fps))

    return frames_to_mp4(
        frames, output_path,
        fps=config.fps, width=config.width, height=config.height
    )


def _calc_tile_size(n_chars: int, config: FlashConfig) -> int:
    """文字数から最適なタイルサイズ（px）を計算する。"""
    available_w = config.width - config.tile_padding * 2 - config.tile_gap * (n_chars - 1)
    available_h = config.height - config.tile_padding * 2 - 60  # ラベル領域を除く
    size_by_w = available_w // n_chars
    return min(size_by_w, available_h)


def _render_frame(
    word: str,
    char_strokes: list[list[str]],
    revealed: list[set[int]],
    tile_size: int,
    config: FlashConfig,
    font_path: Path,
    highlight: tuple[int, int] | None = None,
    answer_mode: bool = False,
) -> np.ndarray:
    """1フレーム分の画像（numpy配列）を生成する。"""
    canvas = Image.new("RGB", (config.width, config.height), config.bg_color)
    draw = ImageDraw.Draw(canvas)

    n = len(word)
    total_w = tile_size * n + config.tile_gap * (n - 1)
    start_x = (config.width - total_w) // 2
    tile_y = (config.height - tile_size) // 2 + 20  # ラベル分だけ下にずらす

    base_style = make_default_style(tile_size, config.stroke_color)

    for ci, char in enumerate(word):
        x = start_x + ci * (tile_size + config.tile_gap)
        strokes = char_strokes[ci]
        visible = revealed[ci]

        # ストロークごとのスタイルを決定
        stroke_styles: dict[int, StrokeStyle] = {}
        for si in visible:
            if answer_mode:
                color = config.answer_color
            elif highlight and highlight == (ci, si):
                color = config.flash_color
            else:
                color = config.stroke_color
            stroke_styles[si] = StrokeStyle(
                color=color, width=base_style.width
            )

        tile_img = render_kanji_tile(
            strokes, visible, tile_size,
            stroke_styles=stroke_styles,
            bg_color=config.tile_bg_color,
            border_color=config.tile_border_color,
        )
        canvas.paste(tile_img, (x, tile_y))

    # 問題ラベル
    if config.question_label:
        _draw_label(draw, config.question_label, font_path, config.label_size,
                    (255, 255, 255), 30, 20)

    # 正解時：文字テキストをタイル下に表示
    if answer_mode:
        _draw_answer_text(draw, word, font_path, config, start_x, tile_y + tile_size + 16, tile_size)

    return np.array(canvas)


def _draw_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    size: int,
    color: tuple,
    x: int,
    y: int,
) -> None:
    font = _load_font(font_path, size)
    draw.text((x, y), text, font=font, fill=color)


def _draw_answer_text(
    draw: ImageDraw.ImageDraw,
    word: str,
    font_path: Path,
    config: FlashConfig,
    start_x: int,
    y: int,
    tile_size: int,
) -> None:
    """正解の読み仮名を各タイルの下に表示（文字のみ）。"""
    font = _load_font(font_path, 48)
    for ci, char in enumerate(word):
        cx = start_x + ci * (tile_size + config.tile_gap) + tile_size // 2
        bbox = draw.textbbox((0, 0), char, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, y), char, font=font, fill=config.answer_color)


def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        if font_path and font_path.exists():
            return ImageFont.truetype(str(font_path), size)
    except Exception:
        pass
    return ImageFont.load_default()


def _generate_fallback(
    word: str,
    output_path: Path | str,
    config: FlashConfig,
    font_path: Path,
) -> Path:
    """書き順データがない場合のフォールバック：文字をフェードイン表示。"""
    canvas = Image.new("RGB", (config.width, config.height), config.bg_color)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(font_path, 240)

    bbox = draw.textbbox((0, 0), word, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (config.width - tw) // 2
    y = (config.height - th) // 2

    frames = []
    n_steps = 20
    for step in range(n_steps + 1):
        alpha = int(255 * step / n_steps)
        frame_img = Image.new("RGB", (config.width, config.height), config.bg_color)
        overlay = Image.new("RGBA", (config.width, config.height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.text((x, y), word, font=font, fill=(*config.answer_color, alpha))
        frame_img = Image.alpha_composite(frame_img.convert("RGBA"), overlay).convert("RGB")
        frames.extend(repeat_frame(np.array(frame_img), 0.1, config.fps))

    frames.extend(repeat_frame(frames[-1], config.answer_duration, config.fps))

    return frames_to_mp4(
        frames, output_path,
        fps=config.fps, width=config.width, height=config.height
    )


def generate_flash_quiz_batch(
    words: list[str],
    output_dir: Path | str,
    config: FlashConfig | None = None,
) -> list[Path]:
    """複数の熟語をまとめてフラッシュクイズMP4に変換する。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i, word in enumerate(words, 1):
        cfg = config or FlashConfig()
        cfg.question_label = f"Q{i}"
        out = output_dir / f"flash_{i:03d}_{word}.mp4"
        print(f"[flash] ({i}/{len(words)}) {word} → {out.name}")
        results.append(generate_flash_quiz(word, out, cfg))
    return results
