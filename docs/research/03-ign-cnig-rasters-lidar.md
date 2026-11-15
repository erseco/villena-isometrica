# 03 — IGN / CNIG rasters, elevation models and LiDAR for Villena

**Verification date: 2026-11-15.** Everything below was checked on that date unless stated otherwise.
Scope: IGN / CNIG / SCNE products only (Cadastre and OSM are in `02-cadastre-osm-aoi.md`).

How to read the "how verified" tags:

- **[queried]** — I sent a request to the live service and read the response.
- **[page]** — read on an official web page / PDF (URL given).
- **[inferred]** — my deduction from queried facts; not stated by the source. Treat as a hypothesis.

Nothing was downloaded beyond capabilities documents, HTML listings, a 16 KB zip, a 145 KB PDF and
three tiny samples (4.7 MB in total, kept outside the repo in the session scratch directory).
**No product file (COG / LAZ) was downloaded**, so nothing about the *inside* of those files
(data type, nodata, internal CRS tags, COPC layout) is verified — see section 10.

---

## 1. Summary table (old town / Castillo de la Atalaya)

| Product | Res. | Acquisition (this zone) | CRS / heights | Unit and file covering the castle | Size | Access |
|---|---|---|---|---|---|---|
| PNOA Máxima Actualidad orthophoto | 0.25 m | 05/2024–06/2024 (castle pixel: 2024-06) | ETRS89 UTM30 | MTN25 `PNOA-MA-OF-ETRS89-HU30-H25-0845-2.TIF` (COG) | 799.01 MB | CdD (interactive) **or WMS/WMTS (scriptable)** |
| MDT50cm, 3rd coverage, V1 (provisional) | 0.5 m | 2023 | ETRS89 UTM30, orthometric | 1:5,000 sheet `MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` (COG) | 61.07 MB | CdD only |
| MDT02, 2nd coverage | 2 m | 2016, 2017 | ETRS89 UTM30, orthometric | MTN25 `MDT02-ETRS89-HU30-0845-2-COB2.TIF` (COG) | 115.58 MB | CdD only |
| MDT05, 1st coverage | 5 m | 2009 | ETRS89 UTM30, orthometric | MTN50 `PNOA-MDT05-ETRS89-HU30-0845-LID.TIF` (COG) | 81.92 MB | CdD, **or WCS (scriptable)** |
| MDT25, 2nd coverage | 25 m | 2016, 2017 | ETRS89 UTM30 | `MDT25-ETRS89-H30-0845-2-COB2.TIF` | 0.88 MB | CdD; 25 m also on WCS |
| MDS50cm, 3rd coverage, V1 (provisional) | 0.5 m | 2023 | ETRS89 UTM30, orthometric | `MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` (COG) | 113.99 MB | CdD only |
| MDS02, 2nd coverage | 2 m | 2016, 2017 | ETRS89 UTM30, orthometric | `MDS02-ETRS89-H30-PM-2-0845-2.TIF` (COG) | 113.06 MB | CdD only |
| MDS05, 1st coverage | 5 m | 2009 | ETRS89 UTM30 | `MDS05-ETRS89-H30-0845-COB1.TIF` (COG) | 82.29 MB | CdD only |
| MDSnE2,5 (buildings nDSM), 2nd cov. | 2.5 m | 2016, 2017 | ETRS89 UTM30, height above ground | MTN50 `NDSM-EDIFICIOS-H30-0845-COB2.TIF` (COG) | 4.26 MB | CdD only |
| MDSnV2,5 (vegetation nDSM), 2nd cov. | 2.5 m | 2016, 2017 | ETRS89 UTM30, height above ground | MTN50 `NDSM-VEGETACION-H30-0845-COB2.TIF` (COG) | 71.94 MB | CdD only |
| LiDAR 3rd coverage | ≥5 pts/m² | 2023 (region flown Aug-2023 → Jun-2024) | ETRS89 UTM30, orthometric (EGM08) | 1×1 km `PNOA-2023-VAL-686-4279-H30-NPC02.laz` | 53.55 MB | CdD only |
| LiDAR 2nd coverage | ≥0.5 pts/m² | 2016–2017 | idem | 2×2 km `PNOA-2016-MUR-VAL-CLM-686-4280-ORT-CLA-RGB.LAZ` (+ `-CIR`) | 23.32 MB (22.69) | CdD only |
| LiDAR 1st coverage | 0.5 pts/m² | 2009–2010 | idem | 2×2 km `PNOA-2009-LOTE3-…-686-4280-ORT-CLA-COL.LAZ` (4 variants) | 38–44 MB | CdD only |

"CdD" = Centro de Descargas, https://centrodedescargas.cnig.es/CentroDescargas/ . All rows **[queried]**
through the CdD file-listing endpoint (section 3) on 2026-11-15, except the regional flight window
(**[page]**, section 6).

**Key finding:** every product at ≤ 2 m, every surface/normalised model and every LiDAR tile is
available **only through the Centro de Descargas, whose download step is protected by reCAPTCHA v3 and
explicit bot detection** (section 3). The scriptable OGC services stop at a 5 m terrain model and the
orthophoto.

---

## 2. Location, sheets and tile geometry

| Fact | Value | How verified |
|---|---|---|
| Castillo de la Atalaya | lat 38.631884563, lon −0.860973419 (so "38.63 N, 0.86 W" is right) | **[queried]** CartoCiudad geocoder, record `BTN_10483257`, type "Fortaleza/castillo", municipality Villena, INE code `03140` |
| Same point in EPSG:25830 | E ≈ 686 187.6, N ≈ 4 278 098.1 | computed locally (Transverse Mercator series on GRS80; no PROJ available). Cross-checked: a WMS GetMap of the 200 m box centred there shows the castle in the middle of the image **[queried]** |
| UTM zone | 30 (so EPSG:25830 is the native CRS of every product here — no reprojection needed) | **[queried]** file names carry `HU30`/`H30`; grid service returns `huso: 30` |
| MTN50 sheet | **0845 "Yecla"** — bbox in EPSG:25830: 657 687.1, 4 262 850.0 → 687 122.0, 4 281 972.1 | **[queried]** WMS `cuadriculas`, layer `cuadricula-mtn50-actual`, grid version `20260303` |
| MTN25 sheet | **0845-2 "Villena"** — bbox: 672 188.3, 4 272 397.5 → 686 906.1, 4 281 972.1 | **[queried]** same service, layer `cuadricula-mtn25-actual` |
| 1:5,000 sheet (3rd-coverage rasters) | **0845-8-2** (column 8 = easternmost, row 2) | **[queried]** from file names returned by CdD; the column/row meaning is **[inferred]** |
| LiDAR 3rd-cov. tile | **686-4279** | **[queried]** |

