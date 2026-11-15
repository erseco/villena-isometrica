# Handoff — WPxx <title>

Copy this file to `docs/handoffs/WPxx-<slug>.md` (one file per task; a re-run appends a dated
section to the same file). Fill in every field. Write "none" rather than deleting a field.
Report what actually happened, including failures.

| Field | Value |
|---|---|
| Task ID | WPxx |
| Date (UTC) | YYYY-MM-DD |
| Provider / client | e.g. OpenAI Codex CLI 0.x |
| Model and effort actually used | exact model ID, effort |
| Branch | `feature/wpxx-<slug>` |
| Base commit | `git merge-base main HEAD` |
| Head commit | hash, or "uncommitted" |
| Status | READY FOR REVIEW / BLOCKED / PARTIAL |

## Changed files

Output of `git diff --stat <base>..HEAD`, plus one line per file that needs explanation.

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `make ...` | pass / fail / not run | paste the failing output below the table |

## Generated artifacts

Path, size, sha256 (for anything outside Git, also say how to regenerate it).

## Decisions and assumptions

Anything a reviewer would not guess from the diff. Decisions that affect other work packages
need an ADR in `docs/decisions/` — link it here.

## Contract change requests

Needed changes to `docs/contracts/` or `packages/geo-contracts/` that you did NOT make
(only the integrator edits contracts). Schema, field, reason.

## Known problems and unresolved issues

## Human approvals needed

## Recommended next task
