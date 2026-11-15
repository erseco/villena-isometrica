# Project

**Villena Isométrica** is an interactive isometric pixel-art map of Villena (Alicante, Spain)
drawn from real open geodata. It is an independent project with its own code, artwork and
identity, inspired by Isometric NYC and Tiny València but sharing nothing with them
(`docs/research/01-prior-art.md`).

Long-term: an engine that can render other Spanish cities (Las Palmas de Gran Canaria is the
second candidate). Villena comes first; generality is added when a second city actually
needs it (`docs/ROADMAP.md`).

## v0.1.0 — scope

| In | Detail |
|---|---|
| Area | 1 km²: E 685500–686500, N 4277500–4278500 (EPSG:25830). Castle, Santiago and Santa María churches, Plaza Mayor, town hall, Teatro Chapí, railway station. |
| Geometry | Catastro building parts; IGN 0.5 m terrain; heights from the IGN surface model, else floors; OSM streets, land cover, trees. |
| Rendering | Fixed orthographic 2:1 dimetric camera looking north-east; original Mediterranean pixel-art style; fully procedural, deterministic, no AI. |
| Viewer | Pan, zoom, touch, keyboard, fullscreen, home; search of selected POIs and all named streets; share URLs (`#map=zoom/lat/lon`); permanent attribution; Spanish UI; desktop and mobile. |
| Delivery | Static site on GitHub Pages at `https://<github-owner>.github.io/villena-isometrica/`; no backend; ≤ 250 MB; reproducible from documented steps. |

| Out | |
|---|---|
| The rest of the municipality, the Plaza de Toros (435 m north of the AOI) | later release |
| Accounts, analytics, tracking, live transport, multiplayer | never planned for v0.x |
| AI-restyled tiles | optional track (WP10); only after a benchmark and owner approval |
| Building-aware picking, addresses, routing | not in v0.1 |
| A multi-city platform, object storage, CDN | when needed |

## Principles

1. **Honest map.** Geometry comes from data. What is estimated (heights, roof type) or
   decorative (façades, tree sprites) is labelled as such in the data and in the site's About
   text. Nothing invented is presented as real.
2. **Open data, clean licences.** Only sources whose licence permits what we do with them.
3. **Reproducible.** Pinned inputs with checksums, pinned tools, byte-identical outputs.
4. **Small.** One repository, static hosting, no infrastructure that v0.1.0 does not need.
5. **Free to build.** The baseline needs no paid service. Spending needs explicit approval.

## Success criteria for v0.1.0

- A visitor recognises the castle hill, the two churches and the street pattern of the old town.
- Every POI marker sits on the feature it names; share URLs reopen the same view.
- `make check`, the integration tests and the tile validator pass; the pipeline run twice
  gives identical hashes.
- Independent review (WP11) reports no open blocker; attribution is complete.

## Owner decisions still open

See `docs/PROJECT_STATE.md` → "Decisions needed from the owner".
