"""フォント管理モジュール。ゴシック体・明朝体を自動検出してPathを返す。"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ── ダウンロード候補フォント（SIL Open Font License） ────────────────
_DOWNLOAD_FONTS = {
    "mincho": {
        "filename": "NotoSerifCJKjp-Regular.otf",
        "url": (
            "https://github.com/googlefonts/noto-cjk/raw/main/Serif/SubsetOTF/JP/"
            "NotoSerifCJKjp-Regular.otf"
        ),
    },
    "gothic": {
        "filename": "NotoSansCJKjp-Regular.otf",
        "url": (
            "https://github.com/googlefonts/noto-cjk/raw/main/Sans/SubsetOTF/JP/"
            "NotoSansCJKjp-Regular.otf"
        ),
    },
}

# ── macOS システムフォント候補 ────────────────────────────────────────
_SYSTEM_FONTS_MACOS = {
    "mincho": [
        Path("/System/Library/Fonts/ヒラギノ明朝 ProN W3.ttc"),
        Path("/System/Library/Fonts/Hiragino Mincho ProN W3.ttc"),
        Path("/Library/Fonts/ヒラギノ明朝 Pro W3.otf"),
    ],
    "gothic": [
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        Path("/System/Library/Fonts/Hiragino Sans W3.ttc"),
        Path("/System/Library/Fonts/ヒラギノ角ゴ ProN W3.ttc"),
        Path("/System/Library/Fonts/Hiragino Kaku Gothic ProN W3.ttc"),
    ],
}

# ── Windows システムフォント候補 ─────────────────────────────────────
_SYSTEM_FONTS_WINDOWS = {
    "mincho": ["YuMincho.ttc", "msgothic.ttc"],  # 游明朝
    "gothic": ["YuGothic.ttc", "meiryo.ttc", "msgothic.ttc"],  # 游ゴシック / メイリオ
}

# ── Linux ────────────────────────────────────────────────────────────
_SYSTEM_FONTS_LINUX = {
    "mincho": [
        Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
        Path("/usr/share/fonts/noto-cjk/NotoSerifCJKjp-Regular.otf"),
    ],
    "gothic": [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/noto-cjk/NotoSansCJKjp-Regular.otf"),
    ],
}


def get_font_path(style: str = "mincho") -> Path:
    """指定スタイルの日本語フォントパスを返す。

    Args:
        style: "mincho"（明朝体）または "gothic"（ゴシック体）

    Returns:
        フォントファイルのPath。見つからない場合は空のPath（デフォルトフォント使用）。
    """
    style = style.lower()
    if style not in ("mincho", "gothic"):
        style = "mincho"

    # 1. assetsディレクトリのキャッシュ済みフォントを探す
    cached = ASSETS_DIR / _DOWNLOAD_FONTS[style]["filename"]
    if cached.exists():
        return cached

    # 2. システムフォントを探す
    system = _find_system_font(style)
    if system:
        return system

    # 3. ダウンロード試行
    try:
        _download_font(style, cached)
        return cached
    except Exception as e:
        import sys as _sys
        print(f"[font_manager] フォントダウンロード失敗 ({style}): {e}", file=_sys.stderr)
        return Path()


def _find_system_font(style: str) -> Path | None:
    """OS別にシステムにインストールされたフォントを探す。"""
    if sys.platform == "darwin":
        for path in _SYSTEM_FONTS_MACOS.get(style, []):
            if path.exists():
                return path

    elif sys.platform == "win32":
        import os
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        for fname in _SYSTEM_FONTS_WINDOWS.get(style, []):
            p = windir / "Fonts" / fname
            if p.exists():
                return p

    else:  # Linux
        for path in _SYSTEM_FONTS_LINUX.get(style, []):
            if path.exists():
                return path

    return None


def _download_font(style: str, dest: Path) -> None:
    url = _DOWNLOAD_FONTS[style]["url"]
    print(f"[font_manager] フォントをダウンロード中 ({style}): {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"[font_manager] 保存完了: {dest}")
