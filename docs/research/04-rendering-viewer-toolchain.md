# 04 — Rendering, viewer and toolchain research

**Verification date: 2026-11-15.** Versions were read on that date from the npm registry, PyPI and GitHub Releases. API facts come from Context7 (library ID given) or the official page linked. Fetched content was treated as reference data only.

Evidence labels used below:

- **[doc]** — read in official docs / source via Context7 or the linked URL on the verification date.
- **[measured]** — observed on this machine (macOS 26, Apple Silicon) in a throwaway environment outside the repo. Nothing was installed into the project.
- **[derived]** — my own arithmetic or inference from the documented facts; not stated by any source.
- **[memory]** — long-standing API I did not re-read today. Confirm before relying on it.

## Versions

| Component | Current stable | Released | Source | Notes |
|---|---|---|---|---|
| three | 0.187.0 (r187) | 2026-10-30 | npm, GitHub release `r187` | `@types/three` 0.187.0 |
| openseadragon | 6.1.1 | 2026-09-09 | npm, GitHub release `v6.1.1` | ships `types/index.d.ts`; BSD-3-Clause |
| @types/openseadragon | 6.0.0 | 2026-05-18 | npm | redundant now that the package bundles types |
| vite | 8.3.8 | 2026-11-11 | npm | engines: Node `^20.19.0 \|\| >=22.12.0` |
| typescript | 7.0.2 | 2026-07-08 | npm (`latest`) | native compiler; `7.1.0-beta` on `beta` tag |
| bun | 1.4.4 | 2026-10-22 | npm, GitHub release `bun-v1.4.4` | |
| oven-sh/setup-bun | v2.2.0 | 2026-03-14 | GitHub releases | |
| playwright / @playwright/test | 1.65.1 | 2026-11-13 | npm | bundles Chromium 158.0.8127.18 (1.65 notes); engines Node `>=20`, notes say use 22/24/26 |
| gl (headless-gl) | 8.1.6 | 2024-10-29 | npm (`latest`) | `9.0.0-rc.10` (2026-04-10) on `next` tag |
| sharp | 0.35.5 | 2026-09-27 | npm | engines Node `>=20.9.0` |
| libvips | 8.18.7 | 2026-09-26 | GitHub releases | 8.19.0-rc1 is a prerelease |
| oxipng | 10.2.1 | 2026-09-02 | GitHub releases | the npm package `oxipng` (1.0.1, 2021) is unrelated/stale; use the binary |
| libwebp / cwebp | 1.6.0 | — | local `cwebp -version` | Homebrew build; upstream release date not checked |
| leaflet | 1.9.4 | 2023-05-18 | npm (`latest`) | 2.0.0-beta.4 (2026-11-12) still prerelease |
| maplibre-gl | 6.18.0 | 2026-11-11 | npm | |
| Node.js LTS | 26.13.1 "Lithium", 24.22.3, 22.23.5 | 2026-11 | nodejs.org/dist/index.json | |
| Python | 3.15.2 / 3.14.10 / 3.13.18 | — | endoflife.date | |
| uv | 0.13.8 | 2026-11-12 | PyPI | |
| GDAL | 3.13.3 | 2026-08-18 | GitHub releases, PyPI | PyPI `GDAL` is sdist only |
| rasterio | 1.5.2 | 2026-09-30 | PyPI | requires Python >=3.12; wheels cp312–cp315 |
| pyogrio | 0.13.0 | 2026-06-26 | PyPI | abi3 wheels for cp311+ |
| geopandas | 1.2.0 | 2026-09-28 | PyPI | pure Python; requires >=3.11 |
| shapely | 2.2.0 | 2026-10-07 | PyPI | bundles GEOS 3.14.1 [measured] |
| pyproj | 3.8.0 | 2026-09-05 | PyPI | requires >=3.12; bundles PROJ 9.8.1 [measured] |
| PDAL (C++) | 2.10.2 | 2026-06-12 | GitHub releases | |
| pdal (Python) | 3.5.5 | 2026-07-31 | PyPI | sdist only |
| pillow | 13.0.0 | 2026-10-16 | PyPI | |
| numpy | 2.5.4 | 2026-10-10 | PyPI | requires >=3.12 |
| bpy (Blender as module) | 5.3.0 | 2026-11-10 | PyPI | Python `==3.13.*` only; Blender 5.2 is the LTS line |

---

## A. Three.js

Context7 ID: `/mrdoob/three.js`. Version r187.

