# Handoff — WP07 Development tooling, CI and GitHub Pages deployment

| Field | Value |
|---|---|
| Task ID | WP07 |
| Date (UTC) | 2026-11-15 |
| Provider / client | OpenAI Codex |
| Model and effort actually used | Not exposed by the runtime |
| Branch | `feature/wp07-ci-cd` |
| Base commit | `85d3036` |
| Head commit | This handoff commit |
| Status | PARTIAL — architect review and integration checks required |

## Changed files

- `Makefile`: package targets, fixture reproducibility check, and feature-prefixed worktree creation.
- `pipeline/pyproject.toml`, `pipeline/uv.lock`, `pipeline/README.md`: pinned Python 3.13, wheel-only scaffold and basic instructions.
- `scripts/check_size.py`, `scripts/fetch_tiles.py`: site budgets and verified, constrained release archive extraction.
- `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`: CI and gated Pages workflows.
- `.editorconfig`, `.gitattributes`, `.env.example`: editor, binary and environment conventions.
- `README.md`: development section.
- `docs/handoffs/WP07-ci-cd.md`: this report. An earlier handoff-only commit recorded the branch naming conflict.

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `make help` | pass | All targets including e2e listed. |
| `make install` | pass | macOS ARM; absent JS packages skipped. |
| `make check` | pass | Contracts, lint, fixture reproducibility; absent tests and JS packages skipped. |
| `make lint test` | pass | Python lint passed; absent packages and Python tests skipped. |
| `python3 scripts/check_size.py --self-test` | pass | Total and individual limits checked. |
| `python3 scripts/fetch_tiles.py --city villena --repo example/example` | pass | Exit 2 and missing lock guidance, as required. |
| Python mock archive checks | pass | Valid archive extracted; digest mismatch and `../` member rejected, existing destination preserved after rejection. |
| `uv run --project pipeline --frozen python -c "import geopandas, rasterio, pyogrio, shapely, pyproj, PIL"` | pass | macOS ARM. |
| `uv sync --project /tmp/villena-wp07-linux-check --frozen --python-platform x86_64-unknown-linux-gnu` | pass | Downloaded and installed wheels into a temporary environment; Linux binaries were not executed on macOS. |
| `uvx actionlint .github/workflows/*.yml` | unavailable | PyPI has no actionlint package. |
| `actionlint .github/workflows/*.yml` | pass | Locally installed actionlint. Ruby YAML parsing also passed. |
| GitHub Actions workflows | not run | No push, deployment or remote workflow execution was performed. |

Initial sandboxed `make check` failed because uv could not write its cache, then a temporary-cache retry failed because DNS was restricted. With access to the existing cache the check passed.

## Generated artifacts

- `pipeline/uv.lock`, 62,767 bytes, SHA-256 `ad7f33f73edc52bd2adafa23c9619cdbd67ce7f93a1a94569711a601b4beceba`; regenerate with `uv lock --project pipeline`.
- Temporary virtual environments under `pipeline/.venv` and `/tmp/villena-wp07-linux-check/.venv` are ignored/disposable; regenerate with the sync commands above. No generated tile artifacts.

## Decisions and assumptions

The owner instructed continuation despite the prompt's `agent/` branch requirement; the user's permanent naming preference takes precedence. The worktree is `/tmp/villena-wp07-ci-cd`. `make worktree` now creates `feature/` branches; the architect should reconcile the other instructions and prompts.

Versions were checked against PyPI. All resolved dependencies were installed as wheels for both target platform tags; macOS imports passed. The Linux wheel environment was not executed on Linux.

Action pins, verified against GitHub tags: checkout v7 `3d3c42e5aac5ba805825da76410c181273ba90b1`; setup-uv v9.0.0 `c771a70e6277c0a99b617c7a806ffedaca235ff9`; setup-bun v2 `0c5077e51419868618aeaa5fe8019c62421857d6`; cache v5 `caa296126883cff596d87d8935842f9db880ef25`; configure-pages v6 `45bfe0192ca1faeb007ade9deae92b16b8254a0d`; upload-pages-artifact v5 `fc324d3547104276b827a68afc52ff2a11cc49c9`; deploy-pages v5 `368f82528645a54fb793d4d04e342629a3f51346`. Pages pins follow the latest major tags identified in project research rather than the older docs examples.

## Contract change requests

None identified for WP07. G1 findings remain open for the architect.

## Known problems and unresolved issues

- Viewer, renderer, Python stage packages and their tests are not yet present; their commands and CI integration have not been exercised end to end. Linux execution and actual GitHub Actions remain unverified. The future owners must confirm package scripts and module interfaces when integrated.
- `make check` regenerates fixtures as WP07 requires, despite the general architect-only fixture instruction. Generated files were unchanged; the architect should reconcile that wording.
- The deploy workflow deliberately fails until the release asset and `cities/villena/tiles.lock.json` exist. No real release asset was fetched.
- `uvx actionlint` failed because the package is unavailable on PyPI; the installed actionlint passed.

## Human approvals needed

No approval was sought for publication. Before an eventual owner-authorized release, set Pages source to GitHub Actions and restrict the `github-pages` environment to `main`; create and pin the approved release asset. Publishing and pushing remain owner actions.

## Recommended next task

Architect review of WP07 and reconciliation of branch/fixture instructions, then an independent review and integration as required by the project workflow. Exercise CI and deployment only once their prerequisites exist and the owner authorizes publication-related actions.
