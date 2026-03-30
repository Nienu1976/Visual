"""漢字フラッシュクイズ動画ジェネレーター（ランダムサンプリング点滅版）。

アニメーション仕様：
  ① 毎フラッシュごとに「ランダムで異なるストロークの組み合わせ」を瞬間表示
  ② 暗転（黒）→ 次の別の組み合わせをフラッシュ → 暗転 … を繰り返す
  ③ ステージが進むごとに「1回のフラッシュで見えるストローク数」が増える
  ④ ユーザーは複数フラッシュを見て脳内で合成し「何の漢字か」を推測する
  ⑤ 最終ステージで全ストロークをゴールド静止表示（正解）

設定パラメータ：
  flash_duration     : 1回のフラッシュ表示時間（秒）
  flash_interval     : フラッシュ間の暗転時間（秒）
  flashes_per_stage  : 1ステージあたりのフラッシュ回数
  strokes_per_stage  : ステージごとに増やすストローク数
  font_style         : "mincho" or "gothic"
"""
from __future__ import annotations

import random
from dataclasses import dataclass
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
    # ── 動画サイズ ──────────────────────────────────────────────
    width: int = 1280
    height: int = 720
    fps: int = 30

    # ── 色 ──────────────────────────────────────────────────────
    bg_color: tuple[int, int, int] = (13, 17, 23)
    tile_bg_color: tuple[int, int, int] = (248, 248, 244)
    tile_border_color: tuple[int, int, int] = (180, 180, 180)
    stroke_color: tuple[int, int, int] = (30, 30, 30)
    answer_color: tuple[int, int, int] = (218, 165, 32)     # ゴールド

    # ── フラッシュタイミング ─────────────────────────────────────
    flash_duration: float = 0.20    # 1フラッシュの表示時間（秒）
    flash_interval: float = 0.25    # フラッシュ間の暗転時間（秒）

    # ── ステージ設定 ────────────────────────────────────────────
    flashes_per_stage: int = 5      # 1ステージあたりのフラッシュ回数
    strokes_per_stage: int = 1      # ステージごとに増やすストローク数（見える量）
    initial_strokes: int = 1        # 最初のステージで見えるストローク数

    # ── 正解表示 ────────────────────────────────────────────────
    answer_duration: float = 3.0

    # ── フォント ────────────────────────────────────────────────
    font_style: str = "mincho"      # "mincho" or "gothic"

    # ── ラベル ──────────────────────────────────────────────────
    question_label: str = ""
    label_size: int = 32
    tile_gap: int = 30
    tile_padding: int = 60


def _sample_across_chars(
    all_refs: list[tuple[int, int]],
    char_strokes: list[list[str]],
    n_show: int,
) -> list[tuple[int, int]]:
    """各文字から最低1ストロークを保証してランダムにn_show個サンプルする。"""
    n_chars = len(char_strokes)
    # 各文字のストローク参照リスト
    per_char = [
        [(ci, si) for (ci, si) in all_refs if ci == i]
        for i in range(n_chars)
    ]
    # 各文字から必ず1本確保（n_show より文字数が多くても全文字を保証）
    guaranteed = [random.choice(refs) for refs in per_char if refs]

    # n_show は guaranteed 数以上に引き上げる（文字数 < n_show なら追加サンプル）
    actual_n = max(n_show, len(guaranteed))
    remaining_pool = [r for r in all_refs if r not in set(guaranteed)]
    extra_count = max(0, actual_n - len(guaranteed))
    extra = random.sample(remaining_pool, min(extra_count, len(remaining_pool)))
    return guaranteed + extra


def generate_flash_quiz(
    word: str,
    output_path: Path | str,
    config: FlashConfig | None = None,
) -> Path:
    """漢字フラッシュクイズ MP4 を生成する。"""
    if config is None:
        config = FlashConfig()

    font_path = get_font_path(config.font_style)
    char_strokes: list[list[str]] = [get_strokes(ch) for ch in word]
    total_strokes = sum(len(s) for s in char_strokes)

    if total_strokes == 0:
        return _generate_fallback(word, output_path, config, font_path)

    # 全ストロークの参照リスト (char_idx, stroke_idx)
    all_refs: list[tuple[int, int]] = [
        (ci, si)
        for ci, strokes in enumerate(char_strokes)
        for si in range(len(strokes))
    ]

    tile_size = _calc_tile_size(len(word), config)

    # 暗転フレーム（共通）
    dark_frame = _render_frame(
        word, char_strokes, [], tile_size, config, font_path
    )

    frames: list[np.ndarray] = []

    # 冒頭：暗転 0.5 秒
    frames.extend(repeat_frame(dark_frame, 0.5, config.fps))

    # ── ステージループ ────────────────────────────────────────
    # ステージ 0: initial_strokes 本表示
    # ステージ 1: initial_strokes + strokes_per_stage 本表示
    # ステージ 2: initial_strokes + strokes_per_stage*2 本表示 …
    # 最終ステージ: 全ストローク表示（正解直前）

    visible_count = config.initial_strokes
    prev_sampled: frozenset[tuple[int, int]] | None = None
    while visible_count <= total_strokes:
        n_show = min(visible_count, total_strokes)

        # 全ストローク表示になったらフラッシュせず正解へ
        if n_show == total_strokes:
            break

        for _ in range(config.flashes_per_stage):
            # 直前と異なる組み合わせになるまで再サンプル（最大10回試行）
            for _attempt in range(10):
                sampled = _sample_across_chars(all_refs, char_strokes, n_show)
                if frozenset(sampled) != prev_sampled:
                    break
            prev_sampled = frozenset(sampled)

            flash_frame = _render_frame(
                word, char_strokes, sampled, tile_size, config, font_path
            )
            frames.extend(repeat_frame(flash_frame, config.flash_duration, config.fps))
            frames.extend(repeat_frame(dark_frame, config.flash_interval, config.fps))

        visible_count += config.strokes_per_stage

    # 正解フレーム：全ストロークをゴールドで静止
    answer_frame = _render_frame(
        word, char_strokes, all_refs, tile_size, config, font_path,
        answer_mode=True,
    )
    frames.extend(repeat_frame(answer_frame, config.answer_duration, config.fps))

    return frames_to_mp4(
        frames, output_path,
        fps=config.fps, width=config.width, height=config.height,
    )


