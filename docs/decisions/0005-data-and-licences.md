# 0005 — Data sources and licences

Status: accepted (2026-11-15) for sources; project licences proposed, owner to confirm.
Details: `docs/DATA_SOURCES.md`, `docs/LICENSING.md`.

## Decision
- Buildings: Catastro INSPIRE `BuildingPart` (ATOM). Terrain and heights: IGN MDT50cm and
  MDS50cm, 3rd coverage (manual download, checksum-pinned), with MDT05 over WCS as a
  scriptable fallback. Streets, land cover, trees, POIs: OpenStreetMap (Overpass snapshot).
- No raw LiDAR, no orthophoto, no OSM buildings in v0.1.0. No Google data, ever.
- Only rendered tiles, the manifest, the POI list and a coarse height grid are published.
  Raw data and scene vectors stay local.
- Heights: surface model → floors → default, with the source recorded per building.
  Landmark parts are zoned by the surface model. Nothing is modelled by hand.
- Proposed project licences: MIT for code; CC BY 4.0 for artwork, tiles and docs.
- Isometric NYC / Tiny València: ideas only; no code, assets, prompts or weights reused.

## Consequences
- One human step (two IGN files) is unavoidable; everything else is scripted.
- Landmark fidelity is limited by 0.5 m rasters and stated publicly.
- If Catastro-derived vectors turn out to be redistributable (WP01), publishing scenes as a
  release asset becomes possible later; nothing depends on it.
