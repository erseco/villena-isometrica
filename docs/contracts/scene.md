# Contract: scene (GIS pipeline → renderer)

Status: **v1 — FROZEN at gate G1 (2026-11-15)**; changes only through
`prompts/00-bootstrap.md` Task B. Schemas: `scene-manifest.schema.json` and
`scene-pois.schema.json` in `packages/geo-contracts/schemas/`. Fixture:
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
- Features and POIs are sorted by `id`; JSON keys are sorted; no timestamps. Same inputs →
  byte-identical scene **from one producer**. `sha256` values in the manifest make this
  checkable. JSON text is not comparable across languages (number formatting differs): tests
  that cross a language boundary compare parsed values, with a tolerance of one unit in the
  last rounded decimal — the rounding mode at exact ties is deliberately not specified.
- Numbers are finite: `NaN` and `Infinity` are not JSON and are rejected at every boundary.
- A consumer checks `schemaVersion` before validating against a schema (schemas are closed, so
  a newer MINOR document fails an older schema on its new optional fields).
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
| `heightM` | number > 0 | height of the **wall top** above `baseH`, m: the roof plane of a flat roof, the eaves of a pitched one. This is the extrusion height. |
| `ridgeHeightM` | number > `heightM` (optional) | highest point of a pitched roof above `baseH`, m — present only when `roof` is `"pitched"` and the ridge was measured (`roofSource: "surface-model"`). Without it the renderer adds a procedural roof no higher than the 6 m roof allowance. The ridge **direction** is never data: it is always procedural. |
| `heightSource` | `"surface-model"` \| `"floors"` \| `"default"` | how `heightM` was obtained |
| `floors` | integer \| null | floors above ground from the source, if any |
| `roof` | `"flat"` \| `"pitched"` \| `"unknown"` | only `"pitched"`/`"flat"` when data supports it |
| `roofSource` | `"surface-model"` \| `"tag"` \| `"none"` | |
| `use` | `"residential"` \| `"religious"` \| `"civic"` \| `"industrial"` \| `"commercial"` \| `"agricultural"` \| `"fortification"` \| `"other"` | drives procedural facade style |
| `landmark` | string \| null | POI id when this part belongs to a named landmark |
| `parapet` | `"battlement"` (optional, v1.1) | curated: the wall top carries merlons. Only on parts of a landmark listed in the city's `landmark-details.json`. |
| `material` | `"stone"` \| `"brick"` \| `"plaster"` (optional, v1.1) | curated wall material of a landmark part; overrides the style derived from `use` |

## roads (`roads.geojson`) — LineString

| Property | Type | Meaning |
|---|---|---|
| `id` | string | e.g. `osm-way-<id>` (split segments get `-<n>`) |
| `class` | `"primary"` \| `"secondary"` \| `"residential"` \| `"service"` \| `"pedestrian"` \| `"steps"` \| `"path"` \| `"rail"` | |
| `widthM` | number > 0 | carriageway width |
| `widthSource` | `"tag"` \| `"class-default"` | |
| `name` | string \| null | |
| `layer` | integer | 0 = on the ground; bridges > 0, tunnels < 0 (tunnels are not rendered) |

Roads are draped on the terrain by the renderer; no per-vertex heights. Bridges (`layer > 0`)
are draped too in v0.1: a bridge over a cutting is drawn at ground level.

## landcover (`landcover.geojson`) — Polygon

Non-overlapping polygons; anything not covered is rendered as the default ground. The producer
resolves overlaps in the source data with a documented class priority; consumers may assume
there are none.

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
| `source` | `"mapped"` \| `"surface-model"` \| `"scattered"` | `"scattered"` = procedurally placed inside a woodland/park polygon; decorative, not a real tree position. Positions derive from a hash of the polygon `id` and an index — never from random-generator state — so reruns are identical. |

## structures (`structures.geojson`, optional) — Polygon

Footprints of landmark structures that Catastro does not model as buildings — in Villena, the
castle's curtain walls and the town walls — taken from OpenStreetMap. Same properties and the
same rendering as `buildings`, in a separate file because the source and its licence differ
(OSM-derived data is never merged into the Catastro-derived layer).

- Source features: the OSM building polygon (way or multipolygon) that contains a POI of kind
  `landmark`, and OSM `barrier=city_wall` / `barrier=wall` lines inside a landmark polygon or
  tagged as historic, buffered to their width. Area already covered by a Catastro building
  part is subtracted, so nothing is drawn twice.
- `id` = `osm-<type>-<id>[_z<n>]`, `buildingId` = `osm-<type>-<id>`, `floors` = null.
- Heights follow the same rules and the same `heightSource` labels as buildings. Without a
  surface model the height is the labelled default: an OSM outline says where a wall is, not
  how tall it is.

