# Work-package prompts

One self-contained prompt per work package. To run one: create its worktree
(`make worktree WP=<nn-slug>`), start the recommended client and model in it
(`docs/AGENT_ROUTING.md`), and send:

> Read `prompts/<file>` and execute it.

For a model that cannot read the repository, build a single-message bundle with
`scripts/make_context_bundle.sh` (the prompt lists the files to include).

| Prompt | Work package | Recommended model (effort) | Needs | Branch |
|---|---|---|---|---|
| `00-bootstrap.md` | Architect: gate G1, contract changes, release review | Claude Fable 5.2 (high) | per task | `feature/wp00-bootstrap` |
| `01-data-research.md` | Data verification, dataset manifest, licensing | Gemini 3.8 Flash (high) | — | `feature/wp01-data-research` |
| `02-architecture-review.md` | Independent maths/architecture review | DeepSeek V4 Pro (high) | — | `feature/wp02-architecture-review` |
| `03-gis-pipeline.md` | Acquisition + scene export | Claude Opus 5.5 (high) | G1, WP01, WP07 | `feature/wp03-gis-pipeline` |
| `04-render-engine.md` | Deterministic pixel-art renderer | Codex Sol (high) | G1 | `feature/wp04-render-engine` |
| `05-frontend.md` | Static viewer | Claude Sonnet 5.5 (medium) | G1 | `feature/wp05-frontend` |
| `06-tile-export.md` | Tile pyramid, manifest, validator | Codex Sol (medium) | G1, WP07 | `feature/wp06-tile-export` |
| `07-ci-cd.md` | Makefile, Python scaffold, CI, Pages deploy | Codex Luna (medium) | — | `feature/wp07-ci-cd` |
| `08-testing.md` | Cross-component tests | Codex Luna (high) | WP04–WP07 merged | `feature/wp08-testing` |
| `09-visual-qa.md` | Visual and UX review | Codex Terra (medium) + Gemini second opinion | real tiles | `feature/wp09-visual-qa` |
| `10-ai-image-benchmark.md` | Optional AI feasibility benchmark | Claude Opus 5.5 (high) | real render; approval for Phase B | `feature/wp10-ai-image-benchmark` |
| `11-independent-review.md` | Pre-release review | DeepSeek V4 Pro (high) + cross-provider reviewer | WP03–WP08 merged | `feature/wp11-independent-review` |
| `12-release-integration.md` | Integration (every merge) and release prep | Codex Sol (high); approval Fable 5.2 | READY handoffs | `main` (integrator only) |

Order and parallelism: `docs/EXECUTION_PLAN.md`. Start now, in parallel: **01, 02, 07**.

Every prompt has the same sections: 0 before you start · 1 objective · 2 read first ·
3 dependencies · 4 inputs and contracts · 5 allowed paths · 6 forbidden paths ·
7 requirements · 8 non-goals · 9 acceptance criteria · 10 commands · 11 deliverables ·
12 stop conditions · 13 handoff · 14 when you finish.

Prompts are owned by the architect. If a prompt is wrong, say so in your handoff rather than
working around it.