Geometry notes, all **[inferred]** from the queried numbers above:

- LiDAR tile names give the **north-west corner in km**: a query at E≈685 587, N≈4 277 500 returned
  tile `685-4278`; the castle (686 188, 4 278 098) returned `686-4279`. So `686-4279` covers
  E 686 000–687 000, N 4 278 000–4 279 000, and the 2×2 km tile `686-4280` covers E 686 000–688 000,
  N 4 278 000–4 280 000.
- The castle sits only **188 m from the west edge and 98 m from the south edge** of LiDAR tile
  `686-4279`. A 1 km² box centred on the castle therefore needs **four** 3rd-coverage tiles
  (`685-4279` 41.14 MB, `686-4279` 53.55 MB, `685-4278` 26.68 MB, `686-4278` 32.70 MB = 154.07 MB)
  **[queried]** sizes.
- The east edge of sheet 0845 (and of 0845-2 and 0845-8-2) is at E ≈ 686 950 at the castle's
  latitude, i.e. **≈ 760 m east of the castle**. Sheet 0845-8-2 should span roughly E 683 270–686 950,
  N 4 277 190–4 279 580 (assuming an even 8×8 split of the MTN50 sheet). A 1 km² box centred on the
  castle (±500 m) then fits **inside the single sheet 0845-8-2**, with ~260 m to spare on the east and
  ~400 m on the south. If the AOI is shifted east or south, sheets `0846-1-2` (MDT 61.95 MB,
  MDS 109.39 MB) or the row-3 sheet come into play. **Check the real extent of the downloaded COG
  before fixing the AOI.**
- The CdD point search appears to use a tolerance: points 600 m east of the castle returned both
  `0845-8-2` and `0846-1-2`.

---

## 3. Centro de Descargas (CdD): how it works and whether it can be scripted

URL: https://centrodedescargas.cnig.es/CentroDescargas/ (redirects to `/home`).

### 3.1 Listing files — scriptable **[queried]**

- Product page: `GET https://centrodedescargas.cnig.es/CentroDescargas/<slug>`; hidden fields give
  `codAgr` and `codSerie`.
- File list: `POST https://centrodedescargas.cnig.es/CentroDescargas/archivosSerie` with form fields
  `numPagina=1`, `codAgr`, `codSerie` and either
  `coordenadas={"type" : "FeatureCollection", "features" : [{"type":"Feature","geometry":{"type": "Point","coordinates": [lon,lat]}}]}`
  or `numHoja=0845` (MTN50 number) or `codIne=03140`. Returns an HTML table: name, format, date, MB,
  and a numeric id (`secuencial`) per file. **A GET to this endpoint returns 403**; POST returns 200.
- The point filter returned nothing for products whose unit is the MTN50 sheet in first coverage
  (MDT05, MDS05); `numHoja=0845` did return them.
- File detail permalink pattern: `…/CentroDescargas/detalleArchivo?sec=<secuencial>` (HTTP 200 for a
  sample id; not checked for each id below).

Product codes and ids found:

| Product | slug | codAgr / codSerie | `secuencial` of the Villena file |
|---|---|---|---|
| MDT50cm 3rd cov. | `modelo-digital-terreno-mdt50cm` | MOMDT / MDT01 | 12759170 |
| MDS50cm 3rd cov. | `modelo-digital-superficies-mds50cm-tercera-cobertura` | MOMDT / MDS50 | 13118318 |
| MDT02 2nd cov. | `modelo-digital-terreno-mdt02-segunda-cobertura` | MOMDT / MDT02 | 10325399 (ETRS89), 11650464 (WGS84) |
| MDS02 2nd cov. | `modelo-digital-superficies-mds02-segunda-cobertura` | MOMDT / MDS02 | 11611329 (ETRS89), 11654474 (WGS84) |
| MDT05 1st cov. | `modelo-digital-terreno-mdt05-primera-cobertura` | MOMDT / MDT05 | not captured |
| MDS05 1st cov. | `modelo-digital-superficies-mds05-primera-cobertura` | MOMDT / MDS05 | not captured |
| MDT25 2nd cov. | `mdt25-segunda-cobertura` | MOMDT / T25C2 | 11782908 |
| MDSnE2,5 2nd cov. | `modelo-digital-superficies-edificacion-segunda-cobertura` | MOMDT / MDSE2 | 11627850 |
| MDSnV2,5 2nd cov. | `modelo-digital-superficies-vegetacion-segunda-cobertura` | MOMDT / MDSV2 | 11626304 |
| LiDAR 3rd cov. | `lidar-tercera-cobertura` | MOMDT / LIDA3 | 12596076 (686-4279), 12594346 (685-4279), 12599742 (685-4278), 12579643 (686-4278) |
| LiDAR 2nd cov. | `lidar-segunda-cobertura` | MOMDT / LIDA2 | 9654279 (RGB), 9644494 (CIR) |
| LiDAR 1st cov. | `lidar-primera-cobertura` | MOMDT / LIDAR | 9923143, 10075479, 9902034, 9938808 |
| PNOA MA orthophoto | `ortofoto-pnoa-maxima-actualidad` | FOTOR / 02211 | 12570873 (TIF), 12571377 (XML), 12571125 (SHP zip) |
| Mapa LiDAR 2nd cov. | `mapa-lidar-segunda-cobertura` | MOMDT / MLID2 | 10415651 |
| BTN | `btn` | BTOCA / 02101 | 12165578 (Alicante GeoPackage) |
| CartoCiudad | `cartociudad` | EGRNA / 02122 | 9106 (Alicante) |

### 3.2 Downloading files — **not scriptable by design** **[queried: page source read; not exercised]**

