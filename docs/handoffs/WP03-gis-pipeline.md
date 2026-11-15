# Handoff — WP03 Geospatial pipeline: acquisition and scene export

| Field | Value |
|---|---|
| Task ID | WP03 |
| Date (UTC) | 2026-11-15 |
| Provider / client | Claude Code 2.1.325 |
| Model and effort actually used | `claude-opus-5-5`; effort as set in the owner's session (not visible to the agent) |
| Branch | `agent/wp03-gis-pipeline` (worktree `../villena-isometrica-worktrees/wp03-gis-pipeline`) |
| Base commit | `ba8ba0c` (head of `agent/wp00-bootstrap`; `main` had not been fast-forwarded yet) |
| Head commit | the commit that adds this file |
| Status | **PARTIAL** — code, tests and synthetic dataset complete; the release-quality Villena scene is blocked (see below) |

## Dependencies at start — and why work went ahead

| Dependency | State | Consequence |
|---|---|---|
| Contracts frozen (G1) | **not frozen** (`PROPOSED v1`, WP02 not run) | The owner asked for the Opus tasks to be done now; per the prompt, that is proceeding at the owner's risk. Any WP02 change to `scene.md` means rework here. |
| WP01 (`datasets.json`, `ACQUISITION.md`, `poi-selection.json`) | **missing** | No official Villena scene, report or preview. The code was exercised on real data through a temporary manifest outside the repository (smoke test below). |
| WP07 (`pipeline/pyproject.toml`, `uv.lock`) | **missing** | Created minimal versions here (see "Contract change requests" — WP07 owns these files). |
| Manual IGN MDT50cm / MDS50cm | **absent** | Full mode verified on synthetic data only. |

## Changed files

All new, all under the allowed paths:

```
pipeline/pyproject.toml, pipeline/uv.lock                 (WP07-owned; created because missing)
pipeline/acquisition/{__init__,fetch}.py, README.md
pipeline/geospatial/{__init__,inputs,buildings,osm,build_scene}.py, README.md
pipeline/tests/acquisition/test_fetch.py
pipeline/tests/geospatial/test_build_scene.py
pipeline/tests/geospatial/data/  make_data.py + generated test data (84 KiB)
docs/handoffs/WP03-gis-pipeline.md
```

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `uv run --project pipeline ruff check pipeline` | pass | |
| `uv run --project pipeline pytest pipeline/tests -q -W error` | **26 passed** in ~1 s | 7 acquisition, 19 geospatial |
| `make check` | pass | |
| Synthetic scene twice → sha256 of every file | identical | test `test_rerun_is_byte_identical` |
| Real Villena smoke test (fallback mode), twice | identical hashes; `scene.json` validates | see below |
| `uv sync --project pipeline --frozen` on Ubuntu | **not run** | macOS arm64 only |
| Full mode on real IGN rasters | **not run** | files not available |

What the synthetic tests prove (known answers, `pipeline/tests/geospatial/data/make_data.py`):
heights recovered within 0.3 m for flat and pitched roofs; `floors` and `default` fallbacks;
0-floor and underground-only parts dropped; a part straddling the clip edge clipped, not
dropped, with its roof elevation preserved; the landmark split into tower (18 m) and walls
(8 m) with the courtyard dropped; canopy peak detected (7.88 m vs 8 m); road clipping, width
tag, ignored construction way; park land cover; POI heights on roof vs ground; street POIs;
fallback mode; rejection of a wrong-CRS raster, a tampered input, an unpinned input, a missing
surface model without `--terrain-fallback`, a POI outside the AOI, and a non-scene output
directory; multipart WCS responses (CRLF, leading blank line, as the IGN server sends them);
landmark snapping to the nearest building only.

## Real-data smoke test (not a deliverable)

Inputs in the session scratchpad, **not committed**, with a temporary manifest: the Catastro
BU zip downloaded by the research agent (`A.ES.SDGC.BU.03140.zip`, 3 971 442 B), one IGN WCS
`GetCoverage` (MDT05, 685350–686650 / 4277350–4278650, 542 395 B) and one Overpass query
(AOI + margin, `out geom`, 471 998 B, OSM base 2026-11-15T12:10:37Z; the public endpoint
returned 502 "at capacity" once, then succeeded on retry).

