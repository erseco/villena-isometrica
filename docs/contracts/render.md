# Contract: render output and published tiles

Status: **v1 — FROZEN at gate G1 (2026-11-15)**; changes only through
`prompts/00-bootstrap.md` Task B. Schemas: `render-manifest.schema.json`,
`palette.schema.json`, `tile-manifest.schema.json`, `poi.schema.json` in
`packages/geo-contracts/schemas/`. Fixtures: `tests/fixtures/render-synthetic/`,
`tests/fixtures/tiles-synthetic/`.

## 1. Render output (renderer → tile export)

Directory `build/<city>/render/` with `render.json`, `palette.json` and one full master-image
file per layer.

| Layer | Encoding | Content |
|---|---|---|
| `color` (required) | `rgba8-png` | Final pixel art, sRGB, straight alpha: alpha is 255 where something was drawn and 0 elsewhere, nothing in between. Every drawn pixel is exactly a colour of `palette.json`. |
| `class` (required) | `index8-png` | 0 background, 1 ground, 2 road, 3 wall, 4 roof, 5 vegetation, 6 water, 7 landmark-detail. |
| `buildingId` (required) | `rgb24-id-png` | `R<<16 \| G<<8 \| B` = index into the JSON array at `index` (array of scene building-part ids; index 0 = "no building"). |
| `depth` (optional) | `gray16-png` | Pixel value `n` encodes `d = offset + scale · n` metres (`d` as in projection.md §3), with `offset = dMin` and `scale = (dMax − dMin) / 65535`, both on the layer object in `render.json`; `dMin`/`dMax` are the extremes of `d` over the drawn pixels. Undrawn pixels carry 0. |

**Palette.** `palette.json` (`palette.schema.json`) is data, not documentation: name, version
and the list of colours with a role each. The render manifest references it with its sha256, so
a palette change is visible and invalidates golden hashes on purpose. The exporter's validator
rejects any drawn `color` pixel that is not in it.

Requirements:

- **Deterministic pixels, everywhere**: the same scene, city config and renderer version
  produce identical *decoded* layers on macOS arm64 and Ubuntu x86-64. Each layer carries
  `pixelSha256` = sha256 of its decoded samples, row-major from the top-left, with no header:
  `rgba8` → 4 bytes R,G,B,A per pixel; `index8` → 1 byte; `rgb24-id` → 3 bytes R,G,B;
  `gray16` → 2 bytes, big-endian. This is the cross-platform identity that tests compare.
- **Deterministic files, within one pinned build**: file bytes (`sha256`) depend on the PNG
  encoder and its zlib, so they are required to be stable only for one pinned toolchain on one
  platform. `renderer.version` records the renderer and its encoder.
- **Pixel-exact**: no anti-aliasing, no filtering, no colour management surprises: every drawn
  colour pixel is exactly a palette colour.
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

- Pyramid geometry: projection.md section 4. Tile size and overlap come from the city config;
  the height-grid cell size is the exporter's choice (default 4 m) and is recorded in the
  manifest. The city config's `tiles.format` is a request to the exporter; for consumers the
  truth is `styles[].format` in the manifest.
- The manifest carries `crs` and `renderSha256` (sha256 of the `render.json` it was cut from),
  so a published pyramid can be traced to its render and its scene.
- `pois.json` is sorted by `id`.
- The alpha channel is flattened onto `background`; published tiles are opaque.
- Level `maxLevel` tiles are the master image cut without resampling. Lower levels are produced
  by repeated 2× reduction with a documented kernel (chosen and benchmarked in WP06); the
  viewer shows magnified pixels with nearest-neighbour sampling.
- Tile files are immutable per `release`. A CDN migration only changes `styles[].tilesBase`
  to an absolute URL; nothing else in the viewer changes.
- `manifest.json` and `pois.json` validate against their schemas; every tile implied by the
  manifest exists; no other files are present. `make validate-tiles` checks all of this plus
  the size budget, and cross-checks the redundant POI coordinates: `forward(E, N, H)`
  reproduces `X, Y` within 1e-3 px, and `geoToWorld(lon, lat)` reproduces `E, N` within
  `maxResidualM` (which must itself be < 0.1 m).

## 3. Viewer obligations

- Reads only `manifest.json`, `pois.json`, the optional height grid and tiles. No GIS library,
  no projection library, no AI provider code in the browser bundle.
- Resolves every URL relative to the manifest URL, which itself is resolved against
  `import.meta.env.BASE_URL`.
- Shows every `attribution` entry at all times (collapsible on small screens, never removed).
- Uses projection.md sections 5.2 and 6 for the URL fragment; POI markers use `X`, `Y` as given.
  A background pixel has no position ("no pick"): the URL and markers are left as they were.
