#!/usr/bin/env python3
"""Split a long marketing image into overlapping tiles and write a coverage manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image


def axis_starts(length: int, tile: int, overlap: int) -> list[int]:
    if length <= tile:
        return [0]
    stride = tile - overlap
    starts = list(range(0, max(length - tile, 0) + 1, stride))
    last = length - tile
    if starts[-1] != last:
        starts.append(last)
    return starts


def axis_is_covered(length: int, tile: int, starts: list[int]) -> bool:
    cursor = 0
    for start in sorted(starts):
        if start > cursor:
            return False
        cursor = max(cursor, min(length, start + tile))
    return cursor >= length


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_image(
    source: Path,
    output_dir: Path,
    tile_width: int,
    tile_height: int,
    overlap_x: int,
    overlap_y: int,
) -> dict:
    if tile_width <= overlap_x or tile_height <= overlap_y:
        raise ValueError("tile dimensions must be greater than overlaps")
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.load()
        width, height = image.size
        xs = axis_starts(width, tile_width, overlap_x)
        ys = axis_starts(height, tile_height, overlap_y)
        tiles = []
        index = 1
        for row, y in enumerate(ys, start=1):
            for col, x in enumerate(xs, start=1):
                right = min(width, x + tile_width)
                bottom = min(height, y + tile_height)
                crop = image.crop((x, y, right, bottom))
                filename = f"tile_r{row:03d}_c{col:03d}_{x}_{y}_{right}_{bottom}.png"
                destination = output_dir / filename
                crop.save(destination, "PNG")
                tiles.append(
                    {
                        "tile_id": f"tile-{index:04d}",
                        "row": row,
                        "column": col,
                        "path": str(destination.resolve()),
                        "x": x,
                        "y": y,
                        "width": right - x,
                        "height": bottom - y,
                        "right": right,
                        "bottom": bottom,
                        "sha256": sha256(destination),
                    }
                )
                index += 1
    coverage_ok = axis_is_covered(width, tile_width, xs) and axis_is_covered(height, tile_height, ys)
    manifest = {
        "manifest_version": "1.0",
        "source_path": str(source.resolve()),
        "source_sha256": sha256(source),
        "source_width": width,
        "source_height": height,
        "tile_width": tile_width,
        "tile_height": tile_height,
        "overlap_x": overlap_x,
        "overlap_y": overlap_y,
        "tile_count": len(tiles),
        "coverage_ok": coverage_ok,
        "uncovered_rectangles": [] if coverage_ok else [{"reason": "tile_grid_gap"}],
        "tiles": tiles,
    }
    manifest_path = output_dir / "coverage_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tile-width", type=int, default=1800)
    parser.add_argument("--tile-height", type=int, default=2200)
    parser.add_argument("--overlap-x", type=int, default=180)
    parser.add_argument("--overlap-y", type=int, default=220)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = split_image(
            args.input,
            args.output_dir,
            args.tile_width,
            args.tile_height,
            args.overlap_x,
            args.overlap_y,
        )
        print(json.dumps({
            "manifest": str((args.output_dir / "coverage_manifest.json").resolve()),
            "tile_count": manifest["tile_count"],
            "coverage_ok": manifest["coverage_ok"],
        }, ensure_ascii=False))
        return 0 if manifest["coverage_ok"] else 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
