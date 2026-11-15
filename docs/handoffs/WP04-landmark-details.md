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
