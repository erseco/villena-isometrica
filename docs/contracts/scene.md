# Contract: scene (GIS pipeline → renderer)

Status: **v1 — proposed, pending WP02 review.** Schema:
`packages/geo-contracts/schemas/scene-manifest.schema.json`. Fixture:
`tests/fixtures/scene-synthetic/`.

A *scene* is a directory, by default `build/<city>/scene/`, containing `scene.json` (the scene
manifest) and the files it references. It is the **only** input of the renderer: the renderer
never reads raw geodata, and the GIS pipeline never renders.

## Rules

- All coordinates are world coordinates: EPSG:25830 `(E, N)` in metres, heights `H` in metres in
  the vertical datum named in the manifest. The renderer subtracts the origin itself.
- Vector layers are GeoJSON `FeatureCollection`s with projected coordinates (a deliberate
  deviation from RFC 7946; the CRS is stated in the manifest, not in the files).
  Coordinates are rounded to 0.01 m. Polygons are valid, exterior rings counter-clockwise,
  no self-intersections, no duplicate consecutive vertices; multi-part geometries are exploded
  into single-part features.
- Features are sorted by `id`; JSON keys are sorted; no timestamps. Same inputs → byte-identical
  scene. `sha256` values in the manifest make this checkable.
- The scene covers the AOI grown by `aoi.marginM` on every side. Features are clipped to that
  rectangle. The terrain grid covers at least the same rectangle.
- Every `id` is a string, unique within its layer and stable across pipeline runs (derived from
  source identifiers, never from row order).
- Every estimated value carries a `...Source` property saying where it came from. The renderer
  and the published credits rely on this to never present a guess as measured fact.

## terrain (`terrain.f32`)

Bare-earth ground heights `H`, raw little-endian float32, row-major, first row northernmost,
samples at cell centres (see the schema's grid description). No NoData: gaps are filled by the
GIS pipeline. Under buildings the grid holds the interpolated ground, not the roof.

## buildings (`buildings.geojson`) — Polygon

One feature per building *part* (a footprint region with a single height).

| Property | Type | Meaning |
|---|---|---|
| `id` | string | e.g. `<cadastral reference>_<part>` |
| `buildingId` | string | groups parts of one building |
| `baseH` | number | ground height at the footprint (minimum terrain under it), m |
| `heightM` | number > 0 | height of the eaves/roof plane above `baseH`, m |
| `heightSource` | `"surface-model"` \| `"floors"` \| `"default"` | how `heightM` was obtained |
| `floors` | integer \| null | floors above ground from the source, if any |
| `roof` | `"flat"` \| `"pitched"` \| `"unknown"` | only `"pitched"`/`"flat"` when data supports it |
| `roofSource` | `"surface-model"` \| `"tag"` \| `"none"` | |
| `use` | `"residential"` \| `"religious"` \| `"civic"` \| `"industrial"` \| `"commercial"` \| `"agricultural"` \| `"fortification"` \| `"other"` | drives procedural facade style |
| `landmark` | string \| null | POI id when this part belongs to a named landmark |

## roads (`roads.geojson`) — LineString

| Property | Type | Meaning |
|---|---|---|
| `id` | string | e.g. `osm-way-<id>` (split segments get `-<n>`) |
| `class` | `"primary"` \| `"secondary"` \| `"residential"` \| `"service"` \| `"pedestrian"` \| `"steps"` \| `"path"` \| `"rail"` | |
| `widthM` | number > 0 | carriageway width |
| `widthSource` | `"tag"` \| `"class-default"` | |
| `name` | string \| null | |
| `layer` | integer | 0 = on the ground; bridges > 0, tunnels < 0 (tunnels are not rendered) |

Roads are draped on the terrain by the renderer; no per-vertex heights.

## landcover (`landcover.geojson`) — Polygon

Non-overlapping polygons; anything not covered is rendered as the default ground.

| Property | Type |
|---|---|
| `id` | string |
| `class` | `"paved"` \| `"park"` \| `"scrub"` \| `"woodland"` \| `"farmland"` \| `"bare-rock"` \| `"water"` \| `"sports"` \| `"cemetery"` |
| `name` | string \| null |

## trees (`trees.geojson`, optional) — Point

| Property | Type | Meaning |
|---|---|---|
| `id` | string | |
| `heightM` | number > 0 | |
| `crownRadiusM` | number > 0 | |
| `source` | `"mapped"` \| `"surface-model"` \| `"scattered"` | `"scattered"` = procedurally placed inside a woodland/park polygon with a fixed seed; decorative, not a real tree position |

## pois (`pois.json`)

Same structure as `poi.schema.json` but `X`, `Y` are omitted: the tile-export step computes
them with the final projection and writes the published file. Linear or large features
(streets, squares) carry `worldBounds`, which the exporter turns into `imageBounds`.

## zRange

`zMin` ≤ (lowest terrain sample − 1 m) − H0 and `zMax` ≥ (highest of terrain, `baseH + heightM`
+ roof allowance of 6 m, tree tops) + 1 m − H0. The renderer derives the master-image size
from it (projection.md section 3), so it must be computed from the data, not guessed.
