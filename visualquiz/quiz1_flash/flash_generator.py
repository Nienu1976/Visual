"""漢字フラッシュクイズ動画ジェネレーター（書き順ストローク点滅版）。

アニメーション仕様：
  ① ランダムに選んだ N ストロークが「点滅（ON/OFF 繰り返し）」
  ② stage_duration 秒後にさらに N ストロークを追加して点滅継続
  ③ ② を全ストロークが追加されるまで繰り返す
  ④ 全ストロークを正解色（ゴールド）で静止表示

これにより「何の漢字か」をストロークの点滅から推測するクイズになる。
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
    bg_color: tuple[int, int, int] = (13, 17, 23)           # 背景（ダークネイビー）
    tile_bg_color: tuple[int, int, int] = (248, 248, 244)   # 漢字タイル（オフホワイト）
    tile_border_color: tuple[int, int, int] = (180, 180, 180)
    stroke_color: tuple[int, int, int] = (30, 30, 30)       # 点滅ON時のストローク色
    answer_color: tuple[int, int, int] = (218, 165, 32)     # 正解時（ゴールド）

    # ── 点滅タイミング ──────────────────────────────────────────
    flash_on: float = 0.25      # 点灯時間（秒）：ストロークが見える時間
    flash_off: float = 0.20     # 消灯時間（秒）：ストロークが消える時間

    # ── ステージ設定 ────────────────────────────────────────────
    strokes_per_stage: int = 1  # 1ステージで追加するストローク数
    stage_duration: float = 2.5 # 1ステージの点滅継続時間（秒）

    # ── 正解表示 ────────────────────────────────────────────────
    answer_duration: float = 3.0  # 正解静止表示の秒数

    # ── フォント ────────────────────────────────────────────────
    font_style: str = "mincho"  # "mincho"（明朝体）or "gothic"（ゴシック体）

    # ── ラベル ──────────────────────────────────────────────────
    question_label: str = ""
    label_size: int = 32
    tile_gap: int = 30
    tile_padding: int = 60


def generate_flash_quiz(
    word: str,
    output_path: Path | str,
    config: FlashConfig | None = None,
) -> Path:
    """漢字フラッシュクイズ MP4 を生成する。

    Args:
        word: クイズにする漢字熟語（1文字以上）。
        output_path: 出力 MP4 ファイルパス。
        config: 生成設定（省略時はデフォルト）。

    Returns:
        生成した MP4 ファイルの Path。
    """
    if config is None:
        config = FlashConfig()

    font_path = get_font_path(config.font_style)

    # ── 書き順ストローク取得 ────────────────────────────────────
    char_strokes: list[list[str]] = [get_strokes(ch) for ch in word]
    total_strokes = sum(len(s) for s in char_strokes)

    if total_strokes == 0:
        # KanjiVG データなし → フォールバック（テキストフェードイン）
        return _generate_fallback(word, output_path, config, font_path)

    # ── ランダムなストローク順序を生成 ─────────────────────────
    all_refs: list[tuple[int, int]] = [
        (ci, si)
        for ci, strokes in enumerate(char_strokes)
        for si in range(len(strokes))
    ]
    random.shuffle(all_refs)

    # ── タイルサイズ計算 ────────────────────────────────────────
    tile_size = _calc_tile_size(len(word), config)

    # ── フレーム生成 ────────────────────────────────────────────
    frames: list[np.ndarray] = []

    # 最初：全ストロークなし（空のタイルのみ表示）で 0.5 秒
    blank = _render_frame(word, char_strokes, set(), tile_size, config, font_path)
    frames.extend(repeat_frame(blank, 0.5, config.fps))

    # ステージループ：ストロークを N 本ずつ追加しながら点滅
    active: set[tuple[int, int]] = set()  # 現在点滅中のストロークセット

    for stage_start in range(0, len(all_refs), config.strokes_per_stage):
        batch = all_refs[stage_start : stage_start + config.strokes_per_stage]
        active.update(batch)

        # このステージで何サイクル点滅するか
        cycle_len = config.flash_on + config.flash_off
        n_cycles = max(1, int(config.stage_duration / cycle_len))

        on_frame = _render_frame(
            word, char_strokes, active, tile_size, config, font_path,
            use_stroke_color=True
        )
        off_frame = _render_frame(
            word, char_strokes, set(), tile_size, config, font_path,
            use_stroke_color=False
        )

        for _ in range(n_cycles):
            frames.extend(repeat_frame(on_frame, config.flash_on, config.fps))
            frames.extend(repeat_frame(off_frame, config.flash_off, config.fps))

    # 正解：全ストロークをゴールドで静止表示
    answer_frame = _render_frame(
        word, char_strokes, set(all_refs), tile_size, config, font_path,
        answer_mode=True
    )
    # 正解直前：一瞬全部点滅させて視線を引く
    for _ in range(3):
        frames.extend(repeat_frame(answer_frame, 0.1, config.fps))
        frames.extend(repeat_frame(off_frame, 0.07, config.fps))
    frames.extend(repeat_frame(answer_frame, config.answer_duration, config.fps))

    return frames_to_mp4(
        frames, output_path,
        fps=config.fps, width=config.width, height=config.height
    )


# ── レンダリング ─────────────────────────────────────────────────────

def _calc_tile_size(n: int, config: FlashConfig) -> int:
    available_w = config.width - config.tile_padding * 2 - config.tile_gap * (n - 1)
    available_h = config.height - config.tile_padding * 2 - 60
    return min(available_w // n, available_h)


def _render_frame(
    word: str,
    char_strokes: list[list[str]],
    active: set[tuple[int, int]],
    tile_size: int,
    config: FlashConfig,
    font_path: Path,
    use_stroke_color: bool = True,
    answer_mode: bool = False,
) -> np.ndarray:
    """1フレーム分の画像を生成する。

    Args:
        active: 表示するストロークの (char_idx, stroke_idx) セット。
        use_stroke_color: True=通常色、False=タイルを完全に空にする（OFF フレーム）。
        answer_mode: True=ゴールドで全ストロークを表示。
    """
    canvas = Image.new("RGB", (config.width, config.height), config.bg_color)
    draw = ImageDraw.Draw(canvas)

    n = len(word)
    total_w = tile_size * n + config.tile_gap * (n - 1)
    start_x = (config.width - total_w) // 2
    tile_y = (config.height - tile_size) // 2 + 20

    base_style = make_default_style(tile_size, config.stroke_color)

    for ci, char in enumerate(word):
        x = start_x + ci * (tile_size + config.tile_gap)
        strokes = char_strokes[ci]

        # このタイルで表示するストロークとスタイルを決定
        visible: set[int] = set()
        stroke_styles: dict[int, StrokeStyle] = {}

        if answer_mode:
            # 全ストロークをゴールドで表示
            visible = set(range(len(strokes)))
            stroke_styles = {
                si: StrokeStyle(color=config.answer_color, width=base_style.width)
                for si in visible
            }
        elif use_stroke_color:
            # アクティブなストロークを通常色で表示
            for (aci, asi) in active:
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

    # ── ラベル描画 ───────────────────────────────────────────────
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
                char, font=af, fill=config.answer_color
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
    config: FlashConfig, font_path: Path
) -> Path:
    """KanjiVG データがない場合：テキストをフェードイン表示。"""
    font = _load_font(font_path, 240)
    frames = []

    for step in range(20 + 1):
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
    """複数の熟語をまとめて MP4 生成する。"""
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
