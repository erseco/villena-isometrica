# Licensing

What we may do with each input, what we must credit, and under which terms the project's own
work is offered. This is an engineering summary of the licence texts read on 2026-11-15
(`docs/research/01`, `02`, `03`, `05`), not legal advice. Where a text was not read in full or
is silent, it says so.

## Project licences (proposed — owner to confirm)

| What | Licence |
|---|---|
| Source code | MIT (`LICENSE`) |
| Original artwork: palette, sprites, rendered tiles, screenshots | CC BY 4.0, with the data credits below preserved |
| Documentation | CC BY 4.0 |

Rendered tiles are derived from the datasets below, so their credits must always accompany
the tiles (the viewer shows them permanently; the release notes repeat them).

## Data licence matrix

| Source | Licence | We may | We must | We must not |
|---|---|---|---|---|
| **IGN / CNIG** (MDT, MDS, PNOA, LiDAR) | CC BY 4.0 under Orden FOM/2807/2015 | use, transform, publish derivatives, redistribute raw files, commercial use | credit with the official formula, e.g. `Obra derivada de MDT50cm-cob3 2022-2025 CC-BY 4.0 scne.es` (link `scne.es` → https://www.scne.es/) | imply endorsement |
| **Catastro INSPIRE** | Catastro's own terms (Resolución de 23 de marzo de 2011 and the INSPIRE service licence) | transform and build new products, including commercial | cite the Dirección General del Catastro as source and state the date of access | redistribute the raw downloaded data; call the product "cartografía catastral" / "información catastral" or anything suggesting it replaces Catastro's services; alter the meaning of the information |
| **OpenStreetMap** | ODbL 1.0 | use; publish rendered images ("Produced Work") under any licence | credit "OpenStreetMap" with a link to https://www.openstreetmap.org/copyright making the ODbL clear | distribute a database derived from OSM under anything but ODbL; hide the credit |

Consequences for this repository:

1. **Published site** contains only rendered tiles, a manifest, a POI list and a coarse
   height grid — produced works and IGN-derived data. Allowed, with credits.
2. **Raw data is never committed or published.** For Catastro this is a licence requirement;
   for the rest it is a size rule.
3. **Scene files (derived vectors) are not published.** Whether Catastro-derived vectors may
   be redistributed is unresolved (WP01). Until resolved they stay local, like raw data.
4. **OSM-derived and Catastro-derived data stay in separate layers/files** and are never
   merged into one distributed database (ODbL share-alike would then apply to the whole).
   The POI list is OSM-derived: it is published and is offered under ODbL.
5. The ministry name in the Catastro citation differs between Catastro's own documents;
   "Dirección General del Catastro" is the stable part and is what we cite until WP01
   confirms the exact wording.

### Attribution shown in the viewer (from `cities/villena/city.json`)

- `Obra derivada de MDT50cm-cob3 2022-2025 y MDS50cm-cob3 2022-2025 CC-BY 4.0 scne.es`
- `Fuente de edificios: Dirección General del Catastro` + date of access (the About dialog
  states the date recorded in the dataset manifest)
- `© OpenStreetMap contributors (ODbL)`

In fallback mode (MDT05 terrain) the first line names that product instead. If an input
changes, the attribution changes with it — it is data, not decoration.

## Forbidden sources

- Google Photorealistic 3D Tiles, Google Earth, Google Maps and Street View imagery or
  geometry: no storing, no derived content. Not for tiles, not for training, not as
  "reference" traced into geometry, not as QA evidence in the repository.
- Any imagery, model or dataset without a recorded licence that permits the intended use.

## Prior art

- **Isometric NYC**: code is MIT (© 2025 Andy Coenen). We reuse none of it today; if a module
  is ever reused, its notice goes into `THIRD_PARTY_NOTICES.md`. Its tiles, datasets, prompts,
  reference images and LoRA weights have no licence we could confirm: treated as all rights
  reserved. Its render path depends on Google 3D Tiles and is not reproduced.
- **Tiny València**: no repository or licence published. Nothing is reused.
- Site design, branding and look of either project are not imitated.

## Landmark reference images

Wikimedia Commons photographs (mostly CC BY-SA or public domain) may be **looked at** to
judge whether a rendered landmark is recognisable, and linked from QA reports. They are not
copied into the repository, not traced, and not used as textures or model inputs — any of
those would bring attribution and share-alike duties and needs an architect decision first.

## Software and models

- Dependencies: permissive licences only (MIT, BSD, Apache-2.0, ISC, MPL-2.0 for unmodified
  use). Each work package reports its dependencies; the integrator maintains
  `THIRD_PARTY_NOTICES.md`.
- Image models (optional track): only weights whose licence allows publishing outputs under an
  open licence. Checked 2026-11-15: `Qwen/Qwen-Image-Edit-2511` and
  `black-forest-labs/FLUX.2-klein-4B` are Apache-2.0. Excluded: Qwen-Image-2.1 (research
  licence), FLUX.2 dev / klein 9B and FLUX.1 Kontext dev (non-commercial). Re-verify on the
  day of use; record model id and revision in every job file.

## Not verified

- The BOE text of the Resolución de 23 de marzo de 2011 and Orden FOM/2807/2015 were not read
  in full; the summaries rest on Catastro's and CNIG's own licence pages.
- OSMF and ODbL pages were read as excerpts.
- Whether CC BY 4.0 data may be used to train or condition image models is not addressed by
  the IGN terms; nothing forbids it.