The product page's own JavaScript shows the download flow:

1. clicking a download link calls `grecaptcha.execute('<site key>', {action: 'preautorizar_descarga'})`
   (the page loads `https://www.google.com/recaptcha/api.js?render=…`, i.e. reCAPTCHA v3);
2. `POST preAutorizarDescarga` with `secuencial` and `recaptchaToken`; the server answers
   `autorizado: 'S'` or the UI shows *"No está autorizado para realizar la descarga"*;
3. `initDescargaDir` → optional licence dialog (`loadLicsDescDir`) → form `POST descargaDir` with
   `secDescDirLA` and a hidden field `nav_signature`;
4. `validarFormularioHumano()` sets `nav_signature` to `BOT_DETECTED` when `navigator.webdriver`
   or Selenium markers are present, with the source comment
   *"Dejamos que envíe para que Java lo cace silenciosamente"*.

I did **not** attempt to call these endpoints or to get around the check: the operator has clearly
chosen to block automated downloads, and working around that would be circumventing an access control.
Consequences for the project:

- Files from the CdD must be fetched **by a person in a normal browser**. It is a handful of clicks.
- No login is needed for the first 20 downloads: *"No es necesario estar registrado ni identificado
  para realizar hasta un máximo de veinte descargas. A partir de la descarga número 21, será
  obligatorio tener cuenta de usuario e iniciar sesión."* **[page]**
  https://centrodedescargas.cnig.es/CentroDescargas/faqs
- The FAQ mentions a multi-file "descarga automática" through an Open Web Start (Java) application.
  That is a desktop helper for bulk downloads started from the site, not a documented API; not tested.
- No public API, FTP, STAC or direct COG/LAZ URL was found (`stac.idee.es`, `api-stac.idee.es`,
  `api-tiles.idee.es` do not resolve). The absence of such an endpoint is **not proven** — only not
  found.

---

## 4. PNOA orthophotos

| Fact | Value | How verified |
|---|---|---|
| Product | "Ortofotos PNOA Máxima Actualidad" — mosaics of the most recent PNOA orthophotos, one per MTN25 sheet, with an XML metadata file and a shapefile of date/resolution patches | **[page]** https://centrodedescargas.cnig.es/CentroDescargas/ortofoto-pnoa-maxima-actualidad |
| File for Villena | `PNOA-MA-OF-ETRS89-HU30-H25-0845-2.TIF`, COG, 799.01 MB; date column "05/2024, 06/2024"; scale column "0,25 M" | **[queried]** CdD listing |
| Date and pixel at the castle | `FECHA = '2024-06'`, `RESOLUCION = '0.25'` | **[queried]** WMS GetFeatureInfo on layer `OI.MosaicElement` |
| CRS | ETRS89 UTM zone 30 | **[page]** + file name |
| True orthoimages ("Ortoimágenes verdaderas", unit = urban nucleus) | none returned for the castle point | **[queried]**; a miss on the point filter is weak evidence, see section 10 |
| "Ortofotos expeditas LiDAR", "Ortofotos PNOA provisionales" | none returned for the castle point | **[queried]** |

OGC services (both declare `AccessConstraints: CC BY 4.0 scne.es`, `Fees: No se aplican condiciones`) **[queried]**:

- **WMS 1.3.0**: `https://www.ign.es/wms-inspire/pnoa-ma` — layers `OI.OrthoimageCoverage` (image),
  `OI.MosaicElement` (date/resolution footprints, queryable), `fondo`. Supports EPSG:25830.
  GetMap formats include `image/jpeg`, `image/png`, `image/tiff`.
- **WMTS 1.0.0**: `https://www.ign.es/wmts/pnoa-ma` — layer `OI.OrthoimageCoverage`, style `default`,
  formats `image/jpeg`, `image/png`; tile matrix sets `GoogleMapsCompatible` / `EPSG:3857` (levels 0–20),
  `EPSG:25830`, `EPSG:4258`, `EPSG:4326` (levels 0–19), and others. Deepest level has scale denominator
  533.18, i.e. 0.149 m per pixel nominal — finer than the 0.25 m source, so it is upsampled **[inferred]**.
- The service title says it also contains Sentinel-2 imagery (small scales) and "ortoimágenes
  verdaderas núcleos urbanos"; which of those feeds Villena at large scale is not stated.
- OGC API Maps also lists `OI.OrthoimageCoverage`: `https://api-maps.idee.es/collections` (not exercised).

Tested requests (both HTTP 200):

```
https://www.ign.es/wms-inspire/pnoa-ma?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=OI.OrthoimageCoverage&STYLES=&CRS=EPSG:25830&BBOX=686090,4278000,686290,4278200&WIDTH=800&HEIGHT=800&FORMAT=image/jpeg
  -> image/jpeg, 800x800 px (0.25 m/px), 204 615 bytes; castle centred in the frame

https://www.ign.es/wmts/pnoa-ma?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=OI.OrthoimageCoverage&STYLE=default&FORMAT=image/jpeg&TILEMATRIXSET=GoogleMapsCompatible&TILEMATRIX=19&TILEROW=201060&TILECOL=260890
  -> image/jpeg, 256x256 px, 16 587 bytes
```

For 1 km² at native 0.25 m the orthophoto is 4000×4000 px. The WMS is the sensible route: scripted,
already in EPSG:25830, and avoids an 800 MB download. Whether a single 4000×4000 GetMap is accepted was
not tested — plan on tiling requests (e.g. 1000×1000 px).

---

## 5. Terrain and surface models

### 5.1 What exists (all **[page]** on the CdD product pages, file facts **[queried]**)

