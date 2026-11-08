"""Assemble a Codex v2 pet atlas from HeiXia's registered assets."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CELL = (192, 208)
FRAME_SIZE = (640, 360)
# State, source filename, zero-based source frames, and Codex display times in ms.
ROWS = (
    ("idle", "思考.webm", (16, 18, 20, 22, 24, 26), (1680, 660, 660, 840, 840, 1920)),
    ("running-right", "rightward.webm", tuple(range(8)), (120,) * 7 + (220,)),
    ("running-left", "巡视.webm", (1, 3, 5, 7, 9, 11, 13, 15), (120,) * 7 + (220,)),
    ("waving", "洗脸.webm", (5, 8, 11, 14), (140, 140, 140, 280)),
    ("jumping", None, (), (140, 140, 140, 140, 280)),
    ("failed", "困困.webm", (0, 2, 4, 6, 8, 10, 12, 14), (140,) * 7 + (240,)),
    ("waiting", "等你.webm", (1, 4, 7, 10, 13, 16), (150,) * 5 + (260,)),
    ("running", "回应.webm", (10, 12, 14, 16, 18, 20), (120,) * 5 + (220,)),
    ("review", "工作.webm", (0,) * 6, (150,) * 5 + (280,)),
)


def decode_frames(source: Path, indices: tuple[int, ...]) -> list[Image.Image]:
    # FFmpeg's native VP9 decoder discards the separately encoded alpha plane.
    raw = subprocess.check_output([
        "ffmpeg", "-nostdin", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(source),
        "-an", "-frames:v", str(max(indices) + 1), "-pix_fmt", "rgba", "-f", "rawvideo", "-",
    ])
    width, height = FRAME_SIZE
    frame_bytes = width * height * 4
    if len(raw) != frame_bytes * (max(indices) + 1):
        raise ValueError(f"Unexpected source dimensions or frame count: {source.name}")
    frames = []
    for index in indices:
        offset = index * frame_bytes
        frame = Image.frombytes("RGBA", FRAME_SIZE, raw[offset:offset + frame_bytes])
        alpha = frame.getchannel("A").point(lambda value: value if value > 8 else 0)
        if not alpha.getbbox() or alpha.getextrema()[0] != 0:
            raise ValueError(f"Missing transparency or subject in {source.name} frame {index}")
        frame.putalpha(alpha)
        frames.append(frame)
    return frames


def normalize_row(frames: list[Image.Image]) -> list[Image.Image]:
    # Register a whole row together so walking, stretching and rolling retain their motion.
    boxes = [frame.getchannel("A").getbbox() for frame in frames]
    crop = (
        min(box[0] for box in boxes), min(box[1] for box in boxes),
        max(box[2] for box in boxes), max(box[3] for box in boxes),
    )
    width, height = crop[2] - crop[0], crop[3] - crop[1]
    scale = min(176 / width, 174 / height)
    size = (round(width * scale), round(height * scale))
    origin = ((CELL[0] - size[0]) // 2, 192 - size[1])
    tiles = []
    for frame in frames:
        tile = Image.new("RGBA", CELL)
        tile.alpha_composite(frame.crop(crop).resize(size, Image.Resampling.LANCZOS), origin)
        tiles.append(tile)
    return tiles


def write_preview(directory: Path, state: str, tiles: list[Image.Image], durations: tuple[int, ...]):
    previews = []
    for tile in tiles:
        background = Image.new("RGBA", CELL, "#eff3f1")
        background.alpha_composite(tile)
        previews.append(background.convert("RGB"))
    if state == "review":
        previews[0].save(directory / "review.png")
        return
    previews[0].save(directory / f"{state}.gif", save_all=True, append_images=previews[1:],
                     duration=list(durations), loop=0)


def read_tiles(source: Path, columns: int, rows: int) -> list[Image.Image]:
    with Image.open(source) as image:
        width, height = CELL
        if image.mode != "RGBA" or image.size != (width * columns, height * rows):
            raise ValueError(f"Unexpected sprite strip geometry: {source}")
        return [
            image.crop((x * width, y * height, (x + 1) * width, (y + 1) * height))
            for y in range(rows)
            for x in range(columns)
        ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-dir", type=Path, required=True, help="Published heixia-animation directory")
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    atlas = Image.new("RGBA", (CELL[0] * 8, CELL[1] * 11))
    package = args.output / "heixia"
    preview_dir = args.output / "previews"
    package.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    for row, (state, filename, indices, durations) in enumerate(ROWS):
        if filename is None:
            source = ROOT / "source" / "jumping.webp"
            tiles = read_tiles(source, 5, 1)
        else:
            source = (ROOT / "source" if state == "running-right" else args.media_dir) / filename
            tiles = normalize_row(decode_frames(source, indices))
        for column, tile in enumerate(tiles):
            atlas.alpha_composite(tile, (column * CELL[0], row * CELL[1]))
        write_preview(preview_dir, state, tiles, durations)
        print(f"{state}: {source.name}, {len(tiles)} frames")
    neutral, = read_tiles(ROOT / "source" / "neutral.webp", 1, 1)
    atlas.alpha_composite(neutral, (6 * CELL[0], 0))
    look = read_tiles(ROOT / "source" / "look.webp", 8, 2)
    for index, tile in enumerate(look):
        atlas.alpha_composite(tile, (index % 8 * CELL[0], (9 + index // 8) * CELL[1]))
    write_preview(preview_dir, "look", look, (170,) * 16)
    atlas.save(package / "spritesheet.webp", lossless=True, method=6, exact=True)


if __name__ == "__main__":
    main()
