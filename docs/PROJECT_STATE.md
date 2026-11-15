# Project state

Maintained by the integrator (WP12); the architect edits the contract line and decisions.
A summary, not a log — details are in `docs/handoffs/`.

Last updated: 2026-11-15 (bootstrap).

## Now

- **Contracts: PROPOSED v1** — not frozen. Freeze happens at gate G1 after WP02.
- Phase 1 can start: **WP01, WP02, WP07** in parallel (`docs/EXECUTION_PLAN.md`).
- The bootstrap is committed on branch `agent/wp00-bootstrap`; `main` must be fast-forwarded to it
  before any worktree is created. Nothing is pushed; no remote exists.

## Work packages

| WP | Status | Branch / commit | Notes |
|---|---|---|---|
| WP00 bootstrap | done | `agent/wp00-bootstrap` | `docs/handoffs/WP00-bootstrap.md` |
| WP01 data verification | ready to start | | |
| WP02 architecture review | ready to start | | |
| WP07 tooling, CI/CD | ready to start | | |
| WP03 GIS pipeline | waiting: G1, WP01, WP07 | | needs the two manual IGN files for a release-quality scene |
| WP04 render engine | waiting: G1 | | |
| WP05 viewer | waiting: G1 | | |
| WP06 tile export | waiting: G1 (WP07 desirable) | | |
| WP08 tests | waiting: WP04–WP07 | | |
| WP09 visual QA | waiting: real tiles | | |
| WP10 AI benchmark | optional; waiting: real render | | Phase B needs a budget approval |
| WP11 independent review | waiting: WP03–WP08 | | |
| WP12 integration | used at every merge | | |

## Decisions needed from the owner

1. **Merge the bootstrap into `main`**: `git switch main && git merge --ff-only agent/wp00-bootstrap`.
2. **Licences**: MIT for code, CC BY 4.0 for artwork/tiles/docs are proposals. Copyright
   holder is written as "Villena Isométrica contributors".
3. **Model access**: confirm which Codex "Sol"/"Terra" generation your plan includes
   (`codex debug models`); whether Gemini CLI works on your plan (`gemini` is not installed
   here); how you want DeepSeek used — chat UI bundles (free) or API (metered).
4. **Manual download**: the two IGN sheets (MDT50cm and MDS50cm, sheet 0845-8-2, 175 MB) from
   the Centro de Descargas. WP01 writes the click-by-click steps; WP03 can start without
   them in fallback mode.
5. **Viewer language**: Spanish UI assumed (English/Valencian later).
6. **AOI**: option A (1 km², bullring excluded) assumed; option B (1.0 × 1.2 km) includes it
   with 37 % more buildings.
7. **Worktree location**: the repository is inside Dropbox; task worktrees default to
   `../villena-isometrica-worktrees`, which is also inside Dropbox. Consider
   `make worktree WORKTREE_ROOT=~/worktrees/villena-isometrica …` to keep `node_modules`,
   virtualenvs and build outputs out of sync.
8. **GitHub owner / remote**: unspecified; nothing assumes one.

## Open risks

See `docs/ARCHITECTURE.md` → Known risks. Most urgent: the contracts have not been
independently reviewed yet (WP02), and the renderer's cross-platform determinism is unproven
until the WP04 spike.

## Open defects

None recorded.
