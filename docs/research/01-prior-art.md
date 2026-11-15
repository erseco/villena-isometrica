# 01 — Prior art: Isometric NYC and Tiny València

**Verification date: 2026-11-15.** Everything below was read on that date.

Conventions:

- `repo:` paths are relative to a shallow clone of <https://github.com/cannoneyed/isometric-nyc> at commit `008446357ec67512c4329d25edefb6c508c7b24d` (committed 2026-01-28; GitHub reports last push 2026-02-06).
- "Article" means <https://cannoneyed.com/projects/isometric-nyc>. It was read through an automated page summariser, so quoted fragments are the summariser's extraction, not a manual transcription. Re-check a quote before publishing it.
- External content was read only; no code from it was executed.

---

## 1. Isometric NYC repository: licence, layout, languages, dependencies

### Licence

- `repo:LICENSE` is the standard MIT text, "Copyright (c) 2025 Andy Coenen". SPDX: `MIT`.
- `repo:pyproject.toml` declares `license = "MIT"`. GitHub's API reports `mit` for the repo.
- There is exactly one licence file in the tree. A search for `*licen*`, `NOTICE*` and `COPYING*` finds only `repo:LICENSE`.
- **No separate licence exists for artwork, tiles, prompts, datasets or model weights.** None of the README, `docs/data.md`, `docs/models.md`, `oxen/README.md` or `inference/README.md` states one. The article makes no licence statement either.
- The generated tiles, training datasets and LoRA weights are not in the git repo. They live on Oxen.ai (`cannoneyed/isometric-nyc-tiles`, `cannoneyed/isometric-nyc`, `cannoneyed/isometric-nyc-v2`; see `repo:docs/data.md`, `repo:docs/models.md`, `repo:inference/README.md`). The MIT file in the git repo cannot be assumed to cover them. The licence shown on those Oxen pages could not be read (see section 6).
- Some non-code assets are inside the git repo and are nominally under its MIT file, but with doubtful provenance: `repo:references/simcity.jpg` (by its name, a third-party game screenshot), `repo:references/style_*.png`, `repo:references/trees/`, `repo:references/water/`.

### Layout

From `repo:README.md` and the file tree:

| Path | Content |
|---|---|
| `src/isometric_nyc/` | Python core: planning, rendering, generation, export |
| `src/isometric_nyc/generation/` | Generation web app, planner, infill templates, DZI export, postprocessing |
| `src/isometric_nyc/synthetic_data/` | Scripts that build the fine-tuning datasets |
| `src/isometric_nyc/oxen_sync/` | Import and export between the SQLite database and Oxen |
| `src/web_render/` | Three.js page that renders Google 3D Tiles with an orthographic camera |
| `src/app/` | Public viewer (React, OpenSeadragon) plus `deploy.py` and a Cloudflare Worker |
| `src/layers/` | Work-in-progress layers: water shader, dark mode, snow |
| `inference/` | Modal server for the fine-tuned Qwen Image Edit model |
| `synthetic_data/` | Dataset CSVs and per-tile `view.json` files |
| `tasks/` | 51 numbered task files written for coding agents |
| `docs/` | setup, app, data, models, generation, deployment, bounds, water shader |
| `tests/` | Two test files, both for the planners |

### Languages

GitHub language sizes in bytes: Python 1,458,734; JavaScript 130,541; TypeScript 117,990; CSS 64,276; HTML 22,267 (`gh repo view cannoneyed/isometric-nyc --json languages`).

The README states the code was written entirely by coding agents and that the author has "looked at less than 1% of it" (`repo:README.md`). Treat code quality accordingly.

### Key dependencies

