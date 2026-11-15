"""Tile encoding benchmark (docs/research/07-tile-encoding-benchmark.md). Prints Markdown tables.

PYTHONPATH=pipeline uv run --project pipeline python -m export.benchmark --render <dir> --scene <dir> --city <city.json>
"""

import argparse
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

from export.build import encode, load_json, load_render, pack_rgb, pyramid


def decode(data: bytes, path: Path) -> np.ndarray:
    path.write_bytes(data)
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render", type=Path, required=True)
    ap.add_argument("--scene", type=Path, required=True)
    ap.add_argument("--city", type=Path, required=True)
    args = ap.parse_args()
    city = load_json(args.city, "city-config")
    _, _, master = load_render(args.render, args.scene)
    size, overlap = city["tiles"]["tileSize"], city["tiles"]["tileOverlap"]
    oxipng = shutil.which("oxipng")
    tmp = Path(tempfile.mkdtemp())
    print(f"master {master.shape[1]}x{master.shape[0]} px, tile {size}+{overlap}, oxipng: {oxipng or 'absent'}")
    print("\n| format | kernel | tiles | total bytes | median B/tile | max B/tile | encode s "
          "| maxLevel decode == master | byte-stable (re-encode) |")
    print("|---|---|---|---|---|---|---|---|---|")
    levels: dict[str, dict[int, np.ndarray]] = {}
    for kernel in ("mode", "mean"):
        tiles = list(pyramid(master, size, overlap, kernel))
        top = tiles[0][0]
        levels[kernel] = {}
        for fmt in ("png", "webp", "png+oxipng"):
            if fmt == "png+oxipng" and not oxipng:
                continue
            t0 = time.perf_counter()
            blobs = [encode(t, "webp" if fmt == "webp" else "png") for *_, t in tiles]
            if fmt == "png+oxipng":
                for i, b in enumerate(blobs):
                    (tmp / f"{i}.png").write_bytes(b)
                subprocess.run([oxipng, "-q", "-o", "max", "--strip", "safe", *map(str, sorted(tmp.glob("*.png")))],
                               check=True)
                blobs = [(tmp / f"{i}.png").read_bytes() for i in range(len(blobs))]
            elapsed = time.perf_counter() - t0
            stable = "n/a" if fmt == "png+oxipng" else (
                "yes" if all(encode(t, fmt) == b for (*_, t), b in zip(tiles, blobs, strict=True)) else "NO")
            ok = all(np.array_equal(decode(b, tmp / "d"), t) for (lvl, *_, t), b in zip(tiles, blobs, strict=True)
                     if lvl == top)
            sizes = [len(b) for b in blobs]
            print(f"| {fmt} | {kernel} | {len(sizes)} | {sum(sizes)} | {statistics.median(sizes):.0f} | {max(sizes)} | "
                  f"{elapsed:.3f} | {'yes' if ok else 'NO'} | {stable} |")
        for lvl, _, _, t in tiles:
            levels[kernel][lvl] = np.union1d(levels[kernel].get(lvl, []), pack_rgb(t))
    print("\n| level | colours (mode) | colours (mean) | indexed PNG possible (mean) |")
    print("|---|---|---|---|")
    for lvl in sorted(levels["mode"], reverse=True):
        a, b = (len(levels[k][lvl]) for k in ("mode", "mean"))
        print(f"| {lvl} | {a} | {b} | {'yes' if b <= 256 else 'no'} |")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
