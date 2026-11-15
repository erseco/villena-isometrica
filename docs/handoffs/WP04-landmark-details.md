# Handoff — WP04 landmark details (scene contract v1.1 in the renderer)

| Field | Value |
|---|---|
| Task ID | WP04 (landmark details) |
| Date (UTC) | 2026-11-15 |
| Provider / client | Anthropic Claude Code (subagent of a workflow run) |
| Model and effort actually used | claude-opus-5-5, high |
| Branch | `feature/wp04-landmark-details` |
| Base commit | `dc02b7c` (`git merge-base main HEAD`); branch starts at `8238eb8` (ADR 0008, contract v1.1) |
| Head commit | the commit that adds this file (see `git log -1`) |
| Status | READY FOR REVIEW |

## Changed files

```
pipeline/rendering/README.md                  new section "Landmark details", class 7, palette, performance
pipeline/rendering/palette.json               + slate-0..2 (64 colours), version "2"
pipeline/rendering/src/scene.ts               details layer + part parapet/material, strict validation
pipeline/rendering/src/geometry.ts            detail tessellation, battlement merlons, Kind.Detail/DetailTop
pipeline/rendering/src/style.ts               materials, analytic round shading, textures, class 7, outline keys
pipeline/rendering/src/render.ts              detail ids appended to the buildingId index
pipeline/rendering/src/cli.ts                 log line counts details
pipeline/rendering/test/detail-scene.ts       synthetic v1.1 scene writer (fixture + details)
pipeline/rendering/test/details.test.ts       9 tests (goldens, chunking, class 7, silhouettes, validation)
pipeline/rendering/test/golden-details.json   pixel hashes of the detail scene (new file; test/golden.json untouched)
pipeline/rendering/test/contact-sheet.ts      regenerates the contact sheet
pipeline/rendering/docs/landmark-details-2x.png  contact sheet, 94 KB
docs/handoffs/WP04-landmark-details.md        this file
```

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `bun run lint` (pipeline/rendering) | pass | biome + tsc strict |
| `bun test` (pipeline/rendering) | pass | 24 tests; `test/golden.json` unchanged and passing |
| linux/amd64 docker command from the README, plus `bun test` in the container | pass | fixture golden hashes printed identical; all 24 tests incl. `golden-details.json` pass on x86_64 |
| Villena scene from `build/villena/scene` (old 1 km² AOI, 8 108 parts) before vs after this change | identical `pixelSha256` for color, class, buildingId | no details in that scene |
| Same scene + 60 synthetic details (scratch copy, `zMax` + 15) | 11.8 s / 2.9 GB; with `--depth` 17.2 s / 4.6 GB | 180 839 class-7 pixels; baseline without details 11.2 s / 2.9 GB |
| `make install` | pass | |
| `make check` | pass (exit 0) | contracts, lint, all tests, integration 52 passed + 1 xfailed, fixtures match |

## Generated artifacts

- `pipeline/rendering/docs/landmark-details-2x.png` (committed, 94 182 bytes): `bun test/contact-sheet.ts`.
  I looked at it (and at 2–3× crops): the battlemented keep and round tower, the slate square
  spire on its tower and the dome on its drum read clearly as pixel art. Iterations: moved the
  dome away from the AOI edge, made the slate courses coarser (0.6 × 1 m) because 0.4 × 0.6 m
  read as noise at 8 px/m.
- Performance outputs were written only to the scratchpad, nothing under `build/`.

## Decisions and assumptions

- Details are planar facets through the existing polygon rasteriser (no new raster path), so
  depth, clipping to the render prism and chunk independence come for free.
- Round surfaces are shaded per pixel from the analytic normal plus a ±0.03 ordered dither on
  `n·L`; square pyramids, caps and merlons use flat facet bands. Arc position for textures comes
  from the facet chord, so no `atan2` is needed (the source-scan test still passes).
