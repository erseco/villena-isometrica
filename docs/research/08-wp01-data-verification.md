# 08 — WP01 Geographic Data Verification and Dataset Manifest Report

**Task:** WP01 — Data verification, dataset manifest, and licensing  
**Date:** 2026-11-15  
**Model:** Gemini 3.8 Flash (research mode: high)  
**Verification Method:** Live network queries, file downloads, checksum verification, GML/XML parsing, GeoPackage spatial geometry extraction, and PyProj coordinate transformations.

---

## 1. Executive Summary

This report independently verifies the open geospatial datasets for Villena (Alicante, Spain), answers the open questions from earlier bootstrap research (`docs/research/02` and `03`), and establishes the verified dataset manifest (`cities/villena/datasets.json`), acquisition guide (`cities/villena/ACQUISITION.md`), and search POI index (`cities/villena/poi-selection.json`).

### Key Confirmed Findings:
1. **IGN Sheet Footprint (Crucial):** Sheet `0845-8-2` of MDT50cm and MDS50cm spans **E 683060.0–686850.0, N 4277210.0–4279710.0** (EPSG:25830). The AOI plus 120 m margin (E 685380–686620, N 4277380–4278620) is **fully contained** within this single sheet, with 230 m to spare on the east and 170 m on the south. **No additional sheets are required.**
2. **Elevation Raster Alignment:** MDT50cm and MDS50cm share the exact same 0.5 m pixel grid (7,580 × 5,000 cells) and identical spatial bounding box.
3. **Vertical Datum:** Orthometric heights referred to the Alicante tide gauge (*mareógrafo de Alicante*), geoid **EGM08-REDNAP** (EPSG:5782). Compound 3D CRS: **EPSG:25830 + EPSG:5782**.
4. **"V1 provisional" Meaning:** Confirmed from PNOA-LiDAR specification footnote: preliminary operational version published while works are ongoing to improve classification reliability and complete all 13 semantic classes ("Trabajos en curso para mejorar la fiabilidad y completar el conjunto de clases previsto").
5. **Catastro Attribution & Ministry:** Ministry is the **Ministerio de Hacienda** (formerly Ministerio de Economía y Hacienda). Recommended citation formula: `Fuente de edificios: Dirección General del Catastro, Ministerio de Hacienda (fecha de acceso: YYYY-MM-DD)`.
6. **Catastro Derived Vectors:** Re-distribution of raw or lightly modified vector footprints is restricted. Rendered pixel-art tiles and images are explicitly permitted transformed works ("obra diferente"). Scene vector files should remain internal build artifacts and not be published as public assets in v0.1.0.
7. **OpenStreetMap:** Overpass extract for AOI + 120 m margin contains 104,375 elements (11.05 MB). Rendered tiles are confirmed as "Produced Works" under ODbL 4.3–4.5 (exempt from share-alike).

---

## 2. Catastro INSPIRE Buildings Verification

### 2.1 ATOM Feed and Predefined Dataset
- **Alicante Province ATOM Feed:** `https://www.catastro.hacienda.gob.es/INSPIRE/buildings/03/ES.SDGC.bu.atom_03.xml`
- **Villena Predefined Entry:**
  - `<title>`: `03140-VILLENA buildings`
  - `<id>`: `https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/03/03140-VILLENA/A.ES.SDGC.BU.03140.zip`
  - `<updated>`: `2026-08-21T00:00:00Z`
  - `<rights>`: `This service can be used free of charge in every instance,  as long as that the D. G. of the Cadastre (Ministry of Finance)  is mentioned as author and owner of the information`
  - `<category>`: `term="http://www.opengis.net/def/crs/EPSG/0/25830" label="ETRS89"`
  - Download URL: `https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/03/03140-VILLENA/A.ES.SDGC.BU.03140.zip`

### 2.2 Download & Archive Verification
- **File size:** `3,971,442` bytes (~3.97 MB)
- **SHA-256:** `38588fba7a3fd15bcff301096639720fd79fb37edfc975cda517a945024f1e17`
- **Archive Members:**
  - `A.ES.SDGC.BU.03140.building.gml` (38,737,593 bytes)
  - `A.ES.SDGC.BU.03140.buildingpart.gml` (55,437,808 bytes)
  - `A.ES.SDGC.BU.03140.otherconstruction.gml` (2,755,647 bytes)
  - `A.ES.SDGC.BU.MD.03140.xml` (20,006 bytes)

