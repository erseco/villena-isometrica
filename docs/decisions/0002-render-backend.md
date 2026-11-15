# 0002 — Renderer: two stages, backend chosen by a determinism spike

Status: accepted (2026-11-15); the outcome of the spike is recorded by WP04 in
`0006-render-backend.md`.

## Context
The brief prefers Three.js "if it can reliably produce deterministic offline tiles". Research
(04 §A–B) found: Three.js r187 can tile an orthographic view with `setViewOffset`, but only in
a browser; headless Chromium falls back to SwiftShader (8192 px texture limit), whose
byte-equality between macOS arm64 and Linux x86-64 is untested and whose WebGL fallback
Chromium says "will soon fail"; colours do not survive render-target readback. `headless-gl`
uses different GL stacks per OS. Blender adds a 250–430 MB dependency. A software rasteriser
is deterministic by construction and small for flat-shaded geometry.

## Decision
1. The renderer has two stages: integer G-buffers (ids, kinds, depth, surface coordinates),
   then a pure-integer styling pass that produces the pixel art. The art never depends on a
   GPU or on floating-point colour.
2. The G-buffer backend is decided by experiment at the start of WP04: Three.js + headless
   Chromium/SwiftShader **only if** hashes match across host, `linux/amd64` container and
   chunk sizes, and installation is one command; in any other case a TypeScript software
   rasteriser. Either outcome is pre-approved.

## Consequences
- Reliability is demonstrated, not assumed, which is what the brief asked for.
- The backend can be replaced later without touching the style or any contract.
- Roughly a quarter of WP04's effort goes to the spike.
