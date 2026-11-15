# Handoff — WP02 independent architecture and mathematical review

| Field | Value |
|---|---|
| Task ID | WP02 |
| Date (UTC) | 2026-11-15 |
| Provider / client | DeepSeek Harness (agentic web client), model `deepseek-flash` |
| Model and effort actually used | `deepseek-flash`; this client exposes no effort selector, the prompt asks for `deepseek-v4-pro` at `high` |
| Branch | `agent/wp02-architecture-review` |
| Base commit | `ba8ba0c11730cf341060822f19fa4871bdd89e61` (`main` = bootstrap, as committed by the owner) |
| Head commit | the commit that adds this file (`git log --oneline -1 agent/wp02-architecture-review`) |
| Status | READY FOR REVIEW |

The prompt asks for DeepSeek V4 Pro at high effort; this session ran on DeepSeek Flash, which
is the model the owner launched. The review is still cross-provider (Claude wrote what is
reviewed), so the rule "never reviewed only by the provider that implemented it" holds. If
the architect wants the stronger model on the same prompt, re-run it and diff the findings;
nothing in the conclusions below depends on model size, every one is a reproducible number.

## Changed files

One file: `docs/handoffs/WP02-architecture-review.md`. `git diff --stat ba8ba0c..HEAD`
shows only that file added. No contract, schema, fixture, code or other document was touched.

## Tests and validation executed

| Command | Result | Notes |
|---|---|---|
| `make check` | pass | `validate_contracts.py`: 7 documents valid, exit 0. `tests/fixtures/scene-synthetic/pois.json` is skipped by the validator (finding R-05). |
| `uv run scripts/make_fixtures.py` ×2, tree sha256 before/after | pass, no change | `0e0e2bb77ef83e4539475977903d54bf30f23a3cee6b316709f37c43ff77e1e7` before and after. Deterministic on this machine (macOS arm64, zlib 1.2.12, Python 3.13). |
| `wp02_checks.py` (appendix A) | pass | all 24 projection vectors, the fixture image and pyramid, `expected.json`, `geoToWorld`, the Villena budget and the occlusion table recomputed from the documents. |
| `wp02_checks2.py` (appendix B) | informational | void pixels, PNG encoder variability, JSON number text, level→master mapping. |
| OpenSeadragon / a browser | not run | no viewer exists yet (WP05); the DZI check is against the Deep Zoom specification as documented, not against a running OSD instance. |

Both scripts need `numpy` and `pyproj`; they import no project code. Run as
`uv run --no-project --with pyproj --with numpy python wp02_checks.py <repo-root>`.

## Generated artifacts

Outside Git, so listed here (regenerate with the commands above):

| Path | sha256 |
|---|---|
| `wp02_checks.py` | `aa5c8aa4b37e0dc3e0093e6e982e71c465f938f0ca87c2a0edd11d714babd50b` |
| `wp02_checks2.py` | `00eaab31409124c793a3329af80e78032e206ff82547de3f74d556a55b912585` |
| output of script A | `8812a1206639ee14b88d811470db14f79c7c86ba3e75803ac28f1c197c71ad5e` |

Both scripts are reproduced verbatim in the appendices, so the hashes are informational.

---

# The review

Method: I treated every document as suspect, recomputed its numbers from first principles
(with an independent method where a second one existed: closed form versus numeric bisection,
document formula versus PROJ), and compared with the committed fixtures. Section references
are to the document named. Numbers in this report come from the two scripts; the scripts are
the evidence, so nothing here is an adjective.

## Item 1 — camera basis, handedness, sign of `v`, exact 2:1

**Check.** Built `r`, `p`, `w` from `projection.md` §2 for 30 combinations of heading ∈
{0, 45, 90, 137, 200, 315} and pitch ∈ {15, 30, 45, 60, 89.9}, and tested `|r|²−1`, `|p|²−1`,
`|w|²−1`, all three dot products and `r × p + w`. Projected a 10 m axis-aligned square at five
headings and took the ratio of the projected horizontal span to the vertical span.

**Result — correct, no finding.**

- Largest violation over all 30 pairs: **2.22e-16** (one ulp). `r`, `p`, `w` are orthonormal
  and `r × p = −w` holds exactly in the sense of §2.
- The 2:1 claim is right for *every* heading, not only 45°: the projected edge vectors of an
  axis-aligned square are `(s·cosα, −s·sinα·sinφ)` and `(−s·sinα, −s·cosα·sinφ)`, so the span
  ratio is `sinφ` = 0.5. Measured 2.000000000 at headings 0, 17, 45, 200 and 333.
- Sign of `v`: `v = −s(p·P)` makes a point 10 m above the ground land at `v = −69.282` instead
  of `+69.282`, i.e. higher in the world is smaller `Y` (higher on screen). Correct for an
  image whose `Y` grows downwards, and consistent with the depth sign (`d` grows away from the
  camera). Worth stating in the contract that `d` is a coordinate along `w`, **not** a distance
  from the camera; nothing in the documents says a camera position exists at all (an
  orthographic camera has none), and that is fine, but `dMin`/`dMax` are then scene
  quantities, which is what the manifests carry.

## Item 2 — recompute three projection vectors by hand

**Check.** Recomputed all 24 vectors from the formulas in §3; three of them by hand below
(camera 1 = heading 45°, pitch 30°, s = 8; camera 2 = heading 90°, pitch 45°, s = 2; camera 4 =
the "oblique" camera, heading 200°, pitch 35°, s = 4).

Camera 1, point (100, 50, 25):

```
u = 8 · (100·cos45 − 50·sin45)            = 8 · 50/√2            = 282.842712475
v = −8 · ((100·sin45 + 50·cos45)·0.5 + 25·cos30)
  = −8 · (53.033008589 + 21.650635094)    = −597.469149469
d = (100·sin45 + 50·cos45)·cos30 − 25·sin30 = 91.855865349 − 12.5 = 79.355865354
```

Camera 2, point (3.5, −7.25, 1.125) — heading 90 means `u` comes only from `−y`:

```
u = 2 · (3.5·0 − (−7.25)·1)                = 14.5
v = −2 · ((3.5·1 + (−7.25)·0)·sin45 + 1.125·cos45)
  = −2 · (3.5 + 1.125)/√2                 = −6.540737726
d = 3.5·cos45 − 1.125·sin45               = 1.679378605
```

Camera 4 (oblique, heading 200° = cos −0.939692621, sin −0.342020143), points (10, 0, 0) and
(0, 10, 0):

```
(10,0,0): u = 4·(10·(−0.939692621) − 0)                    = −37.587704831
          v = −4·(10·(−0.342020143)·sin35)                 = +7.846987799
          d = 10·(−0.342020143)·cos35                      = −2.801664996
(0,10,0): u = 4·(0 − 10·(−0.342020143))                    = +13.680805733
          v = −4·(10·(−0.939692621)·sin35)                 = +21.559421788
          d = 10·(−0.939692621)·cos35                      = −7.697511313
```

**Result — correct, no finding.** All hand values match the file to every printed digit, and
the script's worst error over the 24 vectors is **4.90e-10 px/m**, well inside the 1e-6
tolerance. The oblique camera does catch sign errors: its `u` and `v` signs both flip relative
to the dimetric camera, so an implementation that hard-codes "up is negative `Y`" in the wrong
place fails here.

Note for implementers: a float32 implementation cannot meet 1e-6 at `|u| ≈ 600` (one ulp at 600
is 6e-5). The matrix and the manifest numbers must be computed in float64; float32 is fine for
per-pixel work *after* the matrix exists.

## Item 3 — pixel convention and the `u0`/`width` arithmetic

**Check.** Read §1, §3, §4, §5 for the convention; recomputed `u0`, `v0`, `width`, `height` for
the fixture from the AOI rectangle × `[zMin, zMax]` and compared with the manifest; looked for
off-by-one cases when `min u` is an integer and when `max u` is an integer.

**Result — consistent, no finding.** The convention "continuous coordinates, origin at the
top-left **corner**, pixel `(i,j)` covers `[i,i+1)×[j,j+1)`, centre `(i+0.5, j+0.5)`" is used
identically in §1 (definition), §3 (`X = u − u0`), §4 (`X/2^k`) and §5 (`u = X − tx`). The
fixture confirms it end to end: `u0 = −363`, `v0 = −470`, image `726 × 481`, translation
`[363, 470]`, and the AOI's south-west corner at `z = 0` lands exactly at `(363.0, 470.0)` —
no half-pixel shift, which is conformance check 5 of §7.

`u0 = floor(min u)` and `width = ceil(max u) − u0` are free of off-by-one errors, including the
integer cases:

- `min u` integer, say 362.0: `u0 = 362`, the leftmost content point has `X = 0`, inside.
- `max u` integer, say 362.0: `width = 362 − u0`, so `X = width` is the right *edge* and is
  outside, while the last pixel is `width − 1`. This is the correct behaviour, but the contract
  never says that the image covers `X ∈ [0, width)`. One sentence fixes it.
- Empirical check at the other end: the AOI's north-east corner at `zMax` projects to
  `Y = 0.56` in the fixture (and `Y = 0.6` for Villena), i.e. just inside the top edge, so the
  prism is fully contained and nothing at the AOI boundary is clipped.

## Item 4 — render prism versus the scene margin

**Check.** Projected the AOI corners and the margin corners at `zMin` and `zMax` for Villena
(heading 45, s = 8, relief 120 m from `COSTS.md`, `z ∈ [−30, +90]`), and mapped the four image
corners back to the ground with §5.1.

**Result — the arithmetic is right, the behaviour is undocumented: finding R-16 (minor).**

- The AOI is fully contained: all eight AOI prism corners project inside `11314 × 6489`
  (north-east corner at `zMax` gives `Y = 0.6`, the north-west corner gives `X = 0.1`).
- Margin content is partly clipped: a margin corner north-west of the AOI projects to
  `u = −7014 px` against the prism's `−5657`, i.e. `1357 px` outside the image; the north-east
  margin corner at `zMax` projects to `Y = −678`, above the top edge. So the margin is context
  that *may* be clipped, and tall margin features can be cut at the image edge. Nothing says so.
- The four image corners do not correspond to ground near the AOI at all: the top-left corner
  maps to local `(x 610.3, y 1610.3)` m, the bottom-left to `(−536.8, 463.2)`, i.e. 400–600 m
  outside the 120 m margin. Those corners are background by construction. That is not wrong —
  the image is the bounding box of a rotated, tilted prism — but a reader will assume the image
  is "the AOI with 120 m of context" and it is not: the image rectangle covers a ground
  parallelogram of ≈2.3 km² for a 1 km² AOI, and ≈25 % of its pixels (see item 4 of script B /
  R-01) never meet the scene.
- The fixture cannot test any of this: its renderer paints only `0 ≤ x,y < 128` and returns
  background outside (R-20).

## Item 5 — inverse operations and the terrain-aware pick

**Check.** Verified the algebra of §5.1 and §5.3 symbolically on paper; verified §5.1
numerically (item 6); implemented §5.2 as written and looked at its start point, its step, the
φ = 90 case, rays starting below the surface, the AOI/grid edge, self-occlusion and the stated
error bound; checked the fixture's grid domain against the image.

**Result — §5.1 and §5.3 correct; §5.2 has a blocker and two majors: R-01, R-03, R-04.**

- §5.1: with `a = (X−tx)/s` and `b = (−(Y−ty)/s − zr·cosφ)/sinφ`, substituting into §3 returns
  `(x, y)`; verified against the three committed reference-plane cases (item 6). Correct.
- §5.3: `P = (u/s)·r + (−v/s)·p + d·w` is correct *because* the basis is orthonormal (item 1):
  `r·P = u/s`, `p·P = −v/s`, `w·P = d`. It does assume the depth layer's `d` is the same `d`
  §3 defines; see R-02, which contradicts that.
- Error bound `Δz / tan φ` for the reference plane: right in magnitude (1.73 m per metre at
  φ = 30°), but the wording "metres along the viewing direction" should say **along the
  horizontal projection of the viewing direction**; along the ray itself the error is
  `Δz / sin φ` = 2.0 m per metre. Both points are ground points, so the horizontal statement is
  the meaningful one.
- Self-occlusion: marching from the near end (`b` where `z = zMax`) towards larger `b`, the
  first bracket with `z ≤ terrain` is the nearest crossing, so terrain self-occlusion is
  handled correctly, and the bisection is only used inside that first bracket. Correct.