- Python 3.12+, managed with `uv` (`repo:pyproject.toml`): `pyvips`, `pillow`, `opencv-python`, `numpy`, `shapely`, `pyproj`, `playwright`, `pyvista`, `unfake`, `pmtiles`, `google-genai`, `googlemaps`, `oxenai`, `modal`, `diffusers`, `torch`, `flask`, `fastapi`, `marimo`, `sodapy`, `psycopg2-binary`, `contextily`.
- Viewer (`repo:src/app/package.json`): `openseadragon` ^5.0.1, `react` ^18.3.1, `lucide-react`, Vite 6, TypeScript, Bun.
- Renderer (`repo:src/web_render/package.json`): `three` ^0.181.2, `3d-tiles-renderer` ^0.4.18.

---

## 2. Isometric NYC end-to-end pipeline

### Data sources

- **Google Photorealistic 3D Tiles are the production source.** `repo:src/web_render/main.js` registers `GoogleCloudAuthPlugin` with `VITE_GOOGLE_TILES_API_KEY` (lines 9, 26, 151). `repo:.env.example` requires `GOOGLE_TILES_API_KEY` and `GOOGLE_MAPS_API_KEY`. The article calls the Google Maps 3D tiles API "basically exactly what I needed".
- **Legacy "whitebox" path, abandoned.** City building geometry rendered over satellite imagery. `repo:geo_data/README.md` names the NYC Department of City Planning "NYC 3D Model by Community District" and calls this path "a legacy part of the application". The article also mentions CityGML sources and 3DCityDB; the repo has `src/isometric_nyc/citydb/` and `src/isometric_nyc/whitebox.py`. The article says this path was dropped because the geometry did not match the imagery well enough.
- **Other Google imagery.** `repo:src/isometric_nyc/data/google_maps.py` calls the Google Static Maps API with `maptype=satellite` and the Street View API.
- **NYC Open Data.** `repo:src/isometric_nyc/data/nyc_opendata.py` queries Building Footprints, dataset `5zhs-2jue`, via Socrata.

**Restricted-source warning.** Google's Map Tiles API policy says "you must not pre-fetch, index, store, or cache any Content except under the limited conditions stated in the terms", "Don't create content based on Google Maps Content", and, for Photorealistic 3D Tiles, that 3D objects must not be "extracted, traced, or otherwise derived by hand or machine" from them (<https://developers.google.com/maps/documentation/tile/policies>). The Isometric NYC database stores a rendered Google image per quadrant (the `render` BLOB column in `repo:generations/README.md`) and derives all artwork from those renders. Whether that complies is the NYC author's concern. For us it means this data path is not available to an open-data project.

### Geometry render

- Three.js with `3d-tiles-renderer` and an `OrthographicCamera` (`repo:src/web_render/main.js`, lines 18, 137).
- Camera in the shipped config: azimuth −15°, elevation −45° (`repo:generations/tiny-nyc/generation_config.json`, `repo:src/view.json`).
- Tile: 1024×1024 px covering `view_height_meters: 300`, which is about 0.29 m per pixel (`repo:generations/tiny-nyc/generation_config.json`).
- `tile_step: 0.5`: adjacent tiles overlap by half. The storage unit is therefore the 512×512 px "quadrant" (`repo:src/isometric_nyc/generation/shared.py` lines 590–596, `repo:src/isometric_nyc/generation/infill_template.py`).
- Renders are captured by driving the page in headless Chromium with Playwright, behind a persistent render queue (`repo:src/isometric_nyc/generation/web_renderer.py`).
- State is a SQLite database per map with one row per quadrant: `render` PNG, `generation` PNG, and `flagged`, `starred`, `is_water`, `notes` columns, plus a `generation_queue` table (`repo:generations/README.md`).

### Image models

