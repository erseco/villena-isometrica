# Handoff — WP08 Cross-component automated tests

| Field | Value |
|---|---|
| Task ID | WP08 |
| Date (UTC) | 2026-11-15 |
| Provider / client | Anthropic Claude Code (subagent of a workflow run) |
| Model and effort actually used | `claude-sonnet-5-5`, effort medium (assigned by the owner; the prompt's first choice is Codex Luna, its fallback includes Claude Sonnet 5.5, effort medium) |
| Branch | `feature/wp08-testing` |
| Base commit | `e2f0b9751025e174aeb4039cf6d538d6e16ef643` |
| Head commit | the commit that adds this handoff (`git log -1 feature/wp08-testing`) |
| Status | READY FOR REVIEW (one strict xfail = defect WP08-D-01; fixture requests and a Makefile request below) |

## Changed files

```
 apps/viewer/e2e/failure-modes.spec.ts   (new, 5 tests x 2 projects)
 docs/handoffs/WP08-testing.md           (this file)
 docs/qa/WP08-defects.md                 (new)
 tests/integration/conftest.py           (new)
 tests/integration/helpers.py            (new)
 tests/integration/test_failures.py      (new)
 tests/integration/test_gis_to_tiles.py  (new)
 tests/integration/test_pipeline.py      (new)
 tests/integration/test_projection.py    (new)
 tests/integration/test_reproducibility.py (new)
 tests/integration/ts/dump.ts            (new)
```

No product, contract, fixture, Makefile or CI file was touched. No file was added under `pipeline/tests/`,
`pipeline/rendering/test/` or `apps/viewer/src/`: the existing per-package tests already cover the contract vectors
and `expected.json` in each language, and the cross-language comparisons need Python to hold the expected values.

- `tests/integration/ts/dump.ts` only evaluates the renderer's `projection.ts` and the viewer's `geo.ts` on inputs
  written by the Python tests and prints the results. It holds no expected value. It imports their exported functions.
- Expected values come from `expected.json`, `projection-vectors.json`, the scene fixture files, `city.json` and the
  closed form written in `tests/integration/helpers.py` (`matrix`, `fwd`, `prism_size`, `tile_list`, `plane`).

## Tests and validation executed

All run in the worktree on macOS arm64, Bun 1.4.4, Python 3.13 (uv).

| Command | Result | Notes |
|---|---|---|
| `make install` | pass | uv sync and `bun ci` in both JS packages |
| `uv run --project pipeline pytest tests/integration -q` | pass: **52 passed, 1 xfailed** in 10 s | includes the Docker test (ran, not skipped) |
| `uv run --project pipeline pytest pipeline/tests -q` | pass: 49 passed | unchanged |
| `(cd pipeline/rendering && bun run test)` | pass: 15 pass, 0 fail | unchanged |
| `(cd apps/viewer && bun run test)` | pass: 17 pass, 0 fail | unchanged |
| `(cd apps/viewer && bun run e2e)` | pass: **39 passed, 3 skipped** in 12 s | 29 + 3 skipped before; +10 mine (5 tests x desktop/mobile); the 3 skips are the existing mouse-only/touch-only/keyboard-only tests |
| `uv run --project pipeline ruff check --config pipeline/pyproject.toml tests/integration` | pass | `make lint` only lints `pipeline/`; checked by hand with the project's rule set |
| `make check` | pass | contracts, lint, 49 pytest + 17 + 15 bun tests, "fixtures match the generator" |

Counts. Tests added: 53 pytest (52 pass + 1 strict xfail), 10 Playwright runs (5 tests x 2 projects, all pass).
Skipped: 0 of mine. The Docker test would skip with a visible reason when Docker, its daemon or the local image
`oven/bun:1.4` is missing; here all three were present.

Coverage by section of the prompt:

| Prompt | Where |
|---|---|
| 7.1 end to end | `test_pipeline.py` (size 726 x 481, maxLevel 10, 17 tiles from the formula, projection equals the fixture's, ground points within 1e-3, road/roof/outside/occlusion semantics, POIs, tile assembly equals the render, `--depth` layer decoded and unprojected) |
| 7.2 reproducibility | `test_reproducibility.py`: two full runs, every output file identical; chunk size; `make_fixtures.py` into a scratch dir compared by content with the committed tree; renderer in a `linux/amd64` container, same `pixelSha256` |
| 7.3 failures | `test_failures.py` (renderer 7, exporter 7, validator 11 cases) and `e2e/failure-modes.spec.ts` (one tile 404, height grid 404, height grid of the wrong size, pois 404, background pixel) |
| 7.4 conformance | `test_projection.py`: contract vectors and `expected.json` through renderer TS, viewer TS, exporter Python and the GIS `image_size`; camera to matrix across implementations; image size and translation on 40 random cities |
| 7.5 GIS | WP03's tests already cover clipping, CRS mismatch, `heightSource` and the default height, so none repeated. `test_gis_to_tiles.py` adds the cross-stage chain GIS scene to render to tiles to validator |
| 7.6 properties | `test_projection.py`: inverse(forward(P)) for 3 x 1000 seeded points (viewer reference-plane inverse and renderer surface pick); terrain pick of 200 seeded plane points within 0.05 m; tile interiors cover every pixel of every level once (exported tiles and 60 random image sizes) |

Already covered elsewhere, not repeated: viewer manifest 404 and unknown MAJOR version (`viewer.spec.ts`); the six
`export.validate` cases of WP06 (deleted tile, extra file, wrong dimensions, POI moved, corrupted matrix, budget).

## Generated artifacts

Nothing is committed outside the tests. Temporary outputs live in pytest tmp dirs. For reference, the synthetic
pipeline on this machine (macOS arm64, Bun 1.4.4 zlib; file hashes are only stable per toolchain, ADR 0007):

- `render.json` `613d25eb7a2ab71160e273d98c81899855e0da34d80477408ddea1b1766fb4e4`, `color.png` `89013ae3b0ce0c4e314c25f68948102d866f572522259804be313665124e2dad`.
- `pixelSha256`: color `f70ac3be...becc`, class `78dd7ee6...a656`, buildingId `76201e0f...152c` (these are what the Docker test compares, and they equal `pipeline/rendering/test/golden.json`).
- exported tile directory tree hash (`find . -type f | sort | xargs shasum -a 256 | shasum -a 256`): `9745bfedf630cdb804121fd5f8bce3004e0d3b3a3aac8bda1a4119d4226f18bb`.

## Decisions and assumptions

- **The annex `syn-005_1` is hidden by the keep.** The prompt asks that the `buildingId` layer at the projected roof
  centre of each building resolves to it. For `syn-005_1` (roof centre (100, 88, 18.8)) the ray towards the camera
  crosses the keep's east wall at (96, 84, 22.0), below the keep's 24 m roof, so the pixel truly belongs to the keep.
  The test states that expectation explicitly and checks a second point per building, the north-east corner pulled
  1 m inwards, which is never hidden. Not a defect.
- **Pitched roofs are tested at wall-top height**, not at the apex, so the test does not depend on the renderer's
  30 degree hip rule (a README rule, not a contract rule).
- **Docker variant covers the renderer only.** The container mounts the repository read-only, including the host's
  pure-JavaScript `node_modules`, so it needs no network. The Python exporter is not run in a container: its Linux
  wheels cannot be installed offline. The cross-platform claim for the exporter therefore rests on the pixel
  comparison of the renderer plus the CI run on Ubuntu. The test never pulls an image.
- **`make fixtures`** is run into a scratch directory (`FIXTURES_OUT`) with `scripts/make_fixtures.py` and compared
  with the committed tree by content, using the comparison functions of `scripts/check_fixtures.py` (ADR 0007). The
  committed tree is never written by a test.
- **Imports.** `tests/integration/conftest.py` puts `pipeline/` on `sys.path`, so the documented command works
  without `PYTHONPATH`.
- A test-writing slip, for the record: my first e2e background test picked a viewport centre in the margin strip
  and failed; see O-1 in `docs/qa/WP08-defects.md`. I fixed the test, not the viewer.

## Contract change requests

1. **render.md section 3 vs projection.md 5.2 (O-1).** "A background pixel has no pick" is true only for pixels whose
   ray misses the height grid; the margin strip around the drawn diamond is background but is picked. Say which is
   intended (details and a measured example in `docs/qa/WP08-defects.md`). No two components disagree: the viewer
   follows 5.2 to the letter. The contract text is ambiguous.

## Known problems and unresolved issues

- **WP08-D-01** (minor, WP04): the renderer accepts a polygon ring of 3 positions with exit 0. One strict xfail:
  `test_renderer_polygon_with_fewer_than_four_coordinates`. Evidence and fix in `docs/qa/WP08-defects.md`.
- No two components disagreed about a contract in any other test. Every cross-implementation comparison
  (renderer, viewer, exporter, GIS) agreed within the contract tolerances.
- Not run: the full Villena data (not in scope), the exporter in Docker (see above), any non-Chromium browser.
- Runtime: `tests/integration` 10 s, viewer e2e 12 s, all offline.

## Requests for the architect: richer fixtures (R-04, R-20)

I did not edit `tests/fixtures/` or `scripts/make_fixtures.py`. To test what the synthetic city cannot reach today:

1. **A terrain ridge narrower than one height-grid cell (R-04).** E.g. a ridge about 3 m wide and 2 m high added to
   `terrain.f32` (scene cell 2 m, exporter's height-grid cell 4 m), with an `expected.json` entry giving the ground
   points on and beside it and the documented bound `cellSize / (2 tan phi)` = 3.46 m for the pick error. Today the
   plane makes the pick exact, so the only accuracy claim the suite can check is the 0.05 m one.
2. **Wall, roof and vegetation classes in `render-synthetic` (R-20).** The render fixture is terrain only: its `class`
   layer holds 0, 1, 2 and `buildingId.json` is `[null]`. Draw the six buildings and three trees (any simple fixed
   shading from the palette), with `class` 3, 4, 5 and a populated `buildingId.json`, so the exporter and validator
   are tested against a render that has them. The suite now builds these from the real renderer, which tests the
   exporter, but the committed fixture cannot serve as a renderer-independent oracle.
3. **A building in the margin.** Every scene-fixture building lies inside the AOI. Add one partly or wholly in the
   8 m margin, with an `expected.json` statement that it is clipped by the render prism. WP03's data has one (`SYN0007`)
   and `test_gis_to_tiles.py` uses it, but the contract fixture does not.
4. **A two-part building in the `buildingId` index of the render fixture.** The scene fixture already has one
   (`syn-004` = `syn-004_1` + `syn-005_1`), and the real render resolves both parts; the committed render fixture
   does not include them (see 2).
5. Optional, same regeneration: one pitched roof with `ridgeHeightM` and `roofSource: "surface-model"`, one
   `structures.geojson` feature, one tunnel (`layer < 0`) and one bridge (`layer > 0`) road, and `noPick` cases in
   `expected.json` (image corners, plus a margin-strip pixel with the decision from O-1).

## Human approvals needed

None for spending, publishing or pushing. Decisions wanted:

- **Makefile line (WP07 / integrator).** `make test` and `make check` do not run `tests/integration`. Suggested line
  to append to the `test` target: `uv run --project pipeline --frozen pytest tests/integration -q`. `make e2e` already
  picks up the new Playwright file. Not done: the Makefile is outside my paths. Note the suite needs `bun` on `PATH`,
  and Docker only for the optional test.
- The O-1 reading of the contract (above).

## Recommended next task

WP11 independent review (WP03-WP08 are now all on branches or merged); WP08-D-01 is a few lines for whoever owns
`pipeline/rendering/src/scene.ts`. After the architect regenerates the richer fixtures, extend `test_pipeline.py` with
the ridge and margin cases.
