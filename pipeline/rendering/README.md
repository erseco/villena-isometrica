# rendering — scene → master image (WP04)

Offline, deterministic isometric pixel-art renderer. Reads a scene directory
(`docs/contracts/scene.md`) and a city config, writes the render directory of
`docs/contracts/render.md` §1: `render.json`, `palette.json`, `color.png`, `class.png`,
`buildingId.png` + `buildingId.json`, and `depth.png` with `--depth`. No GPU, browser, network,
paid service or generative AI.

```sh
bun ci
bun run render --scene ../../tests/fixtures/scene-synthetic \
  --city ../../tests/fixtures/city-synthetic/city.json --out ../../build/planeville/render [--depth] [--chunk 2048]
bun run lint     # biome (recommended rules, warnings are errors) + tsc --noEmit (strict)
bun run test     # bun test: projection vectors, golden pixel hashes, chunking, registration, CLI errors
bun run build    # type-check only (the package runs from source under Bun)
```

`--chunk` is the internal render-tile size in pixels; it never changes the output (tested).
Invalid input (a `scene.json` or `city.json` that fails its schema, a layer whose sha256 differs
from the manifest, a non-finite number, a city/scene origin mismatch) exits with status 1 and a
message naming the file; bad arguments exit with status 2.

![Planeville fixture, 2× nearest-neighbour](docs/planeville-color-2x.png)

## Design

Two stages (`docs/decisions/0002-render-backend.md`, `0006-render-backend.md`):

1. **G-buffer** (`src/raster.ts`): a TypeScript software rasteriser. Per chunk, it fills a
   surface-id buffer (`Uint32`) and a depth buffer (`Float64`, `d` of projection.md §3) with a
   one-pixel margin. Terrain cells (two triangles on a fixed NW–SE diagonal), building and
   structure walls (back faces culled), roofs and tree spheres/trunks. Surface-local
   coordinates are recovered exactly in stage 2 from `(X, Y, d)` with the surface pick of
   projection.md §5.3, so the G-buffer stores only id and depth.
2. **Styling** (`src/style.ts`): a pure function of the G-buffers, the scene attributes, the
   top-down ground grid and the palette. It produces palette indices, class codes and building
   indices; nothing else draws.

`src/geometry.ts` turns the scene into primitives: walls are footprint edges extruded from
`baseH` to `baseH + heightM` (holes give courtyard walls); `flat` and `unknown` roofs are a flat
polygon at the wall top; `pitched` parts with a convex single-ring footprint get a hipped roof
(each facet is the region closest to one eave edge, so the ridge direction follows the shape;
pitch 30° capped at the 6 m allowance, or rising to exactly `ridgeHeightM` when present).
Non-convex or holed `pitched` parts fall back to flat geometry with a tile texture: no ridge is
invented. Roads (buffered by `widthM / 2`, tunnels skipped, bridges flat) and landcover are
rasterised into a 0.25 m ground-class grid over the AOI and looked up for every terrain pixel.
Everything outside the render prism (AOI × `[zMin, zMax]`) is clipped per pixel.

## Style

- **Palette**: `palette.json`, 61 colours of my own choosing (≤ 64): limewash and ochre walls,
  pale stone for fortifications and landmarks, terracotta and grey-beige flat roofs, dusty
  ground, asphalt, stone paving, olive and pine greens, water. Every drawn pixel is one of
  them; undrawn pixels have alpha 0. `background` in `render.json` is `#1e2a35`, also in the
  palette so flattened tiles stay exact.
- **Light**: fixed in the world, from the sun at bearing 205° (south-south-west), elevation 45°.
  Lambert `n·L` is quantised into four bands (≥ 0.85, ≥ 0.60, ≥ 0.35, below); with the default
  camera the south façades are band 1, the west façades band 3, flat roofs and flat ground
  band 1, sunward hip facets band 0. No gradients.
- **Façades** from metric surface coordinates (metres along the wall, height above `baseH`):
  `floors`, else `round(heightM / 3)`, windows per floor in bays of about 3 m, doors on the
  ground floor in bays chosen by a hash of the part id and edge number. `use` picks the family:
  housing (limewash or ochre per hash of `buildingId`, with a darker plinth), shops (wide
  ground-floor windows), civic (stone, larger windows), religious (tall windows, sandstone or
  stone), industrial (concrete, ribbon windows, one large door), agricultural (ochre, sparse
  openings), fortification (pale stone courses, no openings). `landmark` parts get stone.
- **Roofs**: terracotta courses parallel to the eave (or the longest edge for flat-geometry tile
  roofs), flat roofs with a light parapet band and a 1 m tile grid, stone tops on
  fortifications. `unknown` roofs on non-industrial parts are textured as tile (allowed by the
  prompt; geometry stays flat).
- **Ground**: speckle and ordered (Bayer 4×4) dithering anchored to world cells and absolute
  image pixels; stone-paving joints; furrows on farmland; ripples on water.