| Product | CdD description (abridged) | Unit | Format |
|---|---|---|---|
| **MDT50cm – 3ª cobertura** (internal code `MDT01`) | 0.5 m DTM from the ground class of the 3rd-coverage LiDAR (2022–2025). Currently the **provisional "MDT50cm v1"**, built from the point cloud at classification level NPC01; a definitive version from NPC02/NPC03 is planned. "Cobertura por completar." | 1:5,000 sheet (MTN50 split 8×8) | COG |
| **MDT02 – 2ª cobertura** | 2 m DTM interpolated from the ground class of 2nd-coverage LiDAR (2015–2021). Water surfaces interpolated/flattened. | MTN25 sheet | COG |
| **MDT05 – 1ª cobertura** | 5 m DTM from 1st-coverage LiDAR | MTN50 sheet | COG |
| MDT25 (1st and 2nd cov.), MDT200 (1st and 2nd cov.) | coarser DTMs | MTN25 / province | COG |
| **MDS50cm – 3ª cobertura** | 0.5 m DSM (ground + vegetation + buildings + other objects). Provisional `MDS50cm_V1` from NPC01; definitive `MDS50cm_V2` from NPC02. "Ambos mantienen el mismo rigor métrico". "Cobertura por completar." | 1:5,000 sheet | COG |
| **MDS02 – 2ª cobertura** | 2 m DSM from ground, vegetation (low/medium/high) and building classes, 2015–2022 | MTN25 sheet | COG |
| MDS05 – 1ª cobertura | 5 m DSM | MTN50 sheet | COG |
| **MDSnE2,5 – 2ª cobertura** | normalised DSM of the **building class (class 6)**: height above ground, 2.5 m grid | MTN50 sheet | COG |
| **MDSnV2,5 – 2ª cobertura** | normalised DSM of the **vegetation classes (3, 4, 5)**: height above ground, 2.5 m grid | MTN50 sheet | COG |
| MDSnE2,5 / MDSnV2,5 – 1ª cobertura | listed in the catalogue menu; not queried for Villena | — | — |
| Mapa LiDAR (1st and 2nd cov.), MDP02/MDP05 slope models | rendered / derived products | MTN50 | ECW / COG |

- There is **no product called "MDT01"** at 1 m. `MDT01` is only the internal series code of MDT50cm.
- No 3rd-coverage normalised model (MDSn) is published yet; the PNOA status table lists v2 models and
  derived products for the Comunitat Valenciana as forecasts for 2H-2026 / 1H-2027 **[page]**
  https://pnoa.ign.es/pnoa-lidar/tercera-cobertura (summarised by a fetch tool, not read verbatim).
- Heights: all DTM/DSM pages say "Alturas ortométricas"; MDSn pages say "Alturas normalizadas,
  referidas al nivel del suelo". The PNOA-LiDAR spec table gives "Altitudes ortométricas, geoide de
  referencia EGM08" **[page]** https://pnoa.ign.es/pnoa-lidar/especificaciones-tecnicas . The exact
  geoid realisation name (EGM08-REDNAP) is not written on those pages — see section 10.
- Accuracy from the same spec table (1st / 2nd / 3rd coverage): DEM grid 5 m / 2 m / 0.5 m;
  DEM RMSE Z ≤ 50 / ≤ 25 / ≤ 15 cm; DEM planimetric ≤ 50 cm for all.
- Metadata record for MDT02: https://idee.es/csw-inspire-idee/static/api/records/spaignMDT02
  (attribution string there: "MDT02-cob2 2015-2021 CC-BY 4.0 scne.es"). That record still says the
  distribution format is ASCII `.asc`; the CdD page and listing say COG. I trust the CdD.

### 5.2 OGC access to elevations — only the 5 m DTM

**WCS 2.0.1**: `https://servicios.idee.es/wcs-inspire/mdt` **[queried]**

- Title "Modelos Digitales del Terreno de España"; `AccessConstraints: CC BY 4.0 scne.es`.
- Coverages: `Elevacion25830_5`, `_25`, `_200`, `_500`, `_1000` (and the same in EPSG:4258, 4083, 4326).
  **Nothing finer than 5 m, and no DSM / nDSM coverage.** `DescribeCoverage` for `Elevacion25830_2`
  returns `NoSuchCoverage`.
- `Elevacion25830_5`: native CRS EPSG:25830, grid origin (−19 450, 4 865 680), offsets 5 m / −5 m,
  native format "COG".
- Advertised formats: `image/tiff`, `ArcGrid`, `application/asc`, `GEOTIFFINT16`, `GEOTIFF_RGB`, PNG/JPEG/GIF.
- The matching OGC API collection `EL.ElevationGridCoverage_25830_5_PB` describes the 5 m data as built
  "a partir de las nubes de puntos LIDAR de la primera Cobertura" and links to the MDT05 record. That the
  WCS serves the same MDT05 data is **[inferred]** (same grid family; the WCS abstract only says
  "PNOA-LiDAR").

Tested GetCoverage, ~200 m box at the castle (HTTP 200):

```
https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=Elevacion25830_5&SUBSET=x(686090,686290)&SUBSET=y(4278000,4278200)&FORMAT=image/tiff
  -> image/tiff, 3 656 bytes, 40 x 40 px, pixel 5 m, tie point (686090, 4278200) = upper-left,
     16-bit SIGNED INTEGER (SampleFormat=2), values 513..551

...same request with &FORMAT=application/asc
  -> multipart/related, 14 173 bytes: ESRI ASCII grid (ncols 40, nrows 40, xllcorner 686090,
     yllcorner 4278000, cellsize 5), .aux.xml and .prj (ETRS89_UTM_zone_30N);
     float values with 3 decimals, 513.024..551.307 m
```

**Gotcha:** `FORMAT=image/tiff` rounds heights to whole metres (Int16). Use `application/asc` to keep
decimals; the response is a MIME multipart and has to be split before GDAL can read it.

Other endpoints:

- WMS (rendering only): `https://servicios.idee.es/wms-inspire/mdt` — layers `EL.ElevationGridCoverage`,
  `EL.ContourLine`, `EL.SpotElevation`. WMTS: `https://servicios.idee.es/wmts/mdt` (from the metadata
  record; not requested).
- OGC API Coverages: `https://api-coverages.idee.es/collections` — same 5 m … 1000 m DTMs plus flood
  layers; "El tamaño máximo de descarga está limitado". My `/coverage?bbox=…&f=GTiff` attempts returned
  HTTP 500 / 400, so this route is **unverified**.
- Mapa LiDAR (coloured DSM rendering with building/vegetation heights, 1st coverage per its abstract):
  WMS `https://wms-mapa-lidar.idee.es/lidar` (layer `EL.GridCoverage`), WMTS
  `https://wmts-mapa-lidar.idee.es/lidar` (layer `EL.GridCoverageDSM`, PNG). These are pictures, not
  height values.
