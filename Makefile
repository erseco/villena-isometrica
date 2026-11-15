# Villena Isométrica — common operations. `make help` lists targets.
# Bootstrap targets only; WP07 adds install / lint / test / build / render / check / size-check.

WORKTREE_ROOT ?= ../villena-isometrica-worktrees

.PHONY: help fixtures validate-contracts check worktree

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 22

fixtures: ## Regenerate the synthetic fixtures (must leave `git status` clean)
	uv run --quiet scripts/make_fixtures.py

validate-contracts: ## Validate schemas, fixtures and city configs
	uv run --quiet scripts/validate_contracts.py

check: validate-contracts ## Everything that must pass before a handoff (WP07 extends this)

worktree: ## Create a task worktree: make worktree WP=03-gis-pipeline
	@test -n "$(WP)" || { echo "usage: make worktree WP=<nn-slug>"; exit 1; }
	git worktree add "$(WORKTREE_ROOT)/wp$(WP)" -b "agent/wp$(WP)" main
	@echo "cd $(WORKTREE_ROOT)/wp$(WP)"
