"""KanjiVG書き順データの取得・キャッシュ・パース。

KanjiVG プロジェクト (https://kanjivg.tagaini.net) の SVG データから
1文字ずつのストロークパス（SVG d属性）を順番に取得する。
ライセンス: CC BY-SA 3.0
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

# ローカルキャッシュディレクトリ
CACHE_DIR = Path.home() / ".cache" / "visualquiz" / "kanjivg"
KANJIVG_RAW = "https://raw.githubusercontent.com/KanjiVG/kanjivg/master/kanji"
KANJIVG_VIEWBOX = 109.0  # KanjiVG の SVG viewBox サイズ（px）


def get_strokes(char: str) -> list[str]:
    """漢字1文字の書き順ストロークパス（SVG d属性）リストを返す。

    データが存在しない・取得失敗の場合は空リストを返す。

    Args:
        char: 漢字1文字

    Returns:
        書き順順に並んだ SVG パス d属性の文字列リスト
    """
    cp = ord(char)
    filename = f"{cp:05x}.svg"
    cache_path = CACHE_DIR / filename

    if not cache_path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = f"{KANJIVG_RAW}/{filename}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            cache_path.write_text(resp.text, encoding="utf-8")
        except Exception:
            return []

    try:
        content = cache_path.read_text(encoding="utf-8")
        return _parse_strokes(content)
    except Exception:
        return []


def get_stroke_count(char: str) -> int:
    """漢字1文字の画数を返す（データなし = 0）。"""
    return len(get_strokes(char))


def _parse_strokes(svg_content: str) -> list[str]:
    """SVGテキストから書き順ストロークの d パスを順番に返す。"""
    # <svg タグ以前（DOCTYPE宣言等）を除去する
    svg_start = svg_content.find("<svg")
    if svg_start > 0:
        svg_content = svg_content[svg_start:]

    # kvg: 名前空間はDTD内で定義されているが、ET.fromstring では未定義になる
    # → xmlns:kvg 宣言を <svg> タグに追加して解決する
    if 'xmlns:kvg' not in svg_content:
        svg_content = svg_content.replace(
            "<svg ", '<svg xmlns:kvg="http://kanjivg.tagaini.net" ', 1
        )

    root = ET.fromstring(svg_content)

    stroke_paths: dict[int, str] = {}
    for elem in root.iter():
        elem_id = elem.get("id", "")
        # kvg:05b57-s1, kvg:05b57-s2 ... のパターンにマッチ
        m = re.match(r"kvg:[0-9a-f]+-s(\d+)$", elem_id)
        if m:
            stroke_num = int(m.group(1))
            d = elem.get("d", "")
            if d:
                stroke_paths[stroke_num] = d

    return [stroke_paths[k] for k in sorted(stroke_paths.keys())]