**Camera**

- `new OrthographicCamera(left = -1, right = 1, top = 1, bottom = -1, near = 0.1, far = 2000)` [doc: `docs/pages/OrthographicCamera.html`].
- `OrthographicCamera.setViewOffset(fullWidth, fullHeight, x, y, width, height)` exists on the orthographic camera, not only the perspective one. It "sets an offset in a larger frustum" [doc]. This is the mechanism for rendering one large image as exact sub-tiles: keep the frustum fixed for the full image and move only the offset. `clearViewOffset()` resets it [memory].
- Camera angles [derived, not from docs]:
  - True isometric: azimuth 45°, elevation `atan(1/√2)` ≈ 35.264° above the ground plane.
  - 2:1 dimetric (the usual pixel-art "isometric"): azimuth 45°, elevation 30° (`sin(elev) = 0.5` makes a ground square a 2:1 diamond). Vertical extrusion is foreshortened by `cos 30°` ≈ 0.866.
  - For pixel-stable output, derive `left/right/top/bottom` from the output pixel size and a fixed metres-per-pixel constant, and never from the viewport.

**Render targets and readback**

- `WebGLRenderTarget(width, height, options)`; options include `samples` (MSAA count, default `0` = off), `count` (number of colour attachments, default `1`), `depthTexture`, `minFilter`, `magFilter` [doc: `docs/pages/RenderTarget.html.md`, `src/core/RenderTarget.js`].
- `renderer.readRenderTargetPixels(renderTarget, x, y, width, height, buffer, activeCubeFaceIndex, textureIndex = 0)` and `readRenderTargetPixelsAsync(...)` returning `Promise<TypedArray>`; the docs recommend the async variant [doc: `docs/pages/WebGLRenderer.html.md`].
- Readback is raw: `gl.readPixels` in the texture's own format/type, with no colour-space transform [doc: `src/renderers/WebGLRenderer.js`].
- Software-renderer limits in Playwright's Chromium 158 headless shell: `MAX_TEXTURE_SIZE` = `MAX_RENDERBUFFER_SIZE` = 8192, `MAX_DRAW_BUFFERS` = 8 [measured]. A full-map render target larger than 8192 px on a side is not possible there, so tiling with `setViewOffset` is required, not optional.

**Antialiasing and filtering**

- The `antialias` constructor flag affects only the default framebuffer. For a render target, MSAA is controlled by `samples`, and `0` disables it [doc].
- `NearestFilter` for `minFilter`/`magFilter` and `generateMipmaps = false` on any texture and on the render target [doc: `webgl_depth_texture`, `webgl_multiple_rendertargets` examples].

**Colour management — the part that bites exact palettes**

- When rendering to a render target, `WebGLRenderer` compiles shaders with the **working** colour space (linear sRGB) and `NoToneMapping`; `outputColorSpace` and `toneMapping` apply only to the default framebuffer [doc: `src/renderers/WebGLRenderer.js` `setProgram()`; Migration Guide 154 → 155].
- Consequence [derived]: a material colour given as an sRGB hex is converted to linear, written to an RGBA8 target as a linear value, and read back as that linear value. The bytes you read are not your palette bytes.
- Options, in order of preference:
  1. Do not render colour at all on the GPU. Render an integer **palette index / feature ID** per pixel and map to palette colours on the CPU. Colour management is then irrelevant.
  2. `ColorManagement.enabled = false` with unlit materials so values pass through untouched [memory — property not re-read today].
  3. Render to the canvas with `outputColorSpace = SRGBColorSpace` and `toneMapping = NoToneMapping`. This round-trips sRGB → linear → sRGB in the shader, and exact 8-bit recovery is not guaranteed [derived].

**ID, depth and semantic passes**

- `WebGLRenderer` MRT: `new WebGLRenderTarget(w, h, { count: N })`, attachments in `renderTarget.textures[i]`, custom `RawShaderMaterial` with `glslVersion: THREE.GLSL3` writing to several outputs [doc: `examples/webgl_multiple_rendertargets.html`]. Built-in materials do not write extra attachments.
- Depth: `renderTarget.depthTexture = new DepthTexture(...)` with `DepthFormat` and `UnsignedShortType` / `UnsignedIntType` / `FloatType` [doc: `examples/webgl_depth_texture.html`, `docs/pages/DepthTexture.html`].
- `scene.overrideMaterial` to re-render the same geometry with an ID material [memory].
- WebGPU path: `mrt({ output, normal, ... })` with `pass.setMRT()` or `renderer.setMRT()` in TSL [doc: `tsl/content/Guide.md`, `examples/webgpu_mrt.html`].

