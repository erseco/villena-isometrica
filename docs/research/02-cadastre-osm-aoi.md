# 02 — Cadastre INSPIRE, OpenStreetMap, landmarks and AOI

**Verification date: 2026-11-15.** Everything below was queried, downloaded or read on that date unless it is listed in [Not verified / unresolved](#8-not-verified--unresolved).

Verification labels used in this document:

- **queried** — live API/service request, response inspected.
- **downloaded** — file fetched, hashed and parsed locally.
- **read** — text read on the official page or PDF.
- **computed** — derived locally from the above (tool stated).

Probe downloads live outside the repo, in the session scratchpad (`…/scratchpad/cadastre-osm/`), and are not part of the project. Hashes are given so the same files can be re-identified.

Tooling actually used: `curl 8.7.1`, Python 3.15 stdlib (`xml.etree`, `zipfile`, `json`), `pdftotext`, **pyproj 3.8.0 / PROJ 9.8.1** (in a throwaway venv). **GDAL/ogrinfo is not installed** on this machine, so GML was parsed with the Python stdlib.

All requests used `User-Agent: geodata-research-script/0.1`.

---

## 1. Municipality codes

| Fact | Value | Source | How |
|---|---|---|---|
| INE municipality code | **03140** (CPRO `03`, CMUN `140`, check digit `9`) | INE, "Relación de municipios y códigos … a 1 de enero de 2026": <https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx> (sha256 `07f8e8d6…dd49052`) | downloaded, parsed |
| Catastro INSPIRE municipality code | **03140** (folder `03140-VILLENA`, territorial office `03` Alicante) | Catastro ATOM feeds (section 2) | downloaded |
| Wikidata | Q502249, P772 (INE code) = `03140` | <https://www.wikidata.org/wiki/Q502249> | queried (API) |
| OSM boundary | relation 345862, `ine:municipio=03140`, `ref:ine=03140000000`, `admin_level=8` | Overpass | queried |

For Villena the INE code and the code used in the Catastro INSPIRE feeds are the same string. (This is not guaranteed for every Spanish municipality; it was only checked for Villena.)

---

## 2. Cadastre INSPIRE (Dirección General del Catastro)

Landing page (read): <https://www.catastro.hacienda.gob.es/webinspire/index.html>. It states that the ATOM predefined datasets are per municipality and "Los datos se actualizan 2 veces al año".

### 2.1 ATOM feeds

| Theme | Top-level feed | Alicante (03) feed |
|---|---|---|
| Buildings (BU) | <https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/ES.SDGC.BU.atom.xml> | <https://www.catastro.hacienda.gob.es/INSPIRE/buildings/03/ES.SDGC.bu.atom_03.xml> |
| Cadastral Parcels (CP) | <https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/ES.SDGC.CP.atom.xml> | <https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/03/ES.SDGC.CP.atom_03.xml> |
| Addresses (AD) | <https://www.catastro.hacienda.gob.es/INSPIRE/Addresses/ES.SDGC.AD.atom.xml> | <https://www.catastro.hacienda.gob.es/INSPIRE/Addresses/03/ES.SDGC.AD.atom_03.xml> |

All six feeds downloaded (HTTP 200). All carry `<updated>2026-08-21T00:00:00Z</updated>`. The province feeds are `ISO-8859-1` with CRLF line endings (a plain `grep villena` fails unless the file is converted or grepped as binary).

### 2.2 Villena datasets (downloaded)

| Theme | Download URL | Zip size (bytes) | HTTP `Last-Modified` | sha256 |
|---|---|---|---|---|
| BU | <https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/03/03140-VILLENA/A.ES.SDGC.BU.03140.zip> | 3,971,442 | Fri, 21 Aug 2026 17:35:52 GMT | `38588fba7a3fd15bcff301096639720fd79fb37edfc975cda517a945024f1e17` |
| CP | <https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/03/03140-VILLENA/A.ES.SDGC.CP.03140.zip> | 6,312,064 | Fri, 21 Aug 2026 12:50:41 GMT | `015a7f8666a103dce36e8ccad6ff2411d15ac7d234fbf5b5ba35a3e3f5b3e9b3` |
| AD | <https://www.catastro.hacienda.gob.es/INSPIRE/Addresses/03/03140-VILLENA/A.ES.SDGC.AD.03140.zip> | 458,829 | Fri, 21 Aug 2026 13:58:36 GMT | `54670273e4c0b37c7ef1b82865bebe0ae5d3ad7aa6893fbbc72cbbb1adebdd94` |

Dataset date/version: **2026-08-21** (feed `<updated>`, metadata XML creation and publication dates, zip member timestamps all agree). There is no version number other than the date.

Zip contents (uncompressed bytes):

| Zip | Member | Size |
|---|---|---|
| BU | `A.ES.SDGC.BU.03140.building.gml` | 38,737,593 |
| BU | `A.ES.SDGC.BU.03140.buildingpart.gml` | 55,437,808 |
| BU | `A.ES.SDGC.BU.03140.otherconstruction.gml` | 2,755,647 |
| BU | `A.ES.SDGC.BU.MD.03140.xml` (ISO 19115 metadata) | 20,006 |
| CP | `A.ES.SDGC.CP.03140.cadastralparcel.gml` | 53,988,893 |
| CP | `A.ES.SDGC.CP.03140.cadastralzoning.gml` | 3,378,914 |
| CP | `A.ES.SDGC.CP.MD..03140.xml` (double dot is in the real file name) | 25,497 |
| AD | `A.ES.SDGC.AD.03140.gml` | 16,272,677 |
| AD | `A.ES.SDGC.AD.MD.03140.xml` | 20,407 |

### 2.3 CRS

**EPSG:25830 (ETRS89 / UTM 30N)** — confirmed three ways: ATOM entry `<category term="http://www.opengis.net/def/crs/EPSG/0/25830" label="ETRS89"/>`; metadata XML reference system `http://www.opengis.net/def/crs/EPSG/0/25830`; and every geometry `srsName` in the GML (`urn:ogc:def:crs:EPSG::25830` in BU/AD, `http://www.opengis.net/def/crs/EPSG/0/25830` in CP). Coordinates are easting-northing, `srsDimension="2"`. So the proposed working CRS matches the source data natively; no reprojection is needed for Catastro.

### 2.4 Layers, feature counts and fields actually present (parsed from the downloaded GML)

Whole municipality of Villena:

| File / feature type | Features | Geometry |
|---|---|---|
| `bu-ext2d:Building` | **8,442** | `gml:Surface` (10,530 exterior rings in total, 677 interior rings) |
| `bu-ext2d:BuildingPart` | **22,217** | `gml:Surface` (874 interior rings) |
| `bu-ext2d:OtherConstruction` | **1,286** | `gml:Polygon` |
| `cp:CadastralParcel` | **22,480** | `gml:MultiSurface` (3,087 interior rings) |
| `cp:CadastralZoning` | **695** | `gml:MultiSurface` |
| `ad:Address` | **11,401** | `gml:Point` |
| `ad:ThoroughfareName` / `PostalDescriptor` / `AdminUnitName` | 392 / 5 / 1 | none |

GML schema: BU uses INSPIRE `bu-ext2d/2.0` (`BuildingExtended2D.xsd`), CP `cp/4.0`, AD `ad/3.0`. Metadata states "Format GML 3.2", lineage "numeric restitution from a photogrammetric flight, or by digitalizing graphic documents existing at the Cadastre", equivalent scale 1:1000.

**Building** (fields with their population in Villena):

- `inspireId/localId` (= 14-character cadastral reference), `namespace` `ES.SDGC.BU`
- `beginLifespanVersion`; `endLifespanVersion` (nil in 8,438 of 8,442)
- `conditionOfConstruction`: functional 8,050 · declined 345 · `-` 36 · ruin 11
- `dateOfConstruction/beginning` and `/end` (populated for all; many are decade placeholders such as `1900-01-01`, `1930-01-01`)
- `currentUse` (8,398 populated): 1_residential 7,047 · 3_industrial 875 · 2_agriculture 215 · 4_2_retail 150 · 4_3_publicServices 92 · 4_1_office 19
- `numberOfBuildingUnits`, `numberOfDwellings`
- `officialArea/value` (m², `grossFloorArea`)
- `document/documentLink` — URL of the façade photograph service (`OVCFotoFachada.svc`), `sourceStatus` NotOfficial
- `horizontalGeometryEstimatedAccuracy` = 0.1 m for every feature; `horizontalGeometryReference` = footPrint
- `addresses`, `cadastralParcels` (xlink to the WFS)
- **`numberOfFloorsAboveGround`: nil (`other:unpopulated`) on all 8,442 Buildings.**

**BuildingPart** — the layer that carries height information:

- `inspireId/localId` = `<refcat>_partN`
- **`numberOfFloorsAboveGround`: populated on all 22,217 parts.** Distribution (floors: parts): 0: 633 · 1: 11,366 · 2: 5,352 · 3: 1,987 · 4: 1,000 · 5: 870 · 6: 417 · 7: 170 · 8: 105 · 9: 70 · 10: 66 · 11: 80 · 12: 71 · 13: 25 · 14: 5.
- `numberOfFloorsBelowGround`: 0: 20,456 · 1: 1,249 · 2: 498 · 3: 14
- `heightBelowGround` (m): exactly 3 × floors below ground (0 / 3 / 6 / 9) — i.e. a nominal 3 m per storey, not a measurement.
- `conditionOfConstruction`: nil on all parts
- **There is no above-ground height in metres anywhere in the dataset.** Height must be estimated as floors × an assumed storey height, or taken from LiDAR (researched separately).

**OtherConstruction**: `constructionNature` = `openAirPool` for all 1,286 (swimming pools only), no height attributes.

**CadastralParcel**: `nationalCadastralReference`, `label`, `areaValue` (m²), `referencePoint`, `beginLifespanVersion`. **Address**: `locator/designator` (number), `position/specification` (Entrance 6,715 · Parcel 4,686), `component` links to thoroughfare/postcode/admin unit.

Catastro's own data description (read, `Conjuntos de datos.pdf`, sha256 `78610670…8b7ba96`, from <https://www.catastro.hacienda.gob.es/webinspire/documentos/Conjuntos%20de%20datos.pdf>) confirms the modelling:

> "BuildingPart es cada una de las construcciones de una parcela catastral que tiene volumen homogéneo, y pueden ser sobre y bajo rasante. Tiene los atributos relacionados con la altura."
>
> "bu-ext2d:numberOfFloorsAboveGround: número de plantas del edificio. Este dato no se puede dar a nivel de edificio ya que en el modelo catastral no podemos delimitar volumetría para el conjunto del edificio, es un valor que va reflejado en BuildinPart."

**Consequence for the pipeline:** extrude `BuildingPart` polygons, not `Building`. Join to `Building` on the cadastral reference (strip `_partN`) to get `currentUse`, `dateOfConstruction` and `conditionOfConstruction` for styling.

**Castle check (computed):** the Castillo de la Atalaya is in Catastro as parcel `6383001XH8768S`, a **single BuildingPart with 117 vertices and `numberOfFloorsAboveGround = 3`**, centroid E 686175.7 N 4278086.0. Cadastral floors are meaningless for a castle with a keep and curtain walls; it will need LiDAR or hand modelling.

### 2.5 WFS / WMS alternatives (queried)

| Service | Endpoint | Verified |
|---|---|---|
| WFS BU | `http://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx` | GetCapabilities 200; feature types `bu:Building`, `bu:BuildingPart`, `bu:OtherConstruction`; default CRS EPSG:25830, also 25829, 25831, 3035, 3857, 4258, 4326, CRS:84 |
| WFS CP | `http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx` | listed on landing page (not called) |
| WFS AD | `http://ovc.catastro.meh.es/INSPIRE/wfsAD.aspx` | listed on landing page (not called) |
| WMS | `http://ovc.catastro.meh.es/cartografia/INSPIRE/spadgcwms.aspx` | GetCapabilities 200; layers `CP.CadastralParcel`, `CP.CadastralZoning`, `AD.Address`, `BU.Building`, `BU.BuildingPart`, `AU.AdministrativeUnit`, `AU.AdministrativeBoundary`; CRS include EPSG:25830, 3857, 4326 |

WFS limits (read, `inspire-bu-WFS.pdf`): "Búsqueda por caja de 4km2 y 5.000 elementos"; no generic SQL filter. Request type names are `BU.BUILDING`, `BU.BUILDINGPART`, `BU.OTHERCONSTRUCTION`.

Live test — a 200 m × 200 m box around the castle returned **472 BuildingParts** (1.16 MB GML, HTTP 200):

```
http://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?service=wfs&version=2&request=getfeature&typenames=BU.BUILDINGPART&bbox=686100,4278000,686300,4278200&srsname=EPSG::25830
```

The proposed 1 km² AOI holds 6,813 BuildingParts, which **exceeds the 5,000-element WFS limit**, so a single WFS call would not cover it. The ATOM zip (4 MB) is the simpler and more polite route; WFS is only worth it for small spot updates.

WMS access constraint, verbatim from GetCapabilities: "Free access, but it is not allowed massive downloads of cartography portions and tiled petitions". So the WMS must not be used as a tile source.

The SEC terms of use (read, <https://www.catastro.hacienda.gob.es/ayuda/condicionesuso.htm>) add that an IP exceeding the request rate is denied service "generalmente 10 días", and that interactive services may not be used for bulk downloads or by automatic processes.

### 2.6 Licence and attribution

**Licence document** (read): "Licencia de acceso y uso de los servicios y conjuntos de datos INSPIRE de la Dirección General del Catastro — Parcela Catastral (CP), Direcciones (AD), Edificios (BU). Versión 1.0, Julio 2016" — <https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf> (sha256 `9265a9c05ad0cf5a4366c59a4b16168eda9cf792ec1279e2c52a53f3f622d652`).

Key clause, verbatim:

> "La descarga masiva de información gráfica y alfanumérica del Catastro y el acceso a los servicios web se autoriza para uso propio del usuario titular de la licencia, o para la elaboración y distribución de nuevos productos de valor añadido a partir la información catastral, siempre que ésta sea transformada por el interesado.
>
> Se autoriza el uso público, incluido el comercial, de la información catastral que haya sido sometida a cualquier proceso previo de transformación en los términos establecidos en el artículo 21 del texto refundido de la Ley de Propiedad Intelectual […]. En consecuencia, no se autoriza la difusión, distribución o comercialización de la información original suministrada, que no puede ser difundida por Internet ni por ningún otro medio sin su previa transformación. Sólo existirá transformación de la información catastral si su traducción, adaptación o cualquier otra modificación en su forma da lugar a una obra diferente, cuyos derechos de propiedad intelectual corresponderán al autor de la obra transformada […]"

and:

> "La transformación de la información catastral no podrá suponer alteración del contenido de la información catastral ni desnaturalización de su sentido. Los nuevos productos o servicios que puedan generarse no suplantarán a los ofrecidos por la Dirección General del Catastro. A estos efectos, se entenderá que los nuevos productos o servicios generados suplantan a los ofrecidos por la Dirección General del Catastro si se identifican como "cartografía catastral", información catastral", o términos equivalentes que puedan inducir a confusión."

The licence is obtained automatically by using the service ("se obtendrá de manera automática").

**Attribution as Catastro states it:**

- In every Villena ATOM entry, `<rights>` (verbatim, including its grammar):
  > "This service can be used free of charge in every instance,  as long as that the D. G. of the Cadastre (Ministry of Finance)  is mentioned as author and owner of the information"
- In the SEC bulk-download licence-type (read, <https://www.catastro.hacienda.gob.es/pdf/ovc/licdescargaES.pdf>, sha256 `e892ccad…9cf69d95`), clause 12:
  > "[…] deberá citarse como fuente en todos los productos o servicios que se elaboren a partir de la información catastral descargada, a la Dirección General del Catastro, del Ministerio de Economía y Hacienda del Reino de España. Asimismo deberá indicarse la fecha en la que se produjo el acceso al producto o servicio utilizado."
  
  and clause 13: use and transformation are authorised "durante un plazo de 10 años" (the term restarts when an updated version is accessed).

The INSPIRE licence PDF does not itself prescribe an attribution string; it refers back to "el número 5 del apartado primero de esta resolución" (the Resolución de 23 de marzo de 2011). The licence-type PDF above is the document for the SEC bulk-download service, which is governed by the same Resolución; it is the only place where the "cite the source + access date" wording was found.

**Verdict:**

| Question | Answer |
|---|---|
| Rendered map / pixel-art tiles derived from the data, public and commercial use | **Allowed** (it is a transformed work). |
| Redistribute the raw GML/zip (e.g. commit it to the repo, mirror it) | **Not allowed** — "no se autoriza la difusión, distribución o comercialización de la información original suministrada". Ship a download script and checksums instead. |
| Redistribute a derived vector dataset (clipped, simplified, merged GeoJSON) | **Unclear** — depends on whether the result is "una obra diferente". See unresolved. |
| Attribution | **Required**: name the Dirección General del Catastro as source/author, plus the access date. |
| Naming | Do **not** label the product "cartografía catastral" / "información catastral". |

Inconsistencies observed in Catastro's own metadata (recorded, not resolved): the top-level ATOM feeds say `Copyright (c) 2012", ES.SDGC; all rights reserved`, while the dataset metadata XML says access constraints "no limitation" / "No conditions apply" and fees "No fees". The licence PDF is the governing text.

---

## 3. OpenStreetMap

### 3.1 Getting an extract

**Overpass API** (queried, `https://overpass-api.de/api/interpreter`; one 502 was received and succeeded on retry). Full-geometry extract for the proposed AOI (WGS84 envelope of the UTM square, see section 6):

```overpassql
[out:xml][timeout:90][bbox:38.626433,-0.869027,38.635648,-0.857279];
( node; way; relation; );
(._; >;);
out meta;
```

The tags-only variant actually run for the statistics below:

```overpassql
[out:json][timeout:90][bbox:38.626433,-0.869027,38.635648,-0.857279];
( node[~"."~"."]; way; relation; );
out tags center;
```

```sh
curl -sS -A "geodata-research-script/0.1" --data-urlencode "data@q_aoi.overpassql" \
  -o aoiA_tags.json https://overpass-api.de/api/interpreter
```

Result: 333,430 bytes, sha256 `10ee263f1989c6cc0ce3455bebded6142e6997fe220432fa16c8fce493500c58`, `timestamp_osm_base` 2026-11-15T11:31:01Z.

**Geofabrik** (read + HEAD request): region **Valencia** (Comunidad Valenciana), <https://download.geofabrik.de/europe/spain/valencia.html>. `valencia-latest.osm.pbf` redirects to `valencia-261114.osm.pbf`, **141,443,749 bytes** (page says "134 MB"), data up to 2026-11-14T21:20:41Z. The page states "No sub regions are defined for this region", so there is no province-level extract. `valencia-latest-free.shp.zip` is 257 MB. For a 1 km² AOI, Overpass is the proportionate tool; Geofabrik would need `osmium extract` to clip.

### 3.2 Completeness in Villena (computed from the Overpass result)

The query box is the WGS84 envelope of AOI A, so it is very slightly larger than the UTM square.

| Theme | Count | Notes |
|---|---|---|
| Elements | 1,960 | 1,830 ways, 103 tagged nodes, 27 relations |
| `highway` ways | 428 (313 named) | residential 248 · steps 41 · footway 36 · tertiary 23 · path 18 · service 15 · motorway 12 · secondary 9 · pedestrian 8 · track 6 · unclassified 5 · cycleway 4 · construction 2 |
| Buildings (ways/relations) | 1,317 | `building=yes` 1,294; only 13 named |
| `building:levels` | **1** | |
| `height` | **0** | |
| `building:part`, `roof:shape` | 0, 0 | |
| `addr:housenumber` | 9 | |
| `landuse` | 3 | retail, forest, residential |
| `natural` | 18 | tree 11 · wood 2 · water 2 · heath 2 · bare_rock 1 |
| Trees (`natural=tree`) | **11** | no `tree_row` |
| `leisure` | 13 | park 6 · playground 5 |
| `barrier` | 17 | **city_wall 12** |
| `railway` | 24 | rail 13, station 1, platforms 2 |
| `amenity` | 41 | parking 10, drinking_water 6, cafe 5, place_of_worship 4, fountain 3 |
| Named POIs (amenity/shop/tourism/historic/leisure/office/craft with `name`) | 39 | |

For comparison, Catastro has **2,498 Buildings / 6,813 BuildingParts** with centroids inside AOI A.

**Assessment:**

- **Streets: good.** The network is detailed, including 41 `steps` ways and footpaths in the old town, and 73 % of ways are named. Use OSM for streets, stairs, squares, railway and the city-wall lines.
- **Buildings: use Catastro, not OSM.** OSM has about half as many footprints as Catastro has buildings, and effectively no height data (1 feature with levels, 0 with height).
- **Vegetation and land cover: poor.** 11 trees and 3 landuse polygons in a square kilometre. Trees and ground cover need another source (orthophoto, LiDAR or procedural placement).
- **POIs: thin** (39 named). Enough for headline landmarks, not for shop-level detail. The Teatro Chapí is not tagged at all (section 4).
- The A-31 motorway appears in the box as the **Túnel de Villena** (`tunnel=yes`, `layer=-1`) under the hill east of the castle; the renderer must not draw it on the surface.

### 3.3 ODbL obligations

Sources read: <https://www.openstreetmap.org/copyright>, <https://osmfoundation.org/wiki/Licence/Attribution_Guidelines>, <https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ>, <https://opendatacommons.org/licenses/odbl/1-0/>. These pages were read through a fetch tool that returns extracts, so the quotations below are short excerpts, not full clauses.

- Licence: "OpenStreetMap is open data, licensed under the Open Data Commons Open Database License (ODbL)."
- Attribution: "Attribution must be to "OpenStreetMap"." and "Attribution must also make it clear that the data is available under the Open Database License." This can be done by "making the text "OpenStreetMap" a link to openstreetmap.org/copyright".
- Placement: for interactive maps "the credit should typically appear in a corner of the map"; "Static images must be generally attributed the same way as interactive maps." For datasets: "You must include the notices in a location (such as a relevant directory) where users would be likely to look for it".
- Share-alike: "If you alter or build upon our data, you may distribute the result only under the same license." (ODbL 4.4: "Any Derivative Database that You Publicly Use must be only under the terms of" ODbL or a compatible licence.)
- **Produced Works** (rendered images/tiles): "You can license a Produced Work under any terms you like." ODbL 4.3: "if you Publicly Use a Produced Work, You must include a notice associated with the Produced Work". ODbL 4.5: making a Produced Work "does not create a Derivative Database for purposes of Section 4.4."
- ODbL 4.6: if a Produced Work is made from a Derivative Database and used publicly, "You must also offer to recipients of the Derivative Database or Produced Work a copy in a machine readable form" of that database, or of the alterations / the method of making them.
- **Collective Database**: "A Collective Database is where the OSM Data is used as part of a collection of otherwise independent databases" and "is not therefore considered a Derivative Database."

**Verdict for this project:**

| Artefact | Status | Obligation |
|---|---|---|
| Rendered pixel-art tiles / images | Produced Work | Any licence; visible "OpenStreetMap" credit with link to the copyright page. |
| OSM extract stored or published as-is | Database | ODbL, with notice file next to the data. |
| OSM data edited, clipped-and-merged or conflated with other data, then published | Derivative Database | Must be ODbL. |
| OSM layer kept separate alongside a Catastro-derived layer | Collective Database | Only the OSM layer is ODbL. |
| Tiles rendered from a modified OSM layer | Produced Work from a Derivative Database | Must offer the modified data or the method. An open-source, reproducible pipeline satisfies "the method". |

Practical rule: **keep OSM-derived and Catastro-derived layers as separate files**, so that share-alike attaches only to the OSM layer and the Catastro "no redistribution of original data" condition is not entangled with it.

### 3.4 Tile requirements

The project renders its own tiles, so the only obligation is attribution (above). If the viewer ever shows the standard `tile.openstreetmap.org` raster as a base or reference layer, the OSMF Tile Usage Policy applies (read, <https://operations.osmfoundation.org/policies/tiles/>): "Show OpenStreetMap licence attribution clearly on the map (typically bottom-right)"; send a clear, unique User-Agent; no bulk download or prefetch; "Offline use is not permitted on `tile.openstreetmap.org`."

---

## 4. Landmarks

Coordinates are OSM element centres (Overpass `out center`, `timestamp_osm_base` 2026-11-15T11:28:02Z) unless marked. EPSG:25830 values were computed with pyproj 3.8.0 (`Transformer.from_crs("EPSG:4326","EPSG:25830", always_xy=True)`). WGS84 and ETRS89 are treated as identical at this precision.

Cross-check of the transformation: OSM way 565944521 (Torre del Homenaje) → E 686176.3 N 4278086.1; the Catastro castle polygon centroid is E 686175.7 N 4278086.0 — two independent sources agree to under 1 m.

| Landmark | OSM element | Wikidata | Lat | Lon | E (25830) | N (25830) | AOI A | AOI B |
|---|---|---|---|---|---|---|---|---|
| Castillo de la Atalaya | node 306347007; outline relation 8046264 | Q2986978 | 38.631934 | -0.860915 | 686192.6 | 4278103.7 | in | in |
| Torre del Homenaje (castle keep) | way 565944521 | — | 38.631779 | -0.861107 | 686176.3 | 4278086.1 | in | in |
| Iglesia Arciprestal de Santiago | way 475846918 | Q4882903 | 38.631572 | -0.863878 | 685935.6 | 4278057.5 | in | in |
| Iglesia de Santa María | way 696092481 | Q4882109 | 38.630219 | -0.861051 | 686185.2 | 4277913.1 | in | in |
| Plaza Mayor | way 410546874 (also way 372469399) | Q4163397 | 38.630241 | -0.862263 | 686079.6 | 4277913.0 | in | in |
| Ayuntamiento (Palacio Municipal) | way 550230731 | Q11697358 | 38.631427 | -0.863049 | 686008.1 | 4278043.1 | in | in |
| Teatro Chapí | **not tagged in OSM** | Q11704261 | 38.630514 ᵂ | -0.866403 ᵂ | 685718.5 | 4277934.9 | in | in |
| Plaza de Toros | way 205835401; building relation 6670463 (`height=12`) | Q6377328 | 38.639558 | -0.868410 | 685520.4 | 4278934.6 | **out** | in |
| Railway station (Villena) | node 2021580965 | Q3329171 | 38.632266 | -0.867951 | 685579.2 | 4278126.3 | in (79 m from W edge) | in |
| Museo Arqueológico José María Soler | node 6536569783 | Q11694497 | 38.631332 | -0.863101 | 686003.8 | 4278032.4 | in | in |
| Museo de Villena (MUVI) | way 384137610 | — | 38.629956 | -0.866537 | 685708.3 | 4277872.7 | in | in |
| Museo Festero | way 696092482 | Q6033364 | 38.631160 | -0.863342 | 685983.3 | 4278012.8 | in | in |
| Museo Escultor Navarro Santafé | node 6536647445 | Q6033319 | 38.634240 | -0.864106 | 685908.8 | 4278353.1 | in | in |
| Ermita de San José | way 713679948 | Q57523002 | 38.630329 | -0.859459 | 686323.5 | 4277928.5 | in | in |
| Plaza de Santiago | way 410546984 | Q5575932 | 38.631401 | -0.863428 | 685975.2 | 4278039.4 | in | in |
| Plaza del Rollo | relation 7869041 | — | 38.629779 | -0.862574 | 686053.7 | 4277861.1 | in | in (61 m from S edge) |
| Plaza de Santa María | way 410546875 | — | 38.630320 | -0.861495 | 686146.2 | 4277923.4 | in | in |
| Paseo Chapí (park) | way 194943361 | — | 38.631331 | -0.866721 | 685688.7 | 4278025.0 | in | in |
| Mirador de la Villa | node 13277775039 | — | 38.631611 | -0.861548 | 686138.3 | 4278066.5 | in | in |
| Centro de Recepción de Visitantes | way 696092479 | — | 38.632815 | -0.859843 | 686283.6 | 4278203.6 | in | in |
| Iglesia María Auxiliadora ("Máxima Auxilidiadora" in OSM) | way 190670666 | — | 38.636530 | -0.866565 | 685688.9 | 4278602.3 | out | in |
| Mercado Municipal | way 190670763 | — | 38.639401 | -0.871279 | 685271.1 | 4278911.4 | out | out |
| Castillo de Salvatierra (ruin on the ridge) | node 2902879970 | Q8342528 | 38.635253 | -0.854262 | 686763.1 | 4278485.5 | out | out |

ᵂ Wikidata P625 coordinate, not OSM. OSM has no `amenity=theatre` and no element named "Teatro…" in the area; the buildings at that spot are untagged `building=yes` ways (e.g. way 833538285). A second Wikidata item, Q117786096 ("Teatro Chapí", heritage-listed, no coordinates), looks like a duplicate.

Wikidata P625 coordinates agree with the OSM centres to within about 20 m for the castle, both churches, Plaza Mayor, the Ayuntamiento, the bullring and the Ermita de San José. They differ more for the station (Wikidata 38.631833, -0.867694, about 50 m from the OSM node), the Museo Navarro Santafé (38.634611, -0.864389, about 50 m) and Q11694497, whose Wikidata label is now "Museo de Villena (MUVI)" with coordinate 38.630038, -0.865234 — near the MUVI building, not at the OSM node "Museo Arqueológico José María Soler" beside the town hall. The table uses the OSM positions. Wikidata P1435 marks the castle, the Iglesia de Santiago, the Palacio Municipal and the Castillo de Salvatierra as Q23712 (Bien de Interés Cultural).

The high-speed station "Villena Alta Velocidad" (Q14623481, 38.584983, -0.873252) is about 5 km south and irrelevant to the AOI.

### 4.1 Openly licensed reference imagery (not downloaded)

Wikimedia Commons categories, with file counts and the licence mix read from each file's `LicenseShortName` via the Commons API:

| Category | Files | Licences |
|---|---|---|
| [Castillo de la Atalaya](https://commons.wikimedia.org/wiki/Category:Castillo_de_la_Atalaya) (+ subcats Bailey, Interior, Parade ground, Capilla de la Virgen de las Nieves, Views from) | 127 | CC BY-SA 3.0: 54 · CC BY-SA 4.0: 38 · Public domain: 26 · CC BY-SA 3.0 es: 5 · CC BY-SA 2.0: 2 · CC BY-SA 2.5: 1 · CC BY 2.0: 1 |
| [Town hall of Villena](https://commons.wikimedia.org/wiki/Category:Town_hall_of_Villena) | 25 | CC BY-SA 4.0: 19 · CC BY-SA 3.0: 5 · CC BY 2.5: 1 |
| [Bullring of Villena](https://commons.wikimedia.org/wiki/Category:Bullring_of_Villena) | 23 | CC BY-SA 3.0: 15 · Public domain: 7 · CC BY-SA 3.0 es: 1 |
| [Teatro Chapí](https://commons.wikimedia.org/wiki/Category:Teatro_Chap%C3%AD) | 18 | CC BY-SA 3.0: 8 · Public domain: 7 · CC BY-SA 4.0: 3 |
| [Plaza Mayor, Villena](https://commons.wikimedia.org/wiki/Category:Plaza_Mayor,_Villena) | 13 | CC BY-SA 3.0: 6 · Public domain: 5 · CC BY 2.5: 1 · CC BY-SA 4.0: 1 |
| [Villena train station](https://commons.wikimedia.org/wiki/Category:Villena_train_station) | 11 | CC BY-SA 4.0: 5 · CC BY-SA 3.0: 4 · Public domain: 2 |
| [Iglesia Arciprestal de Santiago](https://commons.wikimedia.org/wiki/Category:Iglesia_Arciprestal_de_Santiago) (+ Exterior, Interior subcats) | 4 at top level | Public domain: 2 · CC BY-SA 4.0: 2 |
| [Iglesia de Santa María (Villena)](https://commons.wikimedia.org/wiki/Category:Iglesia_de_Santa_Mar%C3%ADa_(Villena)) | 0 at top level, 2 subcats (Exterior, Interior) | subcategories not tallied |
| [Villena](https://commons.wikimedia.org/wiki/Category:Villena) | 11 files, 15 subcats | not tallied |

Most of this is CC BY-SA: fine as visual reference; if any image is used as a texture or traced closely, the result inherits attribution and share-alike duties.

**3D models — Sketchfab** (queried, `https://api.sketchfab.com/v3/search?type=models&q=…`): relevant models exist but **none carries a Creative Commons licence or is downloadable**. They are view-only references.

| Model | Author | Licence field | Downloadable |
|---|---|---|---|
| Castillo de la Atalaya (Villena, Alicante) s.XII — uid `b6ce596583554c139673239ae8c52738` | beliarkvirtual | none | no |
| Castillo Villena — `614286318d3540069f0232416bff89cb` | lolisan78 | none | no |
| Castillo de Villena, España en Minecraft — `6f6bc79feebe437483425a16e60274bb` | sminecrafting | none | no |
| Iglesia de Santiago, Villena — `6f6009c3e68f43b4973ab6bdaff469c6` | raultb99 | none | no |
| Iglesia de Santiago de Villena — `7f1c727d76554c71820e7597b046cd83` | raultb99 | none | no |

Catastro also exposes a façade photograph per building through `Building/document/documentLink`. It falls under the Catastro licence (section 2.6) and was not fetched.

---

## 5. How the two sources should be combined (recommendation)

| Layer | Source | Why |
|---|---|---|
| Building footprints and floor counts | Catastro `BuildingPart` | 6,813 parts in the AOI, all with floors; 0.1 m stated accuracy; native EPSG:25830 |
| Building use / age / condition | Catastro `Building` | `currentUse`, `dateOfConstruction`, `conditionOfConstruction` |
| Parcels, swimming pools | Catastro CP, `OtherConstruction` | optional detail |
| Streets, steps, squares, railway, city walls | OSM | detailed and named |
| Landmark names and identity | OSM + Wikidata | section 4 |
| Trees, land cover | neither is adequate | needs orthophoto/LiDAR or procedural fill |

---

## 6. Proposed AOI

### AOI A (recommended) — 1 km × 1 km on the 500 m grid

| | EPSG:25830 | |
|---|---|---|
| West / East | **685500** / **686500** | |
| South / North | **4277500** / **4278500** | |

| Corner | Lat | Lon |
|---|---|---|
| SW | 38.626643 | -0.869027 |
| SE | 38.626433 | -0.857547 |
| NE | 38.635439 | -0.857279 |
| NW | 38.635648 | -0.868761 |
| Centre (686000, 4278000) | 38.631041 | -0.863154 |

WGS84 envelope (for Overpass or any lat/lon-box API): **S 38.626433, W -0.869027, N 38.635648, E -0.857279**. The UTM square is rotated by about 1.3° relative to the lat/lon grid, so the envelope is slightly larger than the square; clip to the UTM bounds after download.

Computed with pyproj 3.8.0 (PROJ 9.8.1), `Transformer.from_crs("EPSG:25830","EPSG:4326", always_xy=True)`.

**Reasoning:**

- Bounds are multiples of 500 m, and the centre is the round point (686000, 4278000), which falls beside the Ayuntamiento and the Plaza de Santiago. Tile and chunk arithmetic stays trivial.
- **Inside:** castle (310 m from the east edge, so the whole hill and its eastern slope are in), Iglesia de Santiago, Iglesia de Santa María, Plaza Mayor, Ayuntamiento, Teatro Chapí, Paseo Chapí, MUVI, the museums, Ermita de San José, the visitor centre, and the railway station building.
- **Outside:** Plaza de Toros (435 m north of the north edge), Mercado Municipal, Iglesia María Auxiliadora, Castillo de Salvatierra (263 m east of the east edge).
- **Edge risk:** the station sits 79 m from the west edge, so the station building is in but the track fan to the west is cut.
- Content: 2,498 Catastro Buildings, 6,813 BuildingParts, 2,647 parcels, 7 pools. Floors per part: 1: 1,879 · 2: 2,069 · 3: 992 · 4: 531 · 5: 452 · 6: 249 · 7–14: 436 · 0: 205. So this is a varied skyline, not a uniform low-rise town.
- The southern ~350 m of the square lies south of every landmark in the table, so by landmark distribution it is supporting urban fabric, not old town.

### AOI B (alternative) — 1.0 km × 1.2 km, includes the bullring

| | EPSG:25830 |
|---|---|
| West / East | **685400** / **686400** |
| South / North | **4277800** / **4279000** |

| Corner | Lat | Lon |
|---|---|---|
| SW | 38.629365 | -0.870096 |
| SE | 38.629156 | -0.858615 |
| NE | 38.639962 | -0.858293 |
| NW | 38.640172 | -0.869776 |

WGS84 envelope: S 38.629156, W -0.870096, N 38.640172, E -0.858293. Snapped to 100 m.

**The trade-off is real:** the Plaza de Toros is 830 m north of the castle and 1,020 m north of Plaza Mayor, so no 1 km square can hold the bullring and the whole old town with a sensible margin. AOI B solves this by growing to 1.2 km² and moving north:

- Gains: Plaza de Toros, Iglesia María Auxiliadora, 100 m more of the railway to the west.
- Costs: 20 % more area and **37 % more buildings** (3,417 Buildings, 9,579 BuildingParts, 3,531 parcels). The south edge passes only 61 m south of Plaza del Rollo and about 110 m south of Plaza Mayor and Santa María, so the southern fringe of the old town may be clipped. The bullring centre is only 65 m from the north edge. The castle is 207 m from the east edge.
- Not on the 500 m grid.

**Recommendation:** ship AOI A for the first release. It is exactly the stated scope (≈1 km², castle + historic centre), sits on a round grid, and keeps every old-town landmark well inside. Treat the bullring as the first extension northwards (a second block, 685500–686500 × 4278500–4279000, would capture it and stay on the same grid).

---

## 7. Reproducing this research

Catastro's server certificate chains to the FNMT root ("AC RAIZ FNMT-RCM SERVIDORES SEGUROS"). The macOS system `curl` (SecureTransport) rejected it with `SSL certificate problem: unable to get local issuer certificate`; the Homebrew CA bundle accepts it. Certificate verification was **not** disabled:

```sh
CA=/opt/homebrew/etc/ca-certificates/cert.pem
UA="geodata-research-script/0.1"

# ATOM feeds
curl -sS --cacert $CA -A "$UA" -O https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/ES.SDGC.BU.atom.xml
curl -sS --cacert $CA -A "$UA" -O https://www.catastro.hacienda.gob.es/INSPIRE/buildings/03/ES.SDGC.bu.atom_03.xml
iconv -f ISO-8859-1 -t UTF-8 ES.SDGC.bu.atom_03.xml | grep -i -A12 villena

# datasets
for u in Buildings/03/03140-VILLENA/A.ES.SDGC.BU.03140.zip \
         CadastralParcels/03/03140-VILLENA/A.ES.SDGC.CP.03140.zip \
         Addresses/03/03140-VILLENA/A.ES.SDGC.AD.03140.zip; do
  curl -sS --cacert $CA -A "$UA" -O "https://www.catastro.hacienda.gob.es/INSPIRE/$u"
done
shasum -a 256 A.ES.SDGC.*.zip

# WFS / WMS
curl -sS -A "$UA" "http://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?service=WFS&version=2.0.0&request=GetCapabilities"
curl -sS -A "$UA" "http://ovc.catastro.meh.es/cartografia/INSPIRE/spadgcwms.aspx?service=WMS&request=GetCapabilities"

# INE codes
curl -sS -A "$UA" -O https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx

# Geofabrik size
curl -sS -I -L -A "$UA" https://download.geofabrik.de/europe/spain/valencia-latest.osm.pbf
```

GML inspection: Python stdlib `xml.etree.ElementTree.iterparse`, run as `python3 -I script.py file.gml`. The feature is the element at depth 3 (`FeatureCollection/member/Feature`); counts are per feature tag, fields are child paths with text or attributes. With GDAL installed the equivalent is `ogrinfo -so -al A.ES.SDGC.BU.03140.buildingpart.gml`.

Landmark query (Overpass):

```overpassql
[out:json][timeout:60];
(
  nwr["historic"](38.620,-0.885,38.650,-0.845);
  nwr["amenity"~"^(place_of_worship|townhall|theatre|arts_centre|library|marketplace)$"](38.620,-0.885,38.650,-0.845);
  nwr["tourism"~"^(museum|attraction|information|viewpoint)$"](38.620,-0.885,38.650,-0.845);
  nwr["leisure"~"^(bullring|stadium|park)$"]["name"](38.620,-0.885,38.650,-0.845);
  nwr["railway"="station"](38.600,-0.900,38.660,-0.830);
  nwr["place"="square"](38.620,-0.885,38.650,-0.845);
  nwr["building"~"^(church|cathedral|chapel|civic|public)$"](38.620,-0.885,38.650,-0.845);
  nwr["name"~"Chapí|Chapi|Plaza Mayor|Teatro|Castillo|Atalaya|Convento|Trinitarias|Palacio|Tercia|Orejón|Torre",i](38.620,-0.885,38.650,-0.845);
  nwr["wikidata"](38.620,-0.885,38.650,-0.845);
);
out tags center;
```

Wikidata and Commons:

```sh
curl -sS -A "$UA" -G https://www.wikidata.org/w/api.php --data-urlencode action=wbgetentities \
  --data-urlencode "ids=Q2986978|Q4882903|Q4882109|Q4163397|Q11697358|Q11704261|Q6377328|Q3329171" \
  --data-urlencode "props=claims|labels|sitelinks" --data-urlencode format=json

curl -sS -A "$UA" -G https://commons.wikimedia.org/w/api.php --data-urlencode action=query \
  --data-urlencode generator=categorymembers --data-urlencode "gcmtitle=Category:Castillo de la Atalaya" \
  --data-urlencode gcmtype=file --data-urlencode gcmlimit=200 --data-urlencode prop=imageinfo \
  --data-urlencode iiprop=extmetadata --data-urlencode iiextmetadatafilter=LicenseShortName --data-urlencode format=json
```

Coordinate transformation:

```python
from pyproj import Transformer   # pyproj 3.8.0, PROJ 9.8.1
to_utm = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
to_wgs = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
to_utm.transform(-0.860915, 38.631934)   # -> (686192.6, 4278103.7)
to_wgs.transform(685500, 4277500)        # -> (-0.869027, 38.626643)
```

---

## 8. Not verified / unresolved

1. **Whether a derived vector dataset may be redistributed under the Catastro licence.** The licence allows distribution only of information "transformada" into "una obra diferente". Rendered tiles clearly qualify. A clipped or reformatted GeoJSON of footprints probably does not; a simplified, merged, height-enriched model is a grey area. This is a legal judgement that was not resolved. Safe default: never commit Catastro-derived vectors, only the download script and the rendered output.
2. **The Resolución de 23 de marzo de 2011 itself (BOE text) was not located or read.** Its content is known only through the two Catastro PDFs that cite it. The clause the INSPIRE licence refers to ("número 5 del apartado primero") was not seen. The exact official attribution wording for INSPIRE data therefore rests on the ATOM `<rights>` text and on clause 12 of the SEC bulk-download licence-type.
3. **Ministry name in the attribution.** The ATOM feed says "Ministry of Finance"; the licence-type PDF says "Ministerio de Economía y Hacienda", which is an older name. Which name Catastro expects today was not confirmed. Naming "Dirección General del Catastro" is the stable part.
4. **The exact OSM credit string** (commonly "© OpenStreetMap contributors") was not seen verbatim today; the pages read only confirm that attribution must be to "OpenStreetMap" and must make the ODbL clear. ODbL clauses were read as excerpts, not full text.
5. **`numberMatched="26302"` in the CadastralParcel GML header versus 22,480 `cp:CadastralParcel` features actually present** (and 814 versus 695 for zoning). The 814 equals the number of surface patches in the zoning file, so the header may count surfaces, but for parcels the file has 22,480 surfaces, so the discrepancy is unexplained.
6. **BuildingPart floors of 0 (633 parts municipality-wide, 205 in AOI A).** Their meaning (ruins, canopies, below-ground-only parts, courtyards) was not investigated. They need a rule before extrusion.
7. **Storey height.** The data has no above-ground height in metres. The only hint is Catastro's nominal 3 m per below-ground floor. Any metres-per-floor figure for extrusion is an assumption to be calibrated against LiDAR.
8. **Extent of the historic quarter.** No official boundary of the protected "conjunto histórico" was obtained, so "the old town falls inside AOI A" is judged from landmark positions only, and the claim that AOI B may clip its southern fringe is likewise an inference.
9. **Teatro Chapí position** comes from Wikidata alone (not mapped in OSM); the building footprint was not identified with certainty. Q117786096 appears to duplicate Q11704261; not confirmed.
10. **Plaza de Toros footprint size** was not measured, so the 65 m margin in AOI B refers to its centre, not its outer wall.
11. **Wikidata/OSM coordinates are community data**, not surveyed positions. Only the castle keep was cross-checked against Catastro (agreement under 1 m).
12. **WFS endpoints for CP and AD, and the WMS `GetMap` request**, were not exercised; only BU WFS GetCapabilities/GetFeature and WMS GetCapabilities were.
13. **Commons subcategories** (church exteriors/interiors, castle subcats) and the 15 subcategories of `Category:Villena` were listed but their files' licences were not tallied. Per-file licences must be checked before any individual image is reused.
14. **Sketchfab** was searched with two queries only ("villena", "castillo atalaya villena"); other platforms were not searched. "No CC models" is a statement about those results.
15. **The INE = Catastro code equality** was verified for Villena only.
16. **Update cadence**: Catastro says twice a year; the next refresh date after 2026-08-21 is unknown.
