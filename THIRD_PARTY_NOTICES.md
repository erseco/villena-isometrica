# Third-party notices

Maintained by the integrator from the dependency lists in work-package handoffs.

## Data

Rendered tiles are derived from the following open data (terms: `docs/LICENSING.md`):

- Instituto Geográfico Nacional / CNIG — MDT50cm and MDS50cm, 3rd coverage. CC BY 4.0.
  "Obra derivada de MDT50cm-cob3 2022-2025 y MDS50cm-cob3 2022-2025 CC-BY 4.0 scne.es".
- Dirección General del Catastro — INSPIRE Buildings, Villena (03140). Source cited with the
  date of access recorded in `cities/villena/datasets.json`. This project is not cadastral
  cartography and does not replace any service of the Dirección General del Catastro.
- OpenStreetMap contributors — ODbL 1.0. https://www.openstreetmap.org/copyright

## Software

No third-party code is vendored in this repository. Runtime and build dependencies are listed
here, with licences, as packages are added:

| Package | Used by | Licence |
|---|---|---|
| openseadragon 6.1.1 | viewer (runtime, bundled) | BSD-3-Clause |
| ajv 8.20.0 (+ fast-deep-equal, json-schema-traverse, require-from-string) | renderer (runtime) | MIT |
| fast-uri 3.1.9 | renderer (runtime, via ajv) | BSD-3-Clause |
| vite 8.3.8 | viewer (build) | MIT |
| typescript 7.0.2 | viewer, renderer (dev) | Apache-2.0 |
| @playwright/test 1.65.1 | viewer (dev) | Apache-2.0 |
| @biomejs/biome 2.6.8 | renderer (dev) | MIT OR Apache-2.0 |
| @types/bun 1.4.4 (+ bun-types, @types/node, undici-types) | viewer, renderer (dev) | MIT |
| Python packages pinned in `pipeline/uv.lock` | pipeline | see the lock file; transitive licences not yet audited (WP11) |

## Prior art

Inspired by Isometric NYC (Andy Coenen; code MIT) and Tiny València. No code, artwork,
prompts, datasets or model weights from either project are used.
