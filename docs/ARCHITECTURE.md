# Architecture

Status: proposed by the architect on 2026-11-15, pending the WP02 independent review.
Evidence for every choice is in `docs/research/`; decisions are recorded in `docs/decisions/`.

## Overview

```
 cities/villena/datasets.json
          │
          ▼
 ┌─────────────┐  data/raw   ┌─────────────┐  scene/   ┌─────────────┐  render/  ┌─────────────┐  tiles/  ┌────────┐
 │ acquisition │────────────▶│ geospatial  │──────────▶│  rendering  │──────────▶│   export    │─────────▶│ viewer │
 │  (Python)   │             │  (Python)   │ scene.md  │(TypeScript) │render.md§1│  (Python)   │render.md§2│  (TS)  │
 └─────────────┘             └─────────────┘           └─────────────┘           └─────────────┘          └────────┘
   checksums                  EPSG:25830                deterministic             DZI pyramid,             static,
   pinned                     heights, terrain          pixel art + masks         manifest, POIs           no backend
                                                              ▲
                                                 optional ────┘ generation (WP10): restyles render tiles,
                                                                never geometry; separate environment
```

Five stages, four interfaces. Each interface is a directory with a JSON manifest validated by
a schema in `packages/geo-contracts/schemas/`. A stage reads only the previous stage's output,
so each can be built and tested alone against the synthetic fixtures in `tests/fixtures/`.

One projection, defined once in `docs/contracts/projection.md`, is used by every stage. It is
a 2×3 affine matrix from local metres to master-image pixels; manifests carry the matrix so
consumers never recompute it.

## Repository layout

See `AGENTS.md`. Deviations from the layout proposed in the bootstrap brief, and why:

- `pipeline/rendering` is TypeScript; the other pipeline stages are Python. They share only
  files, so the language boundary costs nothing.
- JS packages are standalone (own `package.json` and `bun.lock`), not a workspace: each work
  package owns its lockfile and parallel agents cannot conflict.
- One Python project for acquisition, geospatial and export (`pipeline/pyproject.toml`);
  the optional ML harness has its own environment so PyTorch never enters the main one.
- No Docker: the geo stack installs from wheels with `uv` on macOS arm64 and Linux x86-64
  (research 04 §F). Alpine is not usable for it (no musllinux wheels). Docker is used only as
  a test tool to check cross-platform determinism.
- Two schemas beyond the brief's list: `render-manifest` (renderer and exporter are separate
  agents) and `dataset-manifest` (acquisition must be machine-checkable).

## Geospatial pipeline (WP03)

| Need | Source | Notes |
|---|---|---|
| Building footprints | Catastro INSPIRE `BuildingPart` (ATOM, scriptable, EPSG:25830) | 6 813 parts in the AOI. Floors per part; no metric heights. |
| Ground | IGN MDT50cm 3rd coverage, 0.5 m, 2023 | Manual download (reCAPTCHA); resampled to 1 m. Fallback: MDT05 via WCS (scriptable, 5 m). |
| Heights of buildings and trees | IGN MDS50cm − MDT50cm | Robust statistic inside each footprint; fallback floors × 3 m + 1 m; default 3 m. Source recorded per building. |
| Streets, land cover, trees, POIs | OpenStreetMap via Overpass | Streets are well mapped; OSM buildings are not used. |

Complex landmarks: Catastro models the castle as one part with three floors. Parts belonging
to a landmark (and large multi-level parts) are split into height zones by segmenting the
surface model — measured geometry, not modelling. Raw LiDAR and PDAL are not needed.

Fallback mode (no manual download) produces a lower-quality but valid scene, so no other work
is ever blocked on a human step.

## Rendering (WP04)

Two stages inside the renderer:

1. **G-buffer rasterisation** of terrain mesh, extruded building parts and trees into integer
   attribute buffers (surface id, kind, face, depth, surface-local coordinates).
2. **Styling**: a pure integer function from G-buffers + palette to the colour image and the
   semantic layers. All the pixel art — stepped lighting, procedural windows and doors, roof
   textures, outlines, dithering — lives here.

The stage-1 backend is chosen by a time-boxed experiment at the start of WP04
(`docs/decisions/0002-render-backend.md`): Three.js in headless Chromium with SwiftShader if,
and only if, it is byte-identical across macOS arm64 and Linux x86-64; otherwise a small
software rasteriser in TypeScript. Blender was rejected (250–430 MB install, no determinism
advantage); `headless-gl` was rejected (different GL backends per OS, stale).