- φ = 90: `z(b) = (−(Y−ty)/s − b·sinφ)/cosφ` divides by zero; the schema allows
  `pitchDeg = 90` in all three manifests. **R-03.**
- Start point and step: **R-01** (the start point can be outside the height grid, the lookup
  has no defined domain, and the termination rule cannot be evaluated) and **R-04** (the
  accuracy claim and the march can skip a ridge).

## Item 6 — `expected.json` recomputed independently

**Check.** Derived the ray–plane intersection for `z = 0.10x + 0.05y` from §3 without using
`scripts/make_fixtures.py`: a point projects to `(X, Y)` iff `r·P = u/s` and `p·P = −v/s`
(`u = X + u0`, `v = Y + v0`). Writing the first as `x = a·cosα + b·sinα`, `y = −a·sinα + b·cosα`
(a rotation inverse, `a = u/s`) gives `x·sinα + y·cosα = b`, so the second becomes
`b·sinφ + z·cosφ = q` with `q = −v/s`, and with `z = C1·x + C2·y`:

```
b = (q − a·(C1·cosα − C2·sinα)·cosφ) / (sinφ + (C1·sinα + C2·cosα)·cosφ)
```

As a second, fully independent method I walked the ray parameter `b` and bisected
`z(b) − plane(x(b), y(b))`, which uses no closed form at all. Both were compared with the six
committed ground points and the three reference-plane cases.

**Result — correct, no finding.** Every value reproduces:

| case | file `X`, `Y` | recomputed | numeric pick |
|---|---|---|---|
| E 700000, N 4270000, H 500.000 | 363.0, 470.0 | 363.000000, 470.000000 | E 700000.0000 N 4270000.0000 |
| E 700064, N 4270064, H 509.600 | 363.0, 255.725289 | 363.000000, 255.725289 | E 700064.0000 N 4270064.0000 |
| E 700100, N 4270020, H 511.000 | 589.27417, 262.189255 | 589.274170, 262.189255 | E 700100.0000 N 4270020.0000 |

Largest deviation over all six points: **4.9e-7 px**, i.e. the 6-decimal rounding of the file.
The reference-plane cases (X 0/Y 0 → E 700102.000153 N 4270230.340034; X 363/Y 240.5 →
E 700081.140503 N 4270081.140503; X 726/Y 481 → E 700060.280853 N 4269931.940972) reproduce to
the last digit, including the third case, whose `X = 726`, `Y = 481` are the image's right and
bottom *edges* (valid continuous coordinates, outside the pixel indices).

Caveat worth recording: `expected.json` was generated with the same closed form, so this is a
consistency check between the document and the fixture, not a proof that the closed form is
the right model. The numeric bisection is what closes that gap, and it agrees.

## Item 7 — camera heading for Villena and the occlusion estimate

**Check.** `cities/villena/city.json`: heading 45°, pitch 30°, s = 8, AOI E 685500–686500 /
N 4277500–4278500 (1 km). Castle at E 686188, N 4278098 (local 688, 598). Computed the hidden
ground length behind an obstacle of height `h` (`h/tanφ`) for a range of `h`, located the
castle in the image, and looked for a documented hill height.

**Result — the heading is defensible, but the claim in ADR 0003 is unverifiable as written:
note in R-16, data gap in "Known problems".**

- Hidden length = `h / tan 30°` = `1.732·h`: 5 m → 8.7 m, 10 m → 17.3 m, 20 m → 34.6 m,
  30 m → 52.0 m, 50 m → 86.6 m, 80 m → 138.6 m. For a 100 m wide hill those are 0.09–1.39 ha.
- The castle lands at pixel `(6166, 2436)` of `11314 × 6489` (54 % from the left, 38 % from the
  top at `z = 30 m`), i.e. mid-upper-right, which is where a confident map wants its landmark.
- The old town is south-west and *west* of the hill (Castillo E 686188/N 4278098; Plaza Mayor
  ≈ E 686071/N 4277910, computed from the coordinates in `docs/DATA_SOURCES.md`). With a
  camera looking north-east the town is on the **near** side, so the hill's terrain shadow
  falls north-east, away from the town. ADR 0003's reasoning is right.
- But `docs/DATA_SOURCES.md` states no hill height and no relief figure, so "the castle hill
  hides ground behind it" cannot be checked numerically, and the estimate "about 1.7 m of
  ground per metre of height" (right: 1.73) has no input. Ask WP01 to record the relief
  (castle top vs. Plaza Mayor, and the AOI min/max from the MDT). The check is parametric:
  even a 50 m rise hides only 87 m, i.e. 8.7 % of the AOI side, and it hides it on the far
  side of the hill, which is mostly outside the built-up area.

## Item 8 — geographic handling

**Check.** Recomputed the `geoToWorld` affine for the fixture and for Villena with PROJ
(EPSG:4326 ↔ EPSG:25830, `always_xy=True`), measured the maximum residual on a 25 × 25 grid;
computed the meridian convergence at the AOI centre; compared the documented WGS84 envelope
with the AOI corners; reviewed the vertical-datum handling and the height quantisation.

**Result — accurate and correctly described; one wording fix (R-16/R-14 family), no number
changes needed.**

- Fixture: re-measured residual **5.352e-4 m** vs `maxResidualM` 0.000536 in the manifest.
- Villena: **0.0327 m** over the 1 000 × 1 000 m AOI, **0.0503 m** over the AOI + 120 m margin
  (1 240 m). The schema's ceiling is 0.5 m, forty times what the fit actually needs — see R-14
  for why that matters to the share URL (0.5 m = 4 px at s = 8, 64 CSS px at zoom 4).
- Analytic cross-check of my own: the second-order term of `(lon,lat) → (E,N)` over a span `L`
  is ≈ `L²/(8R)` = 1 240²/(8 · 6.371e6) = **0.030 m**, which matches the measured 0.050 m in
  order of magnitude. "Good to centimetres over ~1 km" is true.
- Grid convergence at the AOI centre: **1.335°** (grid north vs true north), matching the
  "roughly 1–2°" in §1. Ignoring it is a rotation of the whole map, which is harmless because
  everything except the public lat/lon uses grid north; the statement is correct.
- The documented WGS84 envelope in `docs/DATA_SOURCES.md` (lon −0.869027…−0.857279,
  lat 38.626433…38.635648) matches the AOI corners **exactly** to six decimals. Good.
- Vertical datum: heights are orthometric and only the terrain uses them; ETRS89/WGS84 is
  handled explicitly and 2-D only, so no geoid model is needed at run time. Correct. But
  `cities/villena/city.json` puts a TODO inside a normative field
  (`"verticalDatum": "… (exact realisation to be confirmed by WP01)"`), and nothing compares
  the city's string with the scene's. See R-12.
- `uint16` height grid: a 120 m relief at `scale = 0.01` needs 12 000 codes of 65 535, so the
  range is ample; 1 cm quantisation costs 0.0173 m horizontally at φ = 30°, inside the 0.05 m
  tolerance of `expected.json`. Correct.

## Item 9 — Deep Zoom arithmetic and tile rectangles

**Check.** Recomputed `maxLevel`, every level's size, every tile rectangle with
`T = 256`, `overlap = 1` for the 726 × 481 fixture image, and compared the resulting file list
and the file dimensions with the 17 committed PNGs and the DZI convention.

**Result — correct, no finding.** `maxLevel = ceil(log2 726) = 10`; level sizes
1×1, 2×1, 3×2, 6×4, 12×8, 23×16, 46×31, 91×61, 182×121, 363×241, 726×481; tile counts
1,1,1,1,1,1,1,1,1,2,6 = **17 files**, and the recomputed names `{0..8}/0_0.png`,
`9/{0_0,1_0}.png`, `10/{0_0,0_1,1_0,1_1,2_0,2_1}.png` are exactly the files on disk.

Edge behaviour matches the convention: tiles are *cut*, never padded, and overlap is added only
on sides that have a neighbour — level 10 is `257×257`, `258×257`, `215×257`, `257×226`,
`258×226`, `215×226`; level 9 is `257×241` and `108×241` (the right column starts at level
x = 255, i.e. one overlap pixel inside 256). This is what OpenSeadragon expects for a Deep Zoom
source, with the caveat that no OSD instance was run (see "could not check").

## Item 10 — drift in the lower levels

**Check.** Compared the level sizes from repeated `ceil` halving with `ceil(W/2^k)`, proved the
identity `ceil(ceil(a/b)/c) = ceil(a/(bc))`, mapped level pixels back to master pixels
including the overlap, and measured the error a viewer would make by using the ratio of level
and master sizes instead of the power of two.

**Result — no drift; two sentences missing: R-11 (minor).** The identity holds, so level `L`
is always `ceil(W/2^k)` and master `X = X_L · 2^k` is exact. The only deviation is in the last
column/row of a level when `W` or `H` is odd: the 2× box filter replicates the edge pixel, so
the last level pixel averages a block with duplicated edge samples (e.g. `W = 3`, `k = 2`:
`(m0 + m1 + 2·m2)/4` instead of `(m0 + m1 + m2)/3`). That is sub-pixel, confined to the image
edge, and harmless. What is *not* harmless is a viewer that scales by `W / levelWidth`: for
Villena's `H = 6489`, level 13 has 3 245 rows, ratio 1.999692, and the far edge drifts by
**1 master px**. The contract should say "use `2^(maxLevel−L)`, never the ratio", and give the
file-pixel → master-pixel rule with overlap:
`master = (max(col·T − ov, 0) + i) · 2^(maxLevel−L)`.

## Item 11 — ambiguous, redundant, unvalidatable or missing fields

**Check.** Read all seven schemas against the three contract documents and asked, for every
field the renderer or viewer needs: is the unit, the axis order, the reference point and the
range stated, and can a validator check it?

