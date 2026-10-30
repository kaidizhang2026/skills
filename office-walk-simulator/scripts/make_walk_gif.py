#!/usr/bin/env python3
"""Turn one landscape image into a subtle three-step looping GIF."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageEnhance


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a gentle first-person walking loop from a still image."
    )
    parser.add_argument("input", type=Path, help="source PNG/JPEG/WebP image")
    parser.add_argument("output", type=Path, help="destination .gif path")
    parser.add_argument("--steps", type=positive_int, default=3, help="steps per loop")
    parser.add_argument("--fps", type=positive_int, default=12, help="frames per second")
    parser.add_argument("--seconds", type=float, default=3.6, help="loop duration")
    parser.add_argument("--bob", type=float, default=8.0, help="vertical motion in pixels")
    parser.add_argument("--sway", type=float, default=5.0, help="horizontal motion in pixels")
    parser.add_argument("--zoom", type=float, default=1.07, help="base crop zoom")
    parser.add_argument("--width", type=positive_int, default=960, help="output width")
    return parser


def make_frame(
    source: Image.Image,
    width: int,
    height: int,
    phase: float,
    steps: int,
    bob: float,
    sway: float,
    zoom: float,
) -> Image.Image:
    stride = 2 * math.pi * steps * phase
    y_offset = bob * math.sin(stride)
    x_offset = sway * math.sin(stride / 2)
    breathing_zoom = zoom + 0.008 * (1 - math.cos(stride)) / 2

    scaled_w = max(width + 2, round(width * breathing_zoom))
    scaled_h = max(height + 2, round(height * breathing_zoom))
    scaled = source.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    left = (scaled_w - width) / 2 + x_offset
    top = (scaled_h - height) / 2 + y_offset
    left = min(max(left, 0), scaled_w - width)
    top = min(max(top, 0), scaled_h - height)
    frame = scaled.crop((round(left), round(top), round(left) + width, round(top) + height))

    lift = 1.0 + 0.012 * max(0.0, math.sin(stride))
    return ImageEnhance.Brightness(frame).enhance(lift)


def main() -> None:
    args = build_parser().parse_args()
    if args.seconds <= 0:
        raise SystemExit("--seconds must be greater than zero")
    if args.zoom < 1.0:
        raise SystemExit("--zoom must be at least 1.0")
    if args.output.suffix.lower() != ".gif":
        raise SystemExit("output path must end in .gif")

    with Image.open(args.input) as opened:
        source = opened.convert("RGB")

    width = min(args.width, source.width)
    height = max(2, round(width * source.height / source.width))
    source = source.resize((width, height), Image.Resampling.LANCZOS)

    frame_count = max(2, round(args.fps * args.seconds))
    frames = [
        make_frame(
            source,
            width,
            height,
            index / frame_count,
            args.steps,
            args.bob,
            args.sway,
            args.zoom,
        )
        for index in range(frame_count)
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = round(1000 / args.fps)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=True,
    )
    print(f"Created {args.output} ({frame_count} frames, {duration_ms} ms/frame)")


if __name__ == "__main__":
    main()