- Merlons on parts are real boxes; fronts are wall surfaces of the part (no outline between wall
  and merlon), tops are roof surfaces. Edges shorter than 0.35 m get no merlon, so a finely
  tessellated round OSM tower would show none — a battlemented `cylinder` detail is the intended
  way to model round towers.
- Detail validation also checks the feature count against `scene.json` (other layers check
  only sha256, unchanged). `rotationDeg` is accepted on any kind (only used for `sides: 4`).
- New goldens are in a separate file `test/golden-details.json` so `test/golden.json` stays
  byte-identical.
- Palette version bumped to "2" (3 colours appended; existing colours and their order unchanged,
  so existing colour pixels are unchanged; the palette sha in `render.json` changes).
- Materials: metal uses the concrete ramp, brick the terracotta ramp (as tile); slate has 3
  shades, so band 3 and joints on the darkest face collapse to one colour.

## Contract change requests

none

## Known problems and unresolved issues

- Memory at the v1.1 AOI: ≈ 15 557 × 9 006 px is 1.8× the pixels I measured; extrapolated ≈ 5.5 GB
  without `--depth` and ≈ 8 GB with it, i.e. at the budget limit with `--depth`. Pre-existing
  scaling (output buffers), not caused by details. Not measured on the real v1.1 scene, which
  does not exist yet (WP03 must produce it with `details.geojson`).
- No real `cities/villena/landmark-details.json` / `details.geojson` exists yet, so the castle,
  bullring and churches were not rendered with real details here. The owner asked (relayed
  request) for the castle, the Plaza de Toros and the churches of Santiago and Santa María to
  look as close to the real ones as possible using internet reference images; that curation
  (shapes and dimensions from Commons references) belongs to the GIS/data side, not to this
  renderer task, and was not done here.
- The owner's relayed request also said to upload ("súbelo"); per AGENTS.md rule 4 and this
  task's instructions nothing was pushed. Pushing needs the owner's explicit go-ahead to the
  integrator.

## Human approvals needed

- Push/publish of this branch (not done).

## Recommended next task

WP03: write `cities/villena/landmark-details.json` and emit `details.geojson` (+ `parapet` on the
castle walls) for the castle, Plaza de Toros, Santiago and Santa María; then render the full v1.1
scene without `--depth` and review the four landmarks in the contact-sheet style.

## Round 2 — gable halls, arcades, masonry parts, curved-roof textures (2026-11-15)

Started by merging `feature/wp00-aoi-landmarks` (fast-forward to `36e7aa2`: contract adds kind
`gable` and cylinder `openings: "arcade"`, plus the GIS curation). Model claude-opus-5-5.

### Changed files

```
pipeline/rendering/src/scene.ts               gable (lengthM, widthM, wallHeightM, roofMaterial) and openings, strict validation
pipeline/rendering/src/geometry.ts            addGable: long walls, pentagonal end walls, two roof slopes
pipeline/rendering/src/style.ts               gable walls/roofs, arcade, radial tile on cones, dome panel grid, stone/brick parts
pipeline/rendering/test/detail-scene.ts       church rotated 70 deg (gable nave, rotated tower part, spire), small bullring
pipeline/rendering/test/details.test.ts       rotation sign test, dome test, stone-part and arcade test, new validation cases
pipeline/rendering/test/golden-details.json   regenerated (test/golden.json unchanged)
pipeline/rendering/test/contact-sheet.ts      new crops (church, bullring)
pipeline/rendering/docs/landmark-details-2x.png  regenerated, 114 655 bytes
pipeline/rendering/README.md                  details section, tests, performance row
docs/handoffs/WP04-landmark-details.md        this section
```

### What changed