| Measure | Value |
|---|---|
| Wall time / peak RSS | 1.8 s / 220 MB |
| Catastro parts read in clip box → kept | 7 978 → 7 710 (231 zero-floor parts dropped, 40 too small) |
| Roads / land cover / mapped trees | 505 / 47 / 11 |
| POIs | 151 (7 landmarks + 144 named streets) |
| Terrain | 494.0–662.1 m (the Sierra de la Villa in the NE margin sets `zMax`) |
| zRange | −7 … 164 m relative to H0 = 500 |
| Predicted master image (8 px/m, 45°/30°) | **11 314 × 6 843 px** (COSTS.md estimated ≈ 11 300 × 6 500) |
| Scene size | 10 MB (terrain 6.2 MB, buildings 3.7 MB) |

The top-down preview shows the Ensanche grid to the north-west, the old town around the castle
hill and the sierra to the north-east, as expected.

## Decisions and assumptions

All thresholds and mappings are in `pipeline/geospatial/README.md`. The ones a reviewer should
look at:

- **Dataset ids are the interface to WP01**: `catastro-buildings`, `ign-mdt50cm`,
  `ign-mds50cm`, `ign-mdt05-wcs`, `osm-overpass`.
- **`localPath` is resolved against `--data-root`** (default: current directory = repository
  root), not against the manifest's directory.
- **Pitched-roof height = eaves** (p5 of the surface model), flat = p80; heights measured from
  `baseH` = lowest terrain cell centre under the footprint.
- **Zero-floor parts are dropped unless the surface model measures ≥ 2 m** — Catastro means
  "nothing built above ground" (patios, terraces). 231 of them in the clip box.
- **Landmark snapping 25 m** (prompt said 15 m): the OSM castle node is 15.6 m from the keep.
  Only the single nearest building is tagged; next-nearest was 45 m away.
- **Castle → `fortification`** by a name rule (castillo/torre/muralla/alcazaba) because
  `poi-selection.json` has no "fortification" kind.
- Zones get `floors: null` (the parent's floor count does not describe a tower).
- Raster reads use bilinear resampling onto 0.5 m / 1 m grids aligned to whole metres; the
  report states whether the source grids were aligned (unverified for the real IGN files).
- Archives are read in place (`/vsizip/`), so nothing is extracted and no zip-slip risk exists.
- Python packages are installed via hatchling (`acquisition`, `geospatial`); `export` must be
  added to `[tool.hatch.build.targets.wheel] packages` by WP06/WP07.

## Contract change requests (not made — for the architect)

1. **`dataset-manifest.schema.json` → `localPath`**: its description says paths resolve
   against the manifest's directory, but the pattern forbids `..`, so `cities/villena/datasets.json`
   cannot point at `data/raw/…`. Proposal: "relative to the repository root (the pipeline's
   `--data-root`)". WP03 already behaves that way.
2. **Dataset roles**: the schema has no role field, so WP03 relies on fixed ids (above).
   Either add the five ids to `prompts/01-data-research.md` or add an optional `role` field.
3. **The castle's walls are not in Catastro.** Catastro has one 200 m² part (the keep); the
   curtain walls are not buildings. Even full mode will render a keep on a hill, not a castle.
   Options: OSM `historic=castle` / `barrier=wall|city_wall` outlines as a new scene layer
   (`walls.geojson`, heights from the surface model), or accepting the limitation for v0.1.0.
   This changes `scene.md` and WP04 — architect decision.
4. **`pipeline/pyproject.toml` and `uv.lock` were created here** (WP07 owns them). WP07
   should adopt and extend them (add `export`, pytest config for other areas) rather than
   create competing ones; lockfile conflicts resolved by regenerating.

## Corrections to earlier research (for WP01)

- IGN WCS `GetCoverage` returns `multipart/related` (grid + `.aux.xml` + `.prj`, CRLF, leading
  blank line) even with `FORMAT=application/asc`; research 03 recorded it as a plain grid. The
  pipeline stores the response as received and extracts the grid.
- Overpass public endpoint can return 502 "at capacity"; `ACQUISITION.md` should tell people
  to retry with backoff.

## Known problems