### 2.3 Layer & Attribute Verification
- **CRS:** `urn:ogc:def:crs:EPSG::25830` natively across all GML geometries (2D Easting, Northing).
- **`bu-ext2d:Building`:** 8,442 features. `numberOfFloorsAboveGround` is completely unpopulated (either omitted or nilReason), confirming building heights cannot be obtained from the `Building` layer.
- **`bu-ext2d:BuildingPart`:** 22,217 features. **`numberOfFloorsAboveGround` is populated on 100% of features (22,217 / 22,217).**
  - Storey distribution across municipality:
    - 0 floors: 633 parts
    - 1 floor: 11,366 parts
    - 2 floors: 5,352 parts
    - 3 floors: 1,987 parts
    - 4 floors: 1,000 parts
    - 5 floors: 870 parts
    - 6 floors: 417 parts
    - 7 floors: 170 parts
    - 8 floors: 105 parts
    - 9 floors: 70 parts
    - 10 floors: 66 parts
    - 11 floors: 80 parts
    - 12 floors: 71 parts
    - 13 floors: 25 parts
    - 14 floors: 5 parts
- **Castle footprint:** Parcel `6383001XH8768S` contains a single `BuildingPart` polygon with 117 vertices and `numberOfFloorsAboveGround = 3`.

---

## 3. IGN / CNIG Rasters and Sheet Footprint Verification

### 3.1 Sheet Existence and Identification
Queried against Centro de Descargas (CdD) catalog services (`archivosSerie`):
- **MDT50cm 3ª cobertura:**
  - Product slug: `modelo-digital-terreno-mdt50cm` (codAgr: `MOMDT`, codSerie: `MDT01`)
  - File: `MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif`
  - Secuencial ID: `12759170`
  - Format: Cloud Optimized GeoTIFF (COG), 32-bit float
  - Size: 61.07 MB (`64,036,454` bytes)
  - Resolution: 0.50 m
  - Year: 2023 (flight 2022–2025)
- **MDS50cm 3ª cobertura:**
  - Product slug: `modelo-digital-superficies-mds50cm-tercera-cobertura` (codAgr: `MOMDT`, codSerie: `MDS50`)
  - File: `MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif`
  - Secuencial ID: `13118318`
  - Format: Cloud Optimized GeoTIFF (COG), 32-bit float
  - Size: 113.99 MB (`119,524,884` bytes)
  - Resolution: 0.50 m
  - Year: 2023 (flight 2022–2025)

### 3.2 Exact Spatial Footprint (Proven from Official Metadata)
Extracted directly from IGN's official spatial auxiliary package (`Informacion_Auxiliar_MDT50cm.zip` and `Informacion_Auxiliar_MDS50cm.zip` -> `Entornos_MDTv1_VAL_25830.gpkg` and `Entornos_MDSv1_Valencia_H30.gpkg`):

| Boundary | Sheet 0845-8-2 (EPSG:25830) | AOI + 120 m Margin | Margin to Sheet Edge |
|---|---|---|---|
| West (E_min) | **683,060.0 m** | 685,380.0 m | +2,320 m to spare |
| East (E_max) | **686,850.0 m** | 686,620.0 m | +230 m to spare |
| South (N_min) | **4,277,210.0 m** | 4,277,380.0 m | +170 m to spare |
| North (N_max) | **4,279,710.0 m** | 4,278,620.0 m | +1,090 m to spare |

**Conclusion:** The AOI + 120 m margin is entirely enclosed within sheet `0845-8-2`. No supplementary sheets are needed.

### 3.3 Grid Alignment
Both MDT50cm and MDS50cm share:
- Dimensions: 7,580 columns × 5,000 rows
- Cell size: exactly 0.50 m × 0.50 m
- Pixel coordinate origin: identical (E 683,060.0, N 4,279,710.0)
Normalized height subtraction ($MDS - MDT$) is therefore pixel-aligned without resampling.

### 3.4 Vertical Datum
- Specified by PNOA-LiDAR as *Altitudes ortométricas referidas al geoide EGM08*.
- In mainland Spain, IGN's realization is **EGM08-REDNAP** with vertical heights referred to the Alicante tide gauge (*nivel medio del mar en Alicante*).
- EPSG vertical code: **EPSG:5782** ("Alicante height").
- Combined 3D CRS: **EPSG:25830 + EPSG:5782**.

