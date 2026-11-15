# Project state

Maintained by the integrator (WP12); the architect edits the contract line and decisions.
A summary, not a log — details are in `docs/handoffs/`.

Last updated: 2026-11-15 (WP00 and WP02 merged).

## Now

- **Contracts: PROPOSED v1** — not frozen. Gate G1 must resolve the WP02 findings first.
- **WP02 review is in**: 1 blocker (R-01), 6 major (R-02…R-07), 10 minor, 3 notes —
  `docs/handoffs/WP02-architecture-review.md`. Nothing in it asks for a different architecture.
- Phase 1: WP01 and WP07 can continue; WP02 is done; G1 is next and blocks WP03–WP06.
- `main` contains the bootstrap and the WP02 review. Nothing is pushed: `origin/main` is at
  `f25c54c` and `main` is ahead. WP01 and WP03 worktrees are based on `ba8ba0c`; if G1 changes
  a contract, both must re-read it.

## Work packages

| WP | Status | Branch / commit | Notes |
|---|---|---|---|
| WP00 bootstrap | done, merged | `agent/wp00-bootstrap` @ `ba8ba0c` | `docs/handoffs/WP00-bootstrap.md` |
| WP01 data verification | worktree created, no commits yet | `agent/wp01-data-research` | |
| WP02 architecture review | done, merged; findings open | `agent/wp02-architecture-review` @ `13e0d67` | `docs/handoffs/WP02-architecture-review.md`; R-01 blocks G1 |
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

1. ~~Merge the bootstrap into `main`~~ — done: `main` was fast-forwarded to `ba8ba0c`.
   The WP02 review is merged with `--no-ff`; nothing is pushed.
2. **Licences**: code is MIT (the owner's `LICENSE`). CC BY 4.0 for artwork, tiles and docs
   is still a proposal.
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
8. **GitHub owner**: a remote `origin` now exists, but the documents and prompts still use
   `<github-owner>` placeholders, as the brief required. Say if they should be filled in.

## Open risks

See `docs/ARCHITECTURE.md` → Known risks. Most urgent: the WP02 blocker (R-01, the
terrain-aware pick has no rule when the ray never enters the height grid) and R-02…R-07 must be
resolved at G1, because WP03–WP06 would implement them as written. The renderer's
cross-platform determinism is unproven until the WP04 spike, and R-07 says the "byte-identical
PNG" requirement as written cannot hold without a pinned encoder.

## Open defects

Contract defects found by the WP02 review, none fixed yet (the architect resolves them at G1):
R-01 (blocker), R-02…R-07 (major), R-08…R-17 (minor). Full entries with evidence and proposed
text: `docs/handoffs/WP02-architecture-review.md`.