- **Bootstrap.** Nano Banana (Gemini image model) produced the first render-to-pixel-art pairs. `repo:src/isometric_nyc/tile_generation/generate_tile_0*.py` use `gemini-3-pro-image-preview`; `repo:src/notebooks/nano-banana.py` is the notebook named in `repo:docs/models.md`. The article reports consistency of roughly "at best 50/50" and calls it "slow and quite expensive".
- **Production.** `Qwen/Image-Edit` fine-tuned on Oxen.ai, distributed as LoRA adapters (`repo:docs/models.md`; "Download LoRA adapter weights from Oxen" in `repo:inference/README.md`). Three named fine-tunes cover most tiles: `cannoneyed-rural-rose-dingo` (with water), `cannoneyed-quiet-green-lamprey` (more trees) and `cannoneyed-dark-copper-flea` (v2, more terrain; the default).
- **Training data.** Synthetic pairs built from the Nano Banana outputs (`repo:docs/models.md`, `repo:src/isometric_nyc/synthetic_data/`, `repo:synthetic_data/datasets/`). The article gives about 40 input/output pairs for the first fine-tune.
- **Inference settings.** 14 steps, `true_cfg_scale` 2.0, `guidance_scale` 3.0 (`repo:inference/README.md`).

### Seam consistency: the "omni" infill strategy

- The model is trained on an infill task. The input is a 1024×1024 image in which part is already-generated pixel art and a rectangle is the raw 3D render; the model repaints the rectangle to continue its surroundings (`repo:docs/models.md`).
- The infill region is at most 50% of the template and is positioned to maximise context (`repo:src/isometric_nyc/generation/infill_template.py`).
- Placement rules, from `repo:src/isometric_nyc/generation/make_rectangle_plan.py` and `repo:docs/generation.md`:
  - a 2×2 block may be generated only if no side touches an already generated quadrant;
  - a 2×1 or 1×2 block must touch generated quadrants along one long side only;
  - a 1×1 is ideally generated when the other three quadrants of its 2×2 block exist.
- Planning order: all possible 2×2 blocks first, then 2×1 and 1×2 strips, then single quadrants (`repo:src/isometric_nyc/generation/make_rectangle_plan.py`; a strip variant is in `make_strip_plan.py`; tests are in `repo:tests/`).

### QA and retry

- Review is manual, in a bespoke Flask app with tools to flag, star, delete, regenerate, add a positive or negative prompt, fix or fill water by colour pick, and export or import a rectangle as PNG for hand editing (`repo:docs/generation.md`).
- Automated review did not work. `repo:src/isometric_nyc/tile_generation/generation_checker.py` uses `gemini-3-pro-preview`, and the article reports it could not reliably spot seams or bad trees.
- The retry logic in code covers transient download errors: 3 attempts, 10 s apart (`repo:src/isometric_nyc/generation/automatic_generation.py`, lines 664–704). No automatic quality-based retry was found.
- Water is detected by exact colour `#4A6372` (`repo:src/isometric_nyc/generation/detect_water_tiles.py`).
- Postprocessing uses the `unfake` library: grid snap, dominant-colour downscale with pixel size 2, morphological cleanup, and quantisation to a fixed palette shared by the whole city (`repo:src/isometric_nyc/generation/pixel_art_postprocess.py`).

### Tile storage and export

- First attempt was PMTiles with a custom OpenSeadragon tile source. It was dropped for performance and code size; the research note is dated 2026-01-20 (`repo:tasks/047_dzi_or_other_image_type.md`, `repo:tasks/028_pmtiles.md`).
- Final format is **DZI (Deep Zoom Image)**, produced with libvips `dzsave()` through `pyvips`: `tile_size=512`, `overlap=0`, `depth="onetile"`, WebP by default with PNG optional (`repo:src/isometric_nyc/generation/export_dzi.py`, lines 63 and 721–726).
- WebP quality is inconsistent in the source: the module docstring and CLI help say 95, a function default says 85 (`export_dzi.py` lines 22, 642, 1034).
- Output is `tiles.dzi`, a `tiles_metadata.json` sidecar and `tiles_files/<level>/<col>_<row>.webp`; the documented example has levels 9 to 17 (`repo:docs/app.md`).
- Scale: about 32k quadrants, about 10 GB of raw PNG on Oxen, and "~60,000+ WebP files" in the pyramid (`repo:docs/data.md`, `repo:oxen/README.md`, `repo:docs/deployment.md`). The article had estimated about 40k tiles.