- **Trees**: a sphere of `crownRadiusM` whose top is at `heightM`, shaded by its normal, on a
  trunk; olive or pine colouring by a hash of the tree id.
- **Outlines**: 1 px, colour `outline`, on the nearer side of any silhouette (against
  background) and of any boundary between objects (terrain, a part's walls, a part's roof,
  a tree crown, a trunk).
- No anti-aliasing, filtering or colour management anywhere. Nothing comes from Isometric NYC,
  Tiny València or any other project.

The `class` layer uses 1 ground (default ground, paved, bare rock, sports, cemetery),
2 road, 3 wall, 4 roof, 5 vegetation (trees, park, scrub, woodland, farmland), 6 water.
Class 7 (landmark-detail) is not emitted: landmarks have no extra geometry. `class.png` is an
8-bit palette PNG (the samples are the class codes; its PLTE is only for viewing).
`buildingId.json` is `[null, <part ids…>]`: building parts in file order, then structures.

## Determinism

- Only IEEE-754 basic operations and `Math.sqrt/floor/ceil/round/min/max/abs/imul` are used.
  Sine and cosine of the camera and sun angles come from a fixed Taylor series
  (`sinDeg`/`cosDeg`), because ECMAScript leaves `Math.sin` implementation-approximated; a test
  fails if a transcendental `Math` function appears in the source.
- Vertices are snapped to 1/256 px; coverage uses the even-odd rule at pixel centres with
  half-open spans, so shared edges are drawn once. Depth and every texture are evaluated from
  absolute image coordinates, never incrementally, so chunk size cannot matter; the one-pixel
  G-buffer margin gives outlines their neighbours across chunk edges.
- Ties in depth go to the primitive drawn first; the order is fixed (terrain cells, then parts
  in scene order, then trees). All variation comes from FNV-1a/xorshift hashes of ids and
  integer cell coordinates.
- PNG: own encoder (`src/png.ts`), one IDAT, filter Sub on every row, `node:zlib` level 9 as
  bundled with Bun, no ancillary chunks. `renderer.version` records the zlib and Bun versions.
- `test/golden.json` holds the `pixelSha256` of every layer for the synthetic scene (with
  `--depth`); `bun run test` compares it, renders with chunk sizes 64, 300, 1000 and 2048, and
  checks two runs give byte-identical files.

Cross-platform check (run from the repository root; the extra anonymous volume keeps the
container's `node_modules` away from the host's):

```sh
docker run --rm --platform linux/amd64 -v "$PWD":/w -v /w/pipeline/rendering/node_modules \
  -w /w/pipeline/rendering oven/bun:1.4 sh -c "bun ci && bun run render \
  --scene ../../tests/fixtures/scene-synthetic --city ../../tests/fixtures/city-synthetic/city.json \
  --out /tmp/r --depth && bun -e 'for (const l of (await Bun.file(\"/tmp/r/render.json\").json()).layers) \
  console.log(l.name, l.pixelSha256)' && bun test"
```

On 2026-11-15 this printed the golden hashes on `x86_64` (macOS arm64 host: identical), and the
Villena fallback scene gave identical `pixelSha256` on both platforms and for chunk sizes 2048
and 1500.

## Performance (Apple M5, 24 GB, Bun 1.4.4)

| Scene | Image | Time | Peak RSS |
|---|---|---|---|
| Synthetic fixture | 726 × 481 | 0.1 s | 73 MB |
| Villena fallback scene (7 721 parts, 1 m terrain, 505 roads) | 11 314 × 6 836 | 10.2 s | 3.0 GB |
| same, `--depth --chunk 1500` | 11 314 × 6 836 | 14.9 s | 4.2 GB |
| same, `linux/amd64` container under emulation | 11 314 × 6 836 | 19.7 s | 2.6 GB |

The budget is 10 minutes and 8 GB. Memory is dominated by the full-image output buffers
(≈ 40 bytes per pixel with `--depth`); time grows roughly linearly with pixels and terrain cells.

## Dependencies (pinned in `bun.lock`)

| Package | Version | Licence | Use |
|---|---|---|---|
| ajv | 8.20.0 | MIT | validate `scene.json` and `city.json` against the contract schemas |
| fast-deep-equal, json-schema-traverse, require-from-string | 3.1.3, 1.0.0, 2.0.2 | MIT | ajv dependencies |
| fast-uri | 3.1.9 | BSD-3-Clause | ajv dependency |
| @biomejs/biome (dev) | 2.6.8 | MIT OR Apache-2.0 | lint and format check |
| typescript (dev) | 7.0.2 | Apache-2.0 | strict type-check |
| @types/bun (dev; brings bun-types, @types/node, undici-types) | 1.4.4 | MIT | types |

Bun 1.4.4 itself runs the package; its bundled zlib encodes the PNGs.

`docs/spike-a-threejs.mjs` is the throwaway Three.js spike behind ADR 0006; it is not part of
the package and needs `three` and `playwright` installed elsewhere.
