"""歌詞テキストから漢字／非漢字を抽出・マスクするパーサー。"""
from __future__ import annotations

import re
import unicodedata

# CJK統一漢字の範囲
_KANJI_RANGES = [
    (0x4E00, 0x9FFF),    # CJK統一漢字
    (0x3400, 0x4DBF),    # CJK統一漢字拡張A
    (0x20000, 0x2A6DF),  # CJK統一漢字拡張B
    (0xF900, 0xFAFF),    # CJK互換漢字
]


def is_kanji(char: str) -> bool:
    """文字が漢字かどうかを判定する。"""
    cp = ord(char)
    return any(start <= cp <= end for start, end in _KANJI_RANGES)


def mask_non_kanji(text: str, mask_char: str = "＿") -> str:
    """漢字以外の文字をmask_charに置換する（漢字のみ表示モード）。"""
    result = []
    for ch in text:
        if ch in ("\n", "\r", "　", " "):
            result.append(ch)
        elif is_kanji(ch):
            result.append(ch)
        else:
            result.append(mask_char)
    return "".join(result)


def mask_kanji(text: str, mask_char: str = "□") -> str:
    """漢字をmask_charに置換する（漢字以外のみ表示モード）。"""
    result = []
    for ch in text:
        if is_kanji(ch):
            result.append(mask_char)
        else:
            result.append(ch)
    return "".join(result)


def split_lyrics_into_pages(text: str, lines_per_page: int = 4) -> list[list[str]]:
    """歌詞テキストを指定行数ごとのページに分割する。

    空行を段落区切りとして扱い、段落ごとにまとめる。
    1ページに収まらない段落は強制的に分割する。
    """
    lines = text.splitlines()
    pages: list[list[str]] = []
    current_page: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == "":
            # 空行 = 段落区切り → ページ確定
            if current_page:
                pages.append(current_page)
                current_page = []
        else:
            current_page.append(stripped)
            if len(current_page) >= lines_per_page:
                pages.append(current_page)
                current_page = []

    if current_page:
        pages.append(current_page)

    return pages


def count_kanji(text: str) -> int:
    """テキスト中の漢字の数を返す。"""
    return sum(1 for ch in text if is_kanji(ch))


def extract_kanji_list(text: str) -> list[str]:
    """テキストから漢字のみをリストで返す。"""
    return [ch for ch in text if is_kanji(ch)]