**Result — mostly good; the gaps are R-02, R-03, R-05, R-06, R-12, R-13, R-14, R-15, R-17.**
What is already right and should not be touched: coordinates are (E, N) and (lon, lat)
everywhere with a stated exception for URLs; terrain and height grids state row-major,
north-first and cell-centre sampling, and `westE`/`northN` are outer edges (verified against
the fixture: first terrain sample at `westE + 0.5·cell`); polygons are counter-clockwise
(verified in the fixture's `rect()`); ids are stable and derived from source ids; the height
grid's `scale`/`offset` are in the manifest; `background` is a hex colour and the `color` layer
is sRGB with straight alpha.

The gaps, in one line each (full entries in the findings):

- depth is float32 in `projection.md` §3 and gray16 in `render.md` §1, and `dMin` has no
  schema field (R-02);
- `pitchDeg = 90` is allowed and undefined (R-03);
- the scene's `pois.json` has no schema and is skipped by the validator (R-05);
- the palette is referenced but exists nowhere (R-06);
- `heightM` is "the eaves/roof plane", which is two different numbers for a pitched roof (R-13);
- POIs carry `(E,N,H)`, `(lat,lon)` and `(X,Y)` with no consistency check (R-14);
- the tile manifest has no `crs` and no link to the render (`sceneSha256`/`renderSha256`), so a
  published pyramid cannot be traced back (R-15);
- `city.json` carries `tiles.format`, which the tile manifest also carries and which nothing
  consumes; the height-grid resolution fixed at 4 m in `ARCHITECTURE.md` is not configuration;
  `roads.layer > 0` promises bridges but gives no clearance while roads are "draped on the
  terrain"; `landcover` non-overlap cannot be expressed in JSON Schema; `trees.source =
  "scattered"` needs a fixed seed that no document fixes (R-17);
- the fixture's `provenance` is empty while its only dataset has `sha256: null`, which
  `dataset-manifest.schema.json` says the pipeline must refuse (R-17).

## Item 12 — determinism

**Check.** Reviewed every rule that can make byte-identical output fail: JSON key and array
order, float formatting, rounding, image encoding; ran the fixture generator twice and hashed
the whole `tests/fixtures` tree; encoded the same 1 024 bytes with zlib at three levels; printed
Python and Node JSON for the same five numbers.

**Result — risky as written: R-07 (major), R-08, R-09, R-10 (minor).** The fixtures regenerate
to an identical tree on this machine (`0e0e2bb7…e1e7` twice), which proves reproducibility for
one Python + zlib build, not cross-platform identity. Details:

- PNG bytes are a function of the encoder. The same pixels at zlib level 1/6/9 give sha256
  `b03afddb…`, `2abdaf79…`, `eac2ef4e…`; `render.md` §1 demands byte-identical *files* between
  macOS arm64 and Ubuntu x86-64, which the renderer cannot promise without a pinned encoder
  (ADR 0002 puts the encoder choice in front of a Chromium SwiftShader experiment).
- Number text differs across languages for the same value: Python `[1.0, 1e-07, 0.300…04,
  -0.0, 1.2345678901234568e+17]`, Node `[1, 1e-7, 0.300…04, 0, 123456789012345680]`. Each
  published file has a single producer, so this only bites tests that compare JSON *text*;
  say so, and forbid `NaN`/`±Infinity` explicitly (Python's `json` writes them, JSON does not).
- Ordering: features are sorted by id and keys are sorted, but **`pois` arrays are not** — the
  committed fixtures are in definition order (`keep, church, garden, calle-mayor, sw-corner`),
  not id order. Two runs of a set-iterating implementation would differ (R-09).
- Rounding is unspecified: `round(x, 3)` in Python is banker's, a TypeScript implementation
  would use half-up; POI coordinates rounded to 3 decimals could differ (R-10).
- `render.md` says the down-sampling kernel is "chosen and benchmarked in WP06", but the
  fixtures and every level of the pyramid already commit to a 2×2 box filter with edge
  replication. Either fix the kernel now or accept that the fixtures change when WP06 decides.

## Item 13 — versioning, and a second city in another UTM zone

**Check.** Read the `schemaVersion` rule in all seven schemas, the `const` CRS fields, and
followed what a second city (Las Palmas, zone 28N, EPSG:25828) would need.

**Result — workable for v0.1, one cheap improvement: R-19 (note).** The MAJOR.MINOR rule with
`additionalProperties: false` is sound, but two things should be written down: the version
check must happen *before* schema validation (a v1.1 document fails a v1.0 schema on its new
optional field), and a second UTM zone needs a MAJOR bump because `crs.world` is
`const: "EPSG:25830"` in `city-config`, `scene-manifest` and `render-manifest`. The projection
arithmetic itself is CRS-agnostic (local metres), `geoToWorld` and `origin`/`zRange` are
per-city, so nothing else would change — the bump is a formality, not a redesign, and ADR 0003
already records it. Do not relax the `const` now; v0.1 has one city.

## Findings

Each finding has an ID, a severity, the exact location, the evidence (a number or a command
output) and a proposed fix written as replacement text. **blocker** = an implementation
following the document would be wrong or impossible; **major** = will cause rework; **minor** =
should be fixed in the same pass; **note** = record it, no change needed now.

### R-01 — blocker — the terrain-aware pick is undefined where the ray never enters the height grid

Location: `docs/contracts/projection.md` §5.2 (whole paragraph).

Evidence:

- The algorithm starts "at the `b` where `z(b) = zMax`". For the fixture's top-left pixel
  `(0, 0)` that start point is **local (64.0, 192.4) m**, while the published height grid
  covers `x, y ∈ [−8, 136]` — 56 m outside. Likewise `(0, 480)` starts at `(−105.7, 22.7)`,
  `(725, 0)` at `(192.2, 64.2)`, `(725, 480)` at `(22.5, −105.5)`.
- For those rays the plan track moves *further* out as `b` grows, so they never touch the grid:
  **29.1 %** of the fixture's pixels and **25.4 %** of the Villena image (sampled every 24 px)
  have a ray that never meets the scene footprint. For Villena the top-left corner's ray runs
  from `(500, 1500)` at `z = 90` to `(610, 1610)` at `z = 0`, i.e. 380–490 m beyond the margin.
- Three rules are missing: what `terrain(x, y)` returns outside the grid (NaN? clamp to the
  edge? fail?), how the march terminates when the ray is outside the grid (as written it
  loops), and what "leaves the AOI" means when the ray never enters the AOI. The fallback to
  §5.1 with `zr = 0` then returns a lat/lon several hundred metres outside the data, flagged
  only as "approximate" — and the published tiles are opaque, so the viewer cannot tell a
  background click from a ground click.
- §5.2 also says the march stops when the ray "leaves the AOI", while the grid it samples is
  defined by `westE/northN/width/height` and, in the fixture and in `ARCHITECTURE.md`, covers
  the AOI **plus** margin. "AOI" in that sentence is the wrong object.

Proposed fix (replace the second and third sentences of §5.2 and add two):

> Start at `b0 = (q − zMax·cos φ)/sin φ`. If the point at `b0` is outside the height grid,
> advance `b` until it enters the grid or until `z(b) < zMin`; if it never enters, there is no
> pick. March in steps of `0.5 · gridCellSize` until `z(b) ≤ terrain(x(b), y(b))`, then bisect
> to 0.01 m; stop and report **no pick** when `b` leaves the grid rectangle or `z(b) < zMin`.
> `terrain(x, y)` is only defined inside the grid rectangle; behaviour outside it, including
> clamping, is not defined and must not be relied on. "No pick" is a normal result for pixels
> in the image's background: the viewer must neither update the URL nor move the crosshair,
> and may keep the previous valid position. The viewer must not fall back to §5.1 for background
> pixels; when it does fall back (only when a hit is impossible for a pixel whose ray does enter
> the grid), the result is flagged approximate and the URL is not updated either.

### R-02 — major — the depth layer has two contradictory definitions and `dMin` has no home

Location: `docs/contracts/projection.md` §3 last paragraph vs `docs/contracts/render.md` §1
table (`depth` row) vs `packages/geo-contracts/schemas/render-manifest.schema.json` (no `dMin`,
`additionalProperties: false`).

Evidence: §3 says "Depth is stored where needed as `d − dMin` in metres (float32), `dMin` in
the render manifest"; `render.md` says the layer is `gray16-png` with `d = offset + scale·value`
and puts `scale`/`offset` on the layer object; the schema has `scale`/`offset` on the layer and
**no** `dMin` property, so a manifest following §3 fails validation. §5.3 then consumes `d`
without saying which quantisation applies.

Proposed fix: delete the float32/`dMin` sentence from §3 and state the single truth in
`render.md` §1:

> `depth` (optional), `gray16-png`, pixel value `n` encodes `d = offset + scale·n` with
> `offset = dMin` and `scale = (dMax − dMin)/65535`, both on the layer object; `dMin`/`dMax`
> are the extremes of `d` over the rendered prism, so the quantisation step is at most
> 0.002 m for the Villena prism. Pixels with alpha 0 in the colour layer carry 0.

Also state in §5.3 that the depth layer's `d` is the coordinate along `w` used in §3 (not a
distance from a camera, which does not exist in an orthographic view).

### R-03 — major — `pitchDeg = 90` is allowed and the pick divides by `cos φ`

Location: `projection.md` §2 ("0 < φ ≤ 90") and §5.2; `city-config.schema.json`,
`render-manifest.schema.json`, `tile-manifest.schema.json` all allow `pitchDeg = 90`
(`exclusiveMinimum: 0`, `maximum: 90`).

Evidence: §5.2's `z(b) = (−(Y−ty)/s − b·sinφ)/cosφ` and §5.1's `b = (…)/sinφ` are fine at
φ = 90, but the `b` parameterisation of §5.2 collapses (`cp = 0`), so the march has nothing to
step in; the vector fixture camera 0 is *defined* at pitch 90 and reproduces correctly for the
forward direction (`v = −s·z·cosφ = 0`, `d = −z`), which shows the forward map survives while
the inverse does not.

Proposed fix, pick one and write it down: (a) tighten the three schemas to
`exclusiveMaximum: 90` and say "φ = 90 is not supported in v1" — the cheapest, no city needs
it; or (b) add a §5.2a: "for φ = 90 the ray is vertical: `(x, y) = (a·cosα + b·sinα, …)` with
`b` from `v`, and `z` is the bilinear terrain at that point". I recommend (a).

### R-04 — major — "first intersection with the terrain surface" overstates what a grid can do

Location: `projection.md` §5.2 (first sentence and "marches can skip" behaviour);
`tests/fixtures/tiles-synthetic/expected.json` (0.05 m tolerance in `description`).

Evidence: the march compares against a bilinearly interpolated grid, so it finds the first
intersection with the **interpolated grid surface**, not with the terrain. Step
`0.5 · cell` drops `z` by `0.5·cell·tanφ` per step, and a ridge narrower than one cell can be
stepped over; the resulting displacement along the ray is of order `cell/(2·tanφ)`:
**0.43 m** for 0.5 m cells, **1.73 m** for 2 m cells, **3.46 m** for 4 m cells (the 4 m grid is
what `ARCHITECTURE.md` and the fixture use). `expected.json`'s 0.05 m tolerance holds only
because the synthetic terrain is planar; on real terrain the same test would fail.

Proposed fix: say "first intersection with the height grid, bilinearly interpolated", add the
bound `≈ cellSize/(2·tanφ)` along the ray for a one-cell feature, and add a ridge/step case to
the fixtures. Note in `expected.json` that its tolerance is a property of the plane
(quantisation only: 0.01 m/tanφ = 0.0173 m), not a general accuracy claim. If better accuracy is
wanted, the export can publish a finer grid (the format allows any `cellSize`); say what the
4 m grid is for (fast picking, not survey accuracy).

### R-05 — major — the scene's POI file validates against nothing, and the validator skips it

Location: `docs/contracts/scene.md` ("Same structure as `poi.schema.json` but `X`, `Y` are
omitted"), `scripts/validate_contracts.py` lines 60–61.

Evidence: `poi.schema.json` requires `X` and `Y`; the scene's `pois.json` must not have them;
the validator therefore excludes the file with a comment ("checked by the GIS tests instead")
and no GIS test exists yet. `make check` prints 7 `ok` lines and this file is not one of them,
so a typo in the renderer's POI input passes CI. Any consumer writing it against
`poi.schema.json` fails validation.

Proposed fix: add `packages/geo-contracts/schemas/scene-pois.schema.json` (id/name/kind/lat/lon/
E/N/H/source required, `worldBounds` optional, `X`/`Y` forbidden, `imageBounds` forbidden) and
validate the scene's `pois.json` against it. Delete the skip from the validator.

### R-06 — major — the procedural palette is referenced but is not part of the contract

Location: `render.md` §1 (`color` row: "Only colours from the palette file referenced in the
renderer's docs") and §2 ("`make validate-tiles` checks … the size budget").

Evidence: no schema, manifest field or committed file carries the palette; there is no
`pipeline/rendering/` yet. "Every colour pixel is exactly a palette colour" and the `class`
layer's 0–7 semantics cannot be validated by WP04, WP06 or WP09 without it, and a palette
change silently invalidates every golden hash.

Proposed fix: commit the palette as data (e.g. `pipeline/rendering/palette.json`: `{"name",
"version", "colors": [{"hex": "#rrggbb", "role": "ground|road|roof|vegetation|…"}], "classes":
{"0": "background", …}}`), add an optional `paletteSha256` and `palette` path to
`render-manifest.schema.json` (MINOR bump), and require the exporter's validator to reject any
`color` pixel outside it. That also gives WP09 a machine-readable style reference.

### R-07 — major — byte-identical PNGs across platforms is not achievable without a pinned encoder

Location: `render.md` §1 ("Deterministic: … byte-identical layer files on macOS arm64 and
Ubuntu x86-64") and §2 (`tile` files); `render-manifest.schema.json` `sha256` fields;
`ARCHITECTURE.md` "Known risks" row.

Evidence: the same 1 024 bytes of pixels compressed with zlib level 1, 6 and 9 give three
different sha256 values (`b03afddb…`, `2abdaf79…`, `eac2ef4e…`); the compressor is part of the
build (macOS ships a different zlib from Ubuntu, Chromium bundles its own), so file hashes are
a property of the encoder, not of the image. ADR 0002 defers the choice to a Chromium
SwiftShader experiment, which tests rendering, not encoding, across platforms.

Proposed fix: split the requirement in two. (1) **Required**: the decoded layer buffers are
byte-identical across platforms; compare a hash of the decoded pixels (and state the pixel
hash in the manifest, e.g. `pixelSha256`, additive MINOR). (2) **Required within one pinned
build**: file bytes and their `sha256`. Record the encoder in `renderer.version` and make the
WP04 spike test pixel identity first, file identity second, on both platforms.

### R-08 — minor — JSON number text differs across languages; `NaN`/`Infinity` are not excluded

Location: `scene.md` "Rules" ("JSON keys are sorted; no timestamps. Same inputs → byte-identical
scene"), every schema's `schemaVersion` rule.

Evidence: Python `json.dumps([1.0, 1e-7, 0.3+0.2, -0.0, 1.2345678901234568e+17])` gives
`[1.0,1e-07,0.30000000000000004,-0.0,1.2345678901234568e+17]`; Node's `JSON.stringify` on the
same numbers gives `[1,1e-7,0.30000000000000004,0,123456789012345680]`. Also, Python writes
`NaN`/`Infinity`, which are not JSON and which the schemas' `number` type would accept after
`json.loads`.

Proposed fix: one sentence — "determinism applies to files written by one producer; no test may
compare JSON text across languages, compare parsed values"; and a validator rule rejecting
non-finite numbers at the boundary.

### R-09 — minor — `pois` arrays are not sorted

Location: `scene.md` "Rules" (sorts features by id, says nothing about POIs); both committed
`pois.json` files.

Evidence: `tests/fixtures/scene-synthetic/pois.json` and `tiles-synthetic/pois.json` are in
definition order — `keep`, `church`, `garden`, `calle-mayor`, `sw-corner` — while id order is
`calle-mayor`, `church`, `garden`, `keep`, `sw-corner`. An implementation iterating a dict or a
set would produce a different file for the same input.

Proposed fix: "`pois` are sorted by `id`" in both `scene.md` and `render.md`, and sort the
fixtures when they are next regenerated (they are generated, not hand-edited).

### R-10 — minor — rounding rule unspecified

Location: `scene.md` "Coordinates are rounded to 0.01 m"; `make_fixtures.py`'s
`round(X + tx, 3)` for POI coordinates; `poi.schema.json` has no constraint.

Evidence: Python's `round` is round-half-to-even; TypeScript's `toFixed`/`Math.round` are
half-up or decimal-string based. A POI at exactly `x.xxx5` would differ.

Proposed fix: state one rule, e.g. "round half away from zero on the decimal representation, 2
decimals for world coordinates, 3 for image coordinates", and say that implementation-provided
formatters (`toFixed`, Python `round`) are not conformant at halfway points.

### R-11 — minor — the level → master mapping and the overlap offset are not spelled out

Location: `projection.md` §4 last bullet.

Evidence: `X · 2^(maxLevel−L)` is stated as a coordinate mapping but the file-pixel form is not:
a viewer that scales by `W/levelWidth` drifts (Villena `H = 6489`, level 13 = 3 245 rows,
ratio 1.999692, up to 1 master px at the far edge); and the first file pixel of a tile is at
level pixel `max(col·T − overlap, 0)`, not `col·T` (verified: level 10 tile `2_0` starts at level
511, width 215, master 511–726).

Proposed fix: add to §4: "Tile file pixel `(i, j)` of tile `(col, row)` at level `L` is level
pixel `(max(col·T − overlap, 0) + i, max(row·T − overlap, 0) + j)`; multiply by
`2^(maxLevel−L)` to get master pixels. Consumers must use the power-of-two factor, never the
ratio of level and master sizes, and must do picking in master-image coordinates."

### R-12 — minor — `cities/villena/datasets.json` does not exist; the validator does not resolve references

Location: `cities/villena/city.json` (`"datasets": "datasets.json"`), `scripts/validate_contracts.py`.

Evidence: `cities/villena/` contains only `city.json` and `README.md`; `make check` passes
because the validator only validates files that exist. `city.json` also carries a TODO inside a
normative field: `"verticalDatum": "… (exact realisation to be confirmed by WP01)"`, and
nothing checks that a scene's `crs.verticalDatum` equals the city's.

Proposed fix: WP01 owns the file (it is listed as WP01's output), so this is a gate note rather
than a defect — but add to the validator: every relative path referenced by a validated
document (`datasets`, `localPath`, `pois`, `styles[].tilesBase` for the fixture) must resolve;
and a cross-document check `city.crs == scene.crs` once both exist. Replace the TODO string
with the datum name before G1 freezes, or the frozen contract quotes a placeholder.

### R-13 — minor — `heightM` is ambiguous for a pitched roof

Location: `scene.md` buildings table (`heightM`: "height of the eaves/roof plane above
`baseH`"), `roof` enum.

Evidence: for `roof = "pitched"` the eaves and the ridge are different heights, the surface
model measures the highest surface (the ridge), and the renderer needs both to draw a roof.
`DATA_SOURCES.md` says ridge layout is not attempted, so the ridge *direction* is procedural
anyway; the height must still be unambiguous because it enters `zRange` and the master-image
size.

Proposed fix: define `heightM` as the height of the **highest** point of the part (ridge or
parapet) above `baseH`, and add optional `eaveHeightM` (additive MINOR) for pitched parts; or
state that the renderer derives eaves as `heightM − roofPitch·(width/2)` with a fixed
`roofPitch` constant. Also state that ridge orientation is procedural, not data, so nothing
implies it was measured.

### R-14 — minor — POI redundancy is never cross-checked, and the `geoToWorld` ceiling is loose for URLs

Location: `poi.schema.json` (`E`, `N`, `H`, `lat`, `lon`, `X`, `Y` all required);
`poi.schema.json` and `tile-manifest.schema.json`
`geoToWorld.maxResidualM` (`exclusiveMaximum: 0.5`); `projection.md` §6.

Evidence: the same point is stored three ways and no validator checks that the three agree; a
mistake in `lat`/`lon` sends a shared `#map=…` link elsewhere while the marker stays put.
Villena's fit needs 0.033 m over the AOI and 0.050 m over the AOI + margin, so the 0.5 m
ceiling allows a 10× worse fit than the data produces: 0.5 m = 4 px at s = 8, i.e. 64 CSS px at
zoom 4.

Proposed fix: WP06's validator checks (a) `forward(E, N, H)` reproduces `X, Y` to 1e-3 px and
(b) `geoToWorld(lon, lat)` reproduces `E, N` to `maxResidualM`; and tighten the ceiling to
0.1 m (or require `maxResidualM ≤ 0.1` and keep 0.5 m only as a schema hard stop).

### R-15 — minor — the published pyramid cannot be traced to its render

Location: `tile-manifest.schema.json` (has no `crs`, no `sceneSha256`/`renderSha256`),
`render.md` §2.

Evidence: `render.json` carries `sceneSha256`, but the tile manifest carries only a free-text
`release`; a published pyramid cannot be checked against the render it came from, and for a
future city in another UTM zone the manifest's `origin.E0/N0` numbers would not say which CRS
they are in. `make validate-tiles` (WP06) cannot verify "this pyramid came from this render".

Proposed fix: add optional `renderSha256` and `crs` to the tile manifest (additive MINOR), and
require them in the release checklist.

### R-16 — minor — the margin/prism relationship and the occlusion input need written rules

Location: `projection.md` §3 ("render prism"), `scene.md` "Rules" (margin), `projection.md` §1
(convergence), `city-config.schema.json` `aoi.marginM` description, `docs/DATA_SOURCES.md`.

Evidence: see items 4, 5 and 7. The AOI prism is fully contained (north-east corner at `zMax` →
`Y = 0.6`, north-west → `X = 0.1`); margin corners reach `|u| = 7 014 px` against `5 657`, so
margin content is clipped (up to 1 357 px); image corners map to ground 400–600 m outside a
120 m margin, and 25.4 % of the image is void; `DATA_SOURCES.md` has no hill height, so ADR
0003's occlusion claim has no input; and the fine print of §1 says "the viewing direction" where
it means its horizontal projection (the along-ray error is `Δz/sinφ`, not `Δz/tanφ`).

Proposed fix (contract text): "The master image is the bounding box of the AOI prism
(AOI rectangle × `[zMin, zMax]`). Every point of the AOI with `z ∈ [zMin, zMax]` is inside it.
Scene content outside the box is clipped, including the top of a tall feature just beyond the
AOI; the margin exists so that features at the AOI edge, and the ground behind them, are
present — it is not expected to fill the image rectangle, whose corners show background. The
image covers `X ∈ [0, width)`, `Y ∈ [0, height)`." Add to §5.1: "…along the **horizontal**
viewing direction". Add to `DATA_SOURCES.md` (WP01): the castle's height above the Plaza Mayor,
once the MDT is in.

### R-17 — minor — contract lint: redundant or unpinned fields

Location and evidence, one line each:

- `city.json` `tiles.format` duplicates `styles[].format` in the tile manifest and nothing reads
  it — remove it or say which wins (the manifest).
- `scene.md` roads: `layer > 0` promises bridges but roads are "draped on the terrain" and no
  clearance exists, so a bridge over a cutting is drawn at ground level. Say "bridges are
  draped in v0.1" and/or require `layer = 0` in the AOI.
- `scene.md` landcover: "non-overlapping" is not expressible in JSON Schema and pairwise testing
  is expensive; say which class wins on overlap (or that the pipeline fails loudly).
- `scene.md` trees: `source = "scattered"` needs a seed; no document fixes it, so two runs could
  differ. Put the seed in the city config or in a module constant named by the contract.
- `ARCHITECTURE.md` fixes the height grid at 4 m and the tile size at 512, but `city.json`
  carries only the tile size. Either add `heightGrid` settings to the city config or state that
  WP06 chooses them and records them in the manifest (the manifest already has the geometry).
- `tests/fixtures/scene-synthetic/scene.json` has `provenance: []` while its only dataset has
  `sha256: null`, which the dataset-manifest schema says the pipeline must refuse. Exempt
  fixtures explicitly in the schema's description.

### R-18 — note — the image budget is sound, and four corners are void by construction

Evidence: at Villena settings (AOI 1 km, s = 8, relief 120 m) the prism gives
**11 314 × 6 489 px = 73.4 Mpx**; the AOI's projected diamond is 32.0 Mpx, i.e. 43.6 % of the
image; decoded buffers are 294 MB (color rgba8), 220 MB (buildingId rgb24), 147 MB (depth
gray16) and 73 MB (class index8) = **734 MB**, inside the "≤ 8 GB" render budget; 299 base
tiles and a **425-tile** full pyramid (COSTS.md's `4/3·23·13 = 399` estimate is 6 % low, and
its height formula `√2·L·s·sinφ + Δz·s·cosφ = 6 488` matches the exact 6 489). 25.4 % of the
image is void (R-01). No change requested: ADR 0003 already allows `pixelsPerMetre` to change
before release, and the numbers fit the budget.

### R-19 — note — second city in another UTM zone; version check order

Evidence: `crs.world` is `const: "EPSG:25830"` in three schemas; the projection arithmetic is
CRS-agnostic; the fixtures' vectors are in local metres and would not change. A MINOR addition
cannot relax a `const`, so another zone is a MAJOR bump (ADR 0003 already says so). Write down
that consumers must check `schemaVersion` before validating against a schema
(`additionalProperties: false` makes a v1.1 document fail a v1.0 schema on its new optional
field).

### R-20 — note — the synthetic city cannot exercise the parts that matter most

Evidence: the fixture's renderer paints only inside the AOI (`ground_colour` returns the
background outside `[0, 128)`), the `class` layer only contains 0, 1 and 2 (no wall, roof,
vegetation or water), `buildingId` is a constant array, and the POI set has 5 entries. So the
fixtures cannot detect margin drawing (R-16), depth encoding (R-02), palette rules (R-06) or
the tiered layers' registration. When the architect regenerates the fixtures (G1), consider
adding: one building drawn with `class` 3/4, one tree with `class` 5, one water polygon, a
margin-only building, and a two-part building in `buildingId` so index 0 and index ≥ 1 are both
exercised. WP08 will need those fixtures anyway.

