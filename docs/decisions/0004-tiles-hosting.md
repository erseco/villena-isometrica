# 0004 — Tiles are a pinned release asset bundled into the Pages site

Status: accepted (2026-11-15). Evidence: `docs/research/06-agent-clients-and-github.md` §5.

## Context
The site must contain or reliably reference its tiles, with no paid storage. CI cannot build
the tiles: the IGN elevation download is manual. Committing tiles to Git would add tens of MB
per re-render to history. Git LFS cannot be used with Pages.

## Decision
Tiles are built locally, packed into a reproducible archive (`export.pack`) and attached to
the GitHub Release. `cities/villena/tiles.lock.json` pins release tag, asset name, size and
sha256. The deploy workflow downloads the asset, verifies it before extraction, places it
under `tiles/villena/` and publishes one self-contained Pages artifact. No lock file → the
deploy job fails early; it never publishes a site without tiles. CI uses the fixture tiles.

## Consequences
- Git stays small; a deployment is reproducible from a commit plus one checksummed asset.
- Publishing a new render = new release asset + one-line lock change, reviewed like code.
- The first deployment needs the release to exist: an owner step (WP12 §7.6).
- Migration to object storage/CDN later: point `styles[].tilesBase` at an absolute URL. The
  viewer already supports it.