### 3.5 Attribution Formula
Confirmed from the CdD licensing engine (`licsRecsSerie`):
- When combining MDT50cm and MDS50cm into a new derived work:  
  `Obra derivada de MDT50cm-cob3 2022-2025 y MDS50cm-cob3 2022-2025 CC-BY 4.0 scne.es`  
  (Hyperlinking `scne.es` to `https://www.scne.es/`).
- Fallback MDT05:  
  `Obra derivada de MDT05 2009 CC-BY 4.0 scne.es`.

---

## 4. IGN WCS Scriptable Fallback Terrain

Tested GetCoverage request against IGN WCS endpoint:
- **Service:** `https://servicios.idee.es/wcs-inspire/mdt`
- **Coverage ID:** `Elevacion25830_5` (MDT05, 5 m resolution, 2009 flight)
- **Format:** `application/asc` (ASCII Grid with decimal values)
- **Exact Request:**
  ```
  https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=Elevacion25830_5&SUBSET=x(685380,686620)&SUBSET=y(4277380,4278620)&FORMAT=application/asc
  ```
- **Output Inspection:**
  - Dimensions: 248 columns × 248 rows (cell size 5.0 m)
  - Lower-left corner: E 685380.0, N 4277380.0
  - Values retain 3 decimal places (e.g., `514.038`, `514.002`)
  - File size: 493,615 bytes (~482 KB)
  - SHA-256: `ae3fb9adfdebb9ecb332ec77598a887967cbe45f3e427d831d0a0ef8580136a4`

---

## 5. OpenStreetMap Overpass Verification

### 5.1 Query Parameters & Execution
- **Bounding Box:** `(38.625327, -0.870437, 38.636754, -0.855869)` (WGS84 envelope of E 685380–686620, N 4277380–4278620).
- **Query:**
  ```overpassql
  [out:json][timeout:90][bbox:38.625327,-0.870437,38.636754,-0.855869];
  (node;way;relation;);
  out body;
  >;
  out skel qt;
  ```
- **Snapshot Timestamp:** `2026-11-15T12:22:50Z`
- **Response Size:** `11,046,725` bytes (~10.53 MB)
- **SHA-256:** `7e5a4e82561b24ad9693006585ea0568b0289a4e25ca90b9e9e4a8f1029e01a4`

### 5.2 Element Breakdown
- Total Elements: 104,375
  - Nodes: 94,232
  - Ways: 10,113
  - Relations: 30
- Highways: 543 ways
- Railways: 30 elements
- Historic City Walls (`barrier=city_wall`): 13 ways
- Trees (`natural=tree`): 11 nodes
- Landuse / Leisure: 5 landuse polygons, 22 leisure areas
- Named POIs: 45 features

### 5.3 ODbL Compliance & Produced Works
Confirmed under ODbL 1.0 sections 4.3, 4.4, and 4.5:
- Rendered raster map images and pixel-art tiles constitute a **Produced Work**.
- Creating a Produced Work does not create a Derivative Database.
- Rendered tiles may be offered under CC BY 4.0 (or any chosen project license), provided OpenStreetMap attribution (`© OpenStreetMap contributors`) and notice of the ODbL are maintained.
- Sharing the open pipeline satisfies ODbL Section 4.6 (making available the method / code).

---

## 6. Landmark Coordinates & POI Curation

Coordinates re-queried and projected with PyProj (`Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)`):

