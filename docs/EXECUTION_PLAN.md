# Execution plan

How the work packages depend on each other, what can run in parallel, and where the gates
are. Current status lives in `docs/PROJECT_STATE.md`; models in `docs/AGENT_ROUTING.md`.

## Dependency graph

```
WP00 bootstrap (done)
  ├──▶ WP01 data verification ──────────────┐
  ├──▶ WP02 math/architecture review ──▶ G1 ─┼──▶ WP03 GIS pipeline ───────┐
  └──▶ WP07 tooling + CI ───────────────────┤                              │
                                            ├──▶ WP04 render engine ──────┤
                                 (G1) ──────┼──▶ WP05 viewer ─────────────┼──▶ G2 ──▶ WP08 tests ─┐
                                            └──▶ WP06 tile export ────────┘      │                │
                                                                                 ▼                ▼
                                                              real Villena build (WP12 §7.2) ──▶ WP09 visual QA ─┐
                                                                                 │                               ├──▶ G3 ──▶ WP12 release prep ──▶ owner publishes
                                                                                 ├──▶ WP11 independent review ───┘
                                                                                 └──▶ WP10 AI benchmark (optional, off the critical path)
```

| WP | Needs | Blocks |
|---|---|---|
| WP01 | bootstrap | WP03 (dataset manifest, POI selection) |
| WP02 | bootstrap | G1 |
| WP07 | bootstrap | WP03, WP06 (Python scaffold); CI for everything |
| WP03 | G1, WP01, WP07 | real build |
| WP04 | G1 | real build, WP10 |
| WP05 | G1 | release |
| WP06 | G1, (WP07) | real build |
| WP08 | WP04–WP07 merged (WP03 desirable) | G3 |
| WP09 | real Villena tiles, WP05 | G3 |
| WP10 | real render | nothing in v0.1.0 |
| WP11 | WP03–WP08 merged | G3 |
| WP12 | used at every merge; final round after G3 | publication |

## Gates

| Gate | Who | Passes when |
|---|---|---|
| **G1 — contracts frozen** | architect (`prompts/00-bootstrap.md` Task A) | WP02 findings resolved, fixtures regenerated, `Contracts: FROZEN v1` in the state file |
| **G2 — components integrated** | integrator (WP12 §7.1) | WP03–WP07 merged, `make check` green, synthetic pipeline runs end to end |
| **G3 — release candidate** | integrator + architect (Task C) | WP08 green or defects accepted, WP09 and WP11 without open blockers, real build reproducible |
| **Publish** | **human owner only** | owner runs the action list from the WP12 handoff |

## Schedule

Sessions are what matter, not calendar days. One row = things that can run at the same time
in separate worktrees.

| Phase | In parallel | Models | Then |
|---|---|---|---|
| 1 | WP01 · WP02 · WP07 | Gemini Flash · DeepSeek Pro (chat bundle) · Codex Luna | integrator merges WP07 and WP01; architect runs G1 |
| 2 | WP03 · WP04 · WP05 · WP06 | Opus · Codex Sol · Sonnet · Codex Sol (second session) | integrator merges each as it lands (G2); cross-provider review of each |
| 3 | WP08 · real Villena build | Codex Luna · integrator | |
| 4 | WP09 · WP11 (two reviewers) · WP10 Phase A (optional) | Codex Terra + Gemini · DeepSeek + cross-provider · Opus | fixes on new `feature/wpNN-fix-*` branches by the owning model |
| 5 | WP12 final round · architect review | Codex Sol · Fable | owner publishes |

Human steps that cannot be delegated: download the two IGN sheets (once, ~175 MB, before WP03
finishes); approve or decline any spend (WP10 Phase B, DeepSeek API); accept or reject AI
tiles; create the GitHub repository and publish.

If the owner has less parallel capacity, the critical path is
WP02 → G1 → WP04 → WP06 → real build → WP09 → WP12, with WP07 and WP01 first.

## Rules of the road

- Start a task only when its "Needs" are merged in `main` (WP04–WP06 may start at the owner's
  risk before G1; the prompt tells them to record that).
- One branch + one worktree per task; the integrator alone merges. Details: `AGENTS.md`.
- A task that cannot proceed writes a BLOCKED handoff and stops; nobody improvises a contract.
- Fixes after review go back to the model that owns the package, on a new branch
  `feature/wpNN-fix-<topic>`, with the same prompt plus the finding IDs to address.

## Optional: GitHub issues and pull requests

When a remote exists and the owner wants a human-facing trail: one issue per work package
from `.github/ISSUE_TEMPLATE/work-package.md` (the prompt file is the description), one PR
per branch using the PR template. Agents never create them without being asked.
