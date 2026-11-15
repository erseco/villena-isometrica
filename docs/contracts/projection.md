# Contract: canonical world-to-image projection

Status: **v1 — FROZEN at gate G1 (2026-11-15)** after the WP02 independent review
(`docs/decisions/0007-g1-contract-freeze.md`). Changes only through `prompts/00-bootstrap.md`
Task B: version bump, ADR, regenerated fixtures.

Every component (GIS export, renderer, tile export, viewer, generation, tests) uses exactly this
projection. There is one image per city render — the *master image* — and every tile, POI and
URL refers to pixel coordinates in it.

Test vectors: `packages/geo-contracts/fixtures/projection-vectors.json`. An implementation is
conformant when it reproduces every vector within `1e-6` px.

## 1. Frames and units

| Frame | Definition | Units |
|---|---|---|
| Geographic | WGS84 (EPSG:4326), `lat`, `lon`. Public-facing only (URLs, POIs, search). | degrees |
| World | ETRS89 / UTM zone 30N (EPSG:25830): easting `E`, northing `N`; orthometric height `H` in the vertical datum of the source terrain model (recorded in the city config). | metres |
| Local | `x = E − E0`, `y = N − N0`, `z = H − H0`. Origin `(E0, N0, H0)` comes from the city config: `E0, N0` = south-west corner of the AOI, `H0` = reference height. | metres |
| Image | Continuous `(X, Y)`, origin at the **top-left corner** of the top-left pixel, `X` right, `Y` down. Pixel `(i, j)` covers `[i, i+1) × [j, j+1)`; its centre is `(i+0.5, j+0.5)`. | master-image pixels |

ETRS89 and WGS84 are treated as distinct CRSs and always transformed explicitly with PROJ
(`EPSG:4326 ↔ EPSG:25830`, `always_xy=True`); the sub-metre difference is irrelevant at map scale
but the code path must be explicit. Axis order in every file of this project is **(E, N)** and
**(lon, lat)**, except the public URL and POI display, which use `lat, lon`.

"North" means UTM **grid north**. At Villena grid north differs from true north by roughly 1–2°
(meridian convergence); this is ignored and documented.

## 2. Camera

A fixed orthographic camera defined by three numbers from the city config:

- `headingDeg` (α): compass bearing of the horizontal viewing direction, clockwise from grid
  north. α = 45 means the camera looks towards the north-east.
- `pitchDeg` (φ): elevation of the camera above the horizon, `0 < φ < 90`. The view ray descends
  at φ. φ = 30 gives the classic 2:1 pixel-art dimetric projection (`sin 30° = 0.5`). A vertical
  view (φ = 90) is not supported in v1: the terrain-aware pick has no ray to march along. The
  first camera of the test vectors uses φ = 90 to check the forward formulas only.
- `pixelsPerMetre` (s): master-image pixels per metre for a horizontal segment perpendicular to
  the viewing direction.

Unit vectors in the local frame `(x, y, z)`:

```
right   r = (  cos α,        −sin α,        0      )
up      p = (  sin α·sin φ,   cos α·sin φ,  cos φ  )
view    w = (  sin α·cos φ,   cos α·cos φ, −sin φ  )   (from the camera into the scene)
```

They are orthonormal and `r × p = −w` (image `X` right, `Y` down, depth increasing away from the
camera).

## 3. Forward projection (exact)

```
u =  s · (r · P) =  s · ( x·cos α − y·sin α )
v = −s · (p · P) = −s · ( (x·sin α + y·cos α)·sin φ + z·cos φ )
d =       w · P  =  (x·sin α + y·cos α)·cos φ − z·sin φ          (depth, metres)

X = u − u0
Y = v − v0
```

`(u0, v0)` is the image origin offset: `u0 = floor(min u)`, `v0 = floor(min v)` taken over the
eight corners of the *render prism* = AOI rectangle × `[zMin, zMax]`, where `zMin`/`zMax` come
from the scene manifest (lowest terrain, highest roof/tree top, each padded by ≥ 1 m).
Master-image size: `width = ceil(max u) − u0`, `height = ceil(max v) − v0`.

