# geospatial — raw open data → scene

Builds the scene directory defined in `docs/contracts/scene.md` from the datasets listed in
`cities/<city>/datasets.json`. Reads nothing else from the network or disk, never renders.

```sh
make install
make scene CITY=villena            # = the build_scene command below, into build/villena/scene
PYTHONPATH=pipeline uv run --project pipeline --frozen python -m acquisition.fetch --city cities/villena/city.json
PYTHONPATH=pipeline uv run --project pipeline --frozen python -m geospatial.build_scene \
    --city cities/villena/city.json --out build/villena/scene \
    --report cities/villena/scene-report.md --preview cities/villena/scene-preview.png
# without the two manual IGN files (lower quality, never for a release): add --terrain-fallback
uv run --project pipeline --frozen pytest pipeline/tests -q
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
| `ign-mdt05` | IGN MDT05 GetCoverage response (5 m) | fallback |
| `osm` | Overpass JSON; ways with inline geometry (`out geom`) or node references (`out body; >; out skel`) — both work, and repeated skeleton copies of member ways are dropped | both |

Plus `cities/<city>/poi-selection.json` (curated POIs, WP01).

Every input must be listed with a pinned sha256; a mismatch or an unpinned entry stops the build.
CRSs are asserted: rasters must be EPSG:25830 or EPSG:3042 (the same datum and projection with the
authority axis order N,E — what the CNIG 0.5 m sheets are tagged with) (a raster without a CRS is accepted only when its
manifest entry declares EPSG:25830, which is the case for the WCS ASCII grid); Catastro GML must
be EPSG:25830; OSM is WGS84 and is transformed with PyProj (`always_xy=True`).

**WCS responses are multipart.** `servicios.idee.es` answers `GetCoverage` with a
`multipart/related` body (the grid, an `.aux.xml` and a `.prj`) even for
`FORMAT=application/asc`. The response is stored exactly as received (so its checksum is the
download's) and the raster part is extracted when read.

The Overpass query and the WCS request for Villena are in `cities/villena/ACQUISITION.md`.

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
| `heightM`, `surface-model` | samples of the surface model inside the footprint shrunk by 0.75 m; requires ≥ 20 samples and p80(nDSM) ≥ 2 m; then p80(MDS) − baseH for flat/unknown roofs, p5(MDS) − baseH (≈ eaves) for pitched roofs. A pitched part whose eaves would be < 2 m, or whose p95 − p5 rise exceeds 6 m, is not one simple pitched roof (ground at the footprint edge, or several levels in one part): it is measured as `unknown` (p80) |
| `ridgeHeightM` | pitched roofs only: p95(MDS) − baseH, written when it is at least 0.3 m above `heightM` |
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
bare-rock. Closed ways and multipolygon relations whose member ways are closed rings;
relations with rings split over open ways are counted as unresolved in the report.

**Structures** (`structures.geojson`, written only when not empty) — landmark structures Catastro
does not model, from OSM: the building polygon (way or multipolygon) containing a POI of kind
`landmark`, and `barrier=city_wall` ways (also `barrier=wall` when tagged `historic` or inside a
landmark polygon), buffered to their `width` (default 1.5 m). The outer ring of an accepted
polygon is not added again as a wall. What Catastro or an earlier structure already covers is
subtracted; an outline with less than 25 % left is dropped as already modelled, and pieces under
4 m² are dropped. Heights as for buildings (thin walls are sampled without the inward buffer);
landmark structures are zoned. **With a surface model a structure is kept only where the model
measures ≥ 2 m**; without one it gets the labelled 3 m default. In Villena: the castle enclosure
(OSM relation 8046264, whose hole is the keep that Catastro has) and ten town-wall segments.

**Trees** — OSM `natural=tree` nodes (`source: mapped`; height from the `height` tag, else 6 m;
crown from `diameter_crown`, else 2.5 m radius). In full mode also canopy peaks: local maxima of
nDSM ≥ 2.5 m in a 3 m window, outside building and structure footprints grown by 1.5 m (the whole outline of a zoned part, since
zoning leaves gaps), at least 3 m from any
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

- First run on the real Villena sheets (2026-11-15): measured heights agree with Catastro floor
  counts (median difference −0.1 m over 5,097 parts; 7 % differ by more than 6 m, mostly small
  parts inside tower blocks that Catastro records with 1–2 floors). The pitched-roof rule and the
  tree mask were corrected from that run; the other thresholds are unchanged and unreviewed.
- Zoning works at 0.5 m: narrow walls (< 1 m) may disappear or merge with neighbours.
- OSM multipolygon rings split over several open ways are not stitched (1 relation in Villena).
- Mapped trees without a `height` tag get a default height.
