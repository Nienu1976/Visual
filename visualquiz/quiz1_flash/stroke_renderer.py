"""KanjiVGストロークをPIL Imageに描画するレンダラー。

svgpathtools でSVGパスをパースし、Pillow で
ベジェ曲線をサンプリング描画する（Cライブラリ不要）。
"""
from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from visualquiz.quiz1_flash.kanjivg import KANJIVG_VIEWBOX

try:
    from svgpathtools import parse_path as _parse_path
    _HAS_SVGPATHTOOLS = True
except ImportError:
    _HAS_SVGPATHTOOLS = False


class StrokeStyle(NamedTuple):
    color: tuple[int, int, int]
    width: int
    alpha: int = 255  # 0-255


def render_kanji_tile(
    strokes: list[str],
    visible: set[int],
    size: int,
    stroke_styles: dict[int, StrokeStyle],
    bg_color: tuple[int, int, int] = (248, 248, 244),
    border_color: tuple[int, int, int] | None = (200, 200, 200),
    border_width: int = 2,
) -> Image.Image:
    """1文字分のストロークをタイル画像として描画する。

    Args:
        strokes: SVG d属性の文字列リスト（書き順順）
        visible: 表示するストロークのインデックスセット（0始まり）
        size: 出力タイル画像の一辺のピクセル数
        stroke_styles: ストロークインデックス → StrokeStyle の辞書
        bg_color: タイル背景色 (R,G,B)
        border_color: 枠線色 (None で枠なし)
        border_width: 枠線幅 (px)

    Returns:
        size×size の RGB PIL Image
    """
    img = Image.new("RGBA", (size, size), (*bg_color, 255))
    draw = ImageDraw.Draw(img)

    scale = size / KANJIVG_VIEWBOX
    base_stroke_w = max(2, int(3.5 * scale))

    for i, path_d in enumerate(strokes):
        if i not in visible:
            continue
        style = stroke_styles.get(i, StrokeStyle(color=(40, 40, 40), width=base_stroke_w))
        w = style.width if style.width > 0 else base_stroke_w
        _draw_stroke(draw, path_d, scale, style.color, w)

    if border_color:
        draw.rectangle(
            [border_width // 2, border_width // 2,
             size - border_width // 2, size - border_width // 2],
            outline=border_color,
            width=border_width,
        )

    return img.convert("RGB")


def _draw_stroke(
    draw: ImageDraw.ImageDraw,
    path_d: str,
    scale: float,
    color: tuple[int, int, int],
    width: int,
) -> None:
    """1ストロークをサンプリング描画する。"""
    if _HAS_SVGPATHTOOLS:
        _draw_stroke_svgpathtools(draw, path_d, scale, color, width)
    else:
        _draw_stroke_manual(draw, path_d, scale, color, width)


def _draw_stroke_svgpathtools(
    draw: ImageDraw.ImageDraw,
    path_d: str,
    scale: float,
    color: tuple[int, int, int],
    width: int,
) -> None:
    """svgpathtools を使ってストロークを描画する（高品質）。"""
    try:
        path = _parse_path(path_d)
        if not path:
            return

        # パスの長さに比例してサンプル数を決定
        try:
            arc_len = path.length()
        except Exception:
            arc_len = 100.0
        n = max(40, int(arc_len * scale * 1.5))

        points: list[tuple[float, float]] = []
        for k in range(n + 1):
            t = k / n
            try:
                pt = path.point(t)
                points.append((pt.real * scale, pt.imag * scale))
            except Exception:
                continue

        if len(points) < 2:
            return

        draw.line(points, fill=color, width=width)

        # 始点・終点に丸キャップ
        r = width // 2
        for px, py in [points[0], points[-1]]:
            draw.ellipse([(px - r, py - r), (px + r, py + r)], fill=color)

    except Exception:
        pass


def _draw_stroke_manual(
    draw: ImageDraw.ImageDraw,
    path_d: str,
    scale: float,
    color: tuple[int, int, int],
    width: int,
) -> None:
    """svgpathtools なしの手動SVGパスパーサー（フォールバック）。

    KanjiVGで使われる M, m, L, l, C, c, S, s, Z, z コマンドのみ対応。
    """
    import re

    tokens = re.findall(
        r"[MmLlCcSsZz]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?",
        path_d
    )

    def _floats(lst: list[str], n: int) -> list[float]:
        return [float(x) for x in lst[:n]]

    cx, cy = 0.0, 0.0  # 現在地
    sx, sy = 0.0, 0.0  # 直前の制御点（S/s用）
    start_x, start_y = 0.0, 0.0
    points: list[tuple[float, float]] = [(0.0, 0.0)]

    i = 0
    cmd = "M"
    args: list[str] = []

    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            continue

        # コマンドごとに引数を消費
        if cmd in ("M", "m"):
            x, y = _floats(tokens[i:], 2)
            i += 2
            if cmd == "m":
                cx, cy = cx + x, cy + y
            else:
                cx, cy = x, y
            start_x, start_y = cx, cy
            points.append((cx * scale, cy * scale))
            cmd = "l" if cmd == "m" else "L"  # 続く座標は L/l として扱う

        elif cmd in ("L", "l"):
            x, y = _floats(tokens[i:], 2)
            i += 2
            if cmd == "l":
                cx, cy = cx + x, cy + y
            else:
                cx, cy = x, y
            points.append((cx * scale, cy * scale))

        elif cmd in ("C", "c"):
            x1, y1, x2, y2, x, y = _floats(tokens[i:], 6)
            i += 6
            if cmd == "c":
                x1, y1 = cx + x1, cy + y1
                x2, y2 = cx + x2, cy + y2
                x, y = cx + x, cy + y
            pts = _cubic_bezier_points(cx, cy, x1, y1, x2, y2, x, y)
            points.extend([(px * scale, py * scale) for px, py in pts])
            sx, sy = x2, y2
            cx, cy = x, y

        elif cmd in ("S", "s"):
            x2, y2, x, y = _floats(tokens[i:], 4)
            i += 4
            # 直前の制御点を反転
            x1, y1 = 2 * cx - sx, 2 * cy - sy
            if cmd == "s":
                x2, y2 = cx + x2, cy + y2
                x, y = cx + x, cy + y
            pts = _cubic_bezier_points(cx, cy, x1, y1, x2, y2, x, y)
            points.extend([(px * scale, py * scale) for px, py in pts])
            sx, sy = x2, y2
            cx, cy = x, y

        elif cmd in ("Z", "z"):
            cx, cy = start_x, start_y
            points.append((cx * scale, cy * scale))
            i += 1

        else:
            i += 1  # 未対応コマンドはスキップ

    if len(points) >= 2:
        draw.line(points, fill=color, width=width)
        r = width // 2
        for px, py in [points[0], points[-1]]:
            draw.ellipse([(px - r, py - r), (px + r, py + r)], fill=color)


def _cubic_bezier_points(
    x0: float, y0: float,
    x1: float, y1: float,
    x2: float, y2: float,
    x3: float, y3: float,
    n: int = 40,
) -> list[tuple[float, float]]:
    """3次ベジェ曲線をnサンプルで近似した座標リストを返す。"""
    pts = []
    for k in range(n + 1):
        t = k / n
        u = 1 - t
        x = u**3 * x0 + 3*u**2*t * x1 + 3*u*t**2 * x2 + t**3 * x3
        y = u**3 * y0 + 3*u**2*t * y1 + 3*u*t**2 * y2 + t**3 * y3
        pts.append((x, y))
    return pts


def make_default_style(
    size: int,
    color: tuple[int, int, int] = (40, 40, 40),
) -> StrokeStyle:
    """標準ストロークスタイルを生成する。"""
    scale = size / KANJIVG_VIEWBOX
    width = max(3, int(3.5 * scale))
    return StrokeStyle(color=color, width=width)