### Viewer

- React, TypeScript, Vite and OpenSeadragon 5 (`repo:docs/app.md`, `repo:src/app/package.json`). No deck.gl.
- `imageSmoothingEnabled: false` keeps pixels crisp; `crossOriginPolicy: "Anonymous"` (`repo:src/app/src/components/IsometricMap.tsx`, lines 201–237).
- Extras: scanline overlay and a WebGL water shader (`repo:src/app/src/components/`, `repo:docs/water_shader.md`).

### Hosting and deployment

- Static HTML, JS and CSS are pushed to a `gh-pages` branch. Tiles are **not** on GitHub Pages; they are on Cloudflare R2, uploaded with `rclone` (`repo:docs/deployment.md`, `repo:src/app/deploy.py`).
- A Cloudflare Worker in front of R2 adds `Cache-Control: public, max-age=31536000, immutable` and CORS headers (`repo:src/app/worker/src/index.ts`). The tile host is `https://isometric-nyc-tiles.cannoneyed.com` (`repo:src/app/src/config.ts`).
- <https://isometric.nyc/> responds with `server: cloudflare`.

### Costs, time and failure modes reported by the author

All from the article:

- First fine-tune: about 4 hours and about 12 USD on Oxen.
- Oxen-hosted inference was "rather expensive and rather slow". The author moved the weights to a rented Lambda VM with an H100: "less than $3 an hour and more than 200 generations/hour". The repo documents Modal instead (`repo:inference/README.md`).
- No total cost and no total elapsed time are given.
- Failure modes: water (the models could not reliably generate it), trees (described as a pathological case), seams, and terrain. Many edge cases needed manual fixes and purpose-built "micro-tools". The author notes that the last 10% of the work took 90% of the time.

---

## 3. What is reusable, and what must not be copied

### Reusable under MIT

Any copied code must keep the copyright and permission notice. These are the parts worth considering; most are small enough that reimplementing the idea is cleaner than importing agent-written code.

| Item | Source | Note |
|---|---|---|
| Quadrant model: 1024 px tile, 0.5 step, 512 px storage unit | `generation/shared.py`, `generation/infill_template.py` | An idea, not code. Only needed if we add AI tiles |
| Generation-order planner and its tests | `generation/make_rectangle_plan.py`, `make_strip_plan.py`, `tests/` | Self-contained and tested. Only needed for AI tiles |
| DZI export via `pyvips.dzsave` | `generation/export_dzi.py` | The core is one call: `tile_size=512, overlap=0, depth="onetile"`, WebP suffix. Reimplement in a few lines |
| OpenSeadragon configuration | `src/app/src/components/IsometricMap.tsx` | `imageSmoothingEnabled: false`. We do not need React for this |
| Fixed shared palette plus `unfake` cleanup | `generation/pixel_art_postprocess.py` | A shared palette is equally useful for a procedural renderer |
| SQLite per-quadrant state with flag and star columns | `generations/README.md` | Useful pattern if we add a manual QA pass |
| Orthographic camera parameters as a starting point | `generation_config.json` | Azimuth −15°, elevation −45°, 300 m per 1024 px |

Their GitHub Pages plus R2 split exists because of their tile count. It is a pattern to adopt only if our tiles outgrow GitHub Pages.

### Must not be copied