## Verdict

**Approve with changes.** The architecture, the projection and the fixtures are sound: the
camera basis is exactly orthonormal, `r × p = −w`, the 2:1 property holds at every heading, all
24 projection vectors reproduce to 5e-10, the master-image and DZI arithmetic are exact and
match the committed 17-file pyramid pixel for pixel, all six `expected.json` ground points and
all three reference-plane cases reproduce, and the `geoToWorld` fit is 10× better than its
ceiling. Nothing here needs a different architecture, and the second-city question is a
formality.

Before G1 can freeze, resolve **R-01 (blocker)**, **R-02**, **R-03**, **R-04**, **R-05**,
**R-06** and **R-07** — all are contract text or schema text, none requires new data, and
together they are an evening's editing for the architect. R-08 to R-17 should go in the same
pass because the freeze is the last cheap moment; R-18 to R-20 are records, not requests.

The most consequential findings for the work packages:

- **WP05 (viewer)**: R-01 (background clicks must not produce positions), R-11 (use `2^k`, not
  the size ratio), R-14 (URL error budget).
- **WP06 (export)**: R-02 (depth), R-05 (scene POIs), R-11, R-15 (traceability), R-14
  (cross-checks in `validate-tiles`).
- **WP04 (renderer)**: R-06 (palette), R-07 (determinism split), R-13 (eaves/ridge).
- **WP03 (GIS)**: R-12 (`datasets.json`, vertical datum), R-17 (seeds, overlap policy, provenance).
- **WP08 (tests)**: R-04 (a ridge fixture), R-20 (richer Planeville).

