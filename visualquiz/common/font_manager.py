"""フォント管理モジュール。漢字表示に必要なフォントを自動取得・管理する。"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

# プロジェクトルートのassetsディレクトリ
ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# 源ノ明朝（Noto Serif CJK JP）- SIL Open Font License
FONT_URL = (
    "https://github.com/googlefonts/noto-cjk/raw/main/Serif/SubsetOTF/JP/"
    "NotoSerifCJKjp-Regular.otf"
)
FONT_FILENAME = "NotoSerifCJKjp-Regular.otf"

# フォールバック：NotoSansの軽量版
FALLBACK_FONT_URL = (
    "https://github.com/notofonts/noto-cjk/releases/download/"
    "Sans2.004R/03_NotoSansCJKjp.zip"
)


def get_font_path(bold: bool = False) -> Path:
    """利用可能な漢字対応フォントのパスを返す。

    フォントが存在しない場合は自動ダウンロードを試みる。
    ダウンロードに失敗した場合はシステムフォントにフォールバックする。
    """
    font_path = ASSETS_DIR / FONT_FILENAME
    if font_path.exists():
        return font_path

    # システムフォントを探す（macOS / Linux / Windows）
    system_font = _find_system_font()
    if system_font:
        return system_font

    # ダウンロード試行
    try:
        _download_font(font_path)
        return font_path
    except Exception as e:
        print(f"[font_manager] フォントダウンロード失敗: {e}", file=sys.stderr)
        print("[font_manager] Pillowのデフォルトフォントを使用します", file=sys.stderr)
        return Path()  # 空パス = Pillowデフォルトフォント


def _find_system_font() -> Path | None:
    """OSごとにシステムにインストールされた日本語フォントを探す。"""
    candidates: list[Path] = []

    if sys.platform == "darwin":
        candidates = [
            Path("/System/Library/Fonts/ヒラギノ明朝 ProN W3.ttc"),
            Path("/System/Library/Fonts/Hiragino Mincho ProN W3.ttc"),
            Path("/Library/Fonts/Arial Unicode MS.ttf"),
            Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        ]
    elif sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        candidates = [
            Path(windir) / "Fonts" / "msgothic.ttc",
            Path(windir) / "Fonts" / "meiryo.ttc",
            Path(windir) / "Fonts" / "YuMincho.ttc",
        ]
    else:
        # Linux
        candidates = [
            Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/noto-cjk/NotoSerifCJKjp-Regular.otf"),
        ]

    for path in candidates:
        if path.exists():
            return path
    return None


def _download_font(dest: Path) -> None:
    """フォントファイルをダウンロードする。"""
    print(f"[font_manager] フォントをダウンロード中: {FONT_URL}")
    urllib.request.urlretrieve(FONT_URL, dest)
    print(f"[font_manager] 保存完了: {dest}")
