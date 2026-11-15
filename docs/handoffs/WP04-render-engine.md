# Handoff — WP04 Deterministic isometric pixel-art render engine

| Field | Value |
|---|---|
| Task ID | WP04 |
| Date (UTC) | 2026-11-15 |
| Provider / client | Claude Code (subagent of a workflow run started by the owner) |
| Model and effort actually used | `claude-opus-5-5` (the prompt's fallback model, assigned by the owner), effort high |
| Branch | `feature/wp04-render-engine` (worktree `/private/tmp/villena-worktrees/wp04-render-engine`) |
| Base commit | `7a23429` (`git merge-base main HEAD`) |
| Head commit | the commit that adds this file; the code is in `13528cd` |
| Status | **READY FOR REVIEW** |

## Dependencies at start

| Dependency | State |
|---|---|
| Contracts | `docs/PROJECT_STATE.md`: `Contracts: FROZEN v1` |
| `make check` on the base commit | pass (31 Python tests, fixtures match; the JS packages were not present yet) |
| Bun / Docker | Bun 1.4.4; Docker 29.9.2 (Docker Desktop, arm64 VM, `linux/amd64` by emulation) |

## Changed files

```
 docs/decisions/0006-render-backend.md           |  74 +++
 pipeline/rendering/README.md                    | 147 ++++++
 pipeline/rendering/biome.json                   |   8 +
 pipeline/rendering/bun.lock                     | 100 ++++
 pipeline/rendering/docs/planeville-color-2x.png | Bin 0 -> 57328 bytes
 pipeline/rendering/docs/spike-a-threejs.mjs     |  94 ++++
 pipeline/rendering/package.json                 |  21 +
 pipeline/rendering/palette.json                 | 251 ++++++++++
 pipeline/rendering/src/cli.ts                   |  62 +++
 pipeline/rendering/src/geometry.ts              | 580 ++++++++++++++++++++++++
 pipeline/rendering/src/png.ts                   | 121 +++++
 pipeline/rendering/src/projection.ts            | 117 +++++
 pipeline/rendering/src/raster.ts                | 239 ++++++++++
 pipeline/rendering/src/render.ts                | 209 +++++++++
 pipeline/rendering/src/scene.ts                 | 268 +++++++++++
 pipeline/rendering/src/style.ts                 | 336 ++++++++++++++
 pipeline/rendering/test/golden.json             |   6 +
 pipeline/rendering/test/projection.test.ts      |  73 +++
 pipeline/rendering/test/render.test.ts          | 154 +++++++
 pipeline/rendering/tsconfig.json                |  20 +
 docs/handoffs/WP04-render-engine.md             (this file)
```

- `src/projection.ts`: contract projection, deterministic series sine/cosine, surface pick.
- `src/scene.ts`: scene/city loading; schema validation (ajv), sha256 of every referenced file, finite numbers.
- `src/geometry.ts`: terrain cells, walls, flat roofs, hipped roofs on convex footprints, trees; 0.25 m ground-class grid for roads and landcover.
- `src/raster.ts`: stage 1, software rasteriser into surface-id + depth G-buffers.
- `src/style.ts`: stage 2, all pixel art. `src/render.ts`: chunk loop, layers, manifest. `src/png.ts`: own PNG encoder/decoder.
- `docs/spike-a-threejs.mjs`: the throwaway Three.js spike (not part of the package, not run by any script).

## Tests and validation executed

All run in the worktree on the macOS arm64 host unless stated.

| Command | Result | Notes |
|---|---|---|
| `make install` (start) | pass | `uv sync`; JS packages skipped (none existed yet) |
| `make check` (base commit) | pass | 31 passed; fixtures match |
| `cd pipeline/rendering && bun ci` | pass | 13 installs, no changes |
| `bun run lint` | pass | biome `--error-on-warnings` on 11 files, then `tsc --noEmit` strict: no output |
| `bun run test` | pass | 15 pass, 0 fail (2 files) |
| `bun run build` | pass | `tsc --noEmit -p .` |
| `bun run render --scene ../../tests/fixtures/scene-synthetic --city ../../tests/fixtures/city-synthetic/city.json --out ../../build/planeville/render` | pass | `rendered 726x481 px, 6 parts, 3 trees … in 0.1 s, peak RSS 71 MB` |
| `uv run scripts/validate_contracts.py build/planeville/render/render.json` | pass | `ok   build/planeville/render/render.json` (also `palette.json`: ok) |
| `shasum -a 256 build/planeville/render/*.png` | done | see Generated artifacts |
| Pillow cross-check: decode each PNG with Pillow 13 / numpy, sha256 of the array bytes | pass | equals `pixelSha256` for color, class, buildingId (independent decoder) |
| Docker cross-platform check (README command; prompt's command plus `-v /w/pipeline/rendering/node_modules` so the container's install does not overwrite the host's `node_modules`) | pass | `uname -m` = `x86_64`, Bun 1.4.4; printed the golden `pixelSha256` for all four layers; `bun test` inside: 15 pass, 0 fail |
| Same container, `--chunk 64` | pass | identical `pixelSha256` |
| Villena: `make scene`-equivalent `build_scene … --terrain-fallback --data-root <wp01 worktree>` (no `--report/--preview`, which write under `cities/`) | pass | 7 710 parts, 11 structures, 505 roads, 48 landcover, 11 trees; image 11 314 × 6 836 |
| Villena render on host, default chunk 2048 | pass | 10.2 s, peak RSS 2.97 GB (`/usr/bin/time -l`: 3.04 GB max resident) |
| Villena render on host, `--chunk 1500 --depth` | pass | 14.9 s, 4.2 GB; color/class/buildingId `pixelSha256` identical to chunk 2048 |
| Villena render in `linux/amd64` container | pass | 19.7 s (emulated), 2.6 GB; `pixelSha256` and even file sha256 identical to the host |
| `make check` (final, after the handoff) | pass | validate-contracts ok, ruff clean, 31 pytest passed, rendering lint + 15 tests passed, fixtures match |

Spike A (Three.js) is reported in `docs/decisions/0006-render-backend.md`: it ran on the host and in
`mcr.microsoft.com/playwright:v1.65.1-noble` (`linux/amd64`) outside the repository.

## Generated artifacts

Not committed (under the git-ignored `build/`); regenerate with the commands above.

| Path | Size | sha256 (file) | pixelSha256 |
|---|---|---|---|
| `build/planeville/render/color.png` | 37 446 | `89013ae3b0ce0c4e314c25f68948102d866f572522259804be313665124e2dad` | `f70ac3beb2a0a99b76e93fb0b56d4d440254233b6ef918181fb543716333becc` |
| `build/planeville/render/class.png` | 4 838 | `472a63b79e63b3d24cc6855495ac83f6609d0628ed161143b211024a2daeaefb` | `78dd7ee6e6ffe44369f675a5ae96fd8b469da6d6602b52585d39f5497c9da656` |
| `build/planeville/render/buildingId.png` | 2 973 | `9395e169ddd01bb45e63bb9fb9b25b3553c298e201afc908a28e28ebd8802026` | `76201e0f427f8b9476c21e3d8f6481300724877623a719e864538c1eeada152c` |
| `build/planeville/render/depth.png` (`--depth`) | 17 968 | `0cc887081f9d751cfe0697204735c79b3c7aad971b405d83269c082d2ae93e0a` | `c890d00aedbd3f8abf130e093005ba28684db43b1f834a90cd287faafad3c642` |
| `build/planeville/render/palette.json` | 3 274 | `ed75a4cc98f54acc7fef815769725a4ef3e697e6b58c05012fb6013c6fdc5a8f` | — |
| `build/villena/render/color.png` | 9 011 621 | `04dda6a348590a862598a63cd2117ea762664d149fb584944703e44c5d2a1ddc` | `0e6dceb40e062baa619786714fdac9d02c421cafdd2a2638b42db5554b1ebaee` |
| `build/villena/render/class.png` | 832 296 | `723bb8ce7cae0f21c02aac588342c18a1881a06584adc63bd773bfbbef44270c` | `5e436b425b1de8f2542fe40c2a3cc7965f873165728954278daa2c0d5be1342f` |
| `build/villena/render/buildingId.png` | 1 696 617 | `57474ae4e1b7e7324c5e9ded546eec4806f1ef702e32e79bedc3529c1101af9b` | `6cb1af19697aec37dd7f98967a57e925a8337d81114e31b4d0b26a66fb00b7cc` |

Committed: `pipeline/rendering/docs/planeville-color-2x.png` (57 328 bytes; the fixture's
`color.png` at 2× nearest-neighbour) and `test/golden.json` (the four fixture `pixelSha256`).

**The three determinism hashes** (synthetic scene, color layer; the other layers behave the same,
see ADR 0006): host chunk 2048 `f70ac3be…becc` = host chunks 64/300/1000 `f70ac3be…becc` =
`linux/amd64` container `f70ac3be…becc`.

## Decisions and assumptions

- **Backend B, software rasteriser** — `docs/decisions/0006-render-backend.md`. Spike A gave
  identical buffers host vs container per chunk size, but different buffers for chunk sizes
  512/256/100, and needs two install commands (plus root on Ubuntu).
- Determinism: no transcendental `Math` functions (a test enforces it); sine/cosine from a fixed
  series. Vertices snapped to 1/256 px, half-open even-odd coverage, depth and textures from
  absolute image coordinates.
- The G-buffer stores surface id + depth only; surface-local coordinates (metres along a wall,
  height above `baseH`, world x/y for ground and roofs) are recovered exactly from `(X, Y, d)`
  via the surface pick (projection.md §5.3). Same information as the prompt's list, less memory.
- Light from bearing 205°, elevation 45°, four Lambert bands (README §Style).
- Pitched roofs: hipped roof built from per-edge facets on **convex single-ring** footprints
  only. Non-convex or holed `pitched` parts get flat geometry with a tile texture rather than an
  invented ridge. The Villena fallback scene has no `pitched` part at all (all 7 721 are
  `unknown`), so this only shows on the fixture today.
- `unknown` roofs are flat geometry; textured as terracotta tile except industrial (flat grey)
  and fortification (stone). Residential walls are limewash or ochre by a hash of `buildingId`;
  tree colour (olive/pine) by a hash of the tree id. These are style choices, not data claims.
- Prism clipping is per pixel: a building that straddles the AOI edge is cut open (its interior
  back walls are culled, so the ground shows through the cut). Terrain is clipped at the AOI, so
  the image is a "diorama" diamond with background corners, as projection.md §3 describes.
- Class 7 (landmark-detail) is never emitted. Park, scrub, woodland and farmland ground are
  class 5 (vegetation); paved/pedestrian/steps/rail/path are class 2 (road).
- `class.png` is a palette PNG (colour type 3, like the fixture); samples are the class codes.
- `buildingId.json` = `[null, building part ids in file order, then structure ids]`.
- `render.json` `background` = `#1e2a35`, which is also in `palette.json`.
- `renderer.version` = `0.1.0 (software rasteriser; PNG: own encoder, filter Sub, zlib <ver> level 9, Bun <ver>)`.
- The CLI deletes a stale `depth.png` in `--out` when run without `--depth`, so the directory
  holds exactly the files the manifest lists (other foreign files are left alone).
- The Villena scene was built only for smoke tests, into the worktree's ignored `build/`, reading
  `--data-root /Users/ernesto/Dropbox/Trabajo/git/villena-isometrica-worktrees/wp01-data-research`.
  No raw data was copied into Git. No Villena image is committed (licence attribution of a
  Catastro/OSM-derived image is the integrator's call).

## Contract change requests

None required. Observations for the architect:

- projection.md §7.4 / render.md §1 could state explicitly that `--chunk` (or any internal tile
  size) must not change `pixelSha256`; the spike showed GPU paths silently violate this.
- render.md §1 could say whether `palette.json` must contain the `background` colour (it does here).

## Known problems and unresolved issues

- No straight-skeleton roofs: non-convex pitched footprints render flat (see above).
- Buildings cut by the AOI edge show no cap face.
- At 4 px/m (fixture) the roof-course and stone-joint textures read as fine noise; at Villena's
  8 px/m they read as intended. Tuning is style work, not correctness.
- The docker command differs from the prompt's by one extra anonymous volume
  (`-v /w/pipeline/rendering/node_modules`); without it the container's `bun ci` replaces the
  host's platform-specific `node_modules` (biome and tsc binaries). Documented in the README.
- The `linux/amd64` runs were under emulation on Apple Silicon, not on native x86-64 hardware.
  CI (`ubuntu-latest`) is native x86-64 and runs the same golden test.

## Dependencies (for `THIRD_PARTY_NOTICES.md`)

| Package | Version | Licence | Kind |
|---|---|---|---|
| ajv | 8.20.0 | MIT | runtime |
| fast-deep-equal | 3.1.3 | MIT | runtime (ajv) |
| fast-uri | 3.1.9 | BSD-3-Clause | runtime (ajv) |
| json-schema-traverse | 1.0.0 | MIT | runtime (ajv) |
| require-from-string | 2.0.2 | MIT | runtime (ajv) |
| @biomejs/biome (+ platform CLI packages) | 2.6.8 | MIT OR Apache-2.0 | dev |
| typescript (+ `@typescript/typescript-<platform>`) | 7.0.2 | Apache-2.0 | dev |
| @types/bun, bun-types, @types/node, undici-types | 1.4.4, 1.4.4, 26.6.6, 8.9.0 | MIT | dev |

No new data source, model or asset. The palette is original (61 colours).

## Human approvals needed

None for this package. The spike downloaded Playwright's Chrome Headless Shell (≈ 100 MB) and the
public `mcr.microsoft.com/playwright:v1.65.1-noble` and `oven/bun:1.4` images; nothing was paid,
pushed or published.

## Recommended next task

WP06 (tile export) can now consume `build/<city>/render/`; WP08 can add a cross-component test
render → tiles. Re-render Villena when the full-quality (MDT50cm/MDS50cm) scene exists: with
`ridgeHeightM` data the hipped roofs will appear on real buildings.
