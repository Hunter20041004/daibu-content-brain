"""Burn approved captions by exact frame index after all video edits."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 30
FRAME_BYTES = WIDTH * HEIGHT * 3
FONT_PATH = Path("assets/fonts/LINESeedTW_OTF_Bd.otf")


@dataclass(frozen=True)
class Cue:
    start_frame: int
    end_frame: int
    text: str


def timestamp_frames(value: str) -> int:
    hours, minutes, remainder = value.split(":")
    seconds, milliseconds = remainder.split(",")
    total_seconds = (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )
    return round(total_seconds * FPS)


def read_cues(path: Path) -> list[Cue]:
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    cues = []
    for block in blocks:
        lines = block.splitlines()
        match = re.fullmatch(
            r"(\d{2}:\d{2}:\d{2},\d{3}) --> "
            r"(\d{2}:\d{2}:\d{2},\d{3})",
            lines[1],
        )
        if match is None:
            raise ValueError(f"Invalid SRT timing: {lines[1]}")
        cues.append(
            Cue(
                timestamp_frames(match.group(1)),
                timestamp_frames(match.group(2)),
                " ".join(lines[2:]).strip(),
            )
        )
    return cues


def caption_layer(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    padding_x = 26
    padding_y = 15
    pill_width = min(text_width + padding_x * 2, 1020)
    pill_height = text_height + padding_y * 2
    left = (WIDTH - pill_width) // 2
    top = HEIGHT - pill_height - 34
    draw.rounded_rectangle(
        (left, top, left + pill_width, top + pill_height),
        radius=18,
        fill=(17, 21, 47, 226),
        outline=(132, 207, 219, 210),
        width=2,
    )
    draw.text(
        (WIDTH // 2, top + pill_height // 2 - 1),
        text,
        font=font,
        fill=(255, 255, 255, 255),
        anchor="mm",
    )
    return layer


def burn(input_video: Path, srt: Path, output_video: Path) -> None:
    cues = read_cues(srt)
    font = ImageFont.truetype(str(FONT_PATH), 28)
    layers = {cue.text: caption_layer(cue.text, font) for cue in cues}

    decoder = subprocess.Popen(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            str(input_video),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-r",
            str(FPS),
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_video),
        ],
        stdin=subprocess.PIPE,
    )
    assert decoder.stdout is not None
    assert encoder.stdin is not None

    frame_index = 0
    try:
        while True:
            raw_frame = decoder.stdout.read(FRAME_BYTES)
            if not raw_frame:
                break
            if len(raw_frame) != FRAME_BYTES:
                raise RuntimeError("Decoder returned an incomplete video frame")
            active = next(
                (
                    cue
                    for cue in cues
                    if cue.start_frame <= frame_index < cue.end_frame
                ),
                None,
            )
            if active is None:
                output_frame = raw_frame
            else:
                base = Image.frombytes("RGB", (WIDTH, HEIGHT), raw_frame)
                output_frame = Image.alpha_composite(
                    base.convert("RGBA"),
                    layers[active.text],
                ).convert("RGB").tobytes()
            encoder.stdin.write(output_frame)
            frame_index += 1
    finally:
        decoder.stdout.close()
        encoder.stdin.close()

    decoder_status = decoder.wait()
    encoder_status = encoder.wait()
    if decoder_status != 0 or encoder_status != 0:
        raise RuntimeError(
            f"Caption burn failed: decoder={decoder_status}, "
            f"encoder={encoder_status}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_video", type=Path)
    parser.add_argument("srt", type=Path)
    parser.add_argument("output_video", type=Path)
    arguments = parser.parse_args()
    burn(arguments.input_video, arguments.srt, arguments.output_video)


if __name__ == "__main__":
    main()
