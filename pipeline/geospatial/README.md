# geospatial — raw open data → scene

Builds the scene directory defined in `docs/contracts/scene.md` from the datasets listed in
`cities/<city>/datasets.json`. Reads nothing else from the network or disk, never renders.

```sh
uv sync --project pipeline --frozen
uv run --project pipeline python -m acquisition.fetch --city cities/villena/city.json
uv run --project pipeline python -m geospatial.build_scene --city cities/villena/city.json \
    --out build/villena/scene --report cities/villena/scene-report.md --preview cities/villena/scene-preview.png
# without the two manual IGN files (lower quality, never for a release):
uv run --project pipeline python -m geospatial.build_scene --city cities/villena/city.json \
    --out build/villena/scene --terrain-fallback
uv run --project pipeline pytest pipeline/tests -q
```

`--data-root` (default `.`) is the directory that `localPath` in the dataset manifest is relative
to: the repository root for `data/raw/...` paths.

## Inputs

The build looks datasets up by **id** in the dataset manifest:

| Dataset id | Role | Mode |
|---|---|---|
| `catastro-buildings` | Catastro INSPIRE Buildings zip (`*.buildingpart.gml`, `*.building.gml`), read in place with pyogrio's bundled GDAL | both |
| `ign-mdt50cm` | IGN MDT50cm, bare earth | full |
| `ign-mds50cm` | IGN MDS50cm, surface | full |
| `ign-mdt05-wcs` | IGN MDT05 GetCoverage response (5 m) | fallback |
| `osm-overpass` | Overpass JSON with `out geom` (query: below) | both |

Plus `cities/<city>/poi-selection.json` (curated POIs, WP01).

Every input must be listed with a pinned sha256; a mismatch or an unpinned entry stops the build.
CRSs are asserted: rasters must be EPSG:25830 (a raster without a CRS is accepted only when its
manifest entry declares EPSG:25830, which is the case for the WCS ASCII grid); Catastro GML must
be EPSG:25830; OSM is WGS84 and is transformed with PyProj (`always_xy=True`).

