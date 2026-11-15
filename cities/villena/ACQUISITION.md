# Dataset Acquisition — Villena

Step-by-step instructions for acquiring all datasets required to build the Villena 3D isometric scene (WP03).

---

## 1. Summary and Storage Requirements

- **Total download volume:** ~200 MB.
- **Estimated disk space needed:**
  - `data/raw/`: ~200 MB (pristine input datasets).
  - `data/interim/`: ~400 MB (clipped rasters, intermediate geometries).
  - `build/villena/scene/`: ~50 MB (final vector layers and terrain crop).
  - **Recommended free space:** ≥ 2 GB.
- **Directories:** All raw downloads are placed in `data/raw/<dataset-id>/` relative to the repository root.

---

## 2. Automated Scripted Downloads

Run these commands from the root of the repository.

### 2.1 Catastro INSPIRE Buildings (`catastro-buildings`)
Predefined municipal ATOM dataset containing Building and BuildingPart GML footprints with storey counts.

```bash
mkdir -p data/raw/catastro-buildings

curl -sS -A "Mozilla/5.0 (compatible; geodata-research/1.0)" \
  -o data/raw/catastro-buildings/A.ES.SDGC.BU.03140.zip \
  "https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/03/03140-VILLENA/A.ES.SDGC.BU.03140.zip"
```
- **Expected size:** `3,971,442` bytes (~3.97 MB)
- **Expected SHA-256:** `38588fba7a3fd15bcff301096639720fd79fb37edfc975cda517a945024f1e17`

### 2.2 IGN MDT05 Fallback Terrain (`ign-mdt05`)
Scriptable 5 m resolution bare-earth elevation model requested via WCS for the AOI + 120 m margin. Used as an automated fallback when the manual 0.5 m rasters are absent.

```bash
mkdir -p data/raw/ign-mdt05

curl -sS -A "Mozilla/5.0 (compatible; geodata-research/1.0)" \
  -o data/raw/ign-mdt05/mdt05-aoi-margin-v2.asc \
  "https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=Elevacion25830_5&SUBSET=x(685230,686620)&SUBSET=y(4277380,4279220)&FORMAT=application/asc"
```
- **Expected size:** `820,135` bytes (~801 KB)
- **Expected SHA-256:** `f08987ac44367acf5546b196762996ac716f551a8aff61abf7e208099cda5663`

### 2.3 OpenStreetMap Extract (`osm`)
Streets, railways, landcover, leisure, water, barriers, and POIs within the AOI + 120 m margin.

```bash
mkdir -p data/raw/osm

curl -sS -A "villena-isometrica/0.1" \
  --data-urlencode 'data=[out:json][timeout:120][bbox:38.625327,-0.872159,38.642189,-0.855708];(node;way;relation;);out body;>;out skel qt;' \
  https://overpass-api.de/api/interpreter \
  -o data/raw/osm/osm-aoi-margin-v2.json
```
- **Expected size:** ~11.6 MB (`11,581,743` bytes on snapshot 2026-11-15)
- **Expected SHA-256:** `61532bcea24cba860246050295c45a048ab192fe9568cfbb750e93421a60c50b` (snapshot pinned at retrieval)

---

## 3. Manual Downloads (IGN / CNIG Centro de Descargas)

The high-resolution 0.5 m elevation rasters from the PNOA-LiDAR 3rd coverage (2023 flight) must be downloaded manually through a web browser because the portal uses reCAPTCHA v3. Circumventing this protection is forbidden.

### 3.1 MDT50cm 3ª cobertura (`ign-mdt50cm`)
1. Open your web browser and navigate directly to the file details page:
   [https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=12759170](https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=12759170)  
   *(Alternative navigation: Go to https://centrodedescargas.cnig.es/CentroDescargas/ -> "Modelos Digitales del Terreno" -> "MDT50 cm - 3ª cobertura" -> Filter by hoja "0845" or coordinate 38.6319, -0.8609).*
2. Confirm the file name is **`MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif`** (Size: ~61.07 MB, Formato: COG, Año: 2023).
3. Click the download icon / link and accept the license terms (CC BY 4.0 scne.es).
4. Save the file directly to:
   ```
   data/raw/ign-mdt50cm/MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif
   ```

### 3.2 MDS50cm 3ª cobertura (`ign-mds50cm`)
1. Open your web browser and navigate directly to the file details page:
   [https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=13118318](https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=13118318)  
   *(Alternative navigation: Go to https://centrodedescargas.cnig.es/CentroDescargas/ -> "Modelos Digitales del Terreno" -> "Modelo Digital de Superficies MDS50 cm - 3ª cobertura" -> Filter by hoja "0845" or coordinate 38.6319, -0.8609).*
2. Confirm the file name is **`MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif`** (Size: ~113.99 MB, Formato: COG, Año: 2023).
3. Click the download icon / link and accept the license terms (CC BY 4.0 scne.es).
4. Save the file directly to:
   ```
   data/raw/ign-mds50cm/MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif
   ```

---

## 4. Verification and Checksums

After downloading the datasets, verify file integrity and contract validity:

```bash
# 1. Print checksums and sizes of downloaded files
shasum -a 256 data/raw/*/*

# 2. Check contract compliance against the JSON schema
uv run scripts/validate_contracts.py cities/villena/datasets.json
```

> [!NOTE]
> When the manual IGN files are placed into `data/raw/ign-mdt50cm/` and `data/raw/ign-mds50cm/`, compute their sha256 (`shasum -a 256 data/raw/ign-md*/*.tif`), update the `sha256` and `retrievedAt` fields in `cities/villena/datasets.json`, and re-run `validate_contracts.py`.
