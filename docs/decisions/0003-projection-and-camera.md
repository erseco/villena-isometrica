# 0003 — Projection, camera and picking

Status: proposed (2026-11-15), pending WP02 review. Contract: `docs/contracts/projection.md`.

## Decision
- World CRS EPSG:25830, heights orthometric as delivered by IGN; WGS84 only at the public edge.
- Orthographic camera given by heading, pitch and pixels per metre; the projection is a 2×3
  affine matrix carried in every manifest.
- Villena: heading 45° (looking north-east), pitch 30° (exact 2:1 pixel-art dimetric),
  8 px/m (master image ≈ 11 300 × 6 500 px).
- A pixel is a ray. Three inverse operations are defined and named: reference-plane (exact,
  approximate on slopes), terrain-aware (the viewer's), surface (offline, with depth).
- Share URLs carry WGS84 lat/lon of the terrain-aware pick at the viewport centre plus a zoom
  defined in image pixels, so they survive a re-render at another scale.
- The browser gets a coarse height grid and an affine lon/lat↔E/N fit instead of PROJ.

## Why heading 45°
The castle (≈ E 686188, N 4278098) stands on a hill east of the old town. A 30° camera hides
about 1.7 m of ground per metre of height behind an obstacle. Looking north-east puts that
shadow on the far, north-east side of the hill, away from the old town; looking north-west
would drop it onto the town. North-east also shows south- and west-facing façades, the sunlit
ones. WP02 checks the occlusion estimate; WP09 checks the result.

## Consequences
- North is up-left, east up-right: the map is rotated 45° from a conventional map. The
  viewer's About text says so.
- `pixelsPerMetre` may still change before the first release; nothing but tiles depends on it.
- Grid north is used; the ~1–2° meridian convergence is ignored and documented.
- World CRS is fixed in the schemas: a second city in another UTM zone needs a MAJOR bump.
