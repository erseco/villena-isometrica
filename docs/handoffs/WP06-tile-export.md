# Handoff — WP06 Tile export and publication format

| Field | Value |
|---|---|
| Task ID | WP06 |
| Date (UTC) | 2026-11-15 |
| Provider / client | Anthropic Claude Code (subagent of a workflow run) |
| Model and effort actually used | `claude-opus-5-5`, effort medium (assigned by the owner instead of the prompt's recommended Codex Sol / fallback Sonnet) |
| Branch | `feature/wp06-tile-export` |
| Base commit | `7a2342951ef691acd9c2fae25bad68016b65b767` |
| Head commit | `7626922` (code) + the commit adding this handoff |
| Status | READY FOR REVIEW |

## Changed files

```
 docs/research/07-tile-encoding-benchmark.md |  95 ++++++++
 pipeline/export/README.md                   |  32 +++
 pipeline/export/__init__.py                 |   1 +
 pipeline/export/benchmark.py                |  76 +++++++
 pipeline/export/build.py                    | 331 ++++++++++++++++++++++++++++
 pipeline/export/pack.py                     |  60 +++++
 pipeline/export/validate.py                 | 228 +++++++++++++++++++
 pipeline/tests/export/test_export.py        | 195 ++++++++++++++++
 docs/handoffs/WP06-tile-export.md           (this file)
```

- `build.py`: validates render/scene/city/scene-pois against the schemas, layer `sha256` **and** decoded
  `pixelSha256`, `sceneSha256`, palette sha and palette membership of drawn pixels; flattens, cuts the
  pyramid, writes POIs, height grid, `geoToWorld`, manifest (sorted keys, schema-checked before writing).
- `validate.py`: independent of build (own tile enumeration from the manifest, own forward projection, own
  camera check). Optional `--render <dir>` checks `renderSha256` and the palette.
- `pack.py`: validates first, refuses a directory containing the fixture's `expected.json`.
- `benchmark.py`: produces the tables in the research doc.
- No dependency added; `pipeline/pyproject.toml` / `uv.lock` untouched.

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `make install` | pass | `uv sync` ok; viewer and rendering skipped (not present) |
| `uv sync --project pipeline --frozen` | pass | "Checked 29 packages" |
| `uv run --project pipeline ruff check pipeline/export pipeline/tests/export` | pass | "All checks passed!" |
| `uv run --project pipeline pytest pipeline/tests/export -q` | pass | 18 passed |
| `... python -m export.build --render tests/fixtures/render-synthetic --scene tests/fixtures/scene-synthetic --city tests/fixtures/city-synthetic/city.json --out build/planeville/tiles --release fixture-1` | pass | 726×481 px, levels 0..10, 17 tiles, kernel mode, residual 0.000687 m |
| `... python -m export.validate build/planeville/tiles --max-bytes 262144000` | pass (exit 0) | table below |
| `... python -m export.validate tests/fixtures/tiles-synthetic` | pass (exit 0) | prints a note that `expected.json` is ignored (see Decisions) |
| `... python -m export.pack build/planeville/tiles --out build/planeville/tiles.tar.gz` | pass | run twice: same sha256 `2339ef7f…a9922`, 21 363 bytes |
| `... python -m export.benchmark ...` (fixture) | pass | numbers in `docs/research/07-tile-encoding-benchmark.md` |
| `make check` | pass (exit 0) | contracts ok, ruff clean, 49 tests passed, "fixtures match the generator" |
| `make tiles` / `make validate-tiles` for Villena | not run | no `build/villena/render` exists |

Acceptance criteria, with the test that covers each: (1) `test_build_passes_validate`,
`test_same_tiles_as_fixture_and_max_level_pixel_identical`; (2) `test_manifest_and_pois_match_fixture`;
(3) `test_validate_passes_on_fixture_unchanged` + 6 × `test_validate_rejects[...]` (deleted tile, extra file,
wrong dimensions, POI moved 2 px, corrupted matrix, budget exceeded); (4) `test_build_and_pack_are_reproducible`;
(5) `test_png_and_webp_decode_identically`; (6) research doc 07; (7) ruff + pytest above.
Extra: mean kernel reproduces **every** fixture level pixel-exactly; mode-kernel known-answer test; height grid
against the analytic terrain plane (≤ 0.006 m); `geoToWorld` against `expected.json` ground points; build refuses
a mismatched scene and an out-of-image POI.

Size table of the built fixture (PNG, mode kernel, `export.validate` output):

```
level  tiles       bytes   max tile
    0      1          82         82
    1      1          82         82
    2      1          84         84
    3      1         101        101
    4      1         122        122
    5      1         176        176
    6      1         340        340
    7      1         778        778
    8      1        1655       1655
    9      2        4421       3258
   10      6       11997       3004
total     17       25546  (all files)
```

## Generated artifacts

Not committed (`build/` is git-ignored); regenerate with the section-10 commands.

- `build/planeville/tiles/` — 20 files, 25 546 bytes; tree hash (`find . -type f | sort | xargs shasum -a 256 | shasum -a 256`)
  `39b438f66712582c7d1f4bc30b65de7ee8189852f3a7e272af4e8e96f24ce051`.
- `build/planeville/tiles.tar.gz` — 21 363 bytes, sha256 `2339ef7fd4bdee4ba9d82a7bfbbd008c39461a51ab1873fe4917571af10a9922`
  (macOS arm64, Python 3.13 zlib from uv).

## Decisions and assumptions

- **Recommended format/kernel: indexed PNG + mode kernel** (default `--kernel mode`; city configs keep
  `"png"`). Mode is palette-exact at every level and 33 % smaller than mean on the fixture; it drops 1 px
  features when zoomed out. Lossless WebP is 36 % smaller than plain PNG but ~140× slower to encode and only
  8 % smaller than PNG + oxipng. Details: `docs/research/07-tile-encoding-benchmark.md`.
- Mode tie-break: first maximum in the order top-left, top-right, bottom-left, bottom-right.
- PNG: indexed when ≤ 256 colours, palette = sorted unique colours, zlib level 9, `optimize=False`;
  RGB otherwise. WebP: `lossless=True, quality=100, method=6, exact=True`. Pillow writes no ancillary chunks
  or timestamps for these calls.
- Height grid: bilinear resample of the scene terrain to 4 m cell centres over the scene terrain rectangle
  (clamped at the border); `offset = floor(min H)` as the prompt says, so the fixture build gives
  `offset 499.0` while the committed fixture has `498.8` (the fixture is not a reference for this field; no
  acceptance criterion compares it).
- `geoToWorld`: 9 × 9 fit grid over AOI **+ margin** (the viewer converts positions anywhere in the image),
  centred inputs, NumPy `lstsq`; residual on a 33 × 33 grid, rounded **up** to 1e-6 m. Fixture: 0.000687 m
  (fixture manifest, fitted over the AOI only: 0.000536). Matrix matches the fixture to < 2e-9 relative.
- POI `X`, `Y` and `imageBounds` rounded to 3 decimals (as the fixture); `worldBounds` dropped.
- `validate` checks the `geoToWorld` claim strictly (affine vs PROJ at each POI's E,N ≤ `maxResidualM`), and
  separately checks each POI's own `lat`,`lon` → E,N with an allowance of `maxResidualM + 0.015 m` — see
  the contract change request.
- `validate` ignores a root `expected.json` (the fixture's test oracle) with a printed note, so it passes on
  `tests/fixtures/tiles-synthetic/` unchanged; `pack` refuses to archive a directory containing it.
- `validate` rejects a style whose `tilesBase` is an absolute URL (it cannot check remote tiles).
- `pack`: PAX tar, regular files only, sorted, mode 0644, uid/gid 0, empty owner names, mtime 0; gzip
  level 9, header mtime 0, no file name. The asset name in the lock snippet is the output's base name.

## Contract change requests

1. `render.md` §2 / `projection.md` §6: "`geoToWorld(lon, lat)` reproduces `E, N` within `maxResidualM`" cannot
   hold for published POIs, whose `lat`/`lon` have 7 decimals (≤ 6 mm) and whose scene `E`/`N` are rounded to
   0.01 m (≤ 7 mm), while the fixture's `maxResidualM` is 0.000536 m. Proposal: state the check as "affine vs
   PROJ(E, N) within `maxResidualM`", plus "POI lat/lon within `maxResidualM` + coordinate rounding (0.015 m)".
   Implemented that way now.
2. `render.md` §2 says "no other files are present", but `tests/fixtures/tiles-synthetic/` holds `expected.json`
   and acceptance criterion 3 requires validate to pass on it unchanged. Proposal: move `expected.json` out of
   the tile directory at the next fixture regeneration (e.g. `tests/fixtures/tiles-synthetic.expected.json`),
   then drop the exception in `export/validate.py` (`FIXTURE_ORACLE`).
3. Optional: the fixture's lower levels use the mean kernel; if the architect adopts mode as the documented
   kernel, regenerate them so fixture and exporter agree beyond `maxLevel`.

## Known problems and unresolved issues

- No real Villena render exists, so the benchmark and the 1 km² projection rest on the synthetic fixture
  (a lower bound; re-measure on the first real render).
- Byte identity of tiles/archive between macOS arm64 and `linux/amd64` was **not tested** (no Linux run).
  Decoded pixels are identical by construction (lossless); file bytes depend on Pillow's bundled zlib/libwebp
  and Python's zlib for the archive. `geoToWorld` coefficients may differ in the last bits across platforms
  (LAPACK), which changes `manifest.json` bytes but not its meaning.
- WebP `method=6` encodes at ≈ 0.14 s per 257 px tile; a full Villena set (~400 × 513 px) would take minutes
  single-threaded if WebP were chosen.
- `oxipng` is only used by the benchmark; not wired into build or pack.

## Human approvals needed

none

## Recommended next task

Integrator review of WP06 by a model from a different provider; then, once WP04 produces
`build/villena/render/`, run `make tiles CITY=villena RELEASE=<r>` and `make validate-tiles CITY=villena` and
re-run the benchmark on the real render (WP12 release integration consumes `export.pack`).