## Decisions and assumptions

- I assumed the DeepSeek task assigned to this session is WP02, per `docs/AGENT_ROUTING.md`
  (WP02 primary: DeepSeek V4 Pro; WP11 needs WP03–WP08 merged and WP08 needs WP04–WP07, so
  neither is runnable in this repository state).
- Branch created in the main checkout instead of a separate worktree: the file sandbox of this
  session is confined to the repository root, and `make worktree` writes outside it. The tree
  was clean, `main` = `agent/wp00-bootstrap` = `ba8ba0c`, and no other writer was active.
- For the Villena image and occlusion numbers I used the relief `Δz ≈ 120 m` recorded in
  `docs/COSTS.md` and split it as `z ∈ [−30, +90]` m around `H0 = 500`. The split does not
  change the image size (only the span does) and it does not change any conclusion.
- The cast-shadow question (sun direction) was not reviewed; it is a rendering style decision,
  not a projection one.

## Contract change requests

All of them, un-made (only the architect edits contracts): R-01, R-03, R-04, R-11, R-16 in
`docs/contracts/projection.md`; R-13, R-17 (roads, landcover, trees, margin, POI sort) in
`docs/contracts/scene.md`; R-02, R-06, R-09, R-15 in `docs/contracts/render.md`; R-05 (new
`scene-pois.schema.json`), R-02 (`dMin`/`offset`/`scale` wording), R-03 (`exclusiveMaximum: 90`
or a φ = 90 branch), R-06 (`palette`/`paletteSha256`), R-07 (`pixelSha256`), R-10 (rounding),
R-15 (`crs`, `renderSha256`) in `packages/geo-contracts/schemas/*.schema.json`; R-05 in
`scripts/validate_contracts.py`; R-11/R-13/R-17 in `docs/ARCHITECTURE.md` if the decisions
change. R-09 changes the fixtures, so it must be part of a `make fixtures` run at G1.

## Known problems

1. The castle-hill occlusion cannot be quantified from the repository: `DATA_SOURCES.md` has no
   hill height and no relief figures. WP01 should record the castle's height above the Plaza
   Mayor and the AOI's MDT min/max.
2. Cross-platform determinism is unverified and, for file bytes, unachievable as written (R-07);
   there is no Linux machine in this session and no renderer yet.
3. The DZI check is against the specification; no OpenSeadragon instance exists to confirm that
   the manifest-to-tile-source adapter behaves (WP05/WP08).
4. `docs/PROJECT_STATE.md` still says "Contracts: PROPOSED v1" — correct, but it also still
   says "Nothing is committed beyond the first two commits; nothing is pushed; no remote
   exists", which was true when written and is no longer: the bootstrap is committed on `main`
   and an `origin` remote exists (data for the integrator, not a contract change).
5. The WP00 handoff and `PROJECT_STATE.md` were updated while this review was reading the tree;
   the base commit is `ba8ba0c` and everything above refers to it.

## Human approvals needed

- None for the review itself. Approvals the owner may still want to give:
  - whether this review is accepted as the WP02 sign-off on `deepseek-flash`, or repeated on
    `deepseek-v4-pro`;
  - the `docs/PROJECT_STATE.md` decisions list items 2–8 (licences, model access, IGN download,
    viewer language, AOI option, worktree location, GitHub owner) are unrelated to this review
    but block G1's "what changes for each WP" answer in part;
  - no spend, no push, no publish: none was attempted.

## Recommended next task

Architect session (`prompts/00-bootstrap.md`, **Task A — gate G1**): reproduce R-01 to R-07,
accept or refute each, apply the accepted text, add the new `scene-pois.schema.json`, regenerate
the fixtures (`uv run scripts/make_fixtures.py`), write the ADRs for the changes that touch
another package (R-01, R-02, R-07 at least), then set `Contracts: FROZEN v1` with the commit
hash. In parallel, WP01 and WP07 are unaffected by this review and can continue.

---

# Appendix A — `wp02_checks.py` (verbatim)