Why not simply "Three.js, render colours": render targets are linear and palette bytes do not
survive readback (research 04 §A), SwiftShader caps textures at 8192 px, and Chromium is
phasing out the SwiftShader WebGL fallback. Rendering ids instead of colours removes the first
problem and makes the backend swappable.

Outputs (`render.md` §1): `color`, `class`, `buildingId`, optional `depth` — full master image,
registered, byte-stable. The semantic layers serve QA, tests and the optional AI track.

## Export (WP06)

Flattens the colour layer, cuts a Deep Zoom pyramid (512 px tiles, 1 px overlap), writes the
tile manifest, POIs with image coordinates, a 4 m height grid for terrain-aware picking, and
an affine lon/lat↔E/N fit so the browser needs no projection library. Includes an independent
validator and a reproducible archive for release. Indexed PNG versus lossless WebP and the
down-sampling kernel are decided by benchmark in WP06.

## Viewer (WP05)

Vite + strict TypeScript + OpenSeadragon 6, vanilla DOM, Spanish UI. Reads the manifest,
POIs, height grid and tiles — nothing else. OpenSeadragon was kept over Leaflet/MapLibre/
deck.gl because a single deep-zoom image is its native model (research 04 §C). Picking and URL
semantics: `projection.md` §5–6. No third-party requests at runtime.

## Deployment

- GitHub Pages project site; `base` = `/villena-isometrica/`; everything resolves from
  `import.meta.env.BASE_URL`.
- Tiles are built locally (the IGN download is manual, so CI cannot build them), packed into
  a reproducible archive and attached to the GitHub Release. `cities/villena/tiles.lock.json`
  pins release, asset name, size and sha256; the deploy workflow downloads, verifies and
  bundles them into the Pages artifact (`docs/decisions/0004-tiles-hosting.md`). Git stays
  small; the site is self-contained.
- CI on every PR and on `main`: contracts, lint, tests, build with fixture tiles, e2e, size
  check. Deploy only from `main`, only after validation, with `pages: write` and
  `id-token: write` on the deploy job alone. PRs never deploy.
- Budget: 250 MB (GitHub's limit is 1 GB; soft 100 GB/month bandwidth). Estimated tile set:
  25–60 MB (`docs/COSTS.md`).
- **Later migration to object storage/CDN**: set `styles[].tilesBase` in the manifest to an
  absolute URL. The viewer already accepts that; nothing else changes.

## Optional AI track (WP10)

Isolated in `pipeline/generation/` with its own environment. Provider-independent job files
(`generation-job.schema.json`) record inputs, model revision, seed, prompt, attempts, metrics
and human decisions. A generated tile can only become part of a published style after a human
approval recorded in its job file, and it is published as a second `style` in the manifest,
never as a replacement of the map's geometry. Nothing runs before a free Phase A and an
owner-approved budget.

## Decisions

| ADR | Decision |
|---|---|
| 0001 | Stack and repository layout |
| 0002 | Render backend chosen by determinism spike; two-stage renderer |
| 0003 | Projection, camera (heading 45°, pitch 30°, 8 px/m) and picking semantics |
| 0004 | Tiles as a pinned release asset bundled into Pages |
| 0005 | Data sources and licences; project licences |

## Known risks

| Risk | Mitigation |
|---|---|
| Contract error discovered after parallel work starts | WP02 review + gate G1 before WP03–WP06; conformance vectors; versioned schemas |
| Cross-platform non-determinism in the renderer | Spike first; integer pipeline; golden hashes; Docker check |
| Manual IGN download blocks the pipeline | Fallback terrain via WCS; checksums pinned once downloaded |
| IGN 3rd-coverage models are "V1 provisional" | Version and checksum pinned in the dataset manifest |
| Catastro heights are only floor counts; landmarks under-modelled | Surface-model heights and zoning; QA compares with licensed photos; limits stated publicly |
| Flat-looking procedural art | Style rules in WP04; visual QA (WP09) before release; AI track stays optional |
| Castle hill hides ground behind it | Heading chosen so the hidden side faces away from the town; checked in WP02 and WP09 |
| Model IDs / CLI formats change | Verified 2026-11-15, recorded with sources; fallbacks per work package |