**WCS responses are multipart.** `servicios.idee.es` answers `GetCoverage` with a
`multipart/related` body (the grid, an `.aux.xml` and a `.prj`) even for
`FORMAT=application/asc`. The response is stored exactly as received (so its checksum is the
download's) and the raster part is extracted when read.

Overpass query used for Villena (AOI + 120 m margin, bbox in `s,w,n,e`):

```
[out:json][timeout:90];
( way["highway"](S,W,N,E); way["railway"](S,W,N,E); way["landuse"](S,W,N,E); way["natural"](S,W,N,E);
  way["leisure"](S,W,N,E); way["amenity"~"^(parking|grave_yard)$"](S,W,N,E); way["place"="square"](S,W,N,E);
  way["waterway"="riverbank"](S,W,N,E); node["natural"="tree"](S,W,N,E); );
out geom;
```

## What it does

All work happens inside the clip rectangle = AOI grown by `marginM`.

**Terrain** — MDT50cm resampled to a 1 m grid aligned to whole metres (area average); MDT05 is
resampled bilinearly in fallback mode. Gaps are filled by GDAL `fillnodata`. Rounded to 1 mm.

**Surface model** (full mode) — MDT50cm and MDS50cm on a common 0.5 m grid (bilinear; identical
to a copy when the source grids are aligned, which the report states). nDSM = MDS − MDT. Roof
slope = gradient of a 3×3-smoothed MDS.

**Buildings** (Catastro `BuildingPart`)

| Step | Rule |
|---|---|
| Repair | `make_valid`, clip to the rectangle, explode multi-parts (`<id>-<n>`), 0.01 m precision, drop < 1 m², CCW exterior rings |
| Skip | parts with 0 floors above and ≥ 1 below (underground only); parts with 0 floors above ground and no measured height ≥ 2 m (Catastro: nothing built above ground — patios, terraces) |
| `baseH` | lowest 1 m terrain cell centre inside the footprint (bilinear at an interior point for tiny parts) |
| `heightM`, `surface-model` | samples of the surface model inside the footprint shrunk by 0.75 m; requires ≥ 20 samples and p80(nDSM) ≥ 2 m; then p80(MDS) − baseH for flat/unknown roofs, p5(MDS) − baseH (≈ eaves) for pitched roofs |
| `heightM`, `floors` | `floors × 3.0 + 1.0` m when `numberOfFloorsAboveGround ≥ 1` |
| `heightM`, `default` | 3.0 m (floors unknown) |
| `roof` | median roof gradient inside the footprint shrunk by 1.25 m: `< 0.06` flat, `> 0.15` pitched, else unknown; always unknown without a surface measurement |
| Zoning | landmark parts, and parts > 300 m² whose nDSM p90 − p10 > 4 m, are split into zones: MDS quantised into 3 m bins, polygonised, simplified (0.5 m), intersected with the footprint; zones < 9 m² dropped; zones whose median nDSM < 1.5 m dropped as open ground (courtyards). Each zone is measured like a part, has its own `baseH`, id `<part id>_z<n>`, `floors: null` |
| `use` | `currentUse` of the parent Catastro `Building`: 1_residential→residential, 2_agriculture→agricultural, 3_industrial→industrial, 4_1_office/4_2_retail→commercial, 4_3_publicServices→civic, else other |
| `landmark` | a POI of kind landmark/church/civic/museum tags the part containing it (else the nearest part within 25 m — Villena's castle node is 15.6 m from the keep, its only Catastro part) and every part of the same cadastral reference; church → `religious`, civic/museum → `civic`, landmark whose name matches castillo/torre/muralla/alcazaba → `fortification` |

Heights are always measured relative to `baseH`, so for a part on a slope the roof elevation is
what is preserved. Parts clipped at the rectangle edge keep their real roof elevation.

**Roads** (OSM `highway`, `railway`)

| OSM | class | default width |
|---|---|---|
| motorway, trunk, primary (+ links) | primary | 9.0 |
| secondary, tertiary (+ links) | secondary | 7.5 |
| residential, unclassified, living_street | residential | 6.0 |
| service, track | service | 3.5 |
| pedestrian (not `area=yes`) | pedestrian | 5.0 |
| steps | steps | 2.5 |
| footway, path, cycleway, bridleway | path | 2.0 |
| railway rail, light_rail, narrow_gauge | rail | 3.0 |

Everything else (construction, proposed, platform, corridor, abandoned…) is ignored. `width` tag
in metres wins (`widthSource: tag`). `layer` tag, else bridge → 1, tunnel → −1, else 0.

**Land cover** (closed OSM ways), priority order — earlier classes win where polygons overlap:
water · sports · cemetery · park (park, garden, playground, grass, recreation_ground,
village_green) · paved (pedestrian areas, squares, parking) · woodland · scrub · farmland ·
bare-rock. Multipolygon relations are skipped and counted in the report.

**Trees** — OSM `natural=tree` nodes (`source: mapped`; height from the `height` tag, else 6 m;
crown from `diameter_crown`, else 2.5 m radius). In full mode also canopy peaks: local maxima of
nDSM ≥ 2.5 m in a 3 m window, outside building footprints grown by 1.5 m, at least 3 m from any
other tree (`source: surface-model`; height = nDSM peak; crown radius = 0.35 × height, clamped to
1–6 m). No procedurally scattered trees.

**POIs** — curated POIs from `poi-selection.json` (outside the AOI → error). `H` = roof of the
part containing it for landmark/church/civic/museum, else terrain. Plus one `street` POI per
distinct OSM street name inside the AOI: anchor = point of the merged street nearest its
centroid, `worldBounds` = its bounds inside the AOI, `source.ref` = the longest way.

**zRange** — from the data, per `docs/contracts/scene.md` (6 m roof allowance).

## Guarantees and checks

- Byte-identical output for identical inputs: sorted features and keys, rounded coordinates,
  no timestamps; tested.
- The build fails (never warns) on: unpinned or mismatching inputs, wrong CRS, an input raster
  that does not cover the rectangle, geometry outside the rectangle, invalid polygons after
  rounding, duplicate ids, `heightM` ≤ 0 or > 80 m, NaN terrain, POIs outside the AOI, a
  `scene.json` that does not validate, or an output directory that is not a scene directory.

## Limitations (v0.1)

- Thresholds above were tuned on synthetic data only; check them against the first real
  surface model (the report's disagreement table is the place to look).
- Zoning works at 0.5 m: narrow walls (< 1 m) may disappear or merge with neighbours.
- OSM multipolygon relations are not assembled.
- Mapped trees without a `height` tag get a default height.