**WebGPURenderer status**

- "The renderer itself is still in an experimental state although its maturity level has been greatly improved" [doc: `manual/pages/webgpurenderer.html`].
- "`WebGLRenderer` is still maintained and the recommended choice for pure WebGL 2 applications", with no larger new features planned [doc, same page].
- `ShaderMaterial`, `RawShaderMaterial`, `onBeforeCompile()` and `EffectComposer` are not supported in `WebGPURenderer`; it uses node materials, TSL and `RenderPipeline` [doc].
- Import from `three/webgpu`; `forceWebGL: true` selects its WebGL 2 backend [doc].

**Recommendation (A).** If Three.js is the renderer, use `WebGLRenderer` + `OrthographicCamera` + `setViewOffset` tiles into a `WebGLRenderTarget` with `samples: 0`, and render **IDs, not colours**: one pass per output (feature/palette ID, depth, semantic class), each a separate `renderer.render()` with a different material. Multi-pass over MRT because identical geometry gives identical coverage and it needs no custom GLSL3 plumbing. Skip `WebGPURenderer`: still documented as experimental, and it buys nothing for flat-shaded offline output.

---

## B. Headless / offline deterministic rendering

**Option 1 — Playwright-driven headless Chromium with SwiftShader**

- Chromium documents two SwiftShader routes: GL driver `--use-gl=angle --use-angle=swiftshader`, and WebGL fallback `--use-gl=angle --use-angle=swiftshader-webgl --enable-unsafe-swiftshader` [doc: <https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md>].
- "Allowing automatic fallback to WebGL backed by SwiftShader has been deprecated. WebGL context creation will soon fail instead of falling back to SwiftShader", for security (JIT in the GPU process) [doc, same page].
- Playwright 1.65's `chromium-headless-shell` (Chromium 158.0.8127.18) on macOS arm64, run with **no GPU flags**, reports `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (LLVM 10.0.0)), SwiftShader driver)`, WebGL 2.0, and `navigator.gpu` present. Both documented flag sets give the same renderer string. `--use-angle=metal` switches to `ANGLE Metal Renderer: Apple M5` with 16384 limits [measured].
- So the same CPU rasteriser is available on macOS arm64 and (by documentation) on Linux, from the same Chromium build pinned by the Playwright version.
- Playwright is already needed for section E, so this adds no dependency.

**Option 2 — `headless-gl` (`gl` on npm)**

