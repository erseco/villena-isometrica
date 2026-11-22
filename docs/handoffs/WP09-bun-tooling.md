# Handoff — WP09 Bun tooling

| Field | Value |
|---|---|
| Task ID | WP09 |
| Date (UTC) | 2026-11-22 |
| Provider / client | Anthropic Claude Code (interactive session with the owner) |
| Model and effort actually used | `claude-opus-5-5` |
| Branch | `feature/wp09-bun-tooling` |
| Base commit | `0583490a1a548e30ba7ac7e560a476542bc3bfb5` |
| Head commit | the commit that adds this handoff (`git log -1 feature/wp09-bun-tooling`) |
| Status | READY FOR REVIEW (ADR 0009 is proposed and needs the architect's approval) |

## Changed files

```
 .github/workflows/ci.yml                |   5 +-
 .github/workflows/deploy.yml            |   5 +-
 AGENTS.md                               |   2 +-
 THIRD_PARTY_NOTICES.md                  |   2 -
 apps/viewer/README.md                   |  12 +-
 apps/viewer/bun.lock                    |  43 ------
 apps/viewer/bunfig.toml                 |   5 +
 apps/viewer/e2e/failure-modes.spec.ts   |  24 ++-
 apps/viewer/e2e/viewer.spec.ts          | 101 +++++++++----
 apps/viewer/index.html                  |   5 +-
 apps/viewer/package.json                |   7 +-
 apps/viewer/playwright.config.ts        |   2 +-
 apps/viewer/src/geo.test.ts             |  21 ++-
 apps/viewer/src/geo.ts                  |  80 +++++++---
 apps/viewer/src/main.ts                 | 244 +++++++++++++++++++++++-------
 apps/viewer/src/schema.test.ts          |   3 +-
 apps/viewer/src/schema.ts               |   3 +-
 apps/viewer/src/search.test.ts          |  12 +-
 apps/viewer/src/search.ts               |  15 +-
 apps/viewer/src/strings.ts              |  15 +-
 apps/viewer/src/style.css               | 254 ++++++++++++++++++++++++++------
 apps/viewer/src/types.ts                |  35 ++++-
 apps/viewer/src/url.test.ts             |  12 +-
 apps/viewer/src/url.ts                  |   6 +-
 docs/decisions/0001-stack-and-layout.md |   2 +-
 docs/decisions/0009-bun-tooling.md      |  42 ++++++
 pipeline/rendering/README.md            |  34 ++---
 pipeline/rendering/biome.json           |   8 -
 pipeline/rendering/bun.lock             |  66 ---------
 pipeline/rendering/bunfig.toml          |   8 +
 pipeline/rendering/package.json         |   8 +-
 pipeline/rendering/src/scene.ts         |   2 +-
 pipeline/rendering/test/detail-scene.ts |   2 +-
 33 files changed, 741 insertions(+), 344 deletions(-)
```

- The first commit changes the tooling. The second only reformats the viewer with `bun fmt`; it can be reviewed or
  reverted on its own.
- `pipeline/rendering`: `bun fmt` keeps Biome's output, so no source file changes. Only `README.md` is reformatted.
  The two `biome-ignore` comments for `noExplicitAny` become `eslint-disable-next-line` comments.
- `docs/decisions/0001-stack-and-layout.md`: the "Playwright runs on Node" line points to ADR 0009.

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `bun run lint` in `apps/viewer` | pass | no problems in 16 files, 22 files formatted, no type errors in 15 files |
| `bun run lint` in `pipeline/rendering` | pass | no problems in 13 files, 19 files formatted, no type errors in 13 files |
| `bun run test` in `apps/viewer` | pass | 17 pass |
| `bun run test` in `pipeline/rendering` | pass | 26 pass |
| `bun run e2e` in `apps/viewer` (Playwright 1.65.1 on Bun) | pass | 39 passed, 3 skipped; the same 3 skip on Node on `main` |
| `make check` | pass | Python 51 passed, 1 skipped, 1 xfailed; fixtures match the generator |
| `make build` + `make size-check` | pass | |

Bun used: `1.4.6-canary.1+25c4fca9e`.

## Generated artifacts

none

## Decisions and assumptions

- ADR 0009 (proposed): Bun for lint, format, types and Playwright. It supersedes the "Playwright runs on Node" line
  of ADR 0001 and recommendation (E) of `docs/research/04-rendering-viewer-toolchain.md`.
- Viewer style: single quotes, no semicolons, as the code was written; 120 columns, as the renderer.
- `bun lint` uses Bun's defaults (ESLint and typescript-eslint recommended) with `--deny-warnings`, as Biome ran with
  `--error-on-warnings`.

## Contract change requests

none

## Known problems and unresolved issues

- `bun lint` only exists in Bun canary. The `js` job of `ci.yml` and the deploy job install `canary` until a stable
  Bun ships it. The integration job keeps 1.4.4.
- CI has not run on this branch: nothing was pushed.

## Human approvals needed

- The architect approves ADR 0009.
- The integrator merges `feature/wp09-bun-tooling` into `main` (`--no-ff`), after a review by a model from another
  provider.

## Recommended next task

Move the `js` and deploy jobs from `canary` to the first stable Bun that ships `bun lint`.
