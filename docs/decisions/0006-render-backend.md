# 0006 — Render backend: TypeScript software rasteriser

Status: accepted (2026-11-15, WP04). Outcome of the spike required by
`0002-render-backend.md`; either outcome was pre-approved by the architect.

## Context

The renderer has two stages: integer G-buffers, then a CPU styling pass (ADR 0002). The stage-1
backend had to be chosen by experiment. Decision rule (WP04 prompt §7.2): Three.js in headless
Chromium/SwiftShader **only if** its G-buffer hash is identical on the macOS arm64 host, in a
`linux/amd64` Ubuntu container and for two chunk sizes, the forward projection matches the
contract vectors, and installation is one command on both systems; otherwise a software
rasteriser in TypeScript.

## Options

- **A — Three.js r187 in Playwright's headless Chromium (SwiftShader)**: `OrthographicCamera`
  from the contract vectors r, p, w; `setViewOffset` chunks; `WebGLRenderTarget` with
  `samples: 0`, `NearestFilter`; a `RawShaderMaterial` writing a 24-bit face id as RGBA8; read
  back with `readRenderTargetPixels`.
- **B — software rasteriser in TypeScript**: vertices projected with the contract formulas,
  snapped to 1/256 px, even-odd coverage at pixel centres with half-open spans, depth from the
  plane at each pixel centre, all in absolute image coordinates.

## Evidence (measured 2026-11-15, Apple M5, macOS 26)

Spike A (`pipeline/rendering/docs/spike-a-threejs.mjs`, run outside the repository): terrain
(72 × 72 samples) plus the six synthetic building boxes, 726 × 481 px, sha256 of the stitched
RGBA id buffer.

| Run | Renderer string | chunk 512 | chunk 256 | chunk 100 |
|---|---|---|---|---|
| Host, Playwright 1.65.1, Chrome Headless Shell 159.0.8154.6 | `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (LLVM 10.0.0)), SwiftShader driver)` | `9f720412…48ce` | `da537217…57a9` | `010e7f9f…6255` |
| `mcr.microsoft.com/playwright:v1.65.1-noble`, `--platform linux/amd64` | `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)` | `9f720412…48ce` | `da537217…57a9` | `010e7f9f…6255` |

- Host and container agree for each chunk size, but **the three chunk sizes give three different
  buffers** (and chunk 100 draws 188 920 pixels instead of 188 921). `setViewOffset` changes the
  projection matrix per chunk, so float32 vertex positions, and therefore edge coverage, change
  with the chunk origin. This fails the decision rule (and projection.md §7.4).
- Installation is not one command: `npm install three playwright` plus
  `npx playwright install chromium-headless-shell` (on Ubuntu also `--with-deps`, which needs
  root) — about 100 MB of browser.
- Chromium documents the SwiftShader WebGL fallback as deprecated.

Candidate B, as built in `pipeline/rendering/` (full G-buffers plus styling, all four layers):

| Run | color `pixelSha256` | class | buildingId | depth |
|---|---|---|---|---|
| Host, chunk 2048 (default) | `f70ac3be…becc` | `78dd7ee6…a656` | `76201e0f…152c` | `c890d00a…c642` |
| Host, chunks 64, 300, 1000 (`bun run test`) | same | same | same | same |
| `oven/bun:1.4` (Bun 1.4.4), `--platform linux/amd64`, chunks 2048 and 64 | same | same | same | same |

The real Villena fallback scene (11 314 × 6 836 px) also gave identical `pixelSha256` on the host
with chunks 2048 and 1500 and in the `linux/amd64` container (color `0e6dceb4…baee`). Even the PNG
file hashes matched between host and container (same Bun build and bundled zlib). The forward
projection reproduces every contract vector within 1e-6 px (unit test), using a series sine and
cosine instead of the implementation-approximated `Math.sin/cos`.

## Decision

**B, the TypeScript software rasteriser.** A failed the chunk-size condition and the
one-command installation condition; the rule says B in every such case.

## Consequences

- No browser, GPU or native addon: the renderer is about 1 900 lines of TypeScript plus ajv,
  runs wherever Bun 1.4 runs, and its CI job is the same `bun ci && bun run lint && bun run test`
  as any package.
- Determinism holds by construction (basic IEEE-754 operations only, absolute-coordinate
  evaluation) and is guarded by golden `pixelSha256` values, a chunk-size test, and a test that
  rejects transcendental `Math` functions in the source.
- We own the rasteriser: coverage rules, clipping and the hipped-roof construction are ours to
  test and maintain. Performance is well inside budget (Villena: about 10 s and 3 GB).
- Three.js stays out of the pipeline; the viewer (WP05) is unaffected.
