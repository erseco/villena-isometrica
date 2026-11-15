# Villena Isométrica

_Villena, como nunca la habías visto._

An interactive isometric pixel-art map of Villena (Alicante, Spain), rendered from open
geodata — Catastro building footprints, IGN terrain and surface models, OpenStreetMap streets —
and served as a static site.

**Status: bootstrap.** Architecture, contracts, fixtures and work-package prompts exist;
implementation has not started. See `docs/PROJECT_STATE.md`.

- What and why: `docs/PROJECT.md`
- How it fits together: `docs/ARCHITECTURE.md`
- Who does what, in which order: `docs/EXECUTION_PLAN.md`, `docs/AGENT_ROUTING.md`, `prompts/`
- Rules for contributors (human or AI): `AGENTS.md`
- Data and licences: `docs/DATA_SOURCES.md`, `docs/LICENSING.md`

## Development

Install Python 3.13, uv, Bun, Node.js, make and Git. Then run:

```sh
make install
make check
make help
```

When the viewer package is available, run `bun run fixture` and then `bun run dev` from
`apps/viewer` to view fixture tiles. Pipeline commands are described in
`pipeline/README.md`.

## Licence

Code: MIT. Artwork, tiles and documentation: CC BY 4.0 (proposed). Map data credits:
`THIRD_PARTY_NOTICES.md`.