```
#!/usr/bin/env python3
"""WP02 independent numeric checks for Villena Isometrica.

Reads the repository's contracts, fixtures and city config; recomputes everything from
docs/contracts/projection.md and from first principles. Does not import any project code.
Run: uv run --no-project --with pyproj --with numpy python wp02_checks.py <repo-root>
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
FIX = ROOT / "tests" / "fixtures"

out = []


def say(*a):
    line = " ".join(str(x) for x in a)
    out.append(line)
    print(line)


def load(p):
    return json.loads(Path(p).read_text())


# ---------------------------------------------------------------- A. algebra
say("== A. camera basis ==")
worst = 0.0
for head in (0, 45, 90, 137, 200, 315):
    for pitch in (15, 30, 45, 60, 89.9):
        a, f = math.radians(head), math.radians(pitch)
        r = np.array([math.cos(a), -math.sin(a), 0.0])
        p = np.array([math.sin(a) * math.sin(f), math.cos(a) * math.sin(f), math.cos(f)])
        w = np.array([math.sin(a) * math.cos(f), math.cos(a) * math.cos(f), -math.sin(f)])
        worst = max(worst, abs(r @ r - 1), abs(p @ p - 1), abs(w @ w - 1),
                    abs(r @ p), abs(r @ w), abs(p @ w), np.abs(np.cross(r, p) + w).max())
say(f"max |norms-1|, |dot|, |r x p + w| over 30 (heading,pitch) pairs: {worst:.3e}")

# 2:1 ground diamond: projected edge lengths of a 10 m axis-aligned square
a, f = math.radians(45), math.radians(30)
for L in (10.0,):
    ex = np.array([L * math.cos(a), -L * math.sin(a) * math.sin(f)])   # x edge, image (u,v)
    ey = np.array([-L * math.sin(a), -L * math.cos(a) * math.sin(f)])  # y edge
    span_u = abs(ex[0]) + abs(ey[0])
    span_v = abs(ex[1]) + abs(ey[1])
    say(f"alpha=45, phi=30: {L:.0f} m square -> u span {span_u:.6f} px, v span {span_v:.6f} px,"
        f" ratio {span_u / span_v:.9f} (must be 2)")
for head in (0, 17, 45, 200, 333):
    a = math.radians(head)
    ex = np.array([math.cos(a), -math.sin(a) * math.sin(f)])
    ey = np.array([-math.sin(a), -math.cos(a) * math.sin(f)])
    say(f"  heading {head:>3}: u span/(v span) = {(abs(ex[0]) + abs(ey[0])) / (abs(ex[1]) + abs(ey[1])):.9f}")


# ---------------------------------------------------------------- B. vectors
say("\n== B. projection-vectors.json recomputed ==")
V = load(ROOT / "packages" / "geo-contracts" / "fixtures" / "projection-vectors.json")
maxerr = 0.0
for cam in V["cameras"]:
    a = math.radians(cam["headingDeg"])
    f = math.radians(cam["pitchDeg"])
    s = cam["pixelsPerMetre"]
    ca, sa, cf, sf = math.cos(a), math.sin(a), math.cos(f), math.sin(f)
    cerr = 0.0
    for pt in cam["points"]:
        x, y, z = pt["xyz"]
        u = s * (x * ca - y * sa)
        v = -s * ((x * sa + y * ca) * sf + z * cf)
        d = (x * sa + y * ca) * cf - z * sf
        cerr = max(cerr, abs(u - pt["u"]), abs(v - pt["v"]), abs(d - pt["d"]))
    maxerr = max(maxerr, cerr)
    say(f"  camera {cam['name']:<28} heading {cam['headingDeg']:>5} pitch {cam['pitchDeg']:>4}:"
        f" 6 points, max |err| = {cerr:.3e}")
say(f"  worst error over all vectors: {maxerr:.3e} (tolerance 1e-6)")
obl = V["cameras"][3]
a, f = math.radians(obl["headingDeg"]), math.radians(obl["pitchDeg"])
s = obl["pixelsPerMetre"]
for pt in (obl["points"][1], obl["points"][4]):
    x, y, z = pt["xyz"]
    u = s * (x * math.cos(a) - y * math.sin(a))
    v = -s * ((x * math.sin(a) + y * math.cos(a)) * math.sin(f) + z * math.cos(f))
    d = (x * math.sin(a) + y * math.cos(a)) * math.cos(f) - z * math.sin(f)
    say(f"  oblique (heading {obl['headingDeg']}, pitch {obl['pitchDeg']}) point {pt['xyz']}: "
        f"u {u:.9f} vs {pt['u']}, v {v:.9f} vs {pt['v']}, d {d:.9f} vs {pt['d']}")

# ---------------------------------------------------------------- C. fixture geometry + tiles
say("\n== C. master image and DZI pyramid for the synthetic fixture ==")
city = load(FIX / "city-synthetic" / "city.json")
man = load(FIX / "tiles-synthetic" / "manifest.json")
ren = load(FIX / "render-synthetic" / "render.json")
cam = city["camera"]
a, f, s = math.radians(cam["headingDeg"]), math.radians(cam["pitchDeg"]), cam["pixelsPerMetre"]
ca, sa, cf, sf = math.cos(a), math.sin(a), math.cos(f), math.sin(f)
E0, N0, H0 = city["origin"]["E0"], city["origin"]["N0"], city["origin"]["H0"]
minE, minN, maxE, maxN = city["aoi"]["bounds"]
zMin, zMax = man["zRange"]["zMin"], man["zRange"]["zMax"]
pts = [(minE - E0, minN - N0), (maxE - E0, minN - N0), (minE - E0, maxN - N0), (maxE - E0, maxN - N0)]
uv = [(s * (x * ca - y * sa), -s * ((x * sa + y * ca) * sf + z * cf)) for x, y in pts for z in (zMin, zMax)]
u0, v0 = math.floor(min(q[0] for q in uv)), math.floor(min(q[1] for q in uv))
W, Hh = math.ceil(max(q[0] for q in uv)) - u0, math.ceil(max(q[1] for q in uv)) - v0
say(f"  camera heading {cam['headingDeg']} pitch {cam['pitchDeg']} s {s}; AOI {maxE - minE:.0f} x {maxN - minN:.0f} m;"
    f" zRange [{zMin}, {zMax}]")
say(f"  recomputed from projection.md section 3: u0 {u0}, v0 {v0}, image {W} x {Hh};"
    f" manifest says {man['image']['width']} x {man['image']['height']}, translation {man['projection']['translation']}")
assert (W, Hh) == (man["image"]["width"], man["image"]["height"])

T, OV = man["tiles"]["tileSize"], man["tiles"]["tileOverlap"]
maxL = math.ceil(math.log2(max(W, Hh)))
say(f"  T {T}, overlap {OV}, maxLevel recomputed {maxL} vs manifest {man['tiles']['maxLevel']}")
expected = []
for L in range(maxL + 1):
    k = maxL - L
    lw, lh = -(-W // 2 ** k), -(-Hh // 2 ** k)
    for row in range(-(-lh // T)):
        for col in range(-(-lw // T)):
            x0, y0 = max(col * T - OV, 0), max(row * T - OV, 0)
            x1, y1 = min((col + 1) * T + OV, lw), min((row + 1) * T + OV, lh)
            expected.append((L, col, row, x1 - x0, y1 - y0, lw, lh))
actual = sorted(p.relative_to(FIX / "tiles-synthetic" / "procedural") for p in
                (FIX / "tiles-synthetic" / "procedural").rglob("*.png"))
exp_names = sorted(Path(str(L)) / f"{c}_{r}.png" for L, c, r, *_ in expected)
say(f"  expected {len(expected)} tile files; on disk {len(actual)}; identical list: {actual == exp_names}")
for L, c, r, w, h, lw, lh in expected:
    if L == maxL or (c, r) == (0, 0) or (c == -(-lw // T) - 1 and r == -(-lh // T) - 1):
        say(f"    level {L:>2} size {lw:>3}x{lh:<3} tile {c}_{r}: {w}x{h} px")
edge = [e for e in expected if e[0] == maxL]
say(f"  maxLevel tiles {len(edge)}; sizes: " + ", ".join(f"{c}_{r}={w}x{h}" for L, c, r, w, h, *_ in edge))
say(f"  interior tile at maxLevel is {T + 2 * OV} x {T + 2 * OV} with overlap; edge tiles are clipped, not padded")

# ---------------------------------------------------------------- D. expected.json
say("\n== D. expected.json ground points, recomputed independently ==")
exp = load(FIX / "tiles-synthetic" / "expected.json")
tx, ty = man["projection"]["translation"]
M = man["projection"]["matrix"]
C1, C2 = 0.10, 0.05


def fwd(x, y, z):
    return M[0][0] * x + M[0][1] * y + M[0][2] * z + tx, M[1][0] * x + M[1][1] * y + M[1][2] * z + ty


def plane_pick_numeric(X, Y):
    """Independent: walk the pixel ray parameter t and bisect z(t) - plane(x(t), y(t))."""
    a_ = (X - tx) / s
    q_ = -(Y - ty) / s
    # point on ray: x = a_*ca + b*sa, y = -a_*sa + b*ca, z = q_ - b*sf/cf? z from q = b*sf + z*cf
    def g(b):
        x_ = a_ * ca + b * sa
        y_ = -a_ * sa + b * ca
        z_ = (q_ - b * sf) / cf
        return z_ - (C1 * x_ + C2 * y_)

    lo, hi = -1e4, 1e4  # g is linear; bisection is still an independent check
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if g(lo) * g(mid) <= 0:
            hi = mid
        else:
            lo = mid
    b = 0.5 * (lo + hi)
    return a_ * ca + b * sa, -a_ * sa + b * ca


for gp in exp["groundPoints"]:
    x, y = gp["E"] - E0, gp["N"] - N0
    X, Y = fwd(x, y, gp["H"] - H0)
    px, py = plane_pick_numeric(gp["X"], gp["Y"])
    say(f"  E {gp['E']:.1f} N {gp['N']:.1f} H {gp['H']:.3f}: recomputed X {X:.6f} Y {Y:.6f} | file X {gp['X']} Y {gp['Y']}"
        f" | dXY = {X - gp['X']:+.2e},{Y - gp['Y']:+.2e}"
        f" | numeric pick {E0 + px:.4f},{N0 + py:.4f} (dE {E0 + px - gp['E']:+.4f} dN {N0 + py - gp['N']:+.4f})")
say("  reference-plane cases (projection.md 5.1, zr = 0):")
for c in exp["referencePlane"]["cases"]:
    a_ = (c["X"] - tx) / s
    b_ = (-(c["Y"] - ty) / s) / sf
    x = a_ * ca + b_ * sa
    y = -a_ * sa + b_ * ca
    say(f"    X {c['X']} Y {c['Y']}: recomputed E {E0 + x:.6f} N {N0 + y:.6f} | file E {c['E']} N {c['N']}")

# ---------------------------------------------------------------- E. geoToWorld
say("\n== E. geoToWorld affine ==")
to_geo = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
from_geo = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
fmt = man["geoToWorld"]["matrix"]


def fit_affine(pts_en):
    ll = np.array([to_geo.transform(e, n) for e, n in pts_en])
    lon0, lat0 = ll.mean(axis=0)
    A = np.column_stack([ll[:, 0] - lon0, ll[:, 1] - lat0, np.ones(len(ll))])
    coef, *_ = np.linalg.lstsq(A, np.array(pts_en), rcond=None)
    m = [[coef[0][k], coef[1][k], coef[2][k] - coef[0][k] * lon0 - coef[1][k] * lat0] for k in (0, 1)]
    return m


def residual(m, E, N):
    lon, lat = to_geo.transform(E, N)
    return math.hypot(m[0][0] * lon + m[0][1] * lat + m[0][2] - E,
                      m[1][0] * lon + m[1][1] * lat + m[1][2] - N)


for gp in exp["groundPoints"]:
    lon, lat = to_geo.transform(gp["E"], gp["N"])
    say(f"  (E {gp['E']:.1f}, N {gp['N']:.1f}) -> lon {lon:.8f} lat {lat:.8f} | file lon {gp['lon']} lat {gp['lat']}")
say(f"  fixture affine residual re-measured: {max(residual(fmt, E0 + 128 * i / 8, N0 + 128 * j / 8) for i in range(9) for j in range(9)):.3e} m"
    f" (manifest maxResidualM {man['geoToWorld']['maxResidualM']})")

# Villena AOI, 5x5 and 9x9 fits
vil = load(ROOT / "cities" / "villena" / "city.json")
vminE, vminN, vmaxE, vmaxN = vil["aoi"]["bounds"]
marg = vil["aoi"]["marginM"]
for margin in (0.0, marg):
    e_lo, e_hi, n_lo, n_hi = vminE - margin, vmaxE + margin, vminN - margin, vmaxN + margin
    fit_pts = [(e_lo + (e_hi - e_lo) * i / 4, n_lo + (n_hi - n_lo) * j / 4) for i in range(5) for j in range(5)]
    m = fit_affine(fit_pts)
    r = max(residual(m, e_lo + (e_hi - e_lo) * i / 24, n_lo + (n_hi - n_lo) * j / 24)
            for i in range(25) for j in range(25))
    say(f"  Villena fit over {e_hi - e_lo:.0f} x {n_hi - n_lo:.0f} m (margin {margin:.0f} m): max residual {r:.4f} m")
ll = np.array([to_geo.transform(e, n) for e in (vminE, vmaxE) for n in (vminN, vmaxN)])
say(f"  Villena AOI corners in WGS84: lon {ll[:, 0].min():.6f}..{ll[:, 0].max():.6f},"
    f" lat {ll[:, 1].min():.6f}..{ll[:, 1].max():.6f}")
say(f"  DATA_SOURCES envelope: lon -0.869027..-0.857279, lat 38.626433..38.635648")
say(f"  span comparison: dlon {ll[:, 0].max() - ll[:, 0].min():.6f} vs 0.011748 deg;"
    f" dlat {ll[:, 1].max() - ll[:, 1].min():.6f} vs 0.009215 deg")
geod = None
try:
    from pyproj import Geod
    geod = Geod(ellps="WGS84")
    lon_c = 0.5 * (ll[:, 0].min() + ll[:, 0].max())
    lat_c = 0.5 * (ll[:, 1].min() + ll[:, 1].max())
    E_c, N_c = from_geo.transform(lon_c, lat_c)
    az, _, _ = geod.inv(lon_c, lat_c, *to_geo.transform(E_c, N_c + 1000.0))
    az2, _, _ = geod.inv(lon_c, lat_c, *to_geo.transform(E_c, N_c - 1000.0))
    say(f"  grid convergence at AOI centre: azimuth of grid north = {az:.3f} deg, of grid south = {az2:.3f} deg"
        f" (convergence ~{(az - 0.0):.3f} deg from true north)")
except Exception as exc:  # pragma: no cover
    say(f"  convergence not computed: {exc}")

# ---------------------------------------------------------------- F. Villena image
say("\n== F. Villena master image and tile budget ==")
vcam = vil["camera"]
a, f, s = math.radians(vcam["headingDeg"]), math.radians(vcam["pitchDeg"]), vcam["pixelsPerMetre"]
ca, sa, cf, sf = math.cos(a), math.sin(a), math.cos(f), math.sin(f)
L = vmaxE - vminE
RELIEF = 120.0  # docs/COSTS.md "Δz ~ 120 est."
zMin, zMax = -0.25 * RELIEF, 0.75 * RELIEF
uv = [(s * (x * ca - y * sa), -s * ((x * sa + y * ca) * sf + z * cf))
      for x in (0, L) for y in (0, L) for z in (zMin, zMax)]
u0, v0 = math.floor(min(q[0] for q in uv)), math.floor(min(q[1] for q in uv))
W, Hh = math.ceil(max(q[0] for q in uv)) - u0, math.ceil(max(q[1] for q in uv)) - v0
say(f"  L {L:.0f} m, s {s}, z in [{zMin}, {zMax}] m rel. H0 (relief {RELIEF:.0f} m): image {W} x {Hh}"
    f" = {W * Hh / 1e6:.1f} Mpx; ADR 0003 says ~11 300 x 6 500")
diamond = 2 * s * L / math.sqrt(2) * (2 * s * L / math.sqrt(2) * sf) / 2
say(f"  projected AOI ground diamond {2 * s * L / math.sqrt(2):.0f} px wide, {2 * s * L / math.sqrt(2) * sf:.0f} px tall,"
    f" area {diamond / 1e6:.1f} Mpx = {100 * diamond / (W * Hh):.1f} % of the image (rest is prism band)")
for name, bpp in (("color rgba8", 4), ("class index8", 1), ("buildingId rgb24", 3), ("depth gray16", 2)):
    say(f"  decoded buffer for the {name} layer: {W * Hh * bpp / 1e6:.0f} MB")
T2 = vil["tiles"]["tileSize"]
say(f"  tiles with T={T2}: maxLevel {math.ceil(math.log2(max(W, Hh)))},"
    f" base tiles {-(-W // T2) * -(-Hh // T2)}, full pyramid {sum(-(-(-(-W // 2 ** k)) // T2) * -(-(-(-Hh // 2 ** k)) // T2) for k in range(math.ceil(math.log2(max(W, Hh))) + 1))}"
    f"; COSTS.md estimate (4/3)*ceil(w/T)*ceil(h/T) = {4 / 3 * -(-W // T2) * -(-Hh // T2):.0f}")

# ---------------------------------------------------------------- G. occlusion
say("\n== G. occlusion behind an obstacle, phi = 30 deg ==")
for h in (5, 10, 20, 30, 50, 80):
    say(f"  obstacle {h:>2} m above the ground in front: hidden ground length {h / math.tan(f):6.1f} m"
        f" ({h / math.tan(f) / 1000:.3f} km); hidden area for a 100 m wide hill {100 * h / math.tan(f) / 1e4:.2f} ha")
say("  DATA_SOURCES.md section 'Area of interest' states no hill height or relief figure for Villena")
castle = (686188 - vminE, 4278098 - vminN)
for z in (0, 30, 60):
    x, y = castle
    X = s * (x * ca - y * sa) - u0
    Y = -s * ((x * sa + y * ca) * sf + z * cf) - v0
    say(f"  castle (E 686188, N 4278098, z {z:>2} m): image pixel {X:.0f}, {Y:.0f} of {W} x {Hh}"
        f" ({100 * X / W:.0f} % from left, {100 * Y / Hh:.0f} % from top)")

# ---------------------------------------------------------------- H. margin clipping
say("\n== H. what the AOI prism covers vs the scene margin ==")
mrg = vil["aoi"]["marginM"]
for (x, y, tag) in ((0, 0, "SW corner of AOI"), (L, 0, "SE"), (L, L, "NE"), (0, L, "NW"),
                    (-mrg, L + mrg, "NW margin corner"), (L + mrg, L + mrg, "NE margin corner")):
    for z in (zMin, zMax):
        X = s * (x * ca - y * sa) - u0
        Y = -s * ((x * sa + y * ca) * sf + z * cf) - v0
        say(f"  {tag:<18} z {z:>6.1f}: X {X:>9.1f} Y {Y:>8.1f} -> {'inside' if 0 <= X <= W and 0 <= Y <= Hh else 'OUTSIDE'} the image")
# how far beyond the AOI an image corner lies on the ground
for X, Y, tag in ((0, 0, "top-left"), (W, 0, "top-right"), (0, Hh, "bottom-left")):
    a_ = (X + u0) / s
    b_ = (-(Y + v0) / s) / sf
    x, y = a_ * ca + b_ * sa, -a_ * sa + b_ * ca
    say(f"  {tag:<11} image corner maps to local x {x:>7.1f} y {y:>7.1f} m"
        f" (AOI is 0..{L:.0f}; margin {mrg:.0f} m)")
say(f"  max |u| of a margin corner vs the AOI prism: "
    f"{max(abs(s * (x * ca - y * sa)) for x in (-mrg, L + mrg) for y in (-mrg, L + mrg)):.0f} px vs"
    f" {s * L / math.sqrt(2):.0f} px")

# ---------------------------------------------------------------- I. quantisation / grid
say("\n== I. height grid quantisation and picking tolerance ==")
hg = man["heightGrid"]
zr = man["zRange"]
say(f"  fixture grid {hg['width']}x{hg['height']} cell {hg['cellSize']} m scale {hg['scale']} offset {hg['offset']};"
    f" z span {zr['zMax'] - zr['zMin']} m -> {(zr['zMax'] - zr['zMin']) / hg['scale']:.0f} codes of 65535")
say(f"  Villena relief {RELIEF:.0f} m needs {RELIEF / 0.01:.0f} codes of 65535 -> fits")
for cell in (0.5, 2.0, 4.0):
    say(f"  cell {cell} m: worst-case bilinear undersampling of a 1-cell-wide ridge,"
        f" pick error along the ray ~ {cell / 2 / math.tan(f):.2f} m")
say(f"  1 cm quantisation -> {0.01 / math.tan(f):.4f} m horizontal, well inside the 0.05 m tolerance")

# ---------------------------------------------------------------- J. map bounds consistency
say("\n== J. cross-file consistency ==")
say(f"  render.json image {ren['image']} vs manifest {man['image']}")
say(f"  render projection == manifest projection: {ren['projection'] == man['projection']}")
say(f"  render zRange {ren['zRange']} == manifest {man['zRange']} == scene:"
    f" {ren['zRange'] == man['zRange'] == load(FIX / 'scene-synthetic' / 'scene.json')['zRange']}")
scene = load(FIX / "scene-synthetic" / "scene.json")
say(f"  scene aoi {scene['aoi']} origin {scene['origin']}")
say(f"  scene terrain covers {scene['terrain']['width']}x{scene['terrain']['height']} cells of"
    f" {scene['terrain']['cellSize']} m from westE {scene['terrain']['westE']} northN {scene['terrain']['northN']}")
pois = load(FIX / "tiles-synthetic" / "pois.json")["pois"]
for p in pois:
    X, Y = fwd(p["E"] - E0, p["N"] - N0, p["H"] - H0)
    say(f"  POI {p['id']:<12} forward gives X {X:.3f} Y {Y:.3f} | file {p['X']}, {p['Y']}")
print("\n".join([]) or "", end="")
(Path("/tmp/wp02-villena/checks-output.txt") if Path("/tmp/wp02-villena").is_dir() else Path("checks-output.txt")).write_text("\n".join(out) + "\n")

```

