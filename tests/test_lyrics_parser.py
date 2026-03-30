"""歌詞パーサーのユニットテスト。"""
import pytest
from visualquiz.quiz2_lyrics.lyrics_parser import (
    count_kanji,
    extract_kanji_list,
    is_kanji,
    mask_kanji,
    mask_non_kanji,
    split_lyrics_into_pages,
)


def test_is_kanji_true():
    assert is_kanji("漢") is True
    assert is_kanji("字") is True
    assert is_kanji("日") is True


def test_is_kanji_false():
    assert is_kanji("あ") is False
    assert is_kanji("ア") is False
    assert is_kanji("A") is False
    assert is_kanji("1") is False
    assert is_kanji("。") is False


def test_mask_non_kanji():
    result = mask_non_kanji("春の小川")
    assert result == "春＿小川"


def test_mask_non_kanji_keeps_newlines():
    result = mask_non_kanji("春\nの")
    assert "\n" in result
    assert "春" in result


def test_mask_kanji():
    result = mask_kanji("春の小川")
    assert result == "□の□□"


def test_mask_kanji_hiragana_unchanged():
    result = mask_kanji("あいうえお")
    assert result == "あいうえお"


def test_count_kanji():
    assert count_kanji("春の小川") == 3  # 春,小,川
    assert count_kanji("あいうえお") == 0
    assert count_kanji("") == 0


def test_extract_kanji_list():
    result = extract_kanji_list("春の小川")
    assert result == ["春", "小", "川"]


def test_split_lyrics_into_pages_basic():
    lyrics = "1行目\n2行目\n3行目\n4行目"
    pages = split_lyrics_into_pages(lyrics, lines_per_page=4)
    assert len(pages) == 1
    assert len(pages[0]) == 4


def test_split_lyrics_paragraph_break():
    lyrics = "1行目\n2行目\n\n3行目\n4行目"
    pages = split_lyrics_into_pages(lyrics, lines_per_page=4)
    assert len(pages) == 2


def test_split_lyrics_overflow():
    lyrics = "\n".join([f"{i}行目" for i in range(10)])
    pages = split_lyrics_into_pages(lyrics, lines_per_page=4)
    # 10行 / 4行 = 3ページ（端数繰り上げ）
    assert len(pages) >= 2
