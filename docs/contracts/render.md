# Contract: render output and published tiles

Status: **v1 — proposed, pending WP02 review.** Schemas:
`render-manifest.schema.json`, `tile-manifest.schema.json`, `poi.schema.json` in
`packages/geo-contracts/schemas/`. Fixture: `tests/fixtures/tiles-synthetic/`.

## 1. Render output (renderer → tile export)

Directory `build/<city>/render/` with `render.json` and one full master-image file per layer.

| Layer | Encoding | Content |
|---|---|---|
| `color` (required) | `rgba8-png` | Final pixel art, sRGB, straight alpha. Pixels where nothing was drawn have alpha 0. Only colours from the palette file referenced in the renderer's docs. |
| `class` (required) | `index8-png` | 0 background, 1 ground, 2 road, 3 wall, 4 roof, 5 vegetation, 6 water, 7 landmark-detail. |
| `buildingId` (required) | `rgb24-id-png` | `R<<16 \| G<<8 \| B` = index into the JSON array at `index` (array of scene building-part ids; index 0 = "no building"). |
| `depth` (optional) | `gray16-png` | `d = offset + scale · value` metres (projection.md section 3). |

Requirements:

- **Deterministic**: the same scene, city config and renderer version produce byte-identical
  layer files on macOS arm64 and Ubuntu x86-64. `sha256` of each layer is in the manifest.
- **Pixel-exact**: no anti-aliasing, no filtering, no colour management surprises: every colour
  pixel is exactly a palette colour.
- All layers have exactly `image.width × image.height` pixels and are mutually registered.
- `sceneSha256` = sha256 of the `scene.json` that was rendered.

> ponytail: one file per layer for the whole master image. Fine up to roughly 30 000 px per
> side; add a chunk grid to the manifest (contract MINOR bump) when a city exceeds that.

## 2. Published tiles (tile export → viewer)

Directory layout, everything relative to the manifest:

```
tiles/<city>/
  manifest.json            tile-manifest.schema.json
  pois.json                poi.schema.json
  height.u16               optional height grid for terrain-aware picking
  <style-id>/<L>/<col>_<row>.<format>
```

- Pyramid geometry: projection.md section 4.
- The alpha channel is flattened onto `background`; published tiles are opaque.
- Level `maxLevel` tiles are the master image cut without resampling. Lower levels are produced
  by repeated 2× reduction with a documented kernel (chosen and benchmarked in WP06); the
  viewer shows magnified pixels with nearest-neighbour sampling.
- Tile files are immutable per `release`. A CDN migration only changes `styles[].tilesBase`
  to an absolute URL; nothing else in the viewer changes.
- `manifest.json` and `pois.json` validate against their schemas; every tile implied by the
  manifest exists; no other files are present. `make validate-tiles` checks all of this plus
  the size budget.

## 3. Viewer obligations

- Reads only `manifest.json`, `pois.json`, the optional height grid and tiles. No GIS library,
  no projection library, no AI provider code in the browser bundle.
- Resolves every URL relative to the manifest URL, which itself is resolved against
  `import.meta.env.BASE_URL`.
- Shows every `attribution` entry at all times (collapsible on small screens, never removed).
- Uses projection.md sections 5.2 and 6 for the URL fragment; POI markers use `X`, `Y` as given.