- Probed and not available: `servicios.idee.es/wcs-inspire/mds`, `/mdsn`, `/lidar` (connection reset);
  `wcs-mapa-lidar.idee.es`, `wms-pnoa-lidar.idee.es` (no DNS). A datos.gob.es catalogue entry claims the
  MDSnE is available "a través del servicio de descarga WCS"; I could not find such a service.

---

## 6. LiDAR point clouds (PNOA-LiDAR)

All three coverages exist for the castle **[queried]**.

| | 1st coverage | 2nd coverage | 3rd coverage |
|---|---|---|---|
| CdD product | "LiDAR - 1ª Cobertura (2008-2015)" | "LiDAR - 2ª Cobertura (2015-2021)" | "LiDAR - 3ª Cobertura (2022-2025)" |
| Year shown for the Villena tile | 2009 – 2010 | 2016 – 2017 | 2023 |
| Density (listing / product page) | 0,50 pts/m² | 0,50 pts/m² ("o superior") | 5 pts/m² ("o superior") |
| Tile size | 2×2 km | 2×2 km (some 1×1 km lots) | 1×1 km |
| Format | LAZ | LAZ | LAZ |
| Colour | RGB or IRC variants | RGB (`-RGB`) or IRC (`-CIR`) variants | 4 bands RGBI in one file |
| Classification | classified (`CLA` in name) | classified (`CLA` in name) | level in name: **NPC02** for Villena |
| Villena file(s) | `PNOA-2009-LOTE3-ALI-686-4280-ORT-CLA-COL.LAZ` 39.77 MB; `…-CLM-MUR-ALI-…-CIR.LAZ` 37.81 MB; `…-CLM-MUR-ALI-…-COL.LAZ` 43.88 MB; `…-MUR-…-COL.LAZ` 39.76 MB | `PNOA-2016-MUR-VAL-CLM-686-4280-ORT-CLA-RGB.LAZ` 23.32 MB; `…-CIR.LAZ` 22.69 MB | `PNOA-2023-VAL-686-4279-H30-NPC02.laz` 53.55 MB |

From the PNOA-LiDAR specification table **[page]** https://pnoa.ign.es/pnoa-lidar/especificaciones-tecnicas :

| Characteristic | 1st | 2nd | 3rd |
|---|---|---|---|
| Minimum density | 0.5 pts/m² | 0.5–2 pts/m² | 5 pts/m² |
| Flight years | 2009–2015 | 2015–2021 | 2022–2025 |
| Semantic classes | 5 | 5 | minimum 13 |
| RMSE Z | ≤ 40 cm | ≤ 20 cm | ≤ 10 cm |
| Planimetric accuracy | ≤ 30 cm | ≤ 30 cm | ≤ 25 cm |
| Simultaneous image | no (except Baleares) | yes, since 2016 | yes |
| File format | LAS 1.2 format 3 (cell appears to span 1st and 2nd) | ← | LAS 1.4 format 8 |
| Reference system | ETRS89 or REGCAN95, zones 28–31 as applicable | ← | ← |
| Height reference | orthometric, reference geoid EGM08 | ← | ← |

3rd-coverage classification levels **[page]** (CdD product page):

- **NPC01** — initial: automatic classification of ground, vegetation, buildings and overlap.
- **NPC02** — basic editing: semi-automatic and manual classification of ground, vegetation, buildings,
  bridges and overlaps. *(This is what Villena has.)*
- **NPC03** — advanced: new classes added.

Comunitat Valenciana in the 3rd-coverage status table **[page, via fetch-tool summary]**
https://pnoa.ign.es/pnoa-lidar/tercera-cobertura : flight Aug-2023 → Jun-2024; NPC02 "Publicada (*)";
MDT/MDS v1 "Publicados". The Villena tile itself is labelled 2023.

Spec PDFs (linked, not read): `https://pnoa.ign.es/resources/archivos/EspTec/Especificaciones_tecnicas_clasificacion-LID3.pdf`,
`https://pnoa.ign.es/resources/archivos/EspTec/Definicion_clases-LID3.pdf`,
`https://pnoa.ign.es/resources/archivos/EspTec/2022__Especificaciones_VL.pdf`.

**COPC: not confirmed.** Neither the CdD page ("Fichero LAZ (formato de compresión de ficheros LAS)")
nor the spec page mentions COPC, and a web search found no IGN statement. Whether the 3rd-coverage
`.laz` files happen to be COPC-structured can only be told by opening one.

Other notes:

- No OGC or streaming service for the point clouds was found.
- The two 2nd-coverage files (RGB / CIR) are the same tile with different colouring **[inferred]** from
  names; likewise the four 1st-coverage files look like overlapping production lots of the same tile.

---

## 7. Other IGN products worth knowing

| Product | What it is | For Villena | How verified |
|---|---|---|---|
| **BTN** (Base Topográfica Nacional) | multi-scale 3D topographic database (1:2,000–1:25,000), includes buildings "de los catastros nacionales"; positional accuracy "mejor de 3 metros en X, Y, Z" | `BTN Unidad - Alacant/Alicante`: GeoPackage 506.03 MB or Shapefile 455.42 MB, dated 26/06/2026. National per-theme GeoPackages are 0.03–1.5 GB each (Edificios: 3 parts, 1.1–1.3 GB each) | **[queried]** CdD; https://centrodedescargas.cnig.es/CentroDescargas/btn |
| **CartoCiudad** | addresses (`portalpk_publi`) and cadastral blocks (`manzana`) per province, geographic coordinates | Alicante GeoPackage 77.25 MB, dated 11/2026 | **[queried]** https://centrodedescargas.cnig.es/CentroDescargas/cartociudad |
| CartoCiudad geocoder | REST geocoder | `https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=…` works without key | **[queried]** |
| OGC API Features | INSPIRE addresses, hydrography, transport networks, land cover/use | `https://api-features.idee.es/collections`; **no building collection** in the list. `https://api-features.ign.es/collections` has administrative units, place names, geodetic networks | **[queried]** collection lists only |
| MTN grids | sheet outlines | WMS `https://www.ign.es/wms-inspire/cuadriculas`, layers `cuadricula-mtn50-actual`, `cuadricula-mtn25-actual`, GetFeatureInfo as GeoJSON works | **[queried]** |
| BCN200 / BCN500, BTN100 | small-scale bases | not relevant at 1 km² | catalogue menu only |
| **IGN 3D buildings (LoD1/LoD2, CityGML…)** | — | **No such national IGN product found** in the CdD catalogue menu or by web search. Not proof of absence. | search + catalogue menu |