- Stable 8.1.6 is from 2024-10-29. 9.0.0 has been in RC since 2025 (rc.10, 2026-04-10). The repo is active (commits 2026-11-05) [npm, GitHub].
- README on `master`: conforms to WebGL 1.0.3; WebGL 2 via `createWebGL2Context: true`, "every method implemented" but not run against the WebGL 2 conformance suite; Node 22+ tested; prebuilt binaries for macOS arm64/x64, glibc ≥ 2.34 and Alpine ≥ 3.22 [doc: <https://github.com/stackgl/headless-gl>]. Whether this describes 8.1.6 or only the 9.0 RCs was not checked.
- On headless Linux it needs an X server and an OpenGL driver; the README recommends Xvfb + Mesa and `xvfb-run`. On macOS it uses ANGLE's OpenGL backend [doc].
- Consequence [derived]: Linux rasterises with Mesa (llvmpipe), macOS with the system GPU through ANGLE. Two different rasterisers, so no cross-platform determinism by construction.
- Bun is not mentioned in the README. It is a native addon; Bun compatibility is unverified.

**Option 3 — Blender headless (`bpy`)**

- `bpy` 5.3.0 wheels: 254.5 MB (macOS arm64), 427.5 MB (manylinux x86_64); Python `==3.13.*` only; no Linux aarch64 wheel [PyPI, measured sizes].
- Path-traced or EEVEE output then needs quantising back to a palette; a flat-shaded ID render gains nothing from Blender's renderer [derived].
- Cross-platform bit-exactness of Cycles/EEVEE was not researched. See Unresolved.

**Option 4 — Custom software rasteriser (z-buffer, Python/NumPy or TypeScript)**

- Orthographic projection is affine, so there is no perspective-correct interpolation; flat shading needs one value per triangle. With integer or fixed-point edge functions the output is bit-identical on every platform [derived].
- Palette indices, feature IDs, depth and semantic masks come out of the same loop as plain arrays, with no colour management and no readback [derived].
- Scale check [derived]: 1 km × 1 km in 2:1 dimetric at 4 px/m is roughly 5 700 × 2 900 px plus building height, i.e. under 20 megapixels.
- Cost: you write and test the rasteriser, culling and any shading yourself, and get no interactive preview for free.

**Known pitfalls for bit-exact output across GPUs**

- Hardware GPUs differ in edge tie-breaking, float precision and driver behaviour; MSAA resolve and texture filtering differ too. Avoid by using one software rasteriser, `samples: 0`, `NearestFilter`, and integer outputs [derived].
- SwiftShader JIT-compiles for the host CPU. Whether macOS arm64 and Linux x86_64 produce identical bytes for the same scene is **not verified**.
- An 8192 px limit applies under SwiftShader [measured].
- Chromium may remove SwiftShader WebGL entirely; the opt-in flag is documented as lower-security and for trusted content [doc].

**Recommendation (B).** Render with Three.js inside Playwright's pinned `chromium-headless-shell`, passing `--use-gl=angle --use-angle=swiftshader-webgl --enable-unsafe-swiftshader` explicitly and asserting the `UNMASKED_RENDERER_WEBGL` string contains `SwiftShader` before rendering. Strongest reason: it is the only GPU-API option where the same software rasteriser was observed on macOS arm64 and is documented for Linux, and it reuses a tool already in the stack. Make Ubuntu CI the canonical renderer and treat macOS output as preview until the spike below passes.

The custom integer rasteriser is the most reproducible option by construction and is the fallback. Decide with one spike: render the same fixed scene on macOS arm64 and Ubuntu x86_64 and compare SHA-256 of the raw ID buffers. If they differ, either accept "CI is canonical" or switch to option 4. Reject `headless-gl` (different rasterisers per OS, stable release two years old) and Blender (250–430 MB for output that must be re-quantised anyway).

---

## C. OpenSeadragon

Context7 ID: `/openseadragon/openseadragon`. Docs: <https://openseadragon.github.io/docs/OpenSeadragon.html> (page reports 6.1.1).

**Maintenance.** 6.1.1 on 2026-09-09, 6.1.0 on 2026-08-06, 6.0.2 on 2026-03-12; last push 2026-11-10; not archived [GitHub].

**DZI** [doc: <https://github.com/openseadragon/openseadragon/wiki/The-DZI-File-Format>]

- Layout: `name.dzi` (or `.xml`) descriptor next to `name_files/<level>/<col>_<row>.<ext>`.
- Level 0 is ~1 px; each level doubles; the highest level is full resolution. Odd sizes round up when halving.
- Overlap is added on both sides of a join, on top of the tile size.

**Custom tile source** [doc: `test/demo/customheaders.html`, `src/openseadragon.js`]

- Inline object in `tileSources`: `{ width, height, tileSize` or `tileWidth`/`tileHeight`, `tileOverlap, minLevel, maxLevel, getTileUrl(level, x, y) }`.
- `DziTileSource(width, height, tileSize, tileOverlap, tilesUrl, fileFormat, displayRects, minLevel, maxLevel)` also accepts an inline config object, so no XML fetch is required.
- Subclassing `OpenSeadragon.TileSource` allows `getLevelScale(level)`, `getTileWidth(level)`, `getTileHeight(level)` overrides.

**Coordinates** [doc: `src/viewport.js`]

- `viewport.imageToViewportCoordinates(x, y | Point)`, `viewport.viewportToImageCoordinates(...)`, `viewport.imageToViewportRectangle(...)`, `viewport.viewportToImageRectangle(...)`.
- With one image these delegate to the `TiledImage` methods of the same names; with several images use the `TiledImage` methods directly.
- `viewerElementToImageCoordinates` and the pointer-event → viewport helpers were not re-read today [memory].

**Overlays** [doc: `src/viewer.js`]

- `viewer.addOverlay(element | options, location: Point | Rect, placement = Placement.TOP_LEFT, onDraw?)`; location is in viewport coordinates; fires `add-overlay`. Overlays are HTML elements.

**Controls, touch, keyboard** [doc: Options page and `src/viewer.js`]

- `showNavigationControl`, `showZoomControl`, `showHomeControl`, `showFullPageControl` default `true`; `showNavigator` default `false`. There is no `showFullscreenControl`.
- `gestureSettingsTouch.pinchToZoom` and `.flickEnabled` default `true`.
- `keyboardNavEnabled` default `true`, `tabIndex` default `0`, `pixelsPerArrowPress` default `40`.
- Keys: arrows / WASD pan; Shift+Up/Down or `=`/`-` zoom; `0` home; `r`/`R` rotate; `f` flip.
- `viewer.isFullScreen()` exists.

**Pixel art above 100 %** [doc: Options page, changelog]

- `imageSmoothingEnabled` default `true`; supported by the canvas drawer and, since 5.0.1, the WebGL drawer. Set it to `false`.
- `drawer` default order is `['auto', 'webgl', 'canvas', 'html']`.
- `maxZoomPixelRatio` default `1.1` — must be raised to allow zooming past native resolution.
- `smoothTileEdgesMinZoom` default `1.1` — alternative compositing above this zoom; interaction with crisp pixels not tested.
- Zoom is continuous, so non-integer scales give uneven pixel sizes. No documented integer-zoom snapping was found.

**Types and size**

- 6.1.1 ships its own typings (`types/index.d.ts`) [npm metadata].
- `openseadragon.min.js`: 352 735 bytes raw, 87 195 bytes gzip [measured from jsDelivr]. No `module`/`exports` field in `package.json`; `main` is the UMD build.
- For comparison: `leaflet@1.9.4/dist/leaflet.js` 147 552 raw / 42 439 gzip [measured].

**Alternatives**

- Leaflet `CRS.Simple`: half the bytes, but stable 1.9.4 dates from 2023 and 2.0 is still beta. Tile pyramids are XYZ, not DZI.
- MapLibre GL / deck.gl: built for georeferenced vector/WebGL maps; a single pre-rendered raster pyramid uses none of that. Not evaluated in depth.

**Recommendation (C).** OpenSeadragon 6.1.1 with an inline DZI/custom tile source, `imageSmoothingEnabled: false`, raised `maxZoomPixelRatio`. Strongest reason: it is the one actively released viewer whose native model is exactly "one deep-zoom image pyramid", with image↔viewport conversion, keyboard and pinch built in and bundled types. Prototype crispness at fractional zoom early; that is the open question, not the API.

---

## D. Vite, TypeScript, Bun

**Vite 8** — Context7 ID `/vitejs/vite`

- GitHub Pages project site: set `base: '/<REPO>/'`; user/custom-domain site uses `'/'` [doc: `docs/guide/static-deploy.md`]. Also `vite build --base=/path/`.
- `import.meta.env.BASE_URL` for URLs built at runtime; it is statically replaced, so it must appear verbatim [doc: `docs/guide/build.md`]. Tile URLs in `getTileUrl` need this prefix.
- `public/` is served at `/` in dev and copied as-is to `dist/` without hashing; reference files by root-absolute path [doc: `docs/guide/assets.md`]. `publicDir` default `'public'`.
- Vite transpiles `.ts` only and does not type-check; the transformer is Oxc. Set `"isolatedModules": true`; add `"types": ["vite/client"]` [doc: `docs/guide/features.md`].
- Official Pages workflow: `actions/configure-pages`, `actions/upload-pages-artifact` with `path: './dist'`, `actions/deploy-pages`; permissions `pages: write`, `id-token: write` [doc].

**TypeScript 7.0** — <https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/>

- Released 2026-07-08; `npm i -D typescript` provides the native `tsc` [doc].
- Defaults: `strict: true`, `module: esnext`, `target` = latest stable ES before `esnext`, `noUncheckedSideEffectImports: true`, `rootDir: ./`, `types: []` [doc].
- Hard errors: `target: es5`, `baseUrl`, `moduleResolution: node`/`node10`/`classic`, `module: amd|umd|systemjs|none` [doc].
- 7.0 ships **no programmatic API**; tools that import `typescript` (the post names typescript-eslint and template tooling) need `@typescript/typescript6` until 7.1 [doc].
- Because `types` defaults to `[]`, `vite/client` and any test globals must be listed explicitly [derived].

**Bun 1.4** — Context7 IDs `/oven-sh/bun`, `/oven-sh/setup-bun`

- Text lockfile `bun.lock` is the default since 1.2 (`install.saveTextLockfile = true`) [doc: `docs/runtime/bunfig.mdx`].
- `bun ci` ≡ `bun install --frozen-lockfile`; fails if `package.json` and `bun.lock` disagree [doc: `docs/pm/cli/install.mdx`].
- `bunx --bun vite` runs Vite on the Bun runtime; without `--bun` the `node` shebang is respected [doc: `docs/guides/ecosystem/vite.mdx`].
- `oven-sh/setup-bun@v2`: inputs `bun-version`, `bun-version-file`, `no-cache`; version precedence is input → file → `package.json` → latest [doc].
- `bun test` is Bun's own runner and is separate from Playwright Test. File-pattern collisions between the two were not checked.

**Recommendation (D).** Vite 8 + TypeScript 7 + Bun as package manager and script runner, with `base: '/villena-isometrica/'` and tiles under `public/`. Strongest reason: every piece is documented to work this way, and Vite does not depend on the TypeScript API, so TS 7's missing API does not block the build. Pin Bun via `packageManager`/`bun-version-file` and use `bun ci` in CI. Add a linter only after checking it runs without the TS programmatic API.

---

## E. Playwright

Context7 ID: `/websites/playwright_dev`. Release notes: <https://playwright.dev/docs/release-notes>.

- 1.65: Chromium 158.0.8127.18, Firefox 159.0, WebKit 27.2. "Use Node.js 22, 24 or 26"; Node 20 no longer tested [doc].
- **Bun support arrived in 1.65**: `bunx --bun playwright test`; plain `bunx playwright test` still runs on Node. Limitations under Bun: no watch mode, `--tsconfig` and custom ESM loaders have no effect, stack traces lack async frames, test console output missing from trace/UI mode. Playwright's CI runs under Bun 1.4.3 on Linux only [doc].
- `expect(page).toHaveScreenshot(name?, { maxDiffPixels, maxDiffPixelRatio, threshold })`; `threshold` 0–1, default `0.2` (pixelmatch, YIQ); `maxDiffPixels` and `maxDiffPixelRatio` unset by default; `animations: 'disabled'`, `caret: 'hide'`, `scale: 'css'` defaults [doc: `class-testconfig`, `test-snapshots`].
- Baselines are named `<name>-<project>-<platform>.png` because rendering differs per browser and OS; `snapshotPathTemplate` changes this; `--update-snapshots` regenerates [doc].
- 1.64 added `type: 'png' | 'webp'` for stored screenshots [doc].
- Mobile: `devices['Pixel 7']` etc. set `viewport`, `deviceScaleFactor`, `isMobile`, `hasTouch`; `page.touchscreen.tap(x, y)` requires `hasTouch` [doc].
- Pinch: the docs' recipe dispatches synthetic `touchstart`/`touchmove`/`touchend` with two touch points via `locator.dispatchEvent` [doc: <https://playwright.dev/docs/touch-events>].
- CI: `npx playwright install --with-deps chromium` [doc: <https://playwright.dev/docs/browsers>].

**Recommendation (E).** Playwright 1.65 on Node in CI (`bunx playwright test`, not `--bun`), Chromium only, baselines generated on Ubuntu. Strongest reason: Bun support is three weeks old, Linux-only in Playwright's own CI, and has listed gaps, while the Node path costs nothing extra on a GitHub runner. For the viewer's pixel-art screenshots set `threshold: 0` with a small `maxDiffPixels` rather than the default `0.2`.

---

## F. Python geo stack

**Install story, as observed.** `uv run --python 3.13 --with pyogrio --with rasterio --with geopandas --with shapely --with pyproj` on macOS arm64 resolved to wheels only, with no system GDAL [measured]:

| Package | Version | Bundled library |
|---|---|---|
| pyogrio | 0.13.0 | GDAL 3.12.4, 64 vector drivers |
| rasterio | 1.5.2 | GDAL 3.12.2, 147 raster drivers |
| shapely | 2.2.0 | GEOS 3.14.1 |
| pyproj | 3.8.0 | PROJ 9.8.1 |
| geopandas | 1.2.0 | pure Python |

- **Do wheels bundle GDAL?** Yes for both. pyogrio: "binary wheels that include GDAL", not always the latest, common drivers only [doc: <https://pyogrio.readthedocs.io/en/latest/install.html>]. rasterio: wheels contain libgdal and its dependencies, "omit many of GDAL's optional format drivers", and are "not tested for compatibility with all other binary wheels" [doc: <https://rasterio.readthedocs.io/en/stable/installation.html>].
- **GML via pyogrio wheels?** The `GML` driver is present with read/write capability in the pyogrio 0.13.0 macOS arm64 wheel; so are `GPKG`, `GeoJSON`, `FlatGeobuf`, `DXF`, `OSM`, `KML`, `LIBKML`. `GMLAS` and `Parquet` are absent [measured via `pyogrio.list_drivers()`]. Reading an actual Catastro INSPIRE file was not tested (see Unresolved).
- rasterio wheel has `GTiff`, `COG`, `AAIGrid`, `PNG`, `WEBP`, `JP2OpenJPEG`, `netCDF`, `HDF5`, `VRT` [measured].
- Two different GDAL builds (3.12.4 and 3.12.2) load into one process when pyogrio and rasterio wheels are used together [measured]. pyogrio's docs warn of driver conflicts when mixing with pip-installed Fiona [doc]. Do not add Fiona; `fiona` 1.10.1 is from 2024 and has no cp314 wheels anyway.
- Wheel platforms: rasterio and pyogrio publish macOS arm64, manylinux x86_64 and manylinux aarch64; no musllinux. rasterio's macOS arm64 wheel is tagged `macosx_15_0` [PyPI].
- **PyPI `GDAL` (osgeo bindings) and `pdal` are sdist only** and need the C/C++ library installed first [PyPI; PDAL: "requires a working PDAL installation", <https://pdal.io/en/stable/python.html>]. conda-forge `python-pdal` installs both [doc].

**Python version.** 3.13: every wheel above exists for it, it was the version tested here, and it is the only one `bpy` supports if Blender is ever needed. 3.14 has equal wheel coverage. 3.11 is excluded by rasterio, pyproj and numpy (`>=3.12`).

**uv.** `uv.lock` uses universal resolution and is "portable across platforms… regardless of operating system, architecture, and Python version"; `uv sync --locked` errors if the lock is stale; `astral-sh/setup-uv` for Actions [doc: Context7 `/astral-sh/uv`, `docs/concepts/resolution.md`, `docs/guides/integration/github.md`]. With a wheels-only dependency set this gives a reproducible environment on macOS arm64 and Ubuntu without Docker [derived from the above + measured install].

**Docker, if needed** [doc: <https://github.com/OSGeo/gdal/tree/master/docker>]

- `ghcr.io/osgeo/gdal:ubuntu-small-3.13.3` (~385 MB, Ubuntu 26.04, Python bindings, Python 3.14), `ubuntu-full-3.13.3` (~1.48 GB), `alpine-small-3.13.3` (~59 MB, no Python), `alpine-normal-3.13.3` (~282 MB, Python). Release tags are built for linux/amd64 and linux/arm64.
- The README does not say whether any variant includes PDAL.

**Alpine.** Not viable for the wheel route: rasterio and pyogrio publish no musllinux wheels, so pip would build from source against a system GDAL [PyPI]. Only shapely, pyproj, numpy and pillow have musllinux wheels.

**Recommendation (F).** `uv` project on Python 3.13 with `geopandas`, `pyogrio`, `rasterio`, `shapely`, `pyproj`, `numpy`, `pillow`, locked with `uv.lock`; no Docker, no conda. Strongest reason: the whole set installs from wheels on both target platforms and the GML driver is in the wheel. Leave PDAL out unless raw LiDAR must be processed; if it must, isolate that single step in a conda-forge or Docker environment that writes a GeoTIFF, rather than moving the whole pipeline.

---

## G. Tile image encoding

**Tooling**

- libvips `dzsave`: default layout DeepZoom, 256 px JPEG centre tiles; `suffix` takes format options, e.g. `".png[bitdepth=4]"`; `skip_blanks` default `-1` (5 for Google layout); `region_shrink` default mean [doc: <https://www.libvips.org/API/current/method.Image.dzsave.html>].
- `VipsRegionShrink`: `MEAN`, `MEDIAN`, `MODE`, `MAX`, `MIN`, `NEAREST` (top-left pixel) [doc: <https://www.libvips.org/API/current/enum.RegionShrink.html>]. Mean invents off-palette colours; `MODE` or `NEAREST` keep the palette [derived].
- sharp `tile({ size = 256, overlap = 0, layout = 'dz', depth, skipBlanks = -1, container = 'fs' })`; tile format set by `.png()`/`.webp()`/`.toFormat()`. `png({ palette, colours = 256, compressionLevel = 6, effort = 7, dither = 1.0 })`. `webp({ lossless, nearLossless, effort = 4, exact })` [doc: <https://sharp.pixelplumbing.com/api-output/>]. sharp's `tile()` docs list no `region_shrink` equivalent.
- Pillow 13 writes indexed PNG and lossless WebP; `cwebp -lossless -z 9 -exact`; `oxipng -o max --strip safe` [measured, all ran].

**Browser support.** MDN lists WebP as supported in Chrome, Edge, Firefox, Opera and Safari; Safari needs 14+ on macOS 11+. Lossless mode is part of the format. Maximum 16 383 × 16 383 px [doc: <https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Image_types>].

**Size ratios**

- Google's study: lossless WebP is 42 % denser than libpng output and 23 % denser than ZopfliPNG on 12 000 web PNGs [doc: <https://developers.google.com/speed/webp/docs/webp_lossless_alpha_study>]. MDN: "typically 26% smaller" than PNG [doc].
- One synthetic 512 × 512, 32-colour flat-shaded tile with a dithered band [measured, single sample, not real project output]:

| Encoding | Bytes |
|---|---|
| PNG RGB, Pillow `optimize` | 22 703 |
| PNG indexed, Pillow `optimize` | 13 283 |
| PNG indexed + `oxipng -o max` | 11 662 |
| PNG RGB + `oxipng -o max` (auto-reduced to palette) | 11 662 |
| WebP lossless (`cwebp -z 9` and Pillow `method=6`) | 9 560 |

  WebP lossless was about 18 % smaller than the best PNG here, and decoded back to identical RGB.

**Recommendation (G).** Indexed PNG optimised with `oxipng` as the tile format, built with a nearest/mode downsample for lower pyramid levels. Strongest reason: palette PNG stores the palette index itself, so tiles are inspectable, diff-able and exact by construction, and the measured gap to lossless WebP is modest. Switch to lossless WebP only if real tiles show the Pages payload matters; the pipeline change is one encoder call.

---

## Not verified / unresolved

1. **SwiftShader bit-exactness between macOS arm64 and Linux x86_64.** Same renderer string observed on macOS; Linux not run; byte equality of output not tested on either. This decides section B.
2. **Linux default renderer of Playwright's headless shell.** Assumed SwiftShader from Chromium docs; not observed.
3. **How long Chromium keeps SwiftShader WebGL.** Docs say fallback "will soon fail"; no removal version found. Sources disagree on when the deprecation started (Chrome 130 vs 139).
4. **Catastro INSPIRE GML.** The `GML` driver is in the wheel, but a real `A.ES.SDGC.BU.*.gml` file was not read: the download from `catastro.hacienda.gob.es` failed from this environment (no HTTP response). Attribute/geometry fidelity, and whether a `.gfs` sidecar or `GMLAS` (absent from the wheel) is needed, are open.
5. **Two GDAL copies in one process** (pyogrio 3.12.4 + rasterio 3.12.2): observed to import together; not stress-tested.
6. **`ColorManagement.enabled`, `scene.overrideMaterial`, `clearViewOffset()`, `viewerElementToImageCoordinates`**: cited from memory, not re-read in r187 / 6.1.1 docs today.
7. **Camera angles and frustum sizing** are my derivation, not from Three.js docs. `setViewOffset` seam-exactness on an orthographic camera was not rendered and compared.
8. **OpenSeadragon crispness**: `imageSmoothingEnabled: false` is documented, but behaviour at fractional zoom, with `smoothTileEdgesMinZoom`, on HiDPI, and under the WebGL vs canvas drawer was not tested. No integer-zoom snapping option found.
9. **Playwright synthetic touch events vs OpenSeadragon.** The documented pinch recipe dispatches touch events; whether OpenSeadragon's pointer handling reacts to them was not tested.
10. **`headless-gl`**: which release line the `master` README describes (8.1.6 vs 9.0 RC), and Bun compatibility, unknown.
11. **Blender**: Cycles/EEVEE determinism across platforms and headless EEVEE requirements were not researched; rejected on install weight and fit alone.
12. **TypeScript 7 with linters.** The announcement does not mention Vite; compatibility is inferred from Vite not using the TS API. ESLint/typescript-eslint under TS 7 needs the TS 6 compatibility package per the announcement; not tried.
13. **`bun test` alongside Playwright Test** file-discovery overlap: not checked.
14. **PDAL in `ghcr.io/osgeo/gdal` images**: README silent.
15. **PNG vs WebP ratio** rests on one synthetic image; re-measure on real tiles. libwebp 1.6.0 was read from the local binary, not upstream.
16. **Leaflet / MapLibre / deck.gl** were compared on release status and size only, not prototyped.
