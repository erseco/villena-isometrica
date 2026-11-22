# 0009 — Bun for lint, format, types and Playwright

Status: proposed (2026-11-22), pending the architect's approval. Supersedes the "Playwright runs on Node" line of
ADR 0001.

## Context

The JS packages used different tools for the same jobs. The viewer ran `tsc --noEmit` as its lint and had no
formatter or linter. The renderer ran Biome and `tsc`. Playwright ran on Node, as recommendation (E) of
`docs/research/04-rendering-viewer-toolchain.md` advised when Playwright's Bun support was three weeks old. Bun, already
the package manager, script runner and test runner (`bun test`) of both packages, now ships a linter (`bun lint`), a
formatter (`bun fmt`) and a type checker (`bun check`). Playwright 1.65 runs its test runner under Bun with
`bunx --bun`.

## Options

1. Keep the current mix (Biome + `tsc`, viewer without lint or format, Playwright on Node).
2. Bun for all of it.

## Decision

Option 2, in both packages:

- `bun run lint` = `bun lint --deny-warnings && bun fmt --check && bun check`, configured in each package's
  `bunfig.toml`. The renderer keeps Biome's style: 120 columns, single quotes. The viewer keeps its own: single quotes,
  no semicolons, also at 120 columns.
- The renderer's `build` (a type check) is `bun check`.
- The viewer's fixture script runs with `bun`. Its E2E suite and the `vite build`/`vite preview` web server run with
  `bunx --bun`.
- Removed: `@biomejs/biome` and `typescript` (both packages). Nothing else uses them.
- `bun lint` only exists in Bun canary so far, so the `js` job of `ci.yml` and the deploy job install `canary`. The
  integration job keeps Bun 1.4.4.

## Consequences

- One tool and one configuration file per package. `bun lint` checks each package in milliseconds.
- The viewer gets a linter and a formatter for the first time. The one-off reformat is a separate commit.
- CI depends on a canary until a stable Bun release ships `bun lint`. A canary regression can turn CI red without a
  repository change.
- Under Bun, Playwright has no watch mode and test console output is missing from traces. The suite used neither.
  The suite has no screenshot baselines; if pixel baselines are added later, the browser still renders them, not the
  runner.