For this project BTN is heavy (≥ 455 MB for the province, interactive download) and its building
footprints come from the Cadastre anyway, so it adds little over the Cadastre research in doc 02.

---

## 8. Licence and attribution

### 8.1 Terms

Sources read today:

- Licence text (PDF, 3 pages): http://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf
  — "Licencia de los productos y servicios de datos geográficos producidos por el IGN y de los
  coproducidos por las CC. AA. y la AGE en el marco del Sistema Cartográfico Nacional". **[page]**
- CdD data policy: https://centrodedescargas.cnig.es/CentroDescargas/politica-datos **[page]**
- CdD FAQ: https://centrodedescargas.cnig.es/CentroDescargas/faqs **[page]**
- Order FOM/2807/2015 (BOE 2015-12-26): https://www.boe.es/boe/dias/2015/12/26/pdfs/BOE-A-2015-14129.pdf
  — **linked from the above, not read today**; the quote of its Article 4 below is as reproduced in the
  licence PDF.

Verbatim:

> «El uso de los productos de datos geográficos digitales mencionados en el Artículo 2 tendrá carácter
> libre y gratuito, siempre que se mencione el origen y propiedad de los datos, con el alcance y forma
> que autorice la licencia de uso correspondiente». (Art. 4 of the Order, as quoted in the licence PDF)

> "…el uso de los productos y servicios de información geográfica del IGN definidos en el ámbito de la
> Orden FOM/2807/2015 conlleva la aceptación por el usuario de una licencia CC-BY 4.0 tal y como se
> define en: http://creativecommons.org/licenses/by/4.0/ …" (licence PDF)

> "Esta licencia ampara el uso libre y gratuito para cualquier propósito legítimo, siendo la única
> estricta obligación la de reconocer y mencionar el origen y propiedad de los productos y servicios de
> información geográfica licenciados como del IGN…" (CdD data policy)

> "Se permite el uso libre y gratuito para cualquier propósito legítimo, incluido el comercial y la
> publicación, siempre y cuando se reconozca y se mencione en todo momento el origen y propiedad…"
> (CdD FAQ)

The data policy page also says the State keeps the intellectual property, and that CdD data **not**
produced by IGN/CNIG are under CC-BY 4.0 as well.

### 8.2 Required attribution wording

Rules from the licence PDF:

1. Unmodified product: `«<identificador del producto> <fecha> CC-BY 4.0 <atribución de productores>»`,
   values from the product table at http://www.scne.es/productos.html (not fetched; the CdD serves the
   same formulas per product, below). Must be "visible junto con los datos, de forma legible y a pie de
   mapa, imagen, presentación o ventana de visualización"; if that is manifestly impossible, in layer
   lists, legends, tables of contents or credits.
2. Unmodified service: the formula of the coupled data, or else the service's `<AccessConstraints>`
   (today: `CC BY 4.0 scne.es`).
3. Abbreviated alternative for space/design reasons: `«CC-BY 4.0 <atribución productores> <fecha>»`;
   the attribution should be a hyperlink where feasible.
4. **Derived work**: prefix with **«Obra derivada de»** → `«Obra derivada de <identificador del producto>
   <fecha> CC-BY 4.0 <atribución de productores>»`.
5. A new dataset made by modifying the original must also carry these expressions in its metadata
   (abstract, lineage, access constraints); 6. likewise for a new web service (GetCapabilities etc.).

Exact formulas served by the CdD today (`POST …/CentroDescargas/licsRecsSerie`, `codSerie=<code>`) **[queried]**:

| Product | Unmodified | Derived work ("Tipo 3") |
|---|---|---|
| PNOA 2024 | `PNOA 2024 CC-BY 4.0 scne.es` | `Obra derivada de PNOA 2024 CC-BY 4.0 scne.es` |
| MDT50cm 3rd cov. | `MDT50cm-cob3 2022-2025 CC-BY 4.0 scne.es` | `Obra derivada de MDT50cm-cob3 2022-2025 CC-BY 4.0 scne.es` |
| MDS50cm 3rd cov. | `MDS50cm-cob3 2022-2025 CC-BY 4.0 scne.es` | `Obra derivada de MDS50cm-cob3 2022-2025 CC-BY 4.0 scne.es` |
| LiDAR 3rd cov. | `LiDAR-PNOA-cob3 2022-2025 CC-BY 4.0 scne.es` | `Obra derivada de LiDAR-PNOA-cob3 2022-2025 CC-BY 4.0 scne.es` |
| MDT02 2nd cov. | `MDT02-cob2 2015-2021 CC-BY 4.0 scne.es` | `Obra derivada de MDT02-cob2 2015-2021 CC-BY 4.0 scne.es` |
| MDSnE2,5 2nd cov. | `MDSnEdificación2,5 2015-2021 CC-BY 4.0 scne.es` | `Obra derivada de MDSnEdificación2,5 2015-2021 CC-BY 4.0 scne.es` |
| MDT05 1st cov. | identifier `MDT05-cob1`, date `2008-2015` (full string not decoded) | — |

"scne.es" should link to https://www.scne.es/ . Long-form alternative for PNOA 2024: "PNOA 2024 CC-BY 4.0
Instituto Geográfico Nacional, Fondo Español de Garantía Agraria, Comunidad Autónoma de Canarias,
Comunidad Autónoma de Cataluña, Comunitat Valenciana y O.A. Centro Nacional de Información Geográfica".

The wording "«PNOA cedido por © Instituto Geográfico Nacional»" does **not** appear in the current
licence PDF, data policy or per-product formulas. I could not confirm it as a currently valid formula;
use the CC-BY formulas above.

Suggested credit line for the map (two products, derived work):

