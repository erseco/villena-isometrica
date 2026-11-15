# Project state

Maintained by the integrator (WP12); the architect edits the contract line and decisions.
A summary, not a log — details are in `docs/handoffs/`.

Last updated: 2026-11-15 (gate G1 passed; WP01, WP02, WP03, WP07 merged).

## Now

- **Contracts: FROZEN v1** at commit `417f07e` (`docs/decisions/0007-g1-contract-freeze.md`).
  Changes only through `prompts/00-bootstrap.md` Task B.
- Phase 1 is complete. **Phase 2 can start in parallel: WP04, WP05, WP06.**
- `main` contains the bootstrap, the WP02 review, WP07 tooling/CI, WP01 data, the freeze and the
  WP03 pipeline. `make check` is green (contracts, lint, 31 tests, fixtures reproducible).
- `main` is pushed to `origin` (owner's authorisation, 2026-11-15). **CI is green on GitHub**
  (run 43717180749: contracts, python — 31 tests on Ubuntu —, js). The first run failed on a
  byte-for-byte fixture comparison that could not pass on Linux; fixtures are now compared by
  content (`make fixtures-check`).
- The integration round of 2026-11-15 was run by the architect (Fable 5.2) at the owner's
  request, not by the designated integrator.

## Work packages

| WP | Status | Branch / commit | Notes |
|---|---|---|---|
| WP00 bootstrap + G1 | done, merged | `feature/wp00-g1` @ `417f07e` | ADR 0007 has the verdict on every review finding |
| WP01 data verification | done, merged | `agent/wp01-data-research` @ `9be358d` | Gemini 3.8 Flash. Manifest, acquisition guide, 25 POIs. `curl -k` removed at integration. Handoff quotes head `eeee444`; the real one is `9be358d`. |
| WP02 architecture review | done, merged; findings closed at G1 | `agent/wp02-architecture-review` @ `13e0d67` | DeepSeek V4 Pro. R-10 rejected as proposed, R-20 deferred to WP08; the rest accepted. |
| WP07 tooling, CI/CD | done, merged | `feature/wp07-ci-cd` @ `bb2e399` | Codex. CI runs green on GitHub; the deploy workflow has only run its intended early failure. |
| WP03 GIS pipeline | **merged; real scene fallback-only** | `agent/wp03-gis-pipeline` @ `7095b3d` | Opus 5.5, adapted by the architect after G1. Full mode waits for the two IGN sheets. Cross-provider review owed. |
| WP04 render engine | **ready to start** | | can use the fallback Villena scene (`make scene` needs `data/raw/`, see below) |
| WP05 viewer | **ready to start** | | |
| WP06 tile export | **ready to start** | | |
| WP08 tests | waiting: WP04–WP06 | | owes fixture requests to the architect (R-04, R-20) |
| WP09 visual QA | waiting: real tiles | | |
| WP10 AI benchmark | optional; waiting: real render | | Phase B needs a budget approval |
| WP11 independent review | waiting: WP03–WP08 | | must include WP03 (written and adapted by Claude models) |
| WP12 integration | used at every merge | | |

## What changed at G1 that each work package must know

Each affected prompt carries a "Frozen-contract notes" section; the contracts win over older text.

- **WP04**: `pixelSha256` per layer is the cross-platform identity, file hashes only within one
  build; `palette.json` is an output referenced from `render.json`; `heightM` is the wall top
  and `ridgeHeightM` (optional) the measured ridge; optional `structures.geojson` renders like
  buildings; depth encoding defined once in `render.md`.
- **WP05**: background pixels have **no pick** — never fall back to the reference plane for
  them; power-of-two level factor; POIs sorted by id.
- **WP06**: scene POIs follow `scene-pois.schema.json`; manifest carries `crs` and
  `renderSha256`; `maxResidualM < 0.1`; validator cross-checks POI coordinates and the palette.
- **WP03**: done (dataset ids, node-reference OSM, structures, ridge).
- **All**: branches are `feature/wpNN-slug`; Python modules run with `PYTHONPATH=pipeline` or
  through `make`; pitch must be < 90°.

## Data on this machine

Raw downloads are git-ignored and live per worktree. WP01's are in
`../villena-isometrica-worktrees/wp01-data-research/data/raw/` (Catastro, MDT05, OSM —
checksums match the manifest). To build the scene from another checkout, either copy that
`data/raw/` or pass `--data-root` to it. The OSM snapshot cannot be re-downloaded byte-identically
(OSM changes): keep the file.

## Decisions needed from the owner

1. **Download the two IGN sheets** (MDT50cm and MDS50cm, sheet 0845-8-2, ≈ 184 MB) following
   `cities/villena/ACQUISITION.md` §3, into `data/raw/ign-mdt50cm/` and `data/raw/ign-mds50cm/`.
   Until then every building height comes from floor counts and the castle enclosure is a 3 m
   placeholder block.
2. **Licences**: code is MIT (the owner's `LICENSE`). CC BY 4.0 for artwork, tiles and docs is
   still a proposal.
3. **Branch prefix**: `feature/` adopted on the strength of the WP07 handoff ("the user's
   permanent naming preference"). Say so if that was not intended.
4. **Model access**: which Codex "Sol"/"Terra" generation the plan includes; WP01 ran on
   Antigravity CLI, not Gemini CLI — `GEMINI.md` may not be loaded by it; DeepSeek through chat
   bundles or API.
5. **Viewer language**: Spanish UI assumed.
6. **AOI**: option A (1 km², bullring excluded) assumed.
7. **Worktree location**: worktrees default to a sibling directory of the repository, which may be cloud-synced; WP07's is in
   `/tmp`, which a reboot clears (its branch is merged, so nothing is lost).
8. **GitHub owner placeholders**: documents still say `<github-owner>`; the remote is known now.
9. **GitHub Pages**: the `Deploy Pages` workflow skips its build and deploy jobs (green, with a
   notice) until `cities/villena/tiles.lock.json` exists; nothing to decide until the first release.

## Open risks

- The full-mode height logic (surface model, roof slope, zoning, canopy) has only ever run on
  synthetic data. The first run with the real IGN sheets is the next real test of WP03.
- The renderer's cross-platform pixel determinism is unproven until the WP04 spike.
- The deploy workflow has never run past its tiles-lock guard; the JS job of CI has
  nothing to run yet.
- Catastro has only the castle's keep; the enclosure and the town walls come from OSM outlines,
  whose heights depend entirely on the surface model.
- Review coverage: WP03 has not been reviewed by a non-Claude model; WP07 and WP01 were reviewed
  by the architect only.
- The pipeline has run on Linux only through its tests in CI, never on real data.

## Open defects

None recorded against merged code. Deferred from the WP02 review: R-20 (richer synthetic
fixtures: wall/roof/vegetation classes, a margin building, a terrain ridge) — WP08 lists what it
needs and the architect regenerates.
