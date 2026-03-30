"""フラッシュクイズジェネレーターのユニットテスト。"""
import pytest
from visualquiz.quiz1_flash.flash_generator import (
    FlashConfig,
    FlashMode,
    _KanjiRenderer,
    _build_mask_schedule,
)
from visualquiz.common.font_manager import get_font_path


def make_renderer(word: str = "桜花") -> _KanjiRenderer:
    config = FlashConfig(width=320, height=180, font_size=60, block_size=20)
    font_path = get_font_path()
    return _KanjiRenderer(word, config, font_path)


def test_mask_schedule_length():
    config = FlashConfig(stages=8)
    renderer = make_renderer()
    schedule = _build_mask_schedule(renderer, config)
    assert len(schedule) == 8


def test_mask_schedule_ends_at_one():
    config = FlashConfig(stages=5)
    renderer = make_renderer()
    schedule = _build_mask_schedule(renderer, config)
    assert schedule[-1] == 1.0


def test_mask_schedule_ascending():
    config = FlashConfig(stages=5)
    renderer = make_renderer()
    schedule = _build_mask_schedule(renderer, config)
    assert all(schedule[i] < schedule[i + 1] for i in range(len(schedule) - 1))


def test_render_shape():
    renderer = make_renderer()
    frame = renderer.render(reveal_ratio=0.0)
    assert frame.shape == (180, 320, 3)


def test_render_fully_revealed():
    renderer = make_renderer()
    frame = renderer.render(reveal_ratio=1.0)
    assert frame.shape == (180, 320, 3)


def test_render_answer_mode():
    renderer = make_renderer()
    frame = renderer.render(reveal_ratio=1.0, answer_mode=True)
    assert frame.shape == (180, 320, 3)


def test_flash_modes():
    for mode in FlashMode:
        config = FlashConfig(mode=mode, stages=2, width=160, height=90, block_size=20)
        font_path = get_font_path()
        renderer = _KanjiRenderer("桜花", config, font_path)
        frame = renderer.render(reveal_ratio=0.5)
        assert frame is not None