1. `gable`: hall centred on the point, ridge along bearing `rotationDeg`, walls in `material`
   (masonry; on the long walls pilasters between ~6 m bays and one narrow arched slit per bay;
   end walls plain), slopes in `roofMaterial` with the building-roof tile rows parallel to the
   ridge (slate courses / metal seams for the other roof materials). Class 7, listed in the
   `buildingId` index. Validation: `radiusM` forbidden on a gable; `lengthM`/`widthM`/
   `wallHeightM`/`roofMaterial` required on a gable and forbidden elsewhere; `wallHeightM <
   heightM`; `roofMaterial` ∈ tile/slate/metal.
2. `openings: "arcade"` (cylinder only): two tiers of round-headed dark openings (≈ 2 × 3 m,
   ≈ 4 m apart around the wall, from the arc position so chunk-independent) and a shadowed
   cornice line between the tiers.
3. Part `material: "stone"` now renders as the fortification masonry with no windows or doors.
   `brick` adds 0.5 × 1 m courses and keeps the `use` window layout; `plaster` is plain limewash
   with the window layout (unchanged).
4. Tile cones/frustums: radial channels (~0.9 m at the eave) and darker panel seams (~8 m);
   metal domes: faint meridian/parallel panel grid (texture radius on domes now uses the pixel's
   distance from the axis, because the planar facets sag far inside a flat ellipsoid near the
   crown and the analytic radius broke the meridians into dashes).
5. Rotation test: the synthetic church is rotated 70° (heading 45°). The spire's extent and the
   X of its front base corner and the gable's [left, top, right] are compared with values computed
   in the test from projection.md with `Math.sin/cos`; the test also asserts the `-rotationDeg`
   expectations differ by > 3 px. Mutation check: negating the rotation in the renderer's square
   pyramid, and separately in the gable, makes this test fail (13.8 px off); reverted.
6. Contact sheet regenerated and looked at (castle keep + tower; church with gable nave, tower
   and slate spire; bullring with arcaded drum, radial-tile roof ring and gridded dome; turret and
   frustum).

### Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `bun run lint` (pipeline/rendering) | pass | biome + tsc strict |
| `bun test` (pipeline/rendering) | pass | 26 tests; `test/golden.json` unchanged |
| linux/amd64 docker command from the README + `bun test` | pass | x86_64; fixture hashes equal `test/golden.json`; 26/26 incl. `golden-details.json` |
| `bun run render` on `build/villena/scene` (read-only; output in the session scratchpad), no `--depth` | pass | 15 557 × 9 006 px, 11 600 parts, 10 637 trees, 21 details, 20.6 s, peak RSS 5.3 GB |
| `make install` | pass | |
| `make check` | pass (exit 0) | contracts, lint, Python 69 passed, viewer 17, renderer 26, integration 52 passed + 1 xfailed, fixtures match |

### Looking at the real render (crops at 1–3×, scratchpad only)

- Plaza de Toros: reads as a covered bullring — white arcaded drum with two tiers of arches and a
  cornice, radial-tile roof ring, grey dome with a panel grid. Catastro parts of the bullring
  (`5692001XH8759S_part5_z1/_z2`, 26–30 m, plaster) poke through the roof ring on the east side;
  that is scene data (GIS), not renderer behaviour.
- Santa María: stone gable nave with tile roof, slits and pilasters on the visible long wall;
  the stone tower part now shows masonry without house windows; slate spire on top. The spire
  (rotation 73°) does not exactly match the tower part's footprint, leaving a small notch of the
  tower top visible beside the spire base (scene data).
- Santiago: gable nave, masonry church parts, octagonal chapel drum with a radial-tile cone.
- Castle and Torre del Homenaje: unchanged look (coursed stone, battlements, bartizans); they
  read clearly.
- Minor: on the large roof ring, where the radial channels run almost horizontally in the image
  (back of the ring), the 1 px channel lines show some moiré. Left as is.

### Known problems

- The `-rotationDeg` discrimination relies on the fixture heading (45°); with a camera heading
  where the two expectations coincide the guard assertion would fail loudly rather than pass
  silently.
- Gable end walls carry no openings (no data says which end is the façade).
- Nothing pushed; owner approval needed for any publishing.
