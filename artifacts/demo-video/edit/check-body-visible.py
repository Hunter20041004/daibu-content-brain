#!/usr/bin/env python3
"""Regression check: the demo must visibly show the generated article body."""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

from PIL import Image


FRAME_TIME_SECONDS = "40"
BODY_TEXT_CROP = (700, 300, 1170, 425)
MIN_DARK_PIXEL_RATIO = 0.01


def extract_frame(video_path: Path) -> Image.Image:
    result = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-ss",
            FRAME_TIME_SECONDS,
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    return Image.open(io.BytesIO(result.stdout)).convert("RGB")


def dark_pixel_ratio(image: Image.Image) -> float:
    crop = image.crop(BODY_TEXT_CROP)
    dark_pixels = 0
    total_pixels = crop.width * crop.height
    for red, green, blue in crop.get_flattened_data():
        luminance = (299 * red + 587 * green + 114 * blue) / 1000
        dark_pixels += luminance < 150
    return dark_pixels / total_pixels


def main() -> int:
    video_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("final.mp4")
    ratio = dark_pixel_ratio(extract_frame(video_path))
    print(f"正文可視深色像素比例：{ratio:.4f}")
    if ratio < MIN_DARK_PIXEL_RATIO:
        print("FAIL：影片雖顯示 478 字，但正文文字在畫面上不可見。")
        return 1
    print("PASS：正文文字在影片畫面上可讀。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
