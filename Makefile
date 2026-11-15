# Villena Isométrica — common operations. GNU Make 3.81 compatible.
WORKTREE_ROOT ?= ../villena-isometrica-worktrees
CITY ?= villena
VITE_BASE ?= /villena-isometrica/
RELEASE ?= local

.PHONY: help fixtures fixtures-check validate-contracts check worktree install lint test e2e build scene render tiles validate-tiles site-tiles fetch-tiles size-check clean
help: ## List targets
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 22
fixtures: ## Regenerate synthetic fixtures (architect only)
	uv run --quiet scripts/make_fixtures.py
validate-contracts: ## Validate schemas, fixtures and city configs
	uv run --quiet scripts/validate_contracts.py
install: ## Install Python and available JS packages
	uv sync --project pipeline --frozen
	@for dir in apps/viewer pipeline/rendering; do if [ -f $$dir/package.json ]; then (cd $$dir && bun ci) || exit $$?; else echo "skipped: $$dir not present"; fi; done
lint: ## Lint available packages
	uv run --project pipeline --frozen ruff check pipeline
	@for dir in apps/viewer pipeline/rendering; do if [ -f $$dir/package.json ]; then (cd $$dir && bun run lint) || exit $$?; else echo "skipped: $$dir not present"; fi; done
test: ## Test available packages
	@if [ -d pipeline/tests ]; then PYTHONPATH=pipeline uv run --project pipeline --frozen pytest pipeline/tests; else echo 'skipped: pipeline/tests not present'; fi
	@for dir in apps/viewer pipeline/rendering; do if [ -f $$dir/package.json ]; then (cd $$dir && bun run test) || exit $$?; else echo "skipped: $$dir not present"; fi; done
e2e: ## Run viewer end-to-end tests
	@if [ -f apps/viewer/package.json ]; then cd apps/viewer && bun run e2e; else echo 'skipped: apps/viewer not present'; fi
build: ## Build the viewer
	@if [ -f apps/viewer/package.json ]; then cd apps/viewer && VITE_BASE='$(VITE_BASE)' bun run build; else echo 'skipped: apps/viewer not present'; fi
scene: ## Build the scene (requires acquired data)
	@if [ -f pipeline/geospatial/build_scene.py ]; then PYTHONPATH=pipeline uv run --project pipeline --frozen python -m geospatial.build_scene --city cities/$(CITY)/city.json --out build/$(CITY)/scene; else echo 'skipped: pipeline/geospatial not present'; fi
render: ## Render the scene
	@if [ -f pipeline/rendering/package.json ]; then cd pipeline/rendering && bun run render --scene ../../build/$(CITY)/scene --city ../../cities/$(CITY)/city.json --out ../../build/$(CITY)/render; else echo 'skipped: pipeline/rendering not present'; fi
tiles: ## Export tiles (set RELEASE to identify the release)
	@if [ -f pipeline/export/build.py ]; then PYTHONPATH=pipeline uv run --project pipeline --frozen python -m export.build --render build/$(CITY)/render --scene build/$(CITY)/scene --city cities/$(CITY)/city.json --out build/$(CITY)/tiles --release '$(RELEASE)'; else echo 'skipped: pipeline/export not present'; fi
validate-tiles: ## Validate exported tiles
	@if [ -f pipeline/export/validate.py ]; then PYTHONPATH=pipeline uv run --project pipeline --frozen python -m export.validate build/$(CITY)/tiles; else echo 'skipped: pipeline/export not present'; fi
site-tiles: ## Copy local tiles into the viewer
	@if [ -d apps/viewer ]; then mkdir -p apps/viewer/public/tiles/$(CITY) && cp -R build/$(CITY)/tiles/. apps/viewer/public/tiles/$(CITY)/; else echo 'skipped: apps/viewer not present'; fi
fetch-tiles: ## Fetch pinned release tiles (GITHUB_REPOSITORY required)
	python3 scripts/fetch_tiles.py --city $(CITY)
size-check: ## Check the viewer deployment budget
	python3 scripts/check_size.py apps/viewer/dist
check: validate-contracts lint test fixtures-check ## Everything that must pass before a handoff
fixtures-check: ## Committed fixtures equal the generator's output (by content, on any platform)
	python3 scripts/check_fixtures.py
clean: ## Remove build outputs and caches (never data)
	rm -rf build apps/viewer/dist .pytest_cache .ruff_cache pipeline/.pytest_cache pipeline/.ruff_cache
worktree: ## Create a task worktree: make worktree WP=07-ci-cd
	@test -n "$(WP)" || { echo 'usage: make worktree WP=<nn-slug>'; exit 1; }
	git worktree add "$(WORKTREE_ROOT)/wp$(WP)" -b "feature/wp$(WP)" main