# Appendix B — `wp02_checks2.py` (verbatim)

```
#!/usr/bin/env python3
"""WP02 extra checks: void pixels, encoder determinism, JSON float formatting, level mapping.

Run: uv run --no-project --with pyproj --with numpy python wp02_checks2.py <repo-root>
"""
import json
import math
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
FIX = ROOT / "tests" / "fixtures"


def load(p):
    return json.loads(Path(p).read_text())


# ---------------------------------------------------------------- 1. fixture: ray start
man = load(FIX / "tiles-synthetic" / "manifest.json")
city = load(FIX / "city-synthetic" / "city.json")
hg = man["heightGrid"]
a, f, s = (math.radians(city["camera"]["headingDeg"]), math.radians(city["camera"]["pitchDeg"]),
           city["camera"]["pixelsPerMetre"])
ca, sa, cf, sf = math.cos(a), math.sin(a), math.cos(f), math.sin(f)
tx, ty = man["projection"]["translation"]
E0, N0 = city["origin"]["E0"], city["origin"]["N0"]
zMin, zMax = man["zRange"]["zMin"], man["zRange"]["zMax"]
W, Hh = man["image"]["width"], man["image"]["height"]
gw, gh = hg["width"], hg["height"]
wE, nN, cell = hg["westE"], hg["northN"], hg["cellSize"]
e_lo, e_hi = wE - E0, wE + gw * cell - E0
n_lo, n_hi = nN - gh * cell - N0, nN - N0
print(f"== 1. the fixture's height grid covers local x {e_lo:.1f}..{e_hi:.1f}, y {n_lo:.1f}..{n_hi:.1f} ==")
print(f"   scene terrain covers x {-city['aoi']['marginM']:.1f}..{city['aoi']['bounds'][2] - E0 + city['aoi']['marginM']:.1f},"
      f" y {-city['aoi']['marginM']:.1f}..{city['aoi']['bounds'][3] - N0 + city['aoi']['marginM']:.1f}")
for X, Y in ((0, 0), (0, Hh - 1), (W - 1, 0), (W - 1, Hh - 1), (363, 0)):
    aa = (X - tx) / s
    qq = -(Y - ty) / s
    b = (qq - zMax * cf) / sf
    x, y = aa * ca + b * sa, -aa * sa + b * ca
    inside = e_lo <= x <= e_hi and n_lo <= y <= n_hi
    print(f"   pixel ({X:>3},{Y:>3}): ray at z = zMax {zMax} starts at local x {x:7.1f} y {y:7.1f}"
          f" -> {'inside' if inside else 'OUTSIDE'} the height grid")


# ---------------------------------------------------------------- 2. how much of the image has a ray that reaches the scene
def reach_fraction(W, H, tx, ty, s, ca, sa, cf, sf, zMin, zMax, e_lo, e_hi, n_lo, n_hi, step):
    xs = np.arange(0.5, W, step)
    ys = np.arange(0.5, H, step)
    X, Y = np.meshgrid(xs, ys)
    aa = (X - tx) / s
    qq = -(Y - ty) / s
    b_top = (qq - zMax * cf) / sf
    b_bot = (qq - zMin * cf) / sf
    ok = np.zeros(X.shape, dtype=bool)
    for t in np.linspace(0, 1, 129):
        b = b_top + (b_bot - b_top) * t
        x = aa * ca + b * sa
        y = -aa * sa + b * ca
        ok |= (x >= e_lo) & (x <= e_hi) & (y >= n_lo) & (y <= n_hi)
    return float(ok.mean())


print("\n== 2. share of image pixels whose ray passes through the scene footprint ==")
fr = reach_fraction(W, Hh, tx, ty, s, ca, sa, cf, sf, zMin, zMax, e_lo, e_hi, n_lo, n_hi, 1)
print(f"   fixture 726x481, grid {gw}x{gh} cells of {cell} m: {100 * fr:.1f} % reach the grid,"
      f" {100 * (1 - fr):.1f} % never do (the four corner triangles)")

vil = load(ROOT / "cities" / "villena" / "city.json")
vc = vil["camera"]
a2, f2, s2 = math.radians(vc["headingDeg"]), math.radians(vc["pitchDeg"]), vc["pixelsPerMetre"]
ca2, sa2, cf2, sf2 = math.cos(a2), math.sin(a2), math.cos(f2), math.sin(f2)
L = vil["aoi"]["bounds"][2] - vil["aoi"]["bounds"][0]
mrg = vil["aoi"]["marginM"]
RELIEF = 120.0
zmin2, zmax2 = -0.25 * RELIEF, 0.75 * RELIEF
uv = [(s2 * (x * ca2 - y * sa2), -s2 * ((x * sa2 + y * ca2) * sf2 + z * cf2))
      for x in (0, L) for y in (0, L) for z in (zmin2, zmax2)]
u0, v0 = math.floor(min(q[0] for q in uv)), math.floor(min(q[1] for q in uv))
W2, H2 = math.ceil(max(q[0] for q in uv)) - u0, math.ceil(max(q[1] for q in uv)) - v0
fr2 = reach_fraction(W2, H2, -u0, -v0, s2, ca2, sa2, cf2, sf2, zmin2, zmax2,
                     -mrg, L + mrg, -mrg, L + mrg, 24)
print(f"   Villena {W2}x{H2}, scene footprint {L + 2 * mrg:.0f} x {L + 2 * mrg:.0f} m:"
      f" {100 * fr2:.1f} % reach the scene, {100 * (1 - fr2):.1f} % are void")

# ---------------------------------------------------------------- 3. PNG bytes vs decoded pixels
print("\n== 3. PNG encoding determinism ==")
raw = bytes(range(256)) * 4
for level in (1, 6, 9):
    data = zlib.compress(raw, level)
    print(f"   zlib level {level}: sha256 {__import__('hashlib').sha256(data).hexdigest()[:16]}"
          f" ({len(data)} bytes) for the same 1024 bytes of pixels")
print(f"   python zlib build: {zlib.ZLIB_VERSION} (runtime {zlib.ZLIB_RUNTIME_VERSION});"
      f" the PNG bytes depend on this, the pixels do not")

# ---------------------------------------------------------------- 4. JSON float text across languages
print("\n== 4. JSON number formatting across implementations ==")
vals = [1.0, 1e-7, 0.1 + 0.2, -0.0, 123456789012345678.0]
py = json.dumps(vals, separators=(",", ":"))
print(f"   python json.dumps: {py}")
try:
    js = subprocess.run(["node", "-e", f"console.log(JSON.stringify({json.dumps(vals)}))"],
                        capture_output=True, text=True, check=True).stdout.strip()
    print(f"   node JSON.stringify: {js}")
    print("   identical text:", py == js)
except Exception as exc:  # pragma: no cover
    print(f"   node not available: {exc}")

# ---------------------------------------------------------------- 5. level pixel -> master pixel with overlap
print("\n== 5. file pixel -> master pixel mapping (fixture, maxLevel 10) ==")
T, OV, maxL = man["tiles"]["tileSize"], man["tiles"]["tileOverlap"], man["tiles"]["maxLevel"]
for L, col, row in ((10, 2, 0), (10, 1, 1), (9, 1, 0), (9, 0, 0)):
    k = maxL - L
    lw = -(-W // 2 ** k)
    x0 = max(col * T - OV, 0)
    w = min((col + 1) * T + OV, lw) - x0
    print(f"   level {L} tile {col}_{row}: level x0 {x0} width {w} -> master x0 {x0 * 2 ** k}"
          f" to {(x0 + w) * 2 ** k} (width {w * 2 ** k})")
print(f"   ratio-based mapping at level 13 for Villena height {H2}: level rows {-(-H2 // 2)},"
      f" ratio {H2 / -(-H2 // 2):.6f} vs exact 2.0 -> drift up to {2 * -(-H2 // 2) - H2} master px")

```

# Appendix C — output of the two scripts

<details><summary>script A</summary>

