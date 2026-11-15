# 0008 — Curated landmark details and a larger AOI (scene contract v1.1)

Status: accepted (2026-11-15). Architect: Claude Fable 5.2, on the owner's instruction: the
castle, the bullring and the churches of Santiago and Santa María "must look as much like the
real ones as possible — they are what everybody will look for".

## Context

The first full-quality build showed what footprints plus one height per part can and cannot do.
The castle reads as a castle, but its walls have no battlements and its round towers are stepped
blobs; the church towers end flat where the real ones carry a spire; the Plaza de Toros was 435 m
outside the area. Hard rule 1 of `AGENTS.md` forbade adding "towers, roofs or details the data
does not contain".

## Decision

1. **AOI** grows to E 685350–686500, N 4277500–4279100 (1.15 × 1.6 km) so that it contains the
   Plaza de Toros with more than 100 m around it. The origin moves to the new south-west corner.
   OSM and the fallback terrain were downloaded again for the new rectangle; the IGN sheet
   already covered it.
2. **Curated landmark details** are allowed for the landmarks listed in
   `cities/<city>/landmark-details.json`, and only there. Shape comes from cited reference
   photographs (Wikimedia Commons; links only, no image is stored); position and dimensions are
   measured on the surface model wherever it resolves them and labelled `estimated` otherwise.
   In the scene they are a separate optional layer (`details.geojson`) and two optional
   properties (`parapet`, `material`), every one labelled `shapeSource: "reference"`, so curated
   shape is never mixed up with measured geometry. The renderer marks their pixels with semantic
   class 7.
3. Scene contract **v1.1** (MINOR: only optional additions). Hard rule 1 gets the matching
   exception.

## Options considered

- Keep rule 1 as it was: honest, but the four places people will search for stay unrecognisable.
- Hand-model whole landmarks as meshes: best likeness, but a second geometry pipeline and far
  more invented surface than a handful of labelled primitives.
- AI restyling (WP10): not approved, not deterministic, and it would invent far more.

## Consequences

- No Google imagery was used; references are the Commons files named in the details file.
- The viewer's credits need no change (Commons photographs are consulted, not reproduced).
- A detail is an interpretation. The published "about" text should say that landmark details
  are drawn from photographs (WP12).
- Image ≈ 15 557 × 9 006 px; tile count and render memory roughly double.
