"""漢字フラッシュクイズ動画ジェネレーター。

2文字熟語を部分的にマスクした状態から、段階的にマスクを解除して
最終的に全文字を表示するアニメーションMP4を生成する。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from visualquiz.common.font_manager import get_font_path
from visualquiz.common.video_exporter import blank_frame, frames_to_mp4, repeat_frame


class FlashMode(str, Enum):
    """マスク解除のアニメーションモード。"""
    RANDOM_BLOCKS = "random"      # ランダムブロック単位で解除
    SCAN_HORIZONTAL = "scan_h"    # 横スキャンライン
    SCAN_VERTICAL = "scan_v"      # 縦スキャンライン
    RADIAL = "radial"             # 中心から外側へ拡張


@dataclass
class FlashConfig:
    """フラッシュクイズの生成設定。"""
    width: int = 1280
    height: int = 720
    fps: int = 30
    bg_color: tuple[int, int, int] = (20, 20, 20)
    text_color: tuple[int, int, int] = (255, 255, 255)
    mask_color: tuple[int, int, int] = (20, 20, 20)
    answer_color: tuple[int, int, int] = (255, 215, 0)   # ゴールドで正解表示
    font_size: int = 280
    block_size: int = 20          # ランダムブロックモードの1ブロックのpxサイズ
    stages: int = 8               # 何段階でマスクを解除するか
    stage_duration: float = 0.6   # 各段階の表示時間（秒）
    flash_duration: float = 0.08  # フラッシュ（一瞬見せる）時間（秒）
    answer_duration: float = 2.5  # 正解表示の時間（秒）
    mode: FlashMode = FlashMode.RANDOM_BLOCKS
    question_label: str = ""      # 問題番号などのラベル


def generate_flash_quiz(
    word: str,
    output_path: Path | str,
    config: FlashConfig | None = None,
) -> Path:
    """漢字フラッシュクイズのMP4を生成する。

    Args:
        word: クイズにする漢字熟語（2文字以上可）。
        output_path: 出力MP4ファイルパス。
        config: 生成設定。省略時はデフォルト値を使用。

    Returns:
        生成したMP4ファイルのPath。
    """
    if config is None:
        config = FlashConfig()

    font_path = get_font_path()
    renderer = _KanjiRenderer(word, config, font_path)

    frames: list[np.ndarray] = []

    # ---- マスク生成 ----
    mask_schedule = _build_mask_schedule(renderer, config)

    # ---- 各ステージのフレームを生成 ----
    for stage_idx, reveal_ratio in enumerate(mask_schedule):
        # フラッシュフレーム（マスク解除後の状態を一瞬見せる）
        flash_frame = renderer.render(reveal_ratio=reveal_ratio)
        frames.extend(repeat_frame(flash_frame, config.flash_duration, config.fps))

        # 通常表示フレーム（マスクが少し戻る = 1段階前の状態）
        prev_ratio = mask_schedule[stage_idx - 1] if stage_idx > 0 else 0.0
        hold_frame = renderer.render(reveal_ratio=prev_ratio)
        frames.extend(repeat_frame(hold_frame, config.stage_duration, config.fps))

    # ---- 最終ステージ：完全表示 ----
    full_frame = renderer.render(reveal_ratio=1.0, answer_mode=True)
    frames.extend(repeat_frame(full_frame, config.answer_duration, config.fps))

    return frames_to_mp4(frames, output_path, fps=config.fps, width=config.width, height=config.height)


def _build_mask_schedule(renderer: "_KanjiRenderer", config: FlashConfig) -> list[float]:
    """各ステージで何割のマスクを解除するかのスケジュールを返す。"""
    # 0 → 1.0 を stages 段階で均等に分割（最後は1.0）
    step = 1.0 / config.stages
    return [round(step * (i + 1), 4) for i in range(config.stages)]


class _KanjiRenderer:
    """漢字テキストをマスク付きで描画するクラス。"""

    def __init__(
        self,
        word: str,
        config: FlashConfig,
        font_path: Path,
    ) -> None:
        self.word = word
        self.config = config
        self.font_path = font_path
        self._font = self._load_font()
        self._base_image = self._render_base()
        self._mask_positions = self._build_mask_positions()

    def _load_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if self.font_path and self.font_path.exists():
                return ImageFont.truetype(str(self.font_path), self.config.font_size)
        except Exception:
            pass
        return ImageFont.load_default()

    def _render_base(self) -> Image.Image:
        """マスクなしの素の文字画像を生成する。"""
        img = Image.new("RGB", (self.config.width, self.config.height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), self.word, font=self._font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (self.config.width - text_w) // 2
        y = (self.config.height - text_h) // 2
        draw.text((x, y), self.word, font=self._font, fill=self.config.text_color)
        return img

    def _build_mask_positions(self) -> list[tuple[int, int]]:
        """マスクするブロック座標リストをシャッフルして返す。"""
        cfg = self.config
        positions = []
        for y in range(0, cfg.height, cfg.block_size):
            for x in range(0, cfg.width, cfg.block_size):
                positions.append((x, y))
        random.shuffle(positions)
        return positions

    def render(
        self,
        reveal_ratio: float = 0.0,
        answer_mode: bool = False,
    ) -> np.ndarray:
        """マスク状態を指定してフレームを描画する。

        Args:
            reveal_ratio: 0.0=完全マスク, 1.0=全て表示。
            answer_mode: Trueなら正解色で全文字を表示。

        Returns:
            shape (H, W, 3) のuint8 numpy配列。
        """
        img = self._base_image.copy()

        if answer_mode:
            # 正解色で再描画
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), self.word, font=self._font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (self.config.width - text_w) // 2
            y = (self.config.height - text_h) // 2
            draw.text((x, y), self.word, font=self._font, fill=self.config.answer_color)
            if self.config.question_label:
                label_font = self._load_label_font()
                draw.text((40, 30), self.config.question_label, font=label_font, fill=(180, 180, 180))
            return np.array(img)

        # マスク描画
        reveal_count = int(len(self._mask_positions) * reveal_ratio)
        revealed_set = set(self._mask_positions[:reveal_count])
        draw = ImageDraw.Draw(img)
        for (x, y) in self._mask_positions:
            if (x, y) not in revealed_set:
                draw.rectangle(
                    [x, y, x + self.config.block_size - 1, y + self.config.block_size - 1],
                    fill=self.config.mask_color,
                )

        if self.config.question_label:
            label_font = self._load_label_font()
            draw.text((40, 30), self.config.question_label, font=label_font, fill=(180, 180, 180))

        return np.array(img)

    def _load_label_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if self.font_path and self.font_path.exists():
                return ImageFont.truetype(str(self.font_path), 36)
        except Exception:
            pass
        return ImageFont.load_default()


def generate_flash_quiz_batch(
    words: list[str],
    output_dir: Path | str,
    config: FlashConfig | None = None,
) -> list[Path]:
    """複数の熟語をまとめてフラッシュクイズMP4に変換する。

    Args:
        words: 熟語のリスト。
        output_dir: 出力先ディレクトリ。
        config: 共通設定。

    Returns:
        生成したMP4ファイルのPathリスト。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i, word in enumerate(words, 1):
        cfg = config or FlashConfig()
        cfg.question_label = f"Q{i}"
        out = output_dir / f"flash_{i:03d}_{word}.mp4"
        print(f"[flash] 生成中 ({i}/{len(words)}): {word} → {out.name}")
        results.append(generate_flash_quiz(word, out, cfg))
    return results
