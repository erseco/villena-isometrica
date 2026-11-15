# 06 — Agent clients, model IDs and GitHub hosting limits

**Verification date: 2026-11-15.** Everything below was checked on that date against the cited official page, or against a locally installed CLI (`claude` 2.1.325, `codex-cli` 0.169.0). `gemini` is **not installed** on this machine, so every Gemini CLI claim is docs/source-only.

Conventions: **[V]** verified against the cited source today. **[L]** verified against the local CLI binary. **[U]** not verified — do not use in config without checking. Section 8 collects every **[U]**.

Note on OpenAI URLs: `developers.openai.com/codex/*` now answers `308 Permanent Redirect` to `learn.chatgpt.com/docs/*`. The redirect targets were followed and are the URLs cited here.

---

## 0. Model routing table

| Requested | Verified ID | Client | Effort values | Fallback | Status |
|---|---|---|---|---|---|
| Claude Fable 5.2 | `claude-fable-5-2` (alias `fable`) | Claude Code | `low` `medium` `high` `xhigh` `max` (default `medium`) | `claude-opus-5-5` | [V] |
| Claude Opus 5.5 | `claude-opus-5-5` (alias `opus`) | Claude Code | `low` `medium` `high` `xhigh` `max` (default `medium`) | `claude-sonnet-5-5` | [V] |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` (alias `sonnet`) | Claude Code | `low` `medium` `high` `xhigh` `max` (default `medium`) | `claude-haiku-5-5` | ID from session context; alias→Sonnet 5.5 and effort levels [V]; the literal string `claude-sonnet-5-5` was not seen on a docs page today |
| (Claude Haiku 5.5) | `claude-haiku-5-5` (alias `haiku`) | Claude Code | `low` `medium` `high` `xhigh` `max` (default `medium`) | — | [V] |
| "Codex Sol" | `gpt-6.1-sol` (recommended default). Also in the local catalog: `gpt-6-sol`, `gpt-5.6-sol` | Codex CLI | `low` `medium` `high` `xhigh` `max` `ultra` | `gpt-6-sol` | [V] docs + [L] catalog. Which "Sol" the owner means is ambiguous → assume `gpt-6.1-sol` |
| "Codex Terra" | `gpt-6.1-terra` (needs Codex CLI ≥ 0.159.0). Also `gpt-5.6-terra` | Codex CLI | `low` `medium` `high` `xhigh` `max` `ultra` | `gpt-6-luna` | [V] + [L] |
| "Codex Luna" | `gpt-6-luna`. Also `gpt-5.6-luna` | Codex CLI | `low` `medium` `high` `xhigh` `max` (**no `ultra`**) | `gpt-5.6-luna` | [V] + [L] |
| Gemini 3.8 Flash | `gemini-3.8-flash` (Stable) | Gemini CLI (`-m`/`--model`) | No named effort flag. `thinkingConfig` in `settings.json` (`thinkingBudget` documented; `thinkingLevel` values **[U]**) | `gemini-3.6-flash`, `gemini-3.5-flash` | ID [V] (Google model list + gemini-cli source). Whether the owner's plan still gets Gemini CLI is **[U]** (see §3.6) |
| DeepSeek V4.1 Flash | `deepseek-flash` (= DeepSeek-V4.1-Flash-1017) | API only: Claude Code via Anthropic endpoint, Codex via custom provider, DeepSeek Harness | `low` `high` `max` (default `high`; `medium`/`xhigh`→`high`, `ultra`→`max`) | legacy alias `deepseek-v4-flash` still accepted, routed to the same model | [V] |
| DeepSeek V4 Pro | `deepseek-v4-pro` (= DeepSeek-V4-Pro-0813, text-only) | same as above | `low` `high` `max` (default `high`) | `deepseek-flash` | [V] |

Sources: Claude https://code.claude.com/docs/en/model-config · Codex https://learn.chatgpt.com/docs/models + `codex debug models` · Gemini https://aistudio.google.com/docs/models + https://raw.githubusercontent.com/google-gemini/gemini-cli/main/packages/core/src/config/models.ts · DeepSeek https://api-docs.deepseek.com/quick_start/pricing + https://api-docs.deepseek.com/guides/thinking_mode

---

## 1. Claude Code

### 1.1 Subagent files — `.claude/agents/*.md`

Source: https://code.claude.com/docs/en/sub-agents [V]

Markdown with YAML frontmatter; the body is the system prompt. Only `name` and `description` are required. Field names are camelCase and must match exactly; **unrecognized fields are ignored silently** (so a typo will not error).

| Field | Allowed values / notes |
|---|---|
| `name` (required) | ≤ 256 chars, no `:`. Filename need not match |
| `description` (required) | When Claude should delegate to it |
| `tools` | Comma-separated string (`Read, Grep, Bash`) or YAML list. Omitted = inherit all |
| `disallowedTools` | Same format. An entry with a specifier such as `Bash(git push *)` still removes the **whole** tool |
| `model` | `sonnet`, `opus`, `haiku`, `fable`, a full ID such as `claude-opus-5-5`, or `inherit` |
| `effort` | `low`, `medium`, `high`, `xhigh`, `max`. Overrides session effort, but not `CLAUDE_CODE_EFFORT_LEVEL` |
| `permissionMode` | `default` (alias `manual`), `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` |
| `isolation` | `worktree` (only value) |
| `skills` | Skills preloaded in full at startup |
| `maxTurns` | Positive integer |
| `autoCompactWindow` | Integer `100000`–`1000000` (v2.1.296+) |
| `mcpServers` | Server name, or inline definition |
| `hooks` | Lifecycle hooks scoped to the subagent |
| `memory` | `user`, `project`, `local` |
| `background` | `true` / `false` |
| `omitClaudeMd` | `true` / `false` (v2.1.271+) |
| `color` | `red` `blue` `green` `yellow` `purple` `orange` `pink` `cyan` |
| `initialPrompt` | Only used when run as main agent via `--agent` |
| `experimental` | Map; `cacheTtl: 5m` or `1h` |

There is **no** `reasoning` key; the key is `effort`.

Location priority (highest first): managed settings → `--agents` CLI JSON → `.claude/agents/` → `~/.claude/agents/` → plugin `agents/`.

```markdown
---
name: tile-reviewer
description: Reviews tile-pipeline changes for correctness. Use after any change under tools/tiles.
tools: Read, Glob, Grep, Bash
model: claude-sonnet-5-5
effort: high
permissionMode: default
---

You review changes to the tile pipeline. Do not edit files. Report findings with file paths.
```

### 1.2 `CLAUDE.md` imports and `AGENTS.md`

Source: https://code.claude.com/docs/en/memory [V]

- Import syntax is `@path/to/file`. Relative paths resolve **from the file containing the import**, not the working directory. Absolute and `@~/...` paths are allowed.
- Recursive imports: **maximum depth of four hops**.
- Imports inside Markdown code spans and fenced code blocks are **not** expanded. Quoted paths are not imported. Spaces need a backslash.
- An import that resolves outside the working directory triggers a one-time approval dialog per project.
- Imports do not save context: the imported file loads in full alongside the importer. Target is under 200 lines per `CLAUDE.md`.
- **Claude Code reads `AGENTS.md` natively** (v2.1.277+), but by default **only when there is no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md`** in the working directory or above. If a `CLAUDE.md` exists, only `CLAUDE.md` is read — unless it imports `AGENTS.md`.
- The setting "Project instructions" has the values `claude-md-or-agents-md` (default), `claude-md-and-agents-md`, `claude-md`, `managed-only`. It is honoured only from user settings, `--settings` or managed settings — **not from project settings**, so the repo cannot force it.
- Importing and native reading never double-load: "Keeping the import never makes Claude read `AGENTS.md` twice".

Conclusion for this repo: since we want a `CLAUDE.md` with Claude-specific notes, it **must** start with the import.

```markdown
@AGENTS.md

## Claude Code only
- Use the subagents in `.claude/agents/` for review work.
```

A `ln -s AGENTS.md CLAUDE.md` symlink is also documented, but the docs advise the import instead when anyone may clone on Windows.

### 1.3 Model and effort per session

Source: https://code.claude.com/docs/en/model-config [V]; flags confirmed in `claude --help` [L]

- Model: `/model <alias|name>`, `claude --model <alias|name>`, `ANTHROPIC_MODEL`, or `"model"` in settings. Aliases update over time; pin with the full ID.
- Effort: `/effort <level>`, `claude --effort <level>` (`low, medium, high, xhigh, max`), `CLAUDE_CODE_EFFORT_LEVEL`, the `effortLevel` setting, or `effort` in skill/subagent frontmatter.
- Precedence: `CLAUDE_CODE_EFFORT_LEVEL` → in-session choice → `--effort` → settings → model default.
- The settings keys `effortLevel` / `modelSettings` accept `low`–`xhigh` only; **`max` is not accepted there**.
- Unsupported level falls back to the highest supported level at or below it.

```bash
claude --model claude-opus-5-5 --effort high
```

### 1.4 Worktrees

Source: https://code.claude.com/docs/en/worktrees [V]; `-w, --worktree [name]` in `claude --help` [L]

- `claude --worktree <name>` (or `-w`) creates `.claude/worktrees/<name>/` on a new branch `worktree-<name>`. Name omitted = generated name.
- Base is the remote default branch (`worktree.baseRef: "fresh"`, default) or local `HEAD` (`"head"`). **A branch name is not accepted**; to start from a specific branch use `git worktree add` and run `claude` inside it.
- `claude --worktree "#1234"` branches from a PR.
- `.worktreeinclude` (gitignore syntax) copies gitignored files such as `.env` into new worktrees.
- Add `.claude/worktrees/` to `.gitignore`.
- Subagents: `isolation: worktree` in frontmatter.
- LFS repos set up with `git lfs install --local` get pointer files in Claude-created worktrees; run `git lfs pull` there.

---

## 2. OpenAI Codex CLI

### 2.1 `AGENTS.md` discovery

Source: https://learn.chatgpt.com/docs/agent-configuration/agents-md [V]

- Global: `~/.codex/AGENTS.override.md`, then `~/.codex/AGENTS.md`; first non-empty one only.
- Project: from the project root (normally the Git root) down to the current directory. In each directory: `AGENTS.override.md`, then `AGENTS.md`, then any `project_doc_fallback_filenames`. At most one file per directory.
- Files are concatenated root → cwd; closer files come later and so win.
- Combined size is capped by `project_doc_max_bytes`, default **32 KiB**. Content beyond the cap is dropped — keep `AGENTS.md` small.

### 2.2 Config, profiles, model, effort

Sources: https://learn.chatgpt.com/docs/config-file/config-reference , https://learn.chatgpt.com/docs/config-file/config-advanced [V]; flags in `codex --help` [L]

- User config: `~/.codex/config.toml`. Project config: `.codex/config.toml`, discovered from project root to cwd, **loaded only when the project is trusted** (`projects.<path>.trust_level = "trusted"`).
- Project config **cannot** set `model_provider`, `model_providers`, `profile`, `profiles`, `openai_base_url`, `notify`, `otel` (ignored with a warning).
- **Profiles changed.** Since Codex 0.134.0 a profile is a separate file `~/.codex/<name>.config.toml` selected with `codex --profile <name>`. `[profiles.<name>]` tables and the top-level `profile = "..."` key are **no longer read**. Profiles are user-level only, so they cannot be committed to the repo as working config — only documented.
- `model` — string, e.g. `gpt-6.1-sol`. CLI: `codex -m <id>` / `codex exec -m <id> "..."`.
- `model_reasoning_effort` — string; "`low` through `ultra`", depends on model. Local catalog: `low`, `medium`, `high`, `xhigh`, `max`, `ultra` (Luna stops at `max`). `ultra` uses subagents for parallel work.
- Also: `model_reasoning_summary` (`auto|concise|detailed|none`), `model_verbosity` (`low|medium|high`), `plan_mode_reasoning_effort`, `review_model`.
- One-off override: `codex -c model_reasoning_effort="high"`.

```toml
# .codex/config.toml  (project, loaded only if trusted)
model = "gpt-6.1-sol"
model_reasoning_effort = "medium"
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[agents]
max_concurrent_threads_per_session = 4
```

```toml
# ~/.codex/deep.config.toml  (user profile: codex --profile deep)
model = "gpt-6.1-sol"
model_reasoning_effort = "xhigh"
```

Models currently offered (local catalog, visible): `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-daybreak-blue-latest`. The docs recommend Astra, 6.1 Sol, 6.1 Terra and 6 Luna. Retired: `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex-spark`.

### 2.3 Custom agents — `.codex/agents/*.toml`

Source: https://learn.chatgpt.com/docs/agent-configuration/subagents [V]

**`.codex/agents/` is real.** Format is **TOML, one agent per file** (not Markdown). Personal agents live in `~/.codex/agents/`. The `name` field, not the filename, identifies the agent. Enabled by default (`agents.enabled = true`, `features.multi_agent` on).

- Required keys: `name`, `description`, `developer_instructions`.
- Optional: `model`, `model_reasoning_effort`, `model_reasoning_summary`, `model_verbosity`; `features.*` set to `false` to reduce capability; `skills.config`.
- **Ignored inside an agent file** (they do not override the parent): `sandbox_mode`, `approval_policy`, `model_provider`, `mcp_servers`. So "read-only" must be stated in `developer_instructions` or enforced by the parent session's sandbox.
- Built-ins: `default`, `worker`, `explorer`. A custom agent with the same name wins.
- Invocation: name it in the prompt ("Have reviewer find real risks…"). `/subagents` inspects running threads.
- `[agents]` keys: `enabled`, `max_concurrent_threads_per_session` (`max_threads` is a legacy alias), `default_subagent_model`, `default_subagent_reasoning_effort`, `interrupt_message`.

```toml
# .codex/agents/reviewer.toml
name = "reviewer"
description = "PR reviewer focused on correctness, security, and missing tests."
model = "gpt-6.1-sol"
model_reasoning_effort = "medium"
developer_instructions = """
Review code like an owner.
Do not edit files.
Prioritize correctness, security, behavior regressions, and missing test coverage.
"""
```

### 2.4 Skills and custom prompts

Source: https://learn.chatgpt.com/docs/build-skills [V]

- Skills: `<repo>/.agents/skills/<name>/SKILL.md` (every directory from cwd up to the repo root), `$HOME/.agents/skills`, `/etc/codex/skills`, plus bundled ones. Note the directory is **`.agents/`, not `.codex/`**.
- `SKILL.md` needs frontmatter `name` and `description`. Invoke with `/skills` or `$skill-name`.
- Custom prompts (`~/.codex/prompts/*.md`): the current docs no longer describe them. A maintainer comment in https://github.com/openai/codex/issues/15941 says they were removed in 0.117.0 — **[U]** from official docs, so do not plan on them. Use skills.

### 2.5 Sandbox and approvals

Source: config reference above [V]; `codex --help` [L]

- `sandbox_mode` / `-s`: `read-only`, `workspace-write`, `danger-full-access`.
- `approval_policy` / `-a`: `on-request`, `never`, or `{ granular = { ... } }`. **`untrusted` is unsupported and `on-failure` is deprecated.**
- `sandbox_workspace_write.network_access` (bool), `.writable_roots`, `.exclude_slash_tmp`, `.exclude_tmpdir_env_var`.
- `web_search`: `disabled`, `cached` (default), `indexed`, `live`.
- `codex --worktree` runs the session in a new managed Git worktree [L] (no details verified in docs).

---

## 3. Gemini CLI

### 3.1 `GEMINI.md` discovery and imports

Sources: https://geminicli.com/docs/cli/gemini-md/ , https://geminicli.com/docs/reference/memport/ [V]

- Global `~/.gemini/GEMINI.md`; workspace directories and their parents; plus just-in-time loading of `GEMINI.md` near files a tool touches, up to a trusted root.
- Import syntax `@./file.md`, `@../file.md`, `@/abs/path.md`. Default **maximum depth 5**, circular imports detected, `@` inside code blocks/spans ignored, paths validated against allowed directories.
- `/memory show` prints what was loaded; `/memory reload` rescans.

### 3.2 Loading `AGENTS.md`

Sources: https://geminicli.com/docs/reference/configuration/ , https://agents.md/ [V]

`context.fileName` accepts a string or an array.

```json
{
  "context": {
    "fileName": ["AGENTS.md", "GEMINI.md"]
  }
}
```

Saved as `.gemini/settings.json` (project). With this, `GEMINI.md` can hold Gemini-only notes, or import with `@./AGENTS.md` if the setting is not used. Do not do both, or `AGENTS.md` loads twice (inference, not documented).

### 3.3 Custom commands

Source: https://geminicli.com/docs/cli/custom-commands/ [V]

`<project>/.gemini/commands/**/*.toml` and `~/.gemini/commands/`. Subdirectories become namespaces (`git/commit.toml` → `/git:commit`). Keys: `prompt` (required), `description`. Placeholders: `{{args}}`, `!{shell}`, `@{path}`.

```toml
# .gemini/commands/task/start.toml  ->  /task:start <file>
description = "Start a task prompt from docs/tasks."
prompt = """Read and execute this task:
@{docs/tasks/{{args}}}"""
```

### 3.4 Subagents

Source: https://geminicli.com/docs/core/subagents/ [V]

`.gemini/agents/*.md` (project) and `~/.gemini/agents/*.md`. Markdown with YAML frontmatter; body is the system prompt. Enabled by default (`experimental.enableAgents`, default `true`). Force with `@name`.

Keys: `name` (required, lowercase/digits/`-`/`_`), `description` (required), `kind` (`local` default | `remote`), `tools` (wildcards `*`, `mcp_*`), `mcpServers`, `model` (default `inherit`), `temperature` (0.0–2.0), `max_turns` (default 30), `timeout_mins` (default 10). `/model` and `--model` do **not** change a subagent's model.

```markdown
---
name: asset-checker
description: Checks generated tile assets for naming and size problems.
tools:
  - read_file
  - grep_search
model: gemini-3.8-flash
max_turns: 20
---

Check assets under public/tiles. Do not modify files.
```

Tool names in this example are **[U]** (not checked against the tools reference).

### 3.5 Model and thinking

Sources: https://geminicli.com/docs/cli/model/ , configuration reference, models.ts, https://aistudio.google.com/docs/models [V]

- Selection: `--model` flag, `/model`, `model.name` in settings, `GEMINI_MODEL`.
- `gemini-3.8-flash` exists and is **Stable**; it is `LATEST_GEMINI_FLASH_MODEL` in the CLI source. The `flash` alias resolves to it only behind a flag, so **pass the full ID**.
- Other current IDs: `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gemini-4-carbon`, `gemini-4-argon`, `gemini-4-hydrogen`. `gemini-3-pro-preview` is listed as shut down.
- Thinking: no CLI flag. Set `generateContentConfig.thinkingConfig` through `modelConfigs.overrides` / `customAliases`. `thinkingBudget` and `includeThoughts` are documented; `thinkingLevel: "HIGH"` appears in a built-in alias, but the list of allowed values is **[U]**.

```bash
gemini --model gemini-3.8-flash
```

### 3.6 Availability warning

Source: https://geminicli.com/docs/ [V] — "Unpaid tier and Google One users: Gemini CLI was replaced by Antigravity CLI on June 18th, 2026." and "Gemini CLI has not been optimized for Gemini 4 Argon."

The docs do not say which plans still get Gemini CLI. If the owner's Gemini access is a Google One subscription, the client may be Antigravity CLI, whose instruction-file and config formats were **not researched** here. **[U]** — owner must run `gemini --version` and confirm login works before any `GEMINI.md`/`.gemini/` work is planned.

---

## 4. DeepSeek

Sources: https://api-docs.deepseek.com/ , https://api-docs.deepseek.com/quick_start/pricing , https://api-docs.deepseek.com/guides/thinking_mode , https://api-docs.deepseek.com/guides/anthropic_api [V]

- API IDs: **`deepseek-flash`** (DeepSeek-V4.1-Flash-1017, vision) and **`deepseek-v4-pro`** (DeepSeek-V4-Pro-0813, no vision). 1M context each. `deepseek-v4-flash` is a legacy name, still accepted, routed to V4.1 Flash. There is **no** `deepseek-v4.1-flash` ID.
- Base URLs: `https://api.deepseek.com` (OpenAI format, includes Responses API) and `https://api.deepseek.com/anthropic`.
- Thinking is on by default. Toggle `{"thinking": {"type": "enabled"|"disabled"}}`. Effort: `reasoning_effort` = `low` / `high` / `max` (OpenAI format) or `output_config.effort` (Anthropic format). Default `high`. Other names are mapped: `minimal`→`low`; `medium`,`xhigh`→`high`; `ultra`→`max`. `temperature` is fixed in thinking mode.
- On the Anthropic endpoint, `claude-opus*` maps to `deepseek-v4-pro`; `claude-sonnet*`, `claude-haiku*` and other `claude*` map to `deepseek-flash`. `cache_control`, `budget_tokens`, `mcp_servers` are ignored.

**First-party coding client:** no "DeepSeek CLI" is documented. The official docs link **DeepSeek Harness** (https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart , repo under the `deepseek-ai` GitHub org): a web UI/CLI agent, authenticated with an **API key**. Its instruction-file support (AGENTS.md?) is **[U]**.

**Claude Code** — https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code [V]

```bash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=<your DeepSeek API Key>
export ANTHROPIC_MODEL=deepseek-flash[1m]
export ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-flash[1m]
export ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-flash[1m]
export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-flash
export CLAUDE_CODE_SUBAGENT_MODEL=deepseek-flash
export CLAUDE_CODE_EFFORT_LEVEL=max
export CLAUDE_CODE_AUTO_COMPACT_WINDOW=786432
```

For V4 Pro, set the model variables to `deepseek-v4-pro` (the `[1m]` suffix on Pro is **[U]**; the official page only shows it on Flash). These variables redirect the whole process, so run them in a dedicated shell — never in the shell used for the Claude subscription. In such a session `.claude/agents/*.md` with `model: claude-opus-5-5` would be remapped by prefix to `deepseek-v4-pro` and billed as Pro.

**Codex** — https://api-docs.deepseek.com/quick_start/agent_integrations/codex [V]: user-level `~/.codex/config.toml` with `model_provider = "deepseek"`, `[model_providers.deepseek]` (`base_url = "https://api.deepseek.com/"`, `wire_api = "responses"`), plus a `model_catalog_json` file written by DeepSeek's setup script. It must be user-level (project config cannot set providers); put it in a profile file such as `~/.codex/deepseek.config.toml` to keep the ChatGPT login intact (profile use is my inference from §2.2, not shown on the DeepSeek page). Other documented integrations: OpenCode, OpenClaw, Hermes, Reasonix, WorkBuddy/CodeBuddy, Qoder.

**Billing:** every path above uses **metered API credits** (per-token, peak/off-peak pricing), not a chat subscription. No official DeepSeek page describing a chat or coding subscription was found; third-party articles say DeepSeek is pay-as-you-go only. **[U]** what the owner's "subscription" actually is. **No documented subscription-only path exists** other than pasting prompts into the chat UI and applying the result by hand. Realistic options: (a) buy a small API balance — Flash is $0.15–0.30 per 1M input tokens — and use Claude Code or Codex as the client; (b) treat DeepSeek as a chat-only reviewer fed with Markdown prompts and diffs.

---

## 5. GitHub Pages, Actions, Releases, LFS

### 5.1 Pages limits

Source: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits [V]

| Limit | Value |
|---|---|
| Published site | **≤ 1 GB** |
| Source repository | 1 GB recommended |
| Deployment | times out after **10 minutes** |
| Bandwidth | **100 GB/month**, soft |
| Builds | 10/hour, soft — **does not apply** to custom Actions workflows |
| Rate limiting | HTTP 429 possible |
| Use | not for running an online business; no sensitive transactions |

Per-file / repo (https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github [V]): Git warns above **50 MiB**, GitHub **blocks files above 100 MiB**, browser upload limit 25 MiB; repos ideally < 1 GB, < 5 GB strongly recommended. There is no separate documented per-file limit for Pages artifacts built in Actions.

Pages artifact (https://github.com/actions/upload-pages-artifact README, https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages [V]): a gzip containing a single tar, named `github-pages`, **no symbolic or hard links**, absolute cap 10 GB but the supported maximum is 1 GB. Hidden files are excluded by default (`include-hidden-files: false`); artifact retention defaults to 1 day.

### 5.2 Base path

Source: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages [V]

A project site is served at `https://<owner>.github.io/<repositoryname>`, i.e. under the sub-path `/<repositoryname>/`, one site per repository. Root-absolute URLs (`/tiles/...`) will break; use relative URLs or a configurable base. `actions/configure-pages` exposes `base_path` (e.g. `/my-repo` or empty) and `base_url` outputs so the build does not hard-code it. For this repo the expected path is `/villena-isometrica/` (derived; changes if a custom domain is added).

### 5.3 Deploy workflow

Action versions: the docs page shows `actions/checkout@v6`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v4`, `actions/deploy-pages@v4`. The **latest releases** (GitHub API, today) are `configure-pages` **v6.0.0**, `upload-pages-artifact` **v5.0.0**, `deploy-pages` **v5.0.1**, `checkout` **v7.0.1**, and the major tags `v6` / `v5` / `v5` / `v7` exist. The official starter workflow (https://github.com/actions/starter-workflows/blob/main/pages/static.yml) mixes yet other versions. Docs and releases disagree; the snippet uses the latest majors. The docs versions are the conservative alternative.

Required: `permissions: pages: write` and `id-token: write` on the deploy job; `environment: github-pages` ("The default environment is `github-pages`").

```yaml
name: Deploy Pages
on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - id: pages
        uses: actions/configure-pages@v6
      # build here, passing ${{ steps.pages.outputs.base_path }} to the bundler
      - uses: actions/upload-pages-artifact@v5
        with:
          path: dist

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
```

### 5.4 Ensuring PRs never deploy

1. The deploy workflow has **no `pull_request` trigger** (only `push` to `main` and `workflow_dispatch`).
2. PR checks live in a separate workflow with `permissions: contents: read` and no Pages actions.
3. Guard the deploy job with `if: github.ref == 'refs/heads/main'` (covers `workflow_dispatch` run from another branch).
4. In Settings → Environments → `github-pages`, restrict deployment branches to the default branch. GitHub recommends exactly this: "only the default branch can deploy to this environment" (https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site ; options described in https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments ) [V].

`deploy-pages` has a `preview` input for PR previews, marked alpha and not publicly available — do not use.

### 5.5 Releases, Actions minutes, LFS

- **Releases** (https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases [V]): each asset **< 2 GiB**, up to 1000 assets per release, no limit on total release size or bandwidth. Suitable for large tile archives. Whether release assets can be fetched by browser JS from the Pages origin (CORS) was **not checked** — **[U]**; assume releases are for download/rebuild, not runtime tile serving.
- **Actions** (https://docs.github.com/en/billing/concepts/product-billing/github-actions [V]): standard GitHub-hosted runners in **public repositories are free** and do not consume the included allowance. Larger runners are billed even in public repos.
- **Git LFS** (https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage [V]): "Git LFS cannot be used with GitHub Pages sites." LFS per-file limit on Free/Pro is 2 GB. An Actions build could check out LFS objects and copy them into the artifact, but that is a workaround not covered by the docs (**[U]**), and LFS has its own storage/bandwidth quotas (not researched).

---

## 6. Cross-tool standard: `AGENTS.md`

Source: https://agents.md/ [V]

- Plain Markdown, no required fields or schema. Stewarded by the Agentic AI Foundation under the Linux Foundation.
- Nested files allowed; the nearest file to the edited code wins; explicit user prompts override everything.
- Listed as supported by Codex, Gemini CLI, Cursor, Copilot coding agent, Aider, opencode, Zed, and others. Claude Code is not on that list but documents native support itself (§1.2).

How each client reaches the canonical file:

| Client | Mechanism | In-repo file |
|---|---|---|
| Codex | native | `AGENTS.md` |
| Claude Code | `@AGENTS.md` import (native read is skipped once `CLAUDE.md` exists) | `CLAUDE.md` |
| Gemini CLI | `context.fileName` | `.gemini/settings.json` (+ optional `GEMINI.md`) |
| DeepSeek via Claude Code / Codex | same as the host client | — |
| DeepSeek chat UI | paste | task prompt must be self-contained |

Practical rules:

1. `AGENTS.md` is the only place for shared rules. `CLAUDE.md` and `GEMINI.md` hold only the import/pointer plus client-specific notes.
2. Keep `AGENTS.md` well under **32 KiB** (Codex cap) and preferably under ~200 lines (Claude guidance). Put long material in `docs/` and reference it by path; agents read on demand.
3. Do not use `@path` inside `AGENTS.md` expecting import behaviour everywhere: Claude and Gemini expand it, Codex is not documented to. Write plain paths.
4. Agent role definitions cannot be shared: Claude `.claude/agents/*.md` (YAML frontmatter), Codex `.codex/agents/*.toml`, Gemini `.gemini/agents/*.md` (different keys). Keep the role text short and point each at the same doc under `docs/`.
5. Skills use `SKILL.md` in both Claude Code (`.claude/skills/`) and Codex (`.agents/skills/`), but in different directories.
6. Use full model IDs in committed files, never aliases, and record the verification date beside them.

---

## 7. Config formats at a glance

| File | Format | Verified |
|---|---|---|
| `AGENTS.md` | free Markdown | [V] |
| `CLAUDE.md` | Markdown, first line `@AGENTS.md` | [V] |
| `.claude/agents/<name>.md` | YAML frontmatter + Markdown body | [V] |
| `.codex/config.toml` | TOML, trusted projects only, no provider/profile keys | [V] |
| `.codex/agents/<name>.toml` | TOML: `name`, `description`, `developer_instructions` (+ `model`, `model_reasoning_effort`) | [V] |
| `~/.codex/<profile>.config.toml` | TOML, user-level only | [V] |
| `.agents/skills/<name>/SKILL.md` | Codex skills | [V] |
| `GEMINI.md` | Markdown, `@./file.md` imports | [V] docs only |
| `.gemini/settings.json` | JSON, `context.fileName` | [V] docs only |
| `.gemini/commands/**/*.toml` | TOML: `prompt`, `description` | [V] docs only |
| `.gemini/agents/<name>.md` | YAML frontmatter + Markdown body | [V] docs only |

---

## 8. Not verified / unresolved

1. **Gemini CLI availability for the owner's plan.** Replaced by Antigravity CLI for unpaid and Google One users on 2026-06-18. `gemini` is not installed locally. Antigravity CLI formats were not researched.
2. **Gemini `thinkingLevel` allowed values**, and whether `gemini-3.8-flash` accepts `thinkingLevel` or `thinkingBudget`.
3. **Gemini subagent tool names** used in the §3.4 example.
4. **The string `claude-sonnet-5-5`** was not seen verbatim on a docs page today (pattern and alias confirmed; ID taken from session context).
5. **Which "Sol/Terra" generation the owner means** (`gpt-6.1-*` vs `gpt-6-sol` vs `gpt-5.6-*`) and which of them the owner's plan includes. The docs note that `gpt-6.1-sol` "requires specific account access".
6. **Codex custom prompts** (`~/.codex/prompts`): removal is stated only in a GitHub issue comment, not in current docs.
7. **`codex --worktree`** behaviour (location, branch naming): flag exists locally, docs not checked.
8. **DeepSeek "subscription"**: no official subscription product found. What the owner has is unknown. No subscription-only agentic path is documented.
9. **DeepSeek Harness**: official status inferred from the docs link and the `deepseek-ai` org; whether it reads `AGENTS.md` is unknown.
10. **`deepseek-v4-pro[1m]`** suffix in Claude Code, and effort values accepted by `output_config.effort` beyond `low/high/max`.
11. **Pages action versions**: docs (v5/v4/v4) and latest releases (v6/v5/v5) disagree; neither combination was run.
12. **Release assets as runtime tile source** (CORS, redirects) and **LFS quotas / LFS-in-Actions workaround**.
13. **Fork PR token behaviour** and exact failure mode when an environment rejects a ref.
14. Loading `AGENTS.md` twice in Gemini (via both `context.fileName` and an `@` import) is assumed, not documented.
