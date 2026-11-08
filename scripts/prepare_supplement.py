"""Register the approved GPT jump and the mixed real/GPT look poses."""

import argparse
from pathlib import Path
from statistics import median

from PIL import Image

from build_atlas import CELL, ROOT


def isolate(frame: Image.Image) -> Image.Image:
    frame = frame.convert("RGBA")
    alpha = frame.getchannel("A").point(lambda value: max(0, min(255, round((value - 10) * 255 / 238))))
    box = alpha.getbbox()
    if box is None:
        raise ValueError("Expected an isolated cat in the source tile")
    frame.putalpha(alpha)
    return frame.crop(box)


def split(source: Path, columns: int, rows: int, count: int) -> list[Image.Image]:
    with Image.open(source) as image:
        if image.mode != "RGBA":
            raise ValueError(f"Expected transparent RGBA artwork: {source}")
        width, height = image.size
        return [
            isolate(image.crop((
                (i % columns) * width // columns, (i // columns) * height // rows,
                (i % columns + 1) * width // columns, (i // columns + 1) * height // rows,
            )))
            for i in range(count)
        ]


def place(frame: Image.Image, scale: float, baseline: int, align_paws: bool) -> Image.Image:
    resized = frame.resize((round(frame.width * scale), round(frame.height * scale)), Image.Resampling.LANCZOS)
    center = resized.width / 2
    if align_paws:
        # Register the contact point rather than centering on the head as it turns.
        bottom = resized.getchannel("A").crop((0, resized.height - 18, resized.width, resized.height))
        paws = bottom.point(lambda value: 255 if value > 96 else 0).getbbox()
        if paws:
            center = (paws[0] + paws[2]) / 2
    x = round(CELL[0] / 2 - center)
    y = baseline - resized.height
    if min(x, y) < 4 or x + resized.width > CELL[0] - 4 or baseline > CELL[1] - 4:
        raise ValueError("Cat would come too close to a sprite tile boundary")
    tile = Image.new("RGBA", CELL)
    tile.alpha_composite(resized, (x, y))
    return tile


def write_strip(path: Path, tiles: list[Image.Image], columns: int):
    width, height = CELL
    strip = Image.new("RGBA", (width * columns, height * (len(tiles) // columns)))
    for index, tile in enumerate(tiles):
        strip.alpha_composite(tile, (index % columns * width, index // columns * height))
    strip.save(path, lossless=True, method=6, exact=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpt-dir", type=Path, required=True)
    parser.add_argument("--real-gaze-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "source")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    jump = split(args.gpt_dir / "jumping.png", 3, 2, 5)
    jump_scale = min(172 / max(frame.width for frame in jump), 137 / max(frame.height for frame in jump))
    jump_tiles = [place(frame, jump_scale, baseline, False)
                  for frame, baseline in zip(jump, (192, 176, 152, 170, 192))]
    write_strip(args.output / "jumping.webp", jump_tiles, 5)

    generated = split(args.gpt_dir / "look-right.png", 4, 2, 8)
    generated += split(args.gpt_dir / "look-left.png", 4, 2, 8)
    generated_scale = min(170 / median(frame.height for frame in generated),
                          181 / max(frame.height for frame in generated))
    tiles = [place(frame, generated_scale, 192, True) for frame in generated]
    real = {name: split(args.real_gaze_dir / f"{name}.png", 1, 1, 1)[0]
            for name in ("neutral", "right", "down", "left")}
    real_scale = min(170 / real["neutral"].height, 181 / max(frame.height for frame in real.values()))
    # V010 preserves three usable directions and the resting neutral pose.
    for index, name in ((4, "right"), (8, "down"), (12, "left")):
        tiles[index] = place(real[name], real_scale, 192, True)
    write_strip(args.output / "look.webp", tiles, 8)
    write_strip(args.output / "neutral.webp", [place(real["neutral"], real_scale, 192, True)], 1)


if __name__ == "__main__":
    main()
