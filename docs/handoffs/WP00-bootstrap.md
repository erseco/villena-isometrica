# Handoff — WP00 Bootstrap: research, architecture, contracts, prompts

| Field | Value |
|---|---|
| Task ID | WP00 |
| Date (UTC) | 2026-11-15 |
| Provider / client | Claude Code 2.1.325 |
| Model and effort actually used | `claude-fable-5-2` (architect); six research subagents on the same session |
| Branch | `agent/wp00-bootstrap` |
| Base commit | `87f025b` |
| Head commit | the bootstrap commit on `agent/wp00-bootstrap` |
| Status | READY FOR REVIEW |

## What was produced

- Research with sources and unresolved lists: `docs/research/01`–`06`.
- Architecture, plan, routing, data, licensing, costs, roadmap, state: `docs/*.md`; ADRs
  0001–0005 in `docs/decisions/`.
- Contracts: `docs/contracts/projection.md`, `scene.md`, `render.md`; seven JSON Schemas and
  projection vectors in `packages/geo-contracts/`.
- Synthetic city "Planeville" (`tests/fixtures/`): city config, scene, render output, tile
  pyramid with POIs, height grid and closed-form expected values; generator
  `scripts/make_fixtures.py`; validator `scripts/validate_contracts.py`.
- `cities/villena/city.json` (AOI, camera, attribution) from verified coordinates.
- Shared instructions: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`; agent definitions in
  `.claude/agents/` and `.codex/agents/`; `.codex/config.toml`.
- Thirteen prompts in `prompts/`; templates for handoffs, issues and PRs; minimal `Makefile`.

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `make check` | pass | schemas valid; 6 fixture/city documents validate |
| `uv run scripts/make_fixtures.py` twice | pass | identical tree hash on both runs |
| validator on a manifest with a corrupted matrix | fails as intended | exit 1, names the element |
| TOML parse of `.codex/**` | pass | |
| Hand check of projection vectors | pass | four cases recomputed by hand |
| Visual check of fixture tile `9/0_0.png` | pass | 2:1 diamond, east up-right |

Not done: nothing was run on Linux; no workflow, viewer, renderer or pipeline code exists yet;
agent definition files were written from documentation and not exercised in Codex or Gemini.

## Decisions and assumptions

See ADRs 0001–0005. Assumptions an owner might overturn are listed in
`docs/PROJECT_STATE.md` → "Decisions needed from the owner".

## Deviations from the bootstrap brief

- Two extra schemas (`render-manifest`, `dataset-manifest`).
- No Docker, no JS workspace, no shared projection library (ADR 0001).
- Renderer backend left to a time-boxed experiment with a fixed decision rule (ADR 0002)
  instead of being chosen on paper: research could not show Three.js to be reliably
  deterministic across platforms.
- `GEMINI.md` imports `AGENTS.md`; no `.gemini/settings.json` (doing both would load it twice).
- The brief (`1st-prompt.md`) ends mid-sentence in section 13; nothing after "differences in
  resolution" was available.

## Known problems

- Contracts are unreviewed (that is WP02's job). Likely discussion points: render prism versus
  margin features, tile overlap default, terrain-pick edge cases.
- Several facts rest on inference and are assigned to WP01 (`docs/DATA_SOURCES.md` → Open
  questions): the elevation sheet's footprint, vertical datum name, MDT/MDS alignment,
  Catastro citation wording, redistribution of derived vectors.
- Model IDs for "Sol"/"Terra", Gemini CLI availability and DeepSeek access are unconfirmed
  for the owner's plans.
- Building-zoning of the castle from 0.5 m rasters is untested; landmark fidelity is a risk.

## Human approvals needed

Listed in `docs/PROJECT_STATE.md`. Nothing was pushed, published, purchased or downloaded
beyond small research probes kept outside the repository.

## Recommended next task

In parallel: `prompts/01-data-research.md`, `prompts/02-architecture-review.md`,
`prompts/07-ci-cd.md`. Then the architect runs gate G1 (`prompts/00-bootstrap.md`, Task A).

---

# Gate G1 and integration round — 2026-11-15

| Field | Value |
|---|---|
| Task | `prompts/00-bootstrap.md` Task A (gate G1), plus the integration of WP07, WP01 and WP03 at the owner's request |
| Model and effort actually used | `claude-fable-5-2`; effort as set in the owner's session |
| Branch | `feature/wp00-g1` @ `417f07e`, merged into `main` |
| Status | DONE — `Contracts: FROZEN v1` |

## What was done

1. Reviewed and merged WP07 (`feature/wp07-ci-cd`) and WP01 (`agent/wp01-data-research`): both touched only
   their allowed paths; `make install` and `make check` reproduced. One correction at integration: `curl -k`
   removed from `cities/villena/ACQUISITION.md` (the IGN service validates over normal TLS; checked).
2. Gate G1: every finding of the WP02 review recomputed, then accepted, rejected or deferred —
   `docs/decisions/0007-g1-contract-freeze.md` has the table. Contracts, nine schemas, the validator and the
   fixture generator updated; fixtures regenerated with no change to any expected value.
3. Decisions beyond the review (same ADR): optional `structures` layer, fixed dataset ids, `ridgeHeightM`,
   vertical datum and Catastro citation from WP01, `feature/` branch prefix, WP07's Python layout.
4. WP03 adapted on its branch to the frozen contracts and WP01's real data, then merged
   (`docs/handoffs/WP03-gis-pipeline.md`, round 2).
5. Prompts 03–06 and 08 gained a "Frozen-contract notes" section; `AGENTS.md` lists the real commands.

## Tests and validation executed

| Command | Result |
|---|---|
| Independent recomputation of R-01, R-03, R-04, R-07, R-11 | reproduced (R-01 share 29.8 % vs the reviewer's 29.1 %) |
| `make check` on `main` after each merge | pass; final: 10 documents valid, ruff clean, 31 tests, fixtures reproducible |
| Validator negative cases (NaN, `X` in scene POIs, unsorted POIs, pitch 90) | all rejected |
| `python3 scripts/check_size.py --self-test` | pass |
| Real Villena scene, fallback mode, twice | identical hashes; validates |
| GitHub Actions workflows | not run before this push |
| Linux | not run |

## Deviations from the process, on purpose

- The architect also acted as integrator and edited WP03's code after the freeze. The owner asked for the
  consolidation in one pass; the designated integrator (Codex Sol) did not take part.
- WP03, written by Opus and adapted by Fable, has had no review by another provider. WP11 must cover it.
- WP07's handoff was PARTIAL and WP03's first-round handoff was PARTIAL; both were merged after the checks
  above rather than sent back.

## Recommended next task

In parallel: `prompts/04-render-engine.md`, `prompts/05-frontend.md`, `prompts/06-tile-export.md`.
Owner: download the two IGN sheets.