- **Generated tiles and artwork** (Oxen `isometric-nyc-tiles`, and anything served from the R2 host). No licence was found, and they derive from Google imagery.
- **LoRA weights and fine-tunes** (Oxen `cannoneyed/isometric-nyc*`). No licence was found; they were trained on Google-derived renders and Nano Banana outputs, and the Qwen base model has its own terms.
- **Training datasets** (`repo:synthetic_data/` CSVs and the Oxen data they point to). Same provenance problem.
- **Reference images** in `repo:references/`, in particular `simcity.jpg`.
- **Prompts** (`repo:src/isometric_nyc/generation/app_config.json`, the prompt in `repo:inference/README.md`, `synthetic_data/**/prompt.txt`). They are technically MIT, but they name "isometric nyc pixel art" and only work with those weights. Write our own.
- **The Google 3D Tiles render path** (`repo:src/web_render/`). The code is MIT; the data it needs is not usable by us (section 2).
- **Site design, name and branding** of isometric.nyc and tinyvalencia.com.

---

## 4. Tiny València

Little is public. There is no write-up beyond the site's own About panel, no repository was found, and the author did not describe the build in the Hacker News thread.

- **Author.** Identified only by the handle `@13ug1mb` on X (<https://x.com/13ug1mb>), linked from <https://tinyvalencia.com/>. The Hacker News submitter is `leugim`, who writes "13ug1mb is my twitter" (<https://news.ycombinator.com/item?id=50441518>, "Show HN: Valencia, Spain in Sim City/Isometric View", 261 points when read, posted about four days before the verification date). No real name was found.
- **Technique**, from the site's About text: "Real 3D city data is rendered from a fixed isometric camera. An image model trained on a hand-picked pixel-art style then repaints it, tile by tile, each tile continuing its painted neighbours so the city stays seamless." This is the same family of approach as Isometric NYC, which the site credits as inspiration. The image model is not named. In the HN thread the author answers a question about an odd truck with "Hallucination! I fixed some but clearly not all."
- **Data sources**, from the site's credits: buildings © Dirección General del Catastro; aerial photo and terrain © IGN (PNOA, MDT05), CC BY 4.0; roads, boundary, coast, metro lines and search © OpenStreetMap contributors, ODbL; metro timetable from FGV (Metrovalencia); "3D reference: Google Photorealistic 3D Tiles via Cesium ion". The site also says a few exclaves are unpainted "where there's no 3D imagery to paint from", which indicates the painting depends on the Google 3D imagery.
- **Stack**, observed in the page source on the verification date:
  - OpenSeadragon 4.1.0 loaded from cdnjs.
  - Plain JavaScript files with no visible framework: `app.js`, `world.js`, `metro.js`, `trains.js`, `planes.js`, `boats.js`, `game.js`, `i18n.js`.
  - Interface in English, Spanish and Valencian.
  - Served through Cloudflare (`server: cloudflare`); self-hosted analytics at `stats.13ug1mb.com`.
  - `tiles.json` manifest: image 198,330 × 79,044 px, top level 18, 19 levels, 5,283 tiles listed, `km2: 119.9`, `updated: 2026-11-13`. `app.js` contains `tileSize: 1024` and `tileOverlap: 0`.
  - The manifest carries polynomial coefficients for converting between latitude/longitude and pixels, used for search and for the moving metro, train, plane and boat overlays.
- **Costs.** Only "Painting it takes rented GPUs, and keeping it online a server". The site is funded through Patreon (<https://www.patreon.com/cw/TinyValencia>).
- **Licence.** None stated for the artwork or the code. The footer reads "Data © OpenStreetMap, Catastro, IGN, Google". Treat everything as all rights reserved.

What Tiny València does show: Catastro, IGN PNOA and MDT05, and OpenStreetMap are a workable Spanish data stack for a city map of this kind. All of them cover Villena.

---

## 5. Lessons for a ~1 km² first release with a procedural baseline

1. **Do not use Google 3D Tiles.** Both projects depend on them and Google's policy forbids storing content and creating derived content (section 2). Our geometry has to come from open data. Tiny València's credits point to the obvious stack: Catastro buildings, IGN MDT05 terrain, PNOA orthophoto, OpenStreetMap.
2. **The procedural baseline avoids the hardest problem.** Seams, hallucinations, water and trees are artefacts of image-model repainting, and they absorbed most of the NYC effort (article). A deterministic renderer has none of them. Make it good before spending anything on AI tiles.
3. **Use DZI, WebP and OpenSeadragon.** Both projects ended there; NYC tried PMTiles first and reverted (`repo:tasks/047_dzi_or_other_image_type.md`). `pyvips.dzsave` produces the pyramid in one call and the output is plain static files.
4. **GitHub Pages can hold a 1 km² release.** At NYC's scale of about 0.29 m per pixel, 1 km² is on the order of 3,400 × 3,400 px before isometric foreshortening and margins. That is about 50 tiles of 512 px at full resolution and roughly 70 across the pyramid. NYC needed R2 because it has more than 60,000 files. This estimate is ours, not measured.
5. **Fix the camera and the scale once.** Azimuth, elevation, metres per pixel and grid origin are recorded in one config file in NYC (`generation_config.json`). Changing them later invalidates every tile. In the HN thread the Tiny València author says a change of orientation "will take some hours".
6. **Keep a single shared palette.** NYC quantises all tiles to one city-wide palette (`pixel_art_postprocess.py`). For a procedural renderer this is the cheapest way to get a consistent pixel-art look.
7. **Store a pixel-to-coordinate mapping with the tiles.** NYC writes `tiles_metadata.json`; Tiny València ships projection coefficients in `tiles.json`. Search, deep links and overlays all depend on it.
8. **If AI tiles are added later, copy the method, not the assets.** Half-overlapping tiles, infill conditioned on already painted neighbours, a fixed generation order, a per-quadrant database and a manual review tool. Budget for manual review: automated checking failed for NYC, and both authors fixed errors by hand.
9. **Keep the procedural render as the model input and as the fallback.** In both projects the render is the conditioning image. Ours would be licence-clean, and any tile that fails review can ship as the procedural version.

---

## 6. Not verified / unresolved

- **Licence of the Oxen-hosted tiles, datasets and weights.** `https://www.oxen.ai/cannoneyed/isometric-nyc-tiles` returned HTTP 429 and `https://hub.oxen.ai/cannoneyed/isometric-nyc-tiles` returned 404. Until someone reads those pages, treat the assets as unlicensed.
- **Licence of the Qwen Image Edit base model** and whether it constrains derived LoRAs. Not checked.
- **Whether Isometric NYC's or Tiny València's use of Google 3D Tiles is permitted** by Google or covered by an agreement. Unknown. Neither author addresses it in the material read.
- **Article quotes** come from an automated summariser and were not checked word for word against the page. Treat the figures (about 40 training pairs, about 4 h and 12 USD, under 3 USD per hour, more than 200 generations per hour, about 40k tiles) as "per the article", pending a manual read.
- **Total cost and duration of Isometric NYC.** Not published in the material read.
- **Tile count discrepancy.** The article estimates about 40k tiles; `docs/data.md` says about 32k quadrants. Probably estimate versus final, not confirmed.
- **Which WebP quality production used** (85 or 95; see section 2).
- **Whether the deployed isometric.nyc matches the repo.** Only the `server: cloudflare` header was checked; the live site's network requests were not inspected.
- **Lambda versus Modal.** The article describes a Lambda H100 VM; the repo documents Modal. Which one produced the bulk of the tiles is not stated.
- **Tiny València:** the author's real name, the image model and whether it was fine-tuned, the renderer, the tile image format and URL scheme, the hosting provider behind Cloudflare, costs, and any repository. The `x.com` profile and the Patreon page were not read and may hold more.
- **Tiny València's exact HN posting date.** The thread showed "4 days ago" only.
- **`tinyvalencia.com` area figures.** The manifest says 119.9 km²; a third-party aggregator summary says 112 km². Not reconciled.
- **Spanish data licences for our own use** (Catastro, IGN, OpenStreetMap terms as applied to Villena). Out of scope here; needs its own research note.