```
== A. camera basis ==
max |norms-1|, |dot|, |r x p + w| over 30 (heading,pitch) pairs: 2.220e-16
alpha=45, phi=30: 10 m square -> u span 14.142136 px, v span 7.071068 px, ratio 2.000000000 (must be 2)
  heading   0: u span/(v span) = 2.000000000
  heading  17: u span/(v span) = 2.000000000
  heading  45: u span/(v span) = 2.000000000
  heading 200: u span/(v span) = 2.000000000
  heading 333: u span/(v span) = 2.000000000

== B. projection-vectors.json recomputed ==
  camera top-down, north up           heading     0 pitch   90: 6 points, max |err| = 3.553e-15
  camera dimetric 2:1 looking NE      heading    45 pitch   30: 6 points, max |err| = 4.619e-10
  camera looking east, 45 deg pitch   heading    90 pitch   45: 6 points, max |err| = 3.631e-10
  camera oblique, catches sign errors heading   200 pitch   35: 6 points, max |err| = 4.895e-10
  worst error over all vectors: 4.895e-10 (tolerance 1e-6)
  oblique (heading 200, pitch 35) point [10, 0, 0]: u -37.587704831 vs -37.587704831, v 7.846987799 vs 7.846987799, d -2.801664996 vs -2.801664996
  oblique (heading 200, pitch 35) point [100, 50, 25]: u -307.473019649 vs -307.473019649, v 104.351782498 vs 104.351782498, d -80.843617434 vs -80.843617434

== C. master image and DZI pyramid for the synthetic fixture ==
  camera heading 45.0 pitch 30.0 s 4.0; AOI 128 x 128 m; zRange [-3, 31]
  recomputed from projection.md section 3: u0 -363, v0 -470, image 726 x 481; manifest says 726 x 481, translation [363, 470]
  T 256, overlap 1, maxLevel recomputed 10 vs manifest 10
  expected 17 tile files; on disk 17; identical list: True
    level  0 size   1x1   tile 0_0: 1x1 px
    level  1 size   2x1   tile 0_0: 2x1 px
    level  2 size   3x2   tile 0_0: 3x2 px
    level  3 size   6x4   tile 0_0: 6x4 px
    level  4 size  12x8   tile 0_0: 12x8 px
    level  5 size  23x16  tile 0_0: 23x16 px
    level  6 size  46x31  tile 0_0: 46x31 px
    level  7 size  91x61  tile 0_0: 91x61 px
    level  8 size 182x121 tile 0_0: 182x121 px
    level  9 size 363x241 tile 0_0: 257x241 px
    level  9 size 363x241 tile 1_0: 108x241 px
    level 10 size 726x481 tile 0_0: 257x257 px
    level 10 size 726x481 tile 1_0: 258x257 px
    level 10 size 726x481 tile 2_0: 215x257 px
    level 10 size 726x481 tile 0_1: 257x226 px
    level 10 size 726x481 tile 1_1: 258x226 px
    level 10 size 726x481 tile 2_1: 215x226 px
  maxLevel tiles 6; sizes: 0_0=257x257, 1_0=258x257, 2_0=215x257, 0_1=257x226, 1_1=258x226, 2_1=215x226
  interior tile at maxLevel is 258 x 258 with overlap; edge tiles are clipped, not padded

== D. expected.json ground points, recomputed independently ==
  E 700000.0 N 4270000.0 H 500.000: recomputed X 363.000000 Y 470.000000 | file X 363.0 Y 470.0 | dXY = +0.00e+00,+0.00e+00 | numeric pick 700000.0000,4270000.0000 (dE +0.0000 dN +0.0000)
  E 700064.0 N 4270064.0 H 509.600: recomputed X 363.000000 Y 255.725289 | file X 363.0 Y 255.725289 | dXY = +0.00e+00,-4.89e-07 | numeric pick 700064.0000,4270064.0000 (dE -0.0000 dN -0.0000)
  E 700100.0 N 4270020.0 H 511.000: recomputed X 589.274170 Y 262.189255 | file X 589.27417 Y 262.189255 | dXY = -2.03e-08,-2.51e-07 | numeric pick 700100.0000,4270020.0000 (dE -0.0000 dN -0.0000)
  E 700020.0 N 4270100.0 H 507.000: recomputed X 136.725830 Y 276.045661 | file X 136.72583 Y 276.045661 | dXY = +2.03e-08,+2.09e-07 | numeric pick 700020.0000,4270100.0000 (dE +0.0000 dN +0.0000)
  E 700127.0 N 4270127.0 H 519.050: recomputed X 363.000000 Y 44.798619 | file X 363.0 Y 44.798619 | dXY = +5.68e-14,+3.89e-07 | numeric pick 700127.0000,4270127.0000 (dE +0.0000 dN +0.0000)
  E 700033.3 N 4270077.7 H 507.215: recomputed X 237.417836 Y 288.028801 | file X 237.417836 Y 288.028801 | dXY = -3.39e-07,+4.23e-07 | numeric pick 700033.3000,4270077.7000 (dE +0.0000 dN +0.0000)
  reference-plane cases (projection.md 5.1, zr = 0):
    X 0 Y 0: recomputed E 700102.000153 N 4270230.340034 | file E 700102.000153 N 4270230.340034
    X 363.0 Y 240.5: recomputed E 700081.140503 N 4270081.140503 | file E 700081.140503 N 4270081.140503
    X 726 Y 481: recomputed E 700060.280853 N 4269931.940972 | file E 700060.280853 N 4269931.940972

== E. geoToWorld affine ==
  (E 700000.0, N 4270000.0) -> lon -0.70472752 lat 38.55595575 | file lon -0.70472752 lat 38.55595575
  (E 700064.0, N 4270064.0) -> lon -0.70397524 lat 38.55651765 | file lon -0.70397524 lat 38.55651765
  (E 700100.0, N 4270020.0) -> lon -0.70357501 lat 38.55611334 | file lon -0.70357501 lat 38.55611334
  (E 700020.0, N 4270100.0) -> lon -0.70446951 lat 38.55685173 | file lon -0.70446951 lat 38.55685173
  (E 700127.0, N 4270127.0) -> lon -0.70323470 lat 38.55707078 | file lon -0.7032347 lat 38.55707078
  (E 700033.3, N 4270077.7) -> lon -0.70432338 lat 38.55664793 | file lon -0.70432338 lat 38.55664793
  fixture affine residual re-measured: 5.352e-04 m (manifest maxResidualM 0.000536)
  Villena fit over 1000 x 1000 m (margin 0 m): max residual 0.0327 m
  Villena fit over 1240 x 1240 m (margin 120 m): max residual 0.0503 m
  Villena AOI corners in WGS84: lon -0.869027..-0.857279, lat 38.626433..38.635648
  DATA_SOURCES envelope: lon -0.869027..-0.857279, lat 38.626433..38.635648
  span comparison: dlon 0.011748 vs 0.011748 deg; dlat 0.009215 vs 0.009215 deg
  grid convergence at AOI centre: azimuth of grid north = 1.335 deg, of grid south = -178.666 deg (convergence ~1.335 deg from true north)

== F. Villena master image and tile budget ==
  L 1000 m, s 8, z in [-30.0, 90.0] m rel. H0 (relief 120 m): image 11314 x 6489 = 73.4 Mpx; ADR 0003 says ~11 300 x 6 500
  projected AOI ground diamond 11314 px wide, 5657 px tall, area 32.0 Mpx = 43.6 % of the image (rest is prism band)
  decoded buffer for the color rgba8 layer: 294 MB
  decoded buffer for the class index8 layer: 73 MB
  decoded buffer for the buildingId rgb24 layer: 220 MB
  decoded buffer for the depth gray16 layer: 147 MB
  tiles with T=512: maxLevel 14, base tiles 299, full pyramid 425; COSTS.md estimate (4/3)*ceil(w/T)*ceil(h/T) = 399

== G. occlusion behind an obstacle, phi = 30 deg ==
  obstacle  5 m above the ground in front: hidden ground length    8.7 m (0.009 km); hidden area for a 100 m wide hill 0.09 ha
  obstacle 10 m above the ground in front: hidden ground length   17.3 m (0.017 km); hidden area for a 100 m wide hill 0.17 ha
  obstacle 20 m above the ground in front: hidden ground length   34.6 m (0.035 km); hidden area for a 100 m wide hill 0.35 ha
  obstacle 30 m above the ground in front: hidden ground length   52.0 m (0.052 km); hidden area for a 100 m wide hill 0.52 ha
  obstacle 50 m above the ground in front: hidden ground length   86.6 m (0.087 km); hidden area for a 100 m wide hill 0.87 ha
  obstacle 80 m above the ground in front: hidden ground length  138.6 m (0.139 km); hidden area for a 100 m wide hill 1.39 ha
  DATA_SOURCES.md section 'Area of interest' states no hill height or relief figure for Villena
  castle (E 686188, N 4278098, z  0 m): image pixel 6166, 2644 of 11314 x 6489 (54 % from left, 41 % from top)
  castle (E 686188, N 4278098, z 30 m): image pixel 6166, 2436 of 11314 x 6489 (54 % from left, 38 % from top)
  castle (E 686188, N 4278098, z 60 m): image pixel 6166, 2228 of 11314 x 6489 (54 % from left, 34 % from top)

== H. what the AOI prism covers vs the scene margin ==
  SW corner of AOI   z  -30.0: X    5657.0 Y   6488.8 -> inside the image
  SW corner of AOI   z   90.0: X    5657.0 Y   5657.5 -> inside the image
  SE                 z  -30.0: X   11313.9 Y   3660.4 -> inside the image
  SE                 z   90.0: X   11313.9 Y   2829.0 -> inside the image
  NE                 z  -30.0: X    5657.0 Y    832.0 -> inside the image
  NE                 z   90.0: X    5657.0 Y      0.6 -> inside the image
  NW                 z  -30.0: X       0.1 Y   3660.4 -> inside the image
  NW                 z   90.0: X       0.1 Y   2829.0 -> inside the image
  NW margin corner   z  -30.0: X   -1357.5 Y   3660.4 -> OUTSIDE the image
  NW margin corner   z   90.0: X   -1357.5 Y   2829.0 -> OUTSIDE the image
  NE margin corner   z  -30.0: X    5657.0 Y    153.2 -> inside the image
  NE margin corner   z   90.0: X    5657.0 Y   -678.2 -> OUTSIDE the image
  top-left    image corner maps to local x   610.3 y  1610.3 m (AOI is 0..1000; margin 120 m)
  top-right   image corner maps to local x  1610.3 y   610.3 m (AOI is 0..1000; margin 120 m)
  bottom-left image corner maps to local x  -536.8 y   463.2 m (AOI is 0..1000; margin 120 m)
  max |u| of a margin corner vs the AOI prism: 7014 px vs 5657 px

== I. height grid quantisation and picking tolerance ==
  fixture grid 36x36 cell 4.0 m scale 0.01 offset 498.8; z span 34 m -> 3400 codes of 65535
  Villena relief 120 m needs 12000 codes of 65535 -> fits
  cell 0.5 m: worst-case bilinear undersampling of a 1-cell-wide ridge, pick error along the ray ~ 0.43 m
  cell 2.0 m: worst-case bilinear undersampling of a 1-cell-wide ridge, pick error along the ray ~ 1.73 m
  cell 4.0 m: worst-case bilinear undersampling of a 1-cell-wide ridge, pick error along the ray ~ 3.46 m
  1 cm quantisation -> 0.0173 m horizontal, well inside the 0.05 m tolerance

== J. cross-file consistency ==
  render.json image {'height': 481, 'width': 726} vs manifest {'height': 481, 'width': 726}
  render projection == manifest projection: True
  render zRange {'zMax': 31, 'zMin': -3} == manifest {'zMax': 31, 'zMin': -3} == scene: True
  scene aoi {'bounds': [700000.0, 4270000.0, 700128.0, 4270128.0], 'marginM': 8.0} origin {'E0': 700000.0, 'H0': 500.0, 'N0': 4270000.0}
  scene terrain covers 72x72 cells of 2.0 m from westE 699992.0 northN 4270136.0
  POI keep         forward gives X 363.000 Y 133.803 | file 363.0, 133.803
  POI church       forward gives X 521.392 Y 244.983 | file 521.392, 244.983
  POI garden       forward gives X 278.147 Y 234.887 | file 278.147, 234.887
  POI calle-mayor  forward gives X 363.000 Y 255.725 | file 363.0, 255.725
  POI sw-corner    forward gives X 363.000 Y 470.000 | file 363.0, 470.0

```

</details>

<details><summary>script B</summary>

```
== 1. the fixture's height grid covers local x -8.0..136.0, y -8.0..136.0 ==
   scene terrain covers x -8.0..136.0, y -8.0..136.0
   pixel (  0,  0): ray at z = zMax 31 starts at local x    64.0 y   192.4 -> OUTSIDE the height grid
   pixel (  0,480): ray at z = zMax 31 starts at local x  -105.7 y    22.7 -> OUTSIDE the height grid
   pixel (725,  0): ray at z = zMax 31 starts at local x   192.2 y    64.2 -> OUTSIDE the height grid
   pixel (725,480): ray at z = zMax 31 starts at local x    22.5 y  -105.5 -> OUTSIDE the height grid
   pixel (363,  0): ray at z = zMax 31 starts at local x   128.2 y   128.2 -> inside the height grid

== 2. share of image pixels whose ray passes through the scene footprint ==
   fixture 726x481, grid 36x36 cells of 4.0 m: 70.9 % reach the grid, 29.1 % never do (the four corner triangles)
   Villena 11314x6489, scene footprint 1240 x 1240 m: 74.6 % reach the scene, 25.4 % are void

== 3. PNG encoding determinism ==
   zlib level 1: sha256 b03afddb2157b00a (287 bytes) for the same 1024 bytes of pixels
   zlib level 6: sha256 2abdaf790332d933 (286 bytes) for the same 1024 bytes of pixels
   zlib level 9: sha256 eac2ef4ec31e737b (286 bytes) for the same 1024 bytes of pixels
   python zlib build: 1.2.12 (runtime 1.2.12); the PNG bytes depend on this, the pixels do not

== 4. JSON number formatting across implementations ==
   python json.dumps: [1.0,1e-07,0.30000000000000004,-0.0,1.2345678901234568e+17]
   node JSON.stringify: [1,1e-7,0.30000000000000004,0,123456789012345680]
   identical text: False

== 5. file pixel -> master pixel mapping (fixture, maxLevel 10) ==
   level 10 tile 2_0: level x0 511 width 215 -> master x0 511 to 726 (width 215)
   level 10 tile 1_1: level x0 255 width 258 -> master x0 255 to 513 (width 258)
   level 9 tile 1_0: level x0 255 width 108 -> master x0 510 to 726 (width 216)
   level 9 tile 0_0: level x0 0 width 257 -> master x0 0 to 514 (width 514)
   ratio-based mapping at level 13 for Villena height 6489: level rows 3245, ratio 1.999692 vs exact 2.0 -> drift up to 1 master px
```

</details>
