# Roadmap

Only v0.1.0 is planned in detail (`docs/PROJECT.md`, `docs/EXECUTION_PLAN.md`). Everything
below it is intent, not commitment, and is designed only when its turn comes.

## v0.1.0 — historic centre, procedural

1 km², procedural pixel art, static viewer on GitHub Pages. Work packages WP01–WP12.

## v0.2 — candidates

- Extend north to include the Plaza de Toros (AOI option B in research 02), then outwards.
- Optional AI-restyled second style, **if** WP10 says go and the owner approves the cost.
- Better roofs where the 0.5 m surface model supports it (ridge direction, hips).
- English UI strings.
- Building-aware picking using a published id/depth pyramid.

## Later

- Larger extents: move tiles to object storage/CDN by pointing `styles[].tilesBase` at an
  absolute URL (no viewer change); chunked master image in the render contract (MINOR bump).
- Second city: Las Palmas de Gran Canaria. Known contract work: world CRS is fixed to
  EPSG:25830 today (the Canary Islands use REGCAN95 / UTM zone 28N — verify the EPSG code
  when the time comes); a MAJOR bump of the city
  and scene schemas to make the CRS a per-city value. Not done now on purpose.
- Seasonal or night palettes (the styling stage is a pure function of the G-buffers, so this
  is a re-style, not a re-render).

## Explicitly not planned

Accounts, analytics, tracking, live data, multiplayer, a backend.
