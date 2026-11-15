# Project state

Maintained by the integrator (WP12); the architect edits the contract line and decisions.
A summary, not a log — details are in `docs/handoffs/`.

Last updated: 2026-11-15 (WP04, WP05, WP06 merged; phase 2 complete).

## Now

- **Contracts: FROZEN v1** at commit `417f07e` (`docs/decisions/0007-g1-contract-freeze.md`).
  Changes only through `prompts/00-bootstrap.md` Task B.
- Phases 1 and 2 are complete. **Next: WP08 (tests), then the first real build.**
- WP04–WP06 were run at the owner's request by Claude models in a workflow (Opus 5.5 / Sonnet 5.5),
  each reviewed by the other Claude model and merged by the architect. No non-Claude review yet.
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
| WP03 GIS pipeline | merged; **full-mode scene built** | `agent/wp03-gis-pipeline` @ `7095b3d` | Opus 5.5, adapted by the architect after G1. Full mode waits for the two IGN sheets. Cross-provider review owed. |
| WP04 render engine | done, merged | `feature/wp04-render-engine` @ `1d5623b` | Opus 5.5; reviewed by Sonnet 5.5 (approve). Software rasteriser in TypeScript (ADR 0006; Three.js spike rejected: output depended on chunk size). Villena fallback scene renders in ≈ 10 s, 3 GB. |
| WP05 viewer | done, merged | `feature/wp05-frontend` @ `3cde035` | Sonnet 5.5; reviewed by Opus 5.5 (2 blocking findings fixed: `schemaVersion` check, approximate-position flag). 94 kB gzip. |
| WP06 tile export | done, merged | `feature/wp06-tile-export` @ `6bc35c0` | Opus 5.5; reviewed by Sonnet 5.5 (approve). Indexed PNG, mode kernel. Only run on the synthetic fixture. |
| WP08 tests | **ready to start** | | owes fixture requests to the architect (R-04, R-20) |
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

1. ~~Download the two IGN sheets~~ — done 2026-11-15 (owner's request, through the browser);
   checksums pinned in `cities/villena/datasets.json`. `make scene` now runs in full mode.
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

- Full mode ran on the real sheets for the first time on 2026-11-15 and needed three fixes
  (EPSG:3042 tag, pitched-roof eaves, false trees on zoned landmarks). Other thresholds are
  unreviewed; the result was checked by eye only (castle, Santiago church, overview).
- The renderer's pixel hashes match between macOS arm64 and an emulated linux/amd64 container;
  native x86-64 is covered by the golden test in CI.
- The deploy workflow has never run past its tiles-lock guard; the JS job of CI has
  nothing to run yet.
- Catastro has only the castle's keep; the enclosure and the town walls come from OSM outlines
  with surface-model heights (14 zones kept for the enclosure).
- Review coverage: WP03 has not been reviewed by a non-Claude model; WP07 and WP01 were reviewed
  by the architect only.
- The pipeline has run on Linux only through its tests in CI, never on real data.

## Open defects

None recorded against merged code. Requests to the architect from phase 2 (contracts are frozen;
decide at the next Task B):
- WP06: POI lat/lon and E,N rounding exceeds `maxResidualM` (validator allows 0.015 m extra);
  `expected.json` sits inside the fixture tile directory, which `render.md` forbids; fixture lower
  levels use the mean kernel while the exporter defaults to mode.
- WP05: prompt §7.3 falls back to the reference plane when the height grid fails to load;
  `projection.md` §5.2 allows it only for manifests without a grid. The viewer follows the prompt
  and shows the approximate flag.
- WP04: depth value 0 is ambiguous (the pixel at `dMin` and undrawn pixels).
