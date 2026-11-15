# Data sources

Summary of the datasets chosen for Villena v0.1.0. Facts were verified on 2026-11-15; the
evidence, exact requests and open questions are in `docs/research/02-cadastre-osm-aoi.md` and
`docs/research/03-ign-cnig-rasters-lidar.md`. The machine-readable manifest with sizes and
checksums is `cities/villena/datasets.json` (WP01). Licence terms: `docs/LICENSING.md`.

## Area of interest

| | |
|---|---|
| Municipality | Villena, INE and Catastro code `03140` |
| AOI | E 685500–686500, N 4277500–4278500, ETRS89 / UTM 30N (EPSG:25830) — 1 km² |
| WGS84 envelope | S 38.626433, W −0.869027, N 38.635648, E −0.857279 |
| Margin | 120 m of context on every side for the pipeline |
| Map sheets | MTN50 0845 "Yecla"; MTN25 0845-2 "Villena"; 1:5 000 sheet 0845-8-2 |

Landmarks (OSM element centres, verified by query):

| Landmark | Lat | Lon | Reference |
|---|---|---|---|
| Castillo de la Atalaya | 38.631934 | −0.860915 | OSM node 306347007, Wikidata Q2986978 |
| Iglesia de Santiago | 38.631572 | −0.863878 | OSM way 475846918, Q4882903 |
| Iglesia de Santa María | 38.630219 | −0.861051 | OSM way 696092481, Q4882109 |
| Plaza Mayor | 38.630241 | −0.862263 | OSM way 410546874, Q4163397 |
| Ayuntamiento | 38.631427 | −0.863049 | OSM way 550230731, Q11697358 |
| Teatro Chapí | 38.630514 | −0.866403 | Wikidata Q11704261 (not mapped in OSM) |
| Railway station | 38.632266 | −0.867951 | OSM node 2021580965, Q3329171 |
| Plaza de Toros (outside AOI) | 38.639558 | −0.868410 | OSM way 205835401, Q6377328 |

The castle is at about E 686188, N 4278098: east of centre, with the old town to its west and
south-west. That is why the camera looks north-east (ADR 0003).

## Datasets used

| Dataset | Provider | What we take | Resolution / date | CRS | Access | Size |
|---|---|---|---|---|---|---|
| INSPIRE Buildings `A.ES.SDGC.BU.03140.zip` | Dirección General del Catastro | `BuildingPart` footprints + floors above ground; `Building` use and construction date | vector; dataset date 2026-08-21 | EPSG:25830 | Scriptable (ATOM): `https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/03/03140-VILLENA/A.ES.SDGC.BU.03140.zip` | 3.97 MB |
| MDT50cm, 3rd coverage, V1 (provisional) `MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` | IGN / CNIG | bare-earth terrain | 0.5 m; flight 2023 | ETRS89 UTM 30N, orthometric heights (EGM08) | **Manual** — Centro de Descargas, reCAPTCHA-protected | 61 MB |
| MDS50cm, 3rd coverage, V1 (provisional) `MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` | IGN / CNIG | surface heights → building and tree heights (MDS − MDT) | 0.5 m; flight 2023 | same | **Manual**, same procedure | 114 MB |
| MDT05 via WCS `https://servicios.idee.es/wcs-inspire/mdt`, coverage `Elevacion25830_5` | IGN | fallback terrain when the manual files are absent | 5 m; 2009 | EPSG:25830 | Scriptable (request a format that keeps decimals: `application/asc`) | < 1 MB |
| OpenStreetMap, Overpass snapshot of AOI + margin | OSM contributors | streets, railways, land cover, water, trees, POIs | vector; snapshot date pinned at retrieval | EPSG:4326 | Scriptable (Overpass API) | < 20 MB |

Total to download: about 200 MB. Disk for raw + intermediates + outputs: under 2 GB.

## What the data can and cannot give

- **Footprints** are real (6 813 building parts in the AOI).
- **Heights in metres do not exist in Catastro**: only floors per part (0–14; 205 parts in
  the AOI have 0). Heights come from the surface model where possible, and each building
  records which source was used.
- **The castle** is a single Catastro part with 3 floors. Its towers and walls are recovered,
  as far as 0.5 m rasters allow, by segmenting the surface model. Finer architectural detail
  is not in the data and will not be drawn.
- **Roof shape**: flat versus pitched may be inferred from the surface model; ridge layout is
  not attempted in v0.1.
- **OSM in Villena**: streets good (428 highway ways in the AOI, 313 named, 41 stairways);
  buildings poor (not used); 11 mapped trees — canopy is detected from the surface model.

## Considered and not used in v0.1.0

| Dataset | Why not |
|---|---|
| PNOA orthophoto (0.25 m, 2024; WMS/WMTS scriptable) | Not needed for a procedural render. Useful later for QA or colour hints. |
| PNOA-LiDAR 3rd coverage (≥ 5 pts/m², 1 km LAZ tiles, 154 MB for the AOI) | The ready-made 0.5 m MDT/MDS from the same flight are sufficient; avoids PDAL. |
| MDT02 + MDSnE2,5 / MDSnV2,5 (2016–17) | Older and coarser; documented fallback if the 3rd-coverage sheets prove unusable. |
| Catastro Cadastral Parcels, Addresses | No need in v0.1 (no address search). |
| Catastro WFS / WMS | WFS is capped at 5 000 features per request; WMS forbids bulk use. ATOM is the right channel. |
| OSM buildings | 1 317 in the AOI, one with levels, none with height. |
| BTN, CartoCiudad | Redundant with Catastro + OSM here. |
| Google Photorealistic 3D Tiles, Earth, Street View | Licence forbids storing and deriving content. Never used. |
| Sketchfab models of the castle | None found with a licence permitting reuse. |

## Open questions (assigned to WP01)

1. Exact footprint of sheet 0845-8-2: research inferred it contains the AOI + margin (east
   edge ≈ E 686 950); must be confirmed from the file or the sheet index.
2. Name/EPSG of the vertical reference of the 3rd-coverage models; whether MDT and MDS share
   a pixel grid; implications of "V1 provisional".
3. Whether derived vector data from Catastro may be redistributed (rendered images may).
4. Exact citation wording currently requested by Catastro and by the OSMF.
