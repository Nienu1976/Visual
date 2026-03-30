"""歌詞クイズ動画ジェネレーター。

漢字のみ表示・漢字以外のみ表示の2モードで歌詞クイズMP4を生成する。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from visualquiz.common.font_manager import get_font_path
from visualquiz.common.video_exporter import frames_to_mp4, repeat_frame
from visualquiz.quiz2_lyrics.lyrics_parser import (
    mask_kanji,
    mask_non_kanji,
    split_lyrics_into_pages,
)


class LyricsMode(str, Enum):
    """歌詞クイズの表示モード。"""
    KANJI_ONLY = "kanji_only"       # 漢字のみ表示（他をマスク）
    NON_KANJI_ONLY = "non_kanji"    # 漢字以外のみ表示（漢字をマスク）


@dataclass
class LyricsConfig:
    """歌詞クイズの生成設定。"""
    width: int = 1280
    height: int = 720
    fps: int = 30
    bg_color: tuple[int, int, int] = (10, 10, 30)
    text_color: tuple[int, int, int] = (230, 230, 230)
    mask_color: tuple[int, int, int] = (80, 80, 120)
    answer_color: tuple[int, int, int] = (255, 215, 0)
    font_size: int = 52
    line_spacing: int = 20
    lines_per_page: int = 4
    page_duration: float = 4.0       # 各ページの表示時間（秒）
    transition_duration: float = 0.4 # ページ切り替えのフェード時間（秒）
    answer_duration: float = 3.0     # 正解（元の歌詞）表示時間（秒）
    show_answer: bool = True         # 各ページ後に正解表示するか
    mode: LyricsMode = LyricsMode.KANJI_ONLY
    title: str = ""


def generate_lyrics_quiz(
    lyrics: str,
    output_path: Path | str,
    config: LyricsConfig | None = None,
) -> Path:
    """歌詞クイズのMP4を生成する。

    Args:
        lyrics: 歌詞テキスト（改行区切り）。
        output_path: 出力MP4ファイルパス。
        config: 生成設定。

    Returns:
        生成したMP4ファイルのPath。
    """
    if config is None:
        config = LyricsConfig()

    font_path = get_font_path()
    renderer = _LyricsRenderer(config, font_path)
    pages = split_lyrics_into_pages(lyrics, config.lines_per_page)

    frames: list[np.ndarray] = []

    # タイトルスライド
    if config.title:
        title_frame = renderer.render_title(config.title)
        frames.extend(repeat_frame(title_frame, 2.0, config.fps))

    for page_lines in pages:
        original_text = "\n".join(page_lines)

        # マスク済みテキストを表示
        if config.mode == LyricsMode.KANJI_ONLY:
            masked_text = mask_non_kanji(original_text)
        else:
            masked_text = mask_kanji(original_text)

        quiz_frame = renderer.render_page(masked_text, is_answer=False)
        frames.extend(repeat_frame(quiz_frame, config.page_duration, config.fps))

        # フェードアウト → フェードイン（正解）
        if config.show_answer:
            answer_frame = renderer.render_page(original_text, is_answer=True)
            fade_frames = _crossfade(quiz_frame, answer_frame, config.transition_duration, config.fps)
            frames.extend(fade_frames)
            frames.extend(repeat_frame(answer_frame, config.answer_duration, config.fps))

    return frames_to_mp4(frames, output_path, fps=config.fps, width=config.width, height=config.height)


def _crossfade(
    frame_a: np.ndarray,
    frame_b: np.ndarray,
    duration: float,
    fps: int,
) -> list[np.ndarray]:
    """2フレーム間のクロスフェードを生成する。"""
    n = max(2, int(duration * fps))
    result = []
    for i in range(n):
        alpha = i / (n - 1)
        blended = (frame_a * (1 - alpha) + frame_b * alpha).astype(np.uint8)
        result.append(blended)
    return result


class _LyricsRenderer:
    """歌詞ページを画像として描画するクラス。"""

    def __init__(self, config: LyricsConfig, font_path: Path) -> None:
        self.config = config
        self.font_path = font_path
        self._font = self._load_font(config.font_size)
        self._small_font = self._load_font(28)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if self.font_path and self.font_path.exists():
                return ImageFont.truetype(str(self.font_path), size)
        except Exception:
            pass
        return ImageFont.load_default()

    def render_page(self, text: str, is_answer: bool = False) -> np.ndarray:
        """テキストを1ページとして描画する。"""
        cfg = self.config
        img = Image.new("RGB", (cfg.width, cfg.height), cfg.bg_color)
        draw = ImageDraw.Draw(img)

        lines = text.split("\n")
        line_height = cfg.font_size + cfg.line_spacing
        total_height = line_height * len(lines)
        start_y = (cfg.height - total_height) // 2

        for i, line in enumerate(lines):
            y = start_y + i * line_height
            bbox = draw.textbbox((0, 0), line, font=self._font)
            text_w = bbox[2] - bbox[0]
            x = (cfg.width - text_w) // 2

            if is_answer:
                color = cfg.answer_color
            else:
                # マスク文字は別色で描画
                self._draw_line_with_mask(draw, line, x, y, is_answer)
                continue

            draw.text((x, y), line, font=self._font, fill=color)

        # モード表示ラベル
        mode_label = "漢字のみ表示" if cfg.mode == "kanji_only" else "漢字以外のみ表示"
        if is_answer:
            mode_label = "正解"
        draw.text((20, 20), mode_label, font=self._small_font, fill=(150, 150, 200))

        return np.array(img)

    def _draw_line_with_mask(
        self, draw: ImageDraw.ImageDraw, line: str, x: int, y: int, is_answer: bool
    ) -> None:
        """行テキストを1文字ずつ描画（マスク文字は別色）。"""
        cfg = self.config
        cursor_x = x
        for ch in line:
            is_mask = ch in ("＿", "□")
            color = cfg.mask_color if is_mask else cfg.text_color
            draw.text((cursor_x, y), ch, font=self._font, fill=color)
            bbox = draw.textbbox((0, 0), ch, font=self._font)
            char_w = bbox[2] - bbox[0]
            cursor_x += char_w

    def render_title(self, title: str) -> np.ndarray:
        """タイトルスライドを描画する。"""
        cfg = self.config
        img = Image.new("RGB", (cfg.width, cfg.height), cfg.bg_color)
        draw = ImageDraw.Draw(img)
        title_font = self._load_font(72)
        bbox = draw.textbbox((0, 0), title, font=title_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (cfg.width - text_w) // 2
        y = (cfg.height - text_h) // 2
        draw.text((x, y), title, font=title_font, fill=cfg.answer_color)
        return np.array(img)


def generate_lyrics_quiz_from_file(
    lyrics_path: Path | str,
    output_path: Path | str,
    config: LyricsConfig | None = None,
) -> Path:
    """テキストファイルから歌詞クイズMP4を生成する。"""
    lyrics_path = Path(lyrics_path)
    lyrics = lyrics_path.read_text(encoding="utf-8")
    return generate_lyrics_quiz(lyrics, output_path, config)
