# 07 — Tile encoding and reduction kernel benchmark (WP06)

Measured 2026-11-15 on macOS arm64 (Darwin 25.4.0) with the pinned pipeline environment: Python 3.13,
Pillow 13.0.0 (libwebp 1.6.0, zlib `1.3.1.zlib-ng`), NumPy 2.5.4; `oxipng 10.2.1` from Homebrew (optional).
Reproduce with:

```sh
PYTHONPATH=pipeline uv run --project pipeline python -m export.benchmark --render tests/fixtures/render-synthetic \
  --scene tests/fixtures/scene-synthetic --city tests/fixtures/city-synthetic/city.json
```

**Inputs.** The synthetic fixture render only (726 × 481 px, 256 px tiles + 1 px overlap, levels 0–10,
17 tiles). The real Villena render (`build/villena/render/`) **was not available** in this worktree, so no
real-city numbers exist yet; the fixture is a flat two-tone checkerboard with one road and red POI crosses,
far simpler than real pixel art, so its absolute sizes are a lower bound.

## Results (fixture)

| format | kernel | tiles | total bytes | median B/tile | max B/tile | encode s | maxLevel decode == master | byte-stable (re-encode) |
|---|---|---|---|---|---|---|---|---|
| PNG indexed (Pillow, zlib 9) | mode | 17 | 19 838 | 1 163 | 3 258 | 0.017 | yes | yes |
| WebP lossless (`method=6`) | mode | 17 | 12 710 | 788 | 2 170 | 2.418 | yes | yes |
| PNG indexed + `oxipng -o max --strip safe` | mode | 17 | 13 792 | 823 | 2 172 | 0.188 | yes | n/a |
| PNG (indexed where ≤ 256 colours, else RGB) | mean | 17 | 29 423 | 1 483 | 4 649 | 0.019 | yes | yes |
| WebP lossless (`method=6`) | mean | 17 | 21 772 | 984 | 4 258 | 4.725 | yes | yes |
| PNG + `oxipng -o max --strip safe` | mean | 17 | 23 357 | 1 102 | 3 995 | 0.154 | yes | n/a |

- *Decode correctness*: every `maxLevel` tile decodes to exactly the flattened master-image pixels it was cut
  from, in every format (also asserted by `test_png_and_webp_decode_identically`).
- *Byte stability*: re-encoding every tile in the same process gives identical bytes, and two full `build` runs
  give an identical tree hash (`test_build_and_pack_are_reproducible`). Cross-platform byte identity
  (macOS arm64 vs `linux/amd64`) was **not measured** here; the contract only requires identical *decoded*
  pixels across platforms, which lossless encoding guarantees.
- *Encode time*: WebP `method=6` is ~140× slower than PNG (≈ 0.14 s per 257 px tile here); oxipng adds ~10×.
  Timings are wall clock for one run, single process, and only indicative.

Colours per pyramid level (union over all tiles of the level):

| level | mode | mean |
|---|---|---|
| 10 | 5 | 5 |
| 9 | 5 | 41 |
| 8 | 5 | 177 |
| 7 | 4 | 337 |
| 6 | 4 | 230 |
| 5–3 | 4 | 108 → 19 |
| 2–0 | 1 | 6 → 1 |

## Kernel trade-off (observed)

Levels 9–7 were rendered side by side, magnified with nearest neighbour.

- **Mean** (box, `(a+b+c+d+2)//4`, what the fixture uses) invents colours: up to 337 distinct colours at
  level 7 from a 5-colour palette, so some tiles fall back to RGB PNG and the set is 48 % larger. Visually it
  turns the checkerboard into a soft blur and the red POI cross into a faint brownish smudge — smooth but no
  longer pixel art.
- **Mode** (most frequent of the 2×2, ties broken top-left → top-right → bottom-left → bottom-right) keeps the
  palette exactly at every level, so every tile stays indexed and the set is smallest. It drops 1 px features:
  the 1 px red POI cross survives to level 8 as a dot and is gone at level 7; the checkerboard aliases into
  irregular blocks at level 7, and at levels ≤ 2 the background majority swallows the ground entirely. Real
  1 px outlines and thin streets will behave the same way when zoomed far out.

**Default: mode.** The project is pixel art viewed with nearest-neighbour magnification; palette-exact
lower levels keep that look, guarantee indexed PNG, and are the smallest. The loss of 1 px detail only
affects zoomed-out levels where such detail is sub-pixel on screen anyway. `--kernel mean` remains available
and reproduces the fixture's lower levels pixel-exactly.

## Recommendation

**Indexed PNG with the mode kernel** (city config `tiles.format: "png"`, unchanged).

- Lossless WebP is the smallest (−36 % vs plain indexed PNG on this fixture), but only −8 % vs PNG
  after `oxipng`, and it encodes two orders of magnitude slower. Indexed PNG stores palette indices, so tiles
  stay inspectable and exact by construction (research 04 §G reached the same conclusion on one synthetic tile).
- `oxipng` gives −30 % on top and is worth running as an optional release-time post-pass (WP12); it is not a
  dependency of `export.build`, and its output was not checked for byte stability across versions.
- Switch the city config to `webp` only if the real Villena tile set approaches the budget; the exporter
  already supports it.

## Projected size of a 1 km² city

Villena's config (8 px/m, heading 45°, pitch 30°) gives a master image of ≈ 11 300 × 6 500 px
(`docs/COSTS.md`) = 73.5 Mpx; with 512 px tiles that is 23 × 13 = 299 `maxLevel` tiles, ≈ 400 with the pyramid.

| bytes per master pixel (whole pyramid) | source | projected tile set |
|---|---|---|
| 0.057 | this fixture, PNG + mode (19 838 B / 349 206 px) | ≈ 4 MB |
| 0.068 | 32-colour dithered tile, research 04 §G (13 283 B / 512², × 4/3 pyramid) | ≈ 5 MB |
| 0.34–0.88 | `docs/COSTS.md` estimate (25–65 MB) | 25–65 MB |
| 1.33 | bound for indexed tiles that do not compress at all (1 B/px × 4/3) | ≈ 98 MB |

Every case sits below the **250 MB** site budget, including incompressible indexed tiles.
RGB fallback tiles (only possible with `--kernel mean` or a > 256-colour render) are not covered by the last row.
These are projections from synthetic content — re-measure on the first real Villena render with
`export.validate --max-bytes 262144000`, which prints the per-level size table.
