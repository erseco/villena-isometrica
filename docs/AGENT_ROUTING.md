# Agent routing

Which model does what, how to start it, and what to do when it is not available.
Model IDs and config formats were verified on 2026-11-15; evidence and caveats are in
`docs/research/06-agent-clients-and-github.md`. Re-verify before relying on an ID months later.

## Models

| Role in this project | Client | Model ID | Effort values | Start command |
|---|---|---|---|---|
| Fable 5.2 — architect | Claude Code | `claude-fable-5-2` | low, medium, high, xhigh, max | `claude --model claude-fable-5-2 --effort high` |
| Opus 5.5 — GIS, hard algorithms | Claude Code | `claude-opus-5-5` | same | `claude --model claude-opus-5-5 --effort high` |
| Sonnet 5.5 — frontend, routine | Claude Code | `claude-sonnet-5-5` | same | `claude --model claude-sonnet-5-5 --effort medium` |
| Codex Sol — renderer, integration | Codex CLI | `gpt-6.1-sol` | low, medium, high, xhigh, max, ultra | `codex -m gpt-6.1-sol -c model_reasoning_effort="high"` |
| Codex Terra — visual QA | Codex CLI | `gpt-6.1-terra` | same | `codex -m gpt-6.1-terra -c model_reasoning_effort="medium"` |
| Codex Luna — tests, CI, docs | Codex CLI | `gpt-6-luna` | low … max (no ultra) | `codex -m gpt-6-luna -c model_reasoning_effort="medium"` |
| Gemini 3.8 Flash — research, image comparison | Gemini CLI | `gemini-3.8-flash` | none (see `GEMINI.md`) | `gemini --model gemini-3.8-flash` |
| DeepSeek V4.1 Flash — batch checks | API or chat UI | `deepseek-flash` | low, high, max | see "DeepSeek" |
| DeepSeek V4 Pro — independent review | API or chat UI | `deepseek-v4-pro` | low, high, max | see "DeepSeek" |

Open points the owner must confirm (nobody can verify these from inside a session):

1. **Which "Sol"/"Terra" generation the Codex plan includes.** `gpt-6.1-sol` and
   `gpt-6.1-terra` are assumed; `gpt-6-sol` / `gpt-5.6-terra` also exist. Check with
   `codex debug models`.
2. **Whether Gemini CLI still works on the owner's plan.** `gemini` is not installed on the
   bootstrap machine, and Gemini CLI was replaced by Antigravity CLI for unpaid and Google One
   users on 2026-06-18. If only Antigravity or the Gemini web app is available, use the
   bundle path below.
3. **DeepSeek has no subscription-based coding client.** Every agentic route (Claude Code via
   `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`, Codex custom provider, DeepSeek
   Harness) bills metered API credits and therefore needs explicit owner approval. The
   zero-cost route is the chat UI with a context bundle.

## Routing by work package

| WP | Primary (effort) | Fallback | Escalate when |
|---|---|---|---|
| WP01 data research | Gemini 3.8 Flash (high) | Sonnet 5.5 (high) | a licence is ambiguous → architect + owner |
| WP02 math/architecture review | DeepSeek V4 Pro (high) | Codex Sol (high) | reviewer and architect disagree → second reviewer from a third provider |
| WP03 GIS pipeline | Opus 5.5 (high) | Codex Sol (high) | height estimation fails validation twice → xhigh |
| WP04 render engine | Codex Sol (high) | Opus 5.5 (high) | determinism cannot be achieved → architect (ADR) |
| WP05 viewer | Sonnet 5.5 (medium) | Codex Terra (medium) | picking/URL math bugs → high |
| WP06 tile export | Codex Sol (medium) | Sonnet 5.5 (medium) | pyramid edge cases fail → high |
| WP07 tooling, CI/CD | Codex Luna (medium) | Sonnet 5.5 (medium) | — |
| WP08 tests | Codex Luna (high) | DeepSeek V4.1 Flash (high) | — |
| WP09 visual QA | Codex Terra (medium) + Gemini 3.8 Flash (high) second opinion | Sonnet 5.5 (medium) | — |
| WP10 AI benchmark | Opus 5.5 (high) | Codex Sol (high) | any spend → owner |
| WP11 independent review | DeepSeek V4 Pro (high) + one reviewer from a provider that did not write the code under review | Codex Sol (high) for Claude-written code; Opus 5.5 (high) for Codex-written code | blocker findings → architect |
| WP12 integration, release | Codex Sol (high); approval by Fable 5.2 (high) | Opus 5.5 (high) | contract mismatch → architect |

Rules:

- A work package is never reviewed only by the provider that implemented it.
- `max` / `xhigh` / `ultra` only for a demonstrated blocker, recorded in the handoff.
- The handoff always states the model and effort **actually** used.
- If the primary is unavailable, use the fallback and say so in the handoff; do not wait.

## Starting a task

```sh
make worktree WP=03-gis-pipeline        # creates branch agent/wp03-gis-pipeline in its own worktree
cd ../villena-isometrica-worktrees/wp03-gis-pipeline
claude --model claude-opus-5-5 --effort high
# first message:  Read prompts/03-gis-pipeline.md and execute it.
```

Same for Codex and Gemini with their start command. One writing agent per worktree, always.

## Clients that cannot read the repository (chat UIs)

Each review/research prompt lists its context files. Build one message with:

```sh
scripts/make_context_bundle.sh prompts/02-architecture-review.md AGENTS.md docs/contracts/projection.md ... > /tmp/wp02-bundle.md
```

Paste it into the chat, save the answer verbatim as the handoff file named in the prompt
(`docs/handoffs/WPxx-....md`), add the header table from `docs/handoffs/TEMPLATE.md` by hand,
and commit on the task branch. Chat-only models produce reports and patches as text; a
repository-capable agent (or the owner) applies and tests any patch.

## DeepSeek through an agentic client (needs approval — metered)

Run in a **dedicated shell**, never the one used for the Claude subscription:

```sh
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=...          # from .env, never committed
export ANTHROPIC_MODEL=deepseek-v4-pro
claude
```

In such a session every `claude-*` model name is remapped to a DeepSeek model, including the
ones in `.claude/agents/`.
