"""MP4動画エクスポート共通処理。numpy配列フレームリストをMP4に変換する。"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def frames_to_mp4(
    frames: list[np.ndarray],
    output_path: Path | str,
    fps: int = 30,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """フレームリスト（numpy配列）をMP4ファイルに書き出す。

    Args:
        frames: RGB numpy配列のリスト。各要素は shape (H, W, 3)。
        output_path: 出力先ファイルパス（.mp4）。
        fps: フレームレート。
        width: 動画の横幅（px）。
        height: 動画の縦幅（px）。

    Returns:
        書き出したファイルのPathオブジェクト。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # フレームをuint8に統一
    normalized = [
        (f.astype(np.uint8) if f.dtype != np.uint8 else f) for f in frames
    ]

    # moviepy v2系とv1系の両方に対応
    try:
        from moviepy import ImageSequenceClip  # v2.x
    except ImportError:
        try:
            from moviepy.editor import ImageSequenceClip  # v1.x
        except ImportError:
            raise ImportError("moviepyをインストールしてください: pip install moviepy")

    clip = ImageSequenceClip(normalized, fps=fps)
    clip.write_videofile(
        str(output_path),
        codec="libx264",
        audio=False,
        logger=None,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    )
    clip.close()
    return output_path


def repeat_frame(frame: np.ndarray, duration_sec: float, fps: int = 30) -> list[np.ndarray]:
    """同じフレームをduration_sec秒分繰り返したリストを返す。"""
    count = max(1, int(duration_sec * fps))
    return [frame] * count


def blank_frame(
    width: int = 1280, height: int = 720, color: tuple[int, int, int] = (0, 0, 0)
) -> np.ndarray:
    """単色の空フレームを生成する。"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :] = color
    return frame