- Full-mode thresholds (roof slope, zoning, canopy) are tuned on synthetic data only.
- Mapped OSM trees without a `height` tag get 6 m (labelled `mapped`, which refers to the
  position, not the height).
- OSM multipolygon relations are skipped (0 in Villena's AOI today).
- Not run on Linux.

## Human approvals needed

- Confirm that proceeding before G1 was intended (it was done on the owner's instruction
  "haz las tareas referentes a opus").
- Decision on the castle walls (request 3).

## Recommended next task

WP01 (dataset manifest with the ids above, `ACQUISITION.md`, `poi-selection.json`); the owner
downloads the two IGN sheets; then rerun this prompt's section 7.5 to produce
`build/villena/scene`, `cities/villena/scene-report.md` and `scene-preview.png` in full mode.

---

# Round 2 — after gate G1 (2026-11-15)

| Field | Value |
|---|---|
| Who | Claude Fable 5.2 (`claude-fable-5-2`), acting as architect and integrator at the owner's request ("consolidar lo hecho") |
| Branch | `agent/wp03-gis-pipeline`, with `main` (WP07, WP01, frozen contracts) merged in |
| Status | **READY FOR REVIEW** — code complete against the frozen contracts. The Villena scene is fallback-mode only until the owner downloads the two IGN sheets. |

## What changed

- Python project: WP07's `pyproject.toml`/`uv.lock` adopted (wheels only, not a package); added ruff rule
  selection and pytest `pythonpath`. Commands now use `PYTHONPATH=pipeline` or `make scene`.
- Dataset ids follow the contract: `ign-mdt05`, `osm` (were `ign-mdt05-wcs`, `osm-overpass`).
- OSM loader accepts node-reference extracts (WP01's format), drops the untagged duplicate copies that
  `>; out skel` emits, and assembles multipolygon relations made of closed rings.
- `ridgeHeightM` for measured pitched roofs; `heightM` stays the wall top (contract R-13).
- New optional `structures` layer (ADR 0007): castle enclosure and town walls from OSM.
- Scene POIs validated against `scene-pois.schema.json` inside the build.
- Requests 1, 2 and 3 of round 1 are resolved by ADR 0007; request 4 by adopting WP07's files.

## Tests and validation executed

| Command | Result |
|---|---|
| `uv run --project pipeline --frozen ruff check pipeline` | pass (ruff 0.17.5) |
| `uv run --project pipeline --frozen pytest pipeline/tests -q -W error` | **31 passed** |
| `acquisition.fetch` against WP01's manifest and downloads | `ok` for `catastro-buildings`, `ign-mdt05`, `osm`; the two manual IGN datasets reported missing (exit 1, as designed) |
| `build_scene --terrain-fallback` on the real data, twice | identical sha256 for every file; `scene.json` and `pois.json` validate |
| Full mode on real IGN rasters | **not run** — files not downloaded yet |
| Linux | **not run** |

## Real Villena scene (fallback mode) — `cities/villena/scene-report.md`, `scene-preview.png`

7 710 building parts (all heights from floors), 11 structures (castle enclosure + 10 wall segments, default
height), 505 road features, 48 land-cover polygons, 11 mapped trees, 169 POIs (25 curated + 144 streets),
`zRange` −7…163, predicted master image 11 314 × 6 836 px, 2.9 s, 314 MB peak. Raw data was read from the
WP01 worktree (`--data-root`); nothing raw or derived is committed except the report and the preview image.

Defects found on real data and fixed in this round: the castle's outer ring was added twice (it is also
tagged `barrier=city_wall`); the theatre's OSM outline, already modelled by Catastro, left slivers; WP01's
extract repeats member ways without tags.

## Known problems

- Full-mode thresholds are still tuned on synthetic data only — the first run with the IGN sheets must be
  read critically (disagreement table, castle zones).
- In fallback mode the castle enclosure is one 3 m block: an outline with a labelled default, not a castle.
- One OSM multipolygon in the AOI has rings split over open ways and is skipped.
- Review by another provider (Codex) is still owed, per `AGENTS.md`.

## Recommended next task

Owner: download the two IGN sheets (`cities/villena/ACQUISITION.md` §3), pin their checksums in
`cities/villena/datasets.json`, run `make scene`. Then WP04 can render the real scene.