# ── レンダリング ──────────────────────────────────────────────────────

def _calc_tile_size(n: int, config: FlashConfig) -> int:
    available_w = config.width - config.tile_padding * 2 - config.tile_gap * (n - 1)
    available_h = config.height - config.tile_padding * 2 - 70
    return min(available_w // n, available_h)


def _render_frame(
    word: str,
    char_strokes: list[list[str]],
    visible_refs: list[tuple[int, int]],  # 今回表示する (ci, si) リスト
    tile_size: int,
    config: FlashConfig,
    font_path: Path,
    answer_mode: bool = False,
) -> np.ndarray:
    canvas = Image.new("RGB", (config.width, config.height), config.bg_color)
    draw = ImageDraw.Draw(canvas)

    n = len(word)
    total_w = tile_size * n + config.tile_gap * (n - 1)
    start_x = (config.width - total_w) // 2
    tile_y = (config.height - tile_size) // 2 + 20

    base_style = make_default_style(tile_size, config.stroke_color)
    visible_set = set(visible_refs)

    for ci, char in enumerate(word):
        strokes = char_strokes[ci]
        x = start_x + ci * (tile_size + config.tile_gap)

        # このタイルで表示するストロークとスタイル
        visible: set[int] = set()
        stroke_styles: dict[int, StrokeStyle] = {}

        if answer_mode:
            visible = set(range(len(strokes)))
            for si in visible:
                stroke_styles[si] = StrokeStyle(
                    color=config.answer_color, width=base_style.width
                )
        else:
            for (aci, asi) in visible_set:
                if aci == ci:
                    visible.add(asi)
                    stroke_styles[asi] = base_style

        tile_img = render_kanji_tile(
            strokes, visible, tile_size,
            stroke_styles=stroke_styles,
            bg_color=config.tile_bg_color,
            border_color=config.tile_border_color,
        )
        canvas.paste(tile_img, (x, tile_y))

    # 問題ラベル
    if config.question_label:
        lf = _load_font(font_path, config.label_size)
        draw.text((30, 20), config.question_label, font=lf, fill=(200, 200, 200))

    # 正解時：文字テキストをタイル下に表示
    if answer_mode:
        af = _load_font(font_path, 52)
        for ci, char in enumerate(word):
            cx = start_x + ci * (tile_size + config.tile_gap) + tile_size // 2
            bb = draw.textbbox((0, 0), char, font=af)
            tw = bb[2] - bb[0]
            draw.text(
                (cx - tw // 2, tile_y + tile_size + 14),
                char, font=af, fill=config.answer_color,
            )

    return np.array(canvas)


def _load_font(
    font_path: Path, size: int
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        if font_path and font_path.exists():
            return ImageFont.truetype(str(font_path), size)
    except Exception:
        pass
    return ImageFont.load_default()


def _generate_fallback(
    word: str, output_path: Path | str,
    config: FlashConfig, font_path: Path,
) -> Path:
    font = _load_font(font_path, 240)
    frames = []
    for step in range(21):
        alpha = int(255 * step / 20)
        img = Image.new("RGB", (config.width, config.height), config.bg_color)
        overlay = Image.new("RGBA", (config.width, config.height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        draw_tmp = ImageDraw.Draw(img)
        bb = draw_tmp.textbbox((0, 0), word, font=font)
        x = (config.width - (bb[2] - bb[0])) // 2
        y = (config.height - (bb[3] - bb[1])) // 2
        od.text((x, y), word, font=font, fill=(*config.answer_color, alpha))
        merged = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        frames.extend(repeat_frame(np.array(merged), 0.1, config.fps))
    frames.extend(repeat_frame(frames[-1], config.answer_duration, config.fps))
    return frames_to_mp4(frames, output_path, fps=config.fps,
                         width=config.width, height=config.height)


def generate_flash_quiz_batch(
    words: list[str],
    output_dir: Path | str,
    config: FlashConfig | None = None,
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i, word in enumerate(words, 1):
        cfg = config or FlashConfig()
        cfg.question_label = f"Q{i}"
        out = output_dir / f"flash_{i:03d}_{word}.mp4"
        print(f"[flash] ({i}/{len(words)}) {word}")
        results.append(generate_flash_quiz(word, out, cfg))
    return results
