# 0007 — Gate G1: contracts frozen at v1

Status: accepted (2026-11-15). Architect: Claude Fable 5.2. Inputs: the WP02 independent review
(DeepSeek V4 Pro, `docs/handoffs/WP02-architecture-review.md`, verdict "approve with changes"),
WP01's verified data facts (`docs/research/08-wp01-data-verification.md`), and the contract
change requests in the WP03 handoff.

## Context

The contracts were written by one model and had to be checked by another before four work
packages build on them. The review found one blocker and six major issues, all in contract or
schema text, none in the architecture. Every numerical claim of the review was recomputed
independently before being accepted (R-01 start points and the share of background pixels —
29.8 % here against the reviewer's 29.1 %, a sampling difference; R-03; R-04 bounds; R-07; R-11
tile origin and ratio drift) and the documentary ones were checked against the files.

## Review findings

| ID | Severity | Verdict | Action |
|---|---|---|---|
| R-01 | blocker | accepted | `projection.md` §5.2 rewritten: explicit start, entry into the grid rectangle, termination, and a **no pick** result for background pixels. The viewer never falls back to the reference plane for them. One addition to the proposal: inside the rectangle, the half-cell border is clamped to the nearest cell centre (something has to be defined there). |
| R-02 | major | accepted | The float32/`dMin` sentence is gone from `projection.md`; `render.md` §1 is the single definition of the depth encoding; the schema requires `scale` and `offset` on a depth layer. |
| R-03 | major | accepted, option (a) | `pitchDeg` is `< 90` in the three schemas and in the text. The φ = 90 test-vector camera stays as a forward-only check and is labelled so. |
| R-04 | major | accepted | "First intersection with the height grid, bilinearly interpolated", with the `cellSize/(2·tan φ)` bound and a note on what the fixture tolerance means. The ridge fixture is deferred to WP08 (see R-20). |
| R-05 | major | accepted | New `scene-pois.schema.json`; the validator checks scene POIs and the skip is deleted. `worldBounds` moved out of the published POI schema. |
| R-06 | major | accepted | `palette.json` is a render output with its own schema; the render manifest references it by sha256 (required, not optional: nothing was implemented yet). |
| R-07 | major | accepted | Determinism split: `pixelSha256` (decoded samples, exact byte layout defined) must match across platforms; file `sha256` only within one pinned build. |
| R-08 | minor | accepted | Single-producer determinism stated; non-finite numbers rejected by the validator. |
| R-09 | minor | accepted | POIs sorted by id in both contracts; the validator enforces it; fixtures regenerated. |
| R-10 | minor | **rejected as proposed** | Mandating "round half away from zero on the decimal representation" would force every implementation off its native formatter to settle ties that no consumer can observe: byte identity is required only of one producer with itself (R-08), and cross-language tests compare parsed values. Written instead: the tie rule is unspecified and comparisons allow one unit in the last rounded decimal. |
| R-11 | minor | accepted | Tile-pixel → level → master mapping spelled out; power-of-two factor mandatory. |
| R-12 | minor | accepted in part | `cities/villena/datasets.json` now exists (WP01). The validator checks that a city's `datasets` reference resolves. The placeholder datum is replaced. Not done: resolving `localPath` (raw data is absent by design) and a city/scene `crs` cross-check (the scene copies it from the city by construction). |
| R-13 | minor | accepted, different shape | `heightM` stays the wall top (the extrusion height: roof plane or eaves), now said unambiguously, and an optional `ridgeHeightM` carries the measured highest point of a pitched roof. The reviewer proposed the reverse (highest point + optional eaves); the wall top is what every consumer extrudes, so it is the field that must always exist. `zRange` uses the ridge when present. Ridge direction is stated to be procedural. |
| R-14 | minor | accepted | `maxResidualM < 0.1`; `validate-tiles` cross-checks POI coordinates (WP06). |
| R-15 | minor | accepted | `crs` and `renderSha256` in the tile manifest (required). |
| R-16 | minor | accepted | Prism/margin rules written into `projection.md` §3; "horizontal viewing direction". Occlusion input now on record: by the 5 m model the castle node's ground is ≈ 48 m above Plaza Mayor (550 m vs 502 m), so about 83 m of ground behind the hill top is hidden at φ = 30°, on the north-east side, away from the old town — ADR 0003's claim holds. To be re-measured with the 0.5 m model. |
| R-17 | minor | accepted | `tiles.format` is a request, the manifest is the truth; bridges are draped; land-cover overlaps are the producer's job; scattered trees are hash-seeded; the height-grid cell is the exporter's choice; fixture datasets are exempt from the pinning rule. |
| R-18 | note | recorded | Image ≈ 11 314 × 6 500–6 850 px, ≈ 425 tiles; `docs/COSTS.md` corrected. |
| R-19 | note | accepted | "Check `schemaVersion` before validating" added. Another UTM zone remains a MAJOR bump. |
| R-20 | note | deferred | Planeville still exercises only terrain, roads and POIs. Richer fixtures (wall/roof/vegetation classes, a margin building, a ridge) are assigned to WP08, which needs them; the architect regenerates. |

## Decisions beyond the review

1. **`structures` layer (optional).** Catastro models the Castillo de la Atalaya as a single
   200 m² part — the keep. The curtain walls are not buildings. OpenStreetMap has the castle
   enclosure (multipolygon relation 8046264) and 13 `barrier=city_wall` ways. A separate,
   optional scene layer carries these OSM-derived footprints with the same properties and
   rendering as buildings, heights from the surface model. Separate file because the licence
   differs. Without it v0.1.0 would show a tower on a hill, not the castle that defines the
   town's skyline.
2. **Dataset ids are fixed** (`catastro-buildings`, `ign-mdt50cm`, `ign-mds50cm`, `ign-mdt05`,
   `osm`) — WP01's ids; WP03 adapts. `localPath` is relative to the repository root.
3. **OSM extracts** may carry way geometry inline or as node references; the pipeline accepts
   both (WP01's extract uses node references).
4. **Vertical datum**: Alicante height, EPSG:5782, geoid model EGM08-REDNAP (WP01).
5. **Catastro citation**: "Dirección General del Catastro, Ministerio de Hacienda" with the
   access date (WP01).
6. **Branch prefix `feature/`** instead of `agent/`, the owner's standing preference as
   reported in the WP07 handoff. Existing `agent/…` branches keep their names.
7. **Python project layout**: WP07's (`package = false`, wheels only, `PYTHONPATH=pipeline`)
   replaces the provisional one WP03 created.

## Consequences

- Contracts are **FROZEN v1**. From here, changes go through `prompts/00-bootstrap.md` Task B.
- No expected value in the fixtures changed: tiles, coordinates and vectors are identical; the
  manifests gained fields and the POI files are now sorted.
- What each work package must do differently is listed in `docs/PROJECT_STATE.md`.
- The review was done by one provider. WP11 repeats it against the implementation.
