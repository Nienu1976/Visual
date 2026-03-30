"""漢字スライドパズルクイズ動画ジェネレーター。

参考動画（数字スライドパズル）の漢字版。
A*で求めた解法を再生し、シャッフル状態から完成形まで
段階的に完成するアニメーションMP4を生成する。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from visualquiz.common.font_manager import get_font_path
from visualquiz.common.video_exporter import frames_to_mp4, repeat_frame
from visualquiz.quiz3_puzzle.puzzle_solver import (
    PuzzleState,
    create_shuffled_puzzle,
    solve_astar,
)


@dataclass
class PuzzleConfig:
    """スライドパズルクイズの生成設定。"""
    width: int = 1280
    height: int = 720
    fps: int = 30
    bg_color: tuple[int, int, int] = (15, 15, 25)
    tile_bg_color: tuple[int, int, int] = (40, 60, 120)
    tile_border_color: tuple[int, int, int] = (100, 140, 220)
    tile_text_color: tuple[int, int, int] = (255, 255, 255)
    blank_color: tuple[int, int, int] = (15, 15, 25)
    complete_tile_color: tuple[int, int, int] = (40, 120, 60)   # 完成後のタイル色
    complete_text_color: tuple[int, int, int] = (255, 230, 100)
    tile_padding: int = 6
    border_radius: int = 12
    move_duration: float = 0.25     # 1手の移動アニメーション時間（秒）
    hold_duration: float = 0.15     # 移動後の静止時間（秒）
    shuffle_display: float = 2.0    # シャッフル状態の表示時間（秒）
    complete_duration: float = 3.0  # 完成後の表示時間（秒）
    shuffle_steps: int = 80         # シャッフル手数
    max_solve_moves: int = 150      # A*探索の上限手数
    show_move_count: bool = True    # 手数カウンターを表示


def generate_puzzle_quiz(
    kanji_string: str,
    output_path: Path | str,
    config: PuzzleConfig | None = None,
) -> Path:
    """漢字スライドパズルクイズのMP4を生成する。

    Args:
        kanji_string: パズルのタイルに使う漢字列。
                      文字数からグリッドサイズを自動計算する。
                      例: "日本語学習" → 2×3グリッド（空き1マス含む）
        output_path: 出力MP4ファイルパス。
        config: 生成設定。

    Returns:
        生成したMP4ファイルのPath。
    """
    if config is None:
        config = PuzzleConfig()

    # グリッドサイズ計算（文字数+1スペース）
    n = len(kanji_string) + 1  # 空きスペース分+1
    rows, cols = _calc_grid_size(n)
    chars = list(kanji_string)

    font_path = get_font_path()
    renderer = _PuzzleRenderer(rows, cols, chars, config, font_path)

    # パズル生成・解法取得
    print(f"[puzzle] グリッド: {rows}×{cols}、シャッフル中...")
    shuffled = create_shuffled_puzzle(rows, cols, config.shuffle_steps)
    print(f"[puzzle] A*で解法を探索中...")
    solution = solve_astar(shuffled, config.max_solve_moves)

    if solution is None:
        # 解けない場合は少ないシャッフルで再試行
        print("[puzzle] 解法が見つかりませんでした。再シャッフルします...")
        shuffled = create_shuffled_puzzle(rows, cols, 30)
        solution = solve_astar(shuffled, config.max_solve_moves)

    if solution is None:
        raise RuntimeError(
            "スライドパズルの解法が見つかりませんでした。"
            "max_solve_moves を増やすか、文字数を減らしてください。"
        )

    print(f"[puzzle] 解法: {len(solution)-1}手")

    frames: list[np.ndarray] = []

    # シャッフル状態を表示
    first_frame = renderer.render_state(shuffled, move_count=0)
    frames.extend(repeat_frame(first_frame, config.shuffle_display, config.fps))

    # 解法アニメーション
    for step_idx in range(1, len(solution)):
        prev_state = solution[step_idx - 1]
        curr_state = solution[step_idx]
        move_frames = renderer.render_move_animation(
            prev_state, curr_state, step_idx, config
        )
        frames.extend(move_frames)

    # 完成フレーム（色変え）
    final_state = solution[-1]
    complete_frame = renderer.render_state(
        final_state, move_count=len(solution) - 1, is_complete=True
    )
    frames.extend(repeat_frame(complete_frame, config.complete_duration, config.fps))

    return frames_to_mp4(
        frames, output_path, fps=config.fps, width=config.width, height=config.height
    )


def _calc_grid_size(n: int) -> tuple[int, int]:
    """タイル数nに対して最適なグリッドサイズ（rows, cols）を返す。"""
    # 正方形に近い形を優先
    sqrt_n = int(math.isqrt(n))
    for rows in range(sqrt_n, 0, -1):
        if n % rows == 0:
            return rows, n // rows
    # 割り切れない場合は1行多く取る
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return rows, cols


class _PuzzleRenderer:
    """パズル状態を画像として描画するクラス。"""

    def __init__(
        self,
        rows: int,
        cols: int,
        chars: list[str],
        config: PuzzleConfig,
        font_path: Path,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.chars = chars  # タイル番号1〜len(chars)に対応する文字
        self.config = config
        self.font_path = font_path

        # タイルサイズを動画サイズから自動計算
        margin = 80
        self.tile_w = (config.width - margin * 2) // cols
        self.tile_h = (config.height - margin * 2 - 60) // rows
        self.tile_size = min(self.tile_w, self.tile_h)
        self.font_size = int(self.tile_size * 0.55)
        self.grid_w = self.tile_size * cols
        self.grid_h = self.tile_size * rows
        self.grid_x = (config.width - self.grid_w) // 2
        self.grid_y = (config.height - self.grid_h) // 2 + 20
        self._font = self._load_font(self.font_size)
        self._small_font = self._load_font(32)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if self.font_path and self.font_path.exists():
                return ImageFont.truetype(str(self.font_path), size)
        except Exception:
            pass
        return ImageFont.load_default()

    def render_state(
        self,
        state: PuzzleState,
        move_count: int = 0,
        is_complete: bool = False,
        blank_offset: tuple[float, float] = (0.0, 0.0),
        moving_tile: int | None = None,
        moving_offset: tuple[float, float] = (0.0, 0.0),
    ) -> np.ndarray:
        """パズル状態を1フレームとして描画する。"""
        cfg = self.config
        img = Image.new("RGB", (cfg.width, cfg.height), cfg.bg_color)
        draw = ImageDraw.Draw(img)

        # グリッド外枠
        border_x = self.grid_x - 4
        border_y = self.grid_y - 4
        draw.rectangle(
            [border_x, border_y,
             border_x + self.grid_w + 8, border_y + self.grid_h + 8],
            outline=(60, 80, 140),
            width=3,
        )

        for idx, tile in enumerate(state.tiles):
            row, col = divmod(idx, self.cols)
            x = self.grid_x + col * self.tile_size
            y = self.grid_y + row * self.tile_size

            if tile == 0:
                # 空きスペース
                draw.rectangle(
                    [x + cfg.tile_padding, y + cfg.tile_padding,
                     x + self.tile_size - cfg.tile_padding,
                     y + self.tile_size - cfg.tile_padding],
                    fill=cfg.blank_color,
                )
                continue

            # オフセット適用（アニメーション用）
            ox, oy = 0.0, 0.0
            if moving_tile == tile:
                ox, oy = moving_offset

            tx = x + int(ox)
            ty = y + int(oy)

            tile_color = cfg.complete_tile_color if is_complete else cfg.tile_bg_color
            text_color = cfg.complete_text_color if is_complete else cfg.tile_text_color

            # タイル背景（角丸矩形）
            self._draw_rounded_rect(
                draw,
                tx + cfg.tile_padding, ty + cfg.tile_padding,
                tx + self.tile_size - cfg.tile_padding,
                ty + self.tile_size - cfg.tile_padding,
                radius=cfg.border_radius,
                fill=tile_color,
                outline=cfg.tile_border_color,
            )

            # 漢字テキスト
            char = self.chars[tile - 1] if tile - 1 < len(self.chars) else str(tile)
            bbox = draw.textbbox((0, 0), char, font=self._font)
            cw = bbox[2] - bbox[0]
            ch = bbox[3] - bbox[1]
            cx = tx + (self.tile_size - cw) // 2
            cy = ty + (self.tile_size - ch) // 2
            draw.text((cx, cy), char, font=self._font, fill=text_color)

        # 手数カウンター
        if cfg.show_move_count:
            label = f"手数: {move_count}" if not is_complete else f"完成！ ({move_count}手)"
            label_color = (255, 215, 0) if is_complete else (180, 180, 220)
            draw.text((30, 20), label, font=self._small_font, fill=label_color)

        return np.array(img)

    def render_move_animation(
        self,
        prev_state: PuzzleState,
        curr_state: PuzzleState,
        move_count: int,
        config: PuzzleConfig,
    ) -> list[np.ndarray]:
        """1手の移動アニメーションフレームリストを生成する。"""
        # 動いたタイルを特定
        moved_tile = None
        for i, (p, c) in enumerate(zip(prev_state.tiles, curr_state.tiles)):
            if p != c and p != 0:
                moved_tile = p
                from_idx = i
                break

        if moved_tile is None:
            # 変化なし（フォールバック）
            frame = self.render_state(curr_state, move_count)
            return repeat_frame(frame, config.hold_duration, config.fps)

        to_idx = curr_state.tiles.index(moved_tile)
        from_row, from_col = divmod(from_idx, self.cols)
        to_row, to_col = divmod(to_idx, self.cols)

        dx = (to_col - from_col) * self.tile_size
        dy = (to_row - from_row) * self.tile_size

        n_frames = max(2, int(config.move_duration * config.fps))
        frames = []
        for i in range(n_frames):
            t = i / (n_frames - 1)
            # イーズアウト
            t_eased = 1 - (1 - t) ** 2
            ox = dx * t_eased
            oy = dy * t_eased
            frame = self.render_state(
                prev_state,
                move_count=move_count,
                moving_tile=moved_tile,
                moving_offset=(ox, oy),
            )
            frames.append(frame)

        # 静止フレーム
        hold_frame = self.render_state(curr_state, move_count)
        frames.extend(repeat_frame(hold_frame, config.hold_duration, config.fps))
        return frames

    def _draw_rounded_rect(
        self,
        draw: ImageDraw.ImageDraw,
        x1: int, y1: int, x2: int, y2: int,
        radius: int = 10,
        fill: tuple | None = None,
        outline: tuple | None = None,
        width: int = 2,
    ) -> None:
        """角丸矩形を描画する（Pillow互換）。"""
        try:
            draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)
        except AttributeError:
            # Pillow 8以前のフォールバック
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width)