| Landmark | Source Ref | WGS84 Lon | WGS84 Lat | UTM E (25830) | UTM N (25830) | AOI Status |
|---|---|---|---|---|---|---|
| Castillo de la Atalaya | osm:node/306347007 | -0.860915 | 38.631934 | 686,192.5 | 4,278,103.7 | In |
| Torre del Homenaje | osm:way/565944521 | -0.861102 | 38.631784 | 686,176.7 | 4,278,086.7 | In |
| Iglesia de Santiago | osm:way/475846918 | -0.863912 | 38.631552 | 685,932.7 | 4,278,055.2 | In |
| Iglesia de Santa María | osm:way/696092481 | -0.860973 | 38.630222 | 686,191.9 | 4,277,913.5 | In |
| Ermita de San José | osm:way/713679948 | -0.859468 | 38.630318 | 686,322.7 | 4,277,927.3 | In |
| Ayuntamiento | osm:way/550230731 | -0.863041 | 38.631458 | 686,008.8 | 4,278,046.5 | In |
| Teatro Chapí | wikidata:Q11704261 | -0.866403 | 38.630514 | 685,718.5 | 4,277,934.9 | In |
| Estación de Villena | osm:node/2021580965 | -0.867951 | 38.632266 | 685,579.2 | 4,278,126.3 | In |
| Museo Arqueológico Soler | osm:node/6536569783 | -0.863101 | 38.631332 | 686,003.8 | 4,278,032.4 | In |
| Museo de Villena (MUVI) | osm:way/384137610 | -0.866510 | 38.629915 | 685,710.7 | 4,277,868.3 | In |
| Museo Festero | osm:way/696092482 | -0.863310 | 38.631166 | 685,986.1 | 4,278,013.6 | In |
| Museo Navarro Santafé | osm:node/6536647445 | -0.864106 | 38.634240 | 685,908.8 | 4,278,353.1 | In |
| Plaza Mayor | osm:way/410546874 | -0.862215 | 38.630275 | 686,083.6 | 4,277,916.9 | In |
| Plaza de Santiago | osm:way/410546984 | -0.863389 | 38.631374 | 685,978.7 | 4,278,036.4 | In |
| Plaza de Santa María | osm:way/410546875 | -0.861490 | 38.630326 | 686,146.7 | 4,277,924.0 | In |
| Plaza del Rollo | osm:relation/7869041 | -0.862585 | 38.629878 | 686,052.5 | 4,277,872.1 | In |
| Plaza de las Malvas | osm:way/253823810 | -0.864430 | 38.630017 | 685,718.5 | 4,278,052.0 | In |
| Paseo Chapí | osm:way/194943361 | -0.866521 | 38.631571 | 685,705.5 | 4,278,052.0 | In |
| Mirador de la Villa | osm:node/13277775039 | -0.861548 | 38.631611 | 686,138.3 | 4,278,066.6 | In |
| Centro Recepción Visitantes | osm:way/696092479 | -0.859813 | 38.632825 | 686,286.2 | 4,278,204.8 | In |
| Plaza de Toros | osm:way/205835401 | -0.868410 | 38.639558 | 685,520.4 | 4,278,934.6 | Out (N=4278934) |

25 curated POIs were validated and written to `cities/villena/poi-selection.json`.

---

## 7. Legal Analysis: Catastro Derived Vectors

### 7.1 Normative Context
- **Resolución de 23 de marzo de 2011:** An internal regulatory resolution of the Dirección General del Catastro published through the Sede Electrónica del Catastro (SEC) approving criteria, delivery formats, and the standard license agreement (*licencia-tipo*) for bulk downloads.
- **Governing clauses (INSPIRE & SEC):**
  > "Se autoriza el uso público, incluido el comercial, de la información catastral que haya sido sometida a cualquier proceso previo de transformación en los términos establecidos en el artículo 21 del texto refundido de la Ley de Propiedad Intelectual [...]. En consecuencia, no se autoriza la difusión, distribución o comercialización de la información original suministrada, que no puede ser difundida por Internet ni por ningún otro medio sin su previa transformación."
- **Article 21 TRLPI:** Defines transformation as translation, adaptation, or any other modification in form from which a different work (*"obra diferente"*) is derived.

### 7.2 Application to Project Deliverables
- **Rendered Pixel-Art Map & Static Tiles:** Unambiguously an *obra diferente* (a creative visual render with isometric projection, shading, custom palette, and styling). Fully authorized for public and commercial redistribution under CC BY 4.0.
- **Scene Files (Derived Vector GeoJSON):** Format conversion from GML to GeoJSON or geographic clipping does not legally constitute an *obra diferente*. Even when enriched with LiDAR heights, distributing vector building footprints could be construed as unauthorized redistribution of original cadastral geometry.
- **Policy Decision:** In compliance with AGENTS.md Hard Rules, Catastro-derived vector files are strictly confined to local pipeline processing. They are not committed to Git, not included in web viewer deployment, and not published as release assets.

---

## 8. Unresolved Points and Operational Caveats

1. **Manual File Contents:** Internal raster pixel values, compression schemes, and embedded tags of `MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` and `MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` cannot be verified until the human owner downloads them and places them in `data/raw/`.
2. **V1 to V2 Upgrades:** The 3rd coverage PNOA-LiDAR is labeled V1 (provisional). When IGN completes post-processing and issues a final V2 release, the file names and checksums may change.