The master image is therefore the bounding box of the AOI prism, and covers `X ∈ [0, width)`,
`Y ∈ [0, height)`. Every point of the AOI with `z ∈ [zMin, zMax]` is inside it. Scene content
outside the prism is clipped — including the top of a tall feature just beyond the AOI. The
scene's margin exists so that features at the AOI edge, and the ground in front of and behind
them, are present; it is not expected to fill the image rectangle, whose four corners show
background (about a quarter of the image at Villena's settings).

Matrix form, which is what manifests carry and what consumers must use:

```
[X]   [ a11 a12 a13 ] [x]   [tx]        a11 =  s·cos α          a12 = −s·sin α          a13 = 0
[Y] = [ a21 a22 a23 ] [y] + [ty]        a21 = −s·sin α·sin φ    a22 = −s·cos α·sin φ    a23 = −s·cos φ
                      [z]               tx = −u0                ty = −v0
```

The `matrix` (`[[a11,a12,a13],[a21,a22,a23]]`) and `translation` (`[tx,ty]`) in a manifest are
**authoritative for consumers**. `headingDeg`, `pitchDeg` and `pixelsPerMetre` are carried too;
validators check that both agree to `1e-9`. Producers always derive the matrix from the camera
parameters with IEEE-754 doubles — never hand-edit it.

`d` is the coordinate along `w` (an orthographic view has no camera position to measure a
distance from). Where it is stored, it is the `depth` layer of the render output, whose
encoding is defined in one place only: `render.md` §1. With `(X, Y, d)` the 3-D point is fully
determined (section 5.3).

## 4. Tiles

The master image is published as a Deep Zoom (DZI-layout) pyramid:

- `maxLevel = ceil(log2(max(width, height)))`; level `L` has size
  `ceil(width / 2^(maxLevel−L)) × ceil(height / 2^(maxLevel−L))`.
- Tile `(col, row)` at level `L` nominally covers level pixels
  `[col·T, (col+1)·T) × [row·T, (row+1)·T)`, clipped to the level size, then grown by
  `tileOverlap` pixels on every side that has a neighbour. `T = tileSize`.
- File path: `<tilesBase>/<L>/<col>_<row>.<format>`.
- Master-image pixel `(X, Y)` at level `L` is `(X / 2^(maxLevel−L), Y / 2^(maxLevel−L))`.
- File pixel `(i, j)` of tile `(col, row)` at level `L` is level pixel
  `(max(col·T − tileOverlap, 0) + i, max(row·T − tileOverlap, 0) + j)`; multiply by
  `2^(maxLevel−L)` for master-image pixels. Consumers use the power-of-two factor, never the
  ratio of level size to master size (odd sizes round up, so the ratio drifts), and do all
  picking in master-image coordinates.

`tileSize`, `tileOverlap`, `format`, `minLevel` are in the tile manifest. Tiles that would be
entirely background are still published (no sparse pyramids in v0.1).

*Render tiles* (the chunks the renderer works in) are an internal detail of the renderer and
are unrelated to publication tiles. The renderer must produce output that is bit-identical
regardless of its chunk size; any effect with spatial support (outlines, shadows, dithering)
must be computed with enough margin, or in master-image coordinates, to guarantee that.

## 5. Inverse projection and picking

A pixel corresponds to a *ray*, not a point. Three inverse operations are defined; APIs and
documents must say which one they use.

### 5.1 Reference-plane inverse (exact, cheap)

Given `(X, Y)` and an assumed height `z = zr`:

```
a = (X − tx) / s
b = ( −(Y − ty)/s − zr·cos φ ) / sin φ
x =  a·cos α + b·sin α
y = −a·sin α + b·cos α
```

With `zr = 0` this is the "reference plane" (`H = H0`). On sloping terrain it is wrong by
`Δz / tan φ` metres along the **horizontal** viewing direction (≈ 1.73 m per metre of height at
φ = 30°).

### 5.2 Terrain-aware pick (used by the viewer)

Returns the first intersection of the pixel's ray with the **height grid, bilinearly
interpolated** — the published approximation of the terrain surface — ignoring buildings and
vegetation ("the ground you would see if everything on it were removed"), or **no pick**.

With `q = −(Y − ty)/s` and fixed `a`, points on the ray are parametrised by `b` (horizontal
distance along the viewing direction): `z(b) = (q − b·sin φ) / cos φ`.

1. Start at `b0 = (q − zMax·cos φ) / sin φ`, where `z = zMax`.
2. If the point at `b` is outside the height-grid rectangle, advance `b` until it enters the
   rectangle or until `z(b) < zMin`. If it never enters: **no pick**.
3. March in steps of `0.5 · cellSize` until `z(b) ≤ terrain(x(b), y(b))`, then bisect to 0.01 m.
   If `b` leaves the grid rectangle or `z(b) < zMin` first: **no pick**.

`terrain(x, y)` is defined only inside the height-grid rectangle (the grid's
`westE/northN/width/height`, which covers the AOI plus margin); between cell centres it is
bilinear, and in the half-cell border between the outermost centres and the rectangle edge it
is clamped to the nearest centre. Nothing outside the rectangle may be relied on.

"No pick" is a normal result for the image's background (about a quarter of the pixels). On no
pick the viewer neither updates the URL nor moves any marker, and keeps its last valid
position; it must **not** fall back to 5.1. The reference-plane inverse is used only when the
manifest has no height grid at all, and positions are then flagged approximate.

Accuracy: this finds the intersection with the interpolated grid, not with the terrain. A
feature narrower than one cell can be stepped over; the displacement along the ray is of order
`cellSize / (2·tan φ)` — 3.5 m for the default 4 m grid at φ = 30°. The grid is for fast
picking, not survey accuracy; the exporter may publish a finer one. The 0.05 m tolerance in
`tests/fixtures/tiles-synthetic/expected.json` holds because that terrain is a plane (only the
0.01 m height quantisation matters there).

Clicking on a roof therefore returns the ground point *behind* the building along the ray, not
the building's address. That is the documented v0.1 behaviour; POIs are placed by forward
projection, never by picking.

### 5.3 Surface pick (offline only)

Where the renderer's depth layer is available, with `u = X − tx` and `v = Y − ty`:
`P = (u/s)·r + (−v/s)·p + d·w`, where `d` is decoded from the depth layer (render.md §1). Used by QA and the optional generation pipeline; never shipped to the browser.

### 5.4 Geographic → image

`(lat, lon)` → PROJ → `(E, N)` → `H = terrain(E, N)` → section 3. For points on structures the
caller supplies `H` explicitly (e.g. a POI on the castle keep uses terrain + structure height
so the marker sits on the roof). POI records carry `E`, `N`, `H` and the resulting `X`, `Y` so
the viewer never needs PROJ.

## 6. Public position (shareable URL)

The viewer's URL fragment is `#map=<zoom>/<lat>/<lon>`:

- `lat`, `lon`: WGS84, 6 decimals, of the terrain-aware pick (5.2) at the viewport centre. When
  the centre has no pick, the URL keeps the last valid position.
- `zoom`: `log2(CSS pixels per master-image pixel)`, 2 decimals. `0` = one image pixel per CSS
  pixel; negative = zoomed out.

The viewer needs lon/lat ↔ E/N without PROJ. The tile manifest therefore carries
`geoToWorld`: a least-squares affine fit `(lon, lat) → (E, N)` over the AOI plus its measured
maximum residual, which must be < 0.1 m (Villena's fit is good to 0.05 m over AOI + margin; the
exporter verifies and records it). Inverse = the algebraic inverse of that affine.

## 7. Conformance checklist

1. Forward projection reproduces `projection-vectors.json` to `1e-6` px.
2. `inverse(forward(P), zr = z) == P` to `1e-6` m.
3. Terrain-aware pick of `forward(E, N, terrain(E, N))` returns `(E, N)` within one height-grid
   cell wherever that ground point is not self-occluded by terrain; a pixel whose ray never
   enters the height grid returns "no pick" and terminates.
4. The renderer's output is identical for different render-chunk sizes.
5. Pixel centres, not corners, are sampled: a world point exactly on the AOI's SW corner at
   `z = 0` lands at the `(X, Y)` given by section 3 with no half-pixel shift.
