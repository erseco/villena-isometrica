@AGENTS.md

## Claude Code only

- Model and effort for a work package come from its prompt, e.g.
  `claude --model claude-opus-5-5 --effort high`. Pin full model IDs, not aliases.
- Role subagents live in `.claude/agents/`. Use `qa-reviewer` and `licensing-security-reviewer`
  for review passes; they must not edit source.
- `claude --worktree` cannot start from a named branch. Create the task worktree with
  `make worktree WP=<nn-slug>` and start `claude` inside it.
- Claude Code cannot invoke Codex, Gemini or DeepSeek on the owner's subscriptions. Hand work
  to them through the prompt files and Git, as described in `docs/AGENT_ROUTING.md`.
