# Handoff — WP01 Geographic data verification, dataset manifest and licensing

| Field | Value |
|---|---|
| Task ID | WP01 |
| Date (UTC) | 2026-11-15 |
| Provider / client | Google Antigravity CLI |
| Model and effort actually used | Gemini 3.8 Flash (research mode: high) |
| Branch | `agent/wp01-data-research` |
| Base commit | `ba8ba0c` |
| Head commit | `eeee444` |
| Status | READY FOR REVIEW |

## Changed files

- `cities/villena/datasets.json` — verified dataset manifest adhering to `dataset-manifest.schema.json` with pinned checksums, sizes, URLs, and licenses.
- `cities/villena/ACQUISITION.md` — human-readable, copy-pasteable guide for automated downloads and manual CNIG Centro de Descargas steps.
- `cities/villena/poi-selection.json` — 25 curated POIs for search and display, strictly within the AOI, each with verifiable `source.ref`.
- `cities/villena/landmark-references.md` — photographic references from Wikimedia Commons for 7 major landmarks with author, license, and architectural notes.
- `docs/research/08-wp01-data-verification.md` — complete verification report covering all data sources, open questions, and legal analyses.
- `docs/DATA_SOURCES.md` — updated open questions section with verified facts and technical parameters.
- `docs/LICENSING.md` — updated data licensing matrix, ministry name, and derived vector redistribution policy.
- `docs/handoffs/WP01-data-research.md` — this handoff document.

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `uv run scripts/validate_contracts.py cities/villena/datasets.json` | pass | validates against `dataset-manifest.schema.json` |
| `python3 -c "import json;d=json.load(open('cities/villena/poi-selection.json'));print(len(d),'POIs');assert all(-0.869027<=p['lon']<=-0.857279 and 38.626433<=p['lat']<=38.635648 for p in d)"` | pass | 25 POIs, all strictly within the AOI envelope |
| `shasum -a 256 data/raw/*/*` | pass | all downloaded raw files match `datasets.json` checksums |
| `make check` | pass | schemas, fixtures, and city configurations pass |
| `git status --short` | pass | only allowed files present; no raw data committed |

## Generated artifacts

Local probe downloads in `data/raw/` (git-ignored):
- `data/raw/catastro-buildings/A.ES.SDGC.BU.03140.zip`: `3,971,442` bytes, SHA-256 `38588fba7a3fd15bcff301096639720fd79fb37edfc975cda517a945024f1e17`
- `data/raw/ign-mdt05/mdt05-aoi-margin.asc`: `493,615` bytes, SHA-256 `ae3fb9adfdebb9ecb332ec77598a887967cbe45f3e427d831d0a0ef8580136a4`
- `data/raw/osm/osm-aoi-margin.json`: `11,046,725` bytes, SHA-256 `7e5a4e82561b24ad9693006585ea0568b0289a4e25ca90b9e9e4a8f1029e01a4`

## Decisions and assumptions

1. **Elevation Sheet Coverage:** Proved from IGN official auxiliary spatial metadata that sheet `0845-8-2` spans E 683,060.0–686,850.0 and N 4,277,210.0–4,279,710.0 (EPSG:25830). The AOI plus 120 m margin (E 685,380–686,620, N 4,277,380–4,278,620) is entirely within this single sheet. No secondary or adjacent elevation sheets are needed.
2. **Elevation Raster Alignment:** Verified that MDT50cm and MDS50cm 3rd coverage rasters share identical dimensions (7,580 × 5,000 pixels) and 0.5 m cell grid alignment.
3. **Catastro Derived Vectors Redistribution:** Interpreted under Resolución de 23 de marzo de 2011 and Art. 21 TRLPI. Rendered static tiles and images are authorized transformed works ("obra diferente"). Distributing derived vector footprints (GeoJSON) is ambiguous under Catastro's prohibition against distributing original data; therefore, scene vectors remain internal pipeline artifacts and are not published as release assets in v0.1.0.
4. **Catastro Ministry Citation:** The governing ministry is the **Ministerio de Hacienda** (formerly Ministerio de Economía y Hacienda). Recommended attribution is: `Fuente de edificios: Dirección General del Catastro, Ministerio de Hacienda (fecha de acceso: YYYY-MM-DD)`.
5. **ODbL Produced Works:** Confirmed that rendered map tiles and static images are Produced Works under ODbL 4.3–4.5 and can be offered under the project's CC BY 4.0 license while maintaining OpenStreetMap credit.

## Contract change requests

None. All schemas and contracts (`dataset-manifest.schema.json`, `city-config.schema.json`, `scene.md`) were sufficient without modification.

## Known problems and unresolved issues

1. Internal pixel values and metadata tags inside the manual COG files (`MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` and `MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif`) cannot be verified until downloaded by the owner.
2. The 3rd coverage rasters are currently V1 (provisional), indicating that IGN may issue a revised V2 with improved classifications in the future.

## Human approvals needed

The owner must manually download the two 0.5 m elevation sheets from the CNIG Centro de Descargas following `cities/villena/ACQUISITION.md` section 3:
- `MDT50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` (secuencial 12759170, ~61 MB) -> save to `data/raw/ign-mdt50cm/`
- `MDS50CM-ETRS89-H30-0845-8-2-COB3-V1.tif` (secuencial 13118318, ~114 MB) -> save to `data/raw/ign-mds50cm/`

## Recommended next task

Proceed with Gate G1 (contracts freeze by the architect following WP02 review) or run **WP07 (tooling, CI/CD)** and **WP02 (architecture review)** in parallel.
