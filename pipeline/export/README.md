# pipeline/export — render → published tiles (WP06)

Contract: `docs/contracts/render.md` §2 and `docs/contracts/projection.md` §4–6. Run from the repository root.

```sh
# build: render + scene + city config -> tile directory (manifest.json, pois.json, height.u16, <style>/<L>/<c>_<r>.<fmt>)
PYTHONPATH=pipeline uv run --project pipeline python -m export.build --render build/villena/render \
  --scene build/villena/scene --city cities/villena/city.json --out build/villena/tiles --release <release> \
  [--style-id procedural] [--style-label Procedural] [--kernel mode|mean]

# validate (independent of build); --render also checks renderSha256 and the palette
PYTHONPATH=pipeline uv run --project pipeline python -m export.validate build/villena/tiles [--max-bytes 262144000] [--render build/villena/render]

# pack: reproducible archive + tiles.lock.json entry (refuses an invalid directory)
PYTHONPATH=pipeline uv run --project pipeline python -m export.pack build/villena/tiles --out build/villena/tiles.tar.gz

# benchmark (docs/research/07-tile-encoding-benchmark.md)
PYTHONPATH=pipeline uv run --project pipeline python -m export.benchmark --render <dir> --scene <dir> --city <city.json>
```

`make tiles CITY=villena RELEASE=<release>` and `make validate-tiles CITY=villena` wrap build and validate.

Choices (measured in `docs/research/07-tile-encoding-benchmark.md`):

- Reduction kernel: **mode** (most frequent of the 2×2 source pixels, ties go top-left, top-right, bottom-left,
  bottom-right) — palette-exact at every level. `--kernel mean` is the box mean `(a+b+c+d+2)//4` used by the fixture.
- Format: the city config's `tiles.format`. PNG is indexed when a tile has ≤ 256 colours (always, with the mode
  kernel), zlib level 9, no ancillary chunks. WebP is lossless, `method=6`, `exact`.
- Height grid: bilinear resample of `terrain.f32` to 4 m cell centres, `uint16-le`, scale 0.01 m,
  offset `floor(min H)`.
- `geoToWorld`: least-squares affine over a 9×9 grid on AOI + margin (centred), residual measured on 33×33.
- Pinned: Pillow 13.0.0 (its wheel reports libwebp 1.6.0 and zlib `1.3.1.zlib-ng` on macOS arm64), NumPy 2.5.4, PyProj 3.8.0 (`pipeline/uv.lock`).