## details (`details.geojson`, optional, v1.1) — Point

Curated solids that give the few landmarks everybody looks for their recognisable silhouette
where footprints and a height per part cannot: a spire, a round tower, a dome
(`docs/decisions/0008-landmark-details-and-aoi.md`). They are **not measured geometry**: the
shape comes from cited reference photographs, the position and dimensions from the surface model
wherever it resolves them. They exist only for landmarks listed in
`cities/<city>/landmark-details.json`, which carries the references.

Every solid is a body of revolution (or a regular pyramid) on a vertical axis through the point,
except `gable`, a rectangular hall with a two-pitch roof centred on the point.

| Property | Type | Meaning |
|---|---|---|
| `id` | string | `<landmark>-<name>` |
| `landmark` | string | POI id |
| `kind` | `"cylinder"` \| `"cone"` \| `"dome"` \| `"gable"` | cylinder: constant radius. cone: radius `radiusM` at the base to `topRadiusM` at the top (a frustum when > 0). dome: half ellipsoid, radius `radiusM`, rise `heightM`. gable: a box `lengthM` × `widthM` with vertical walls up to `wallHeightM` and a two-pitch roof whose ridge runs along the length at `heightM`; the two end walls are vertical gables. |
| `baseH` | number | height of the solid's base, m (absolute, same datum as the terrain) |
| `heightM` | number > 0 | height of the solid above `baseH`, m |
| `radiusM` | number > 0 (all kinds but gable) | base radius, m (for `sides` = 4: half the side of the square base) |
| `lengthM`, `widthM` | number > 0 (gable only) | plan size, m; the ridge runs along the length |
| `wallHeightM` | number > 0, < `heightM` (gable only) | eaves height above `baseH`, m |
| `roofMaterial` | `"tile"` \| `"slate"` \| `"metal"` (gable only) | material of the two roof slopes; `material` is the walls |
| `openings` | `"arcade"` (optional, cylinder only) | curated: the wall carries regularly spaced arched openings in two tiers (a bullring facade) |
| `topRadiusM` | number ≥ 0 (optional, cone only; default 0) | top radius, m |
| `sides` | 0 \| 4 (optional, cone only; default 0) | 0 = round, 4 = square pyramid |
| `rotationDeg` | number (optional; default 0) | for `sides` = 4: bearing of one face normal; for a gable: bearing of the ridge. Degrees clockwise from north |
| `material` | `"stone"` \| `"brick"` \| `"plaster"` \| `"tile"` \| `"slate"` \| `"metal"` | |
| `parapet` | `"battlement"` (optional, cylinder only) | merlons on the top rim |
| `shapeSource` | `"reference"` | always: the shape is curated from reference photographs |
| `dimensionsSource` | `"surface-model"` \| `"estimated"` | whether position and size were measured on the surface model or estimated from the references |

The renderer draws details as opaque solids with depth testing like any building, writes
semantic class 7 (`landmark-detail`) for their pixels and lists each detail `id` in the
`buildingId` index. A detail may overlap building parts; nothing is subtracted. `zRange` includes
the details.

## pois (`pois.json`)

Validated by `scene-pois.schema.json`: the published POI record without `X`, `Y` and
`imageBounds`, which the tile-export step computes with the final projection. Linear or large
features (streets, squares) carry `worldBounds`, which the exporter turns into `imageBounds`.
Sorted by `id`.

## zRange

`zMin` ≤ (lowest terrain sample − 1 m) − H0 and `zMax` ≥ (highest of: terrain; for every
building part and structure `baseH + ridgeHeightM` when present, else `baseH + heightM` + the
6 m roof allowance; tree tops) + 1 m − H0. Terrain in the margin counts. The renderer derives the master-image size
from it (projection.md section 3), so it must be computed from the data, not guessed.

## Pipeline inputs (dataset manifest)

Not part of the renderer's contract, but fixed here because two work packages meet on it. The
GIS pipeline finds its inputs in `cities/<city>/datasets.json` by these ids:

| id | Content |
|---|---|
| `catastro-buildings` | Catastro INSPIRE Buildings zip |
| `ign-mdt50cm` | IGN bare-earth model, 0.5 m (manual download) |
| `ign-mds50cm` | IGN surface model, 0.5 m (manual download) |
| `ign-mdt05` | IGN 5 m terrain, WCS response stored as received (fallback mode) |
| `osm` | OpenStreetMap Overpass JSON for AOI + margin (ways with inline geometry or with node references — both are accepted) |

`localPath` is relative to the repository root (the pipeline's `--data-root`), e.g.
`data/raw/osm/osm-aoi-margin.json`. Curated POIs: `cities/<city>/poi-selection.json`.