> Obra derivada de PNOA 2024 CC-BY 4.0 scne.es, MDT50cm-cob3 2022-2025 CC-BY 4.0 scne.es y
> MDS50cm-cob3 2022-2025 CC-BY 4.0 scne.es

(Combining several products in one sentence is my arrangement **[inferred]**; the licence only defines
the per-product expression.)

### 8.3 Redistribution and model training — verdict

- **Derived products** (tiles, sprites, height rasters, the rendered map): allowed, with the "Obra
  derivada de …" credit. Stated directly by the licence.
- **Raw files** (re-hosting the COG/LAZ or a cropped copy, e.g. as a release asset so the build is
  reproducible): allowed. The licence is CC BY 4.0, which grants the right to reproduce and share the
  material in whole or in part; the FAQ adds "incluido el comercial y la publicación". Keep the
  unmodified-product credit with the files. *(I rely on the well-known CC BY 4.0 terms here; the CC legal
  code was not re-read today.)*
- **Training / conditioning image models**: **not addressed explicitly** anywhere in the IGN texts read.
  It falls under "uso libre y gratuito para cualquier propósito legítimo" and CC BY 4.0 places no
  field-of-use restriction, so I see nothing that forbids it **[inferred — a reading, not legal advice]**.
  Open point: how attribution should be carried for model outputs. The conservative approach is to credit
  the sources wherever the model, its training set or its outputs are published. For a written answer,
  the licence names `consulta@cnig.es`.
- No share-alike and no non-commercial clause: the project can choose its own licence for code and
  derived assets, as long as the IGN credit is kept.

---

## 9. Recommendation

Goal: (a) ground model at ≤ 2 m and (b) building/vegetation heights for ~1 km², with as little raw
LiDAR as possible.

**Recommended set — two rasters from the same 2023 flight, 175 MB:**

| Need | File | Res. | Size |
|---|---|---|---|
| (a) ground | `MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` | 0.5 m | 61.07 MB |
| (b) heights | `MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif`, then **nDSM = MDS − MDT** | 0.5 m | 113.99 MB |
| imagery | PNOA MA via WMS `https://www.ign.es/wms-inspire/pnoa-ma` (0.25 m, June 2024) | 0.25 m | a few MB for 1 km² |

Why: both are already in EPSG:25830, are far sharper than the 2nd-coverage products (individual
buildings in an old town are ~5–10 m wide, so 2.5 m nDSM cells are marginal), and come from one
acquisition, so subtracting them is consistent. One sheet should cover a castle-centred 1 km²
(section 2, inferred — verify on the file).

Caveats:

- Both are **V1 provisional** models built from NPC01 classification. Expect some buildings or dense
  vegetation leaking into the "ground" surface; the castle rock is a likely trouble spot. Record the
  version in the pipeline so the V2 files can replace them later.
- MDS − MDT gives height of *everything* above ground. Separating buildings from trees needs footprints
  (Cadastre / OSM, doc 02) — which the project needs anyway.
- That the two COGs share the same pixel grid is assumed, not verified.

**Fallback / complement — ready-made, older, coarser (192 MB, 2016–2017):**
`MDT02-ETRS89-HU30-0845-2-COB2.TIF` (2 m, 115.58 MB) + `NDSM-EDIFICIOS-H30-0845-COB2.TIF` (2.5 m,
4.26 MB) + `NDSM-VEGETACION-H30-0845-COB2.TIF` (2.5 m, 71.94 MB). These need no arithmetic and already
split buildings from vegetation; the 4 MB building raster is a cheap sanity check for the 0.5 m result.

**Raw LiDAR only if the rasters prove insufficient** (e.g. roof shapes): four NPC02 tiles, 154 MB
(section 2).

**Can it be fully scripted? No — not the elevation part.**

- Orthophoto: yes, fully scripted (WMS/WMTS).
- 5 m terrain: yes, fully scripted (WCS, `application/asc`) — but it does not meet the ≤ 2 m target and
  dates from 2009. Useful only as a CI smoke-test or placeholder.
- 0.5 m / 2 m / nDSM / LiDAR: a person must download the files once in a browser (2 files, no account
  needed under 20 downloads).

To keep the build reproducible despite the manual step:

1. Document the two file names, the CdD `secuencial` ids (12759170, 13118318) and the download date.
2. After downloading, record size and SHA-256 in the repo; the pipeline refuses to run on a mismatch.
3. Crop to the AOI and publish the crops (≈ 4000×4000 px float rasters, a few MB each compressed
   **[inferred]**) as a release asset with the "Obra derivada de …" credit. The licence permits this
   (section 8.3), and from then on `make data` is fully scripted against the project's own mirror.

---

## 10. Not verified / unresolved

1. **Contents of every COG and LAZ file**: data type, nodata value, compression, embedded CRS and
   vertical CRS tags, exact extent, whether MDT50cm and MDS50cm are pixel-aligned. Nothing was downloaded.
2. **Exact footprint of sheet 0845-8-2** and whether a castle-centred 1 km² fits in it. Derived from the
   MTN50 outline assuming an even 8×8 split.
3. **LiDAR tile naming = NW corner in km** — inferred from two point queries, not from documentation.
4. **COPC**: no evidence either way for 3rd-coverage LAZ.
5. **LAS version of the 2nd coverage**: the spec table shows "LAS 1.2 format 3 | LAS 1.4 format 8" in two
   cells for three coverages; I read it as 1st+2nd = LAS 1.2, 3rd = LAS 1.4, but the cell merge was lost
   in text extraction.
6. **Vertical datum name**: sources say "alturas ortométricas" and "geoide de referencia EGM08". The
   specific model (EGM08-REDNAP) and the EPSG code of the vertical CRS are not stated on the pages read.
7. **Whether the WCS 5 m coverage is exactly MDT05 (1st coverage, 2009 here)** — inferred from the
   OGC API collection description.
8. **OGC API Coverages** (`api-coverages.idee.es`) — collection metadata reads fine, but my coverage
   requests failed (HTTP 500/400). Parameter syntax or service fault unknown.
9. **WMS limits**: maximum GetMap size, rate limits and whether `image/tiff` output is lossless were not
   tested. WCS maximum request size not tested either.
