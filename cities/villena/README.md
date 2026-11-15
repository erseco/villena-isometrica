# Villena

`city.json` is the hand-written configuration of the first city. Sources for every value:

| Value | Source |
|---|---|
| AOI `685500, 4277500 – 686500, 4278500` (EPSG:25830), 1 km² | `docs/research/02-cadastre-osm-aoi.md` §4 (option A). Contains the castle, both churches, Plaza Mayor, town hall, Teatro Chapí and the railway station. The Plaza de Toros is 435 m north of the edge and is out of scope for v0.1.0. |
| `marginM` 120 | Context so that buildings and terrain in front of the AOI edge that project into the image are present (a 40 m object shifts ~69 m at 30° pitch). |
| `H0` 500 | A round local height origin for numerical convenience. **Not a measured elevation.** |
| Camera heading 45°, pitch 30° | `docs/decisions/0003-projection-and-camera.md`. |
| 8 px/m | Same ADR; gives a master image of roughly 11 300 × 6 500 px. Tunable until the first release. |
| Attribution strings | `docs/LICENSING.md`. |

`datasets.json` (dataset manifest with sizes and checksums) is produced by WP01
(`prompts/01-data-research.md`). `tiles.lock.json` is produced at release time by WP12.

Raw data goes to `data/raw/<dataset-id>/` and is never committed (see `data/README.md`).
