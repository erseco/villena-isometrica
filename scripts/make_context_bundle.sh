#!/bin/sh
# Concatenate files into one Markdown document for a model that cannot read the repository
# (e.g. a chat UI). Usage: scripts/make_context_bundle.sh prompts/02-architecture-review.md AGENTS.md ... > bundle.md
# The first file should be the task prompt. Paste the result as a single message.
set -eu
echo "# Context bundle — $(git rev-parse --short HEAD 2>/dev/null || echo no-git) — files are verbatim"
for f in "$@"; do
  [ -f "$f" ] || { echo "missing: $f" >&2; exit 1; }
  printf '\n\n<file path="%s">\n' "$f"
  cat "$f"
  printf '\n</file>\n'
done