10. **CdD download flow**: read from page source only; never exercised. I do not know how the server
    scores reCAPTCHA, nor whether the Open Web Start bulk downloader is still functional.
11. **Existence of any direct/bulk channel** (FTP, S3, STAC, agreement-based bulk delivery). Not found;
    the page source references a `descargaDirS3` action that none of the listed files used.
12. **True orthoimages for Villena**: the point query returned nothing, but the same kind of query also
    missed MDT05/MDS05, so absence is not established. Same for "ortofotos expeditas LiDAR".
13. **MDSnE2,5 / MDSnV2,5 1st coverage** for Villena: not queried (slugs not identified).
14. **3rd-coverage status table**: obtained through an automated page summary, not read verbatim;
    the footnote behind "Publicada (*)" was not captured in full.
15. **Order FOM/2807/2015, the scne.es product table and the CC BY 4.0 legal code** were not read today.
16. **«PNOA cedido por © Instituto Geográfico Nacional»**: not found in current official texts.
17. **AI-training use**: no explicit IGN/CNIG statement found; the verdict in 8.3 is an interpretation.
18. **IGN national 3D-building product**: none found; absence not proven.
19. **UTM conversion** of the castle was computed with a hand-written series (no PROJ on this machine);
    it agrees with the WMS image to within what the eye can tell (a few metres).

---

## 11. Commands used

All with `-A "Mozilla/5.0 (compatible; geodata-research/1.0)"`; outputs saved in the session scratch
directory, not in the repo.

```sh
# Capabilities
curl "https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&REQUEST=GetCapabilities"
curl "https://www.ign.es/wms-inspire/pnoa-ma?SERVICE=WMS&REQUEST=GetCapabilities"
curl "https://www.ign.es/wmts/pnoa-ma?SERVICE=WMTS&REQUEST=GetCapabilities"
curl "https://servicios.idee.es/wms-inspire/mdt?SERVICE=WMS&REQUEST=GetCapabilities"
curl "https://wmts-mapa-lidar.idee.es/lidar?SERVICE=WMTS&REQUEST=GetCapabilities"
curl "https://wms-mapa-lidar.idee.es/lidar?SERVICE=WMS&REQUEST=GetCapabilities"
curl "https://www.ign.es/wms-inspire/cuadriculas?SERVICE=WMS&REQUEST=GetCapabilities"
curl "https://api-coverages.idee.es/collections?f=json"      # also api-features.idee.es, api-features.ign.es, api-maps.idee.es

# Geocode the castle
curl "https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Castillo%20de%20la%20Atalaya%20Villena&limit=5"

# WCS
curl "https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&VERSION=2.0.1&REQUEST=DescribeCoverage&COVERAGEID=Elevacion25830_5"
curl -o mdt05.tif "https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=Elevacion25830_5&SUBSET=x(686090,686290)&SUBSET=y(4278000,4278200)&FORMAT=image/tiff"
curl -o mdt05.asc "https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=Elevacion25830_5&SUBSET=x(686090,686290)&SUBSET=y(4278000,4278200)&FORMAT=application/asc"

# PNOA
curl -o castle.jpg "https://www.ign.es/wms-inspire/pnoa-ma?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=OI.OrthoimageCoverage&STYLES=&CRS=EPSG:25830&BBOX=686090,4278000,686290,4278200&WIDTH=800&HEIGHT=800&FORMAT=image/jpeg"
curl "https://www.ign.es/wms-inspire/pnoa-ma?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=OI.MosaicElement&QUERY_LAYERS=OI.MosaicElement&STYLES=&CRS=EPSG:25830&BBOX=686090,4278000,686290,4278200&WIDTH=200&HEIGHT=200&I=100&J=100&INFO_FORMAT=text/plain&FORMAT=image/png"
curl -o tile.jpg "https://www.ign.es/wmts/pnoa-ma?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=OI.OrthoimageCoverage&STYLE=default&FORMAT=image/jpeg&TILEMATRIXSET=GoogleMapsCompatible&TILEMATRIX=19&TILEROW=201060&TILECOL=260890"

# MTN sheet outlines at the castle (also with cuadricula-mtn25-actual)
curl "https://www.ign.es/wms-inspire/cuadriculas?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=cuadricula-mtn50-actual&QUERY_LAYERS=cuadricula-mtn50-actual&STYLES=&CRS=EPSG:25830&BBOX=686090,4278000,686290,4278200&WIDTH=200&HEIGHT=200&I=100&J=100&INFO_FORMAT=application/json&FORMAT=image/png&FEATURE_COUNT=5"

# Centro de Descargas: product page, then file listing (POST; GET gives 403)
curl "https://centrodedescargas.cnig.es/CentroDescargas/modelo-digital-terreno-mdt50cm"
curl "https://centrodedescargas.cnig.es/CentroDescargas/archivosSerie" \
  -H "X-Requested-With: XMLHttpRequest" \
  --data-urlencode "numPagina=1" --data-urlencode "codAgr=MOMDT" --data-urlencode "codSerie=MDT01" \
  --data-urlencode 'coordenadas={"type" : "FeatureCollection", "features" : [{"type":"Feature","geometry":{"type": "Point","coordinates": [-0.86097,38.63188]}}]}'
#   repeated per product (codes in section 3.1); corner points -0.8679/-0.8541 x 38.6265/38.6373;
#   MDT05 and MDS05 with  -d "numPagina=1&codAgr=MOMDT&codSerie=MDT05&numHoja=0845"

# Attribution formulas and policy pages
curl "https://centrodedescargas.cnig.es/CentroDescargas/licsRecsSerie" -H "X-Requested-With: XMLHttpRequest" -d "codSerie=MDT01&codAgr=MOMDT"
curl "https://centrodedescargas.cnig.es/CentroDescargas/politica-datos"
curl "https://centrodedescargas.cnig.es/CentroDescargas/faqs"
curl -L -o licencia.pdf "http://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf"

# PNOA-LiDAR pages
curl -L "https://pnoa.ign.es/pnoa-lidar/especificaciones-tecnicas"
#   https://pnoa.ign.es/pnoa-lidar/tercera-cobertura was read through a web-fetch tool
```
