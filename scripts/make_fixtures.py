# /// script
# requires-python = ">=3.11"
# dependencies = ["pyproj>=3.6", "numpy>=1.26"]
# ///
"""Regenerate the synthetic contract fixtures. Run: `uv run scripts/make_fixtures.py`.

"Planeville" is a 128 m x 128 m town on a tilted plane z = 0.10*x + 0.05*y. Because the terrain
is a plane, every picking result has a closed-form answer that does not depend on any
implementation in this repository (see tiles-synthetic/expected.json).

Outputs (all committed, all deterministic):
  tests/fixtures/city-synthetic/     city.json, datasets.json
  tests/fixtures/scene-synthetic/    scene.json + terrain + layers   (renderer input)
  tests/fixtures/render-synthetic/   render.json + palette.json + color/class/buildingId layers (tile-export input;
                                     terrain only: buildings are not drawn)
  tests/fixtures/tiles-synthetic/    manifest.json, pois.json, height.u16, tiles, expected.json
                                     (viewer / export-validator input)
"""
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

E0, N0, H0 = 700000.0, 4270000.0, 500.0
SIZE, MARGIN = 128.0, 8.0
HEADING, PITCH, PPM = 45.0, 30.0, 4.0
C1, C2 = 0.10, 0.05  # terrain plane z = C1*x + C2*y
TILE, OVERLAP = 256, 1
BG = (0x1B, 0x26, 0x32)
VDATUM = "synthetic"

ca, sa = math.cos(math.radians(HEADING)), math.sin(math.radians(HEADING))
cp, sp = math.cos(math.radians(PITCH)), math.sin(math.radians(PITCH))
MATRIX = [[PPM * ca, -PPM * sa, 0.0], [-PPM * sa * sp, -PPM * ca * sp, -PPM * cp]]


def plane(x, y):
    return C1 * x + C2 * y


def uv(x, y, z):
    m = MATRIX
    return m[0][0] * x + m[0][1] * y + m[0][2] * z, m[1][0] * x + m[1][1] * y + m[1][2] * z


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png(path, w, h, rows, ctype=2, plte=None):
    """rows: h bytes objects. ctype 2 = RGB (3 bytes/px), 6 = RGBA (4), 3 = palette index (1, needs plte)."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    raw = b"".join(b"\x00" + r for r in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
                     + (chunk(b"PLTE", plte) if plte else b"") + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- scene
SCENE = ROOT / "scene-synthetic"
crs = {"world": "EPSG:25830", "geographic": "EPSG:4326", "verticalDatum": VDATUM}
aoi = {"bounds": [E0, N0, E0 + SIZE, N0 + SIZE], "marginM": MARGIN}
origin = {"E0": E0, "N0": N0, "H0": H0}


def rect(x0, y0, x1, y1):  # counter-clockwise, world coords
    return [[[E0 + x, N0 + y] for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))]]


def fc(features):
    return {"type": "FeatureCollection", "features": sorted(features, key=lambda f: f["properties"]["id"])}


def feat(geom_type, coords, **props):
    return {"type": "Feature", "geometry": {"type": geom_type, "coordinates": coords}, "properties": props}


def bld(i, x0, y0, x1, y1, h, use="residential", src="floors", floors=None, roof="unknown", landmark=None, bid=None):
    base = min(plane(x, y) for x in (x0, x1) for y in (y0, y1)) + H0
    return feat("Polygon", rect(x0, y0, x1, y1), id=f"syn-{i:03d}_1", buildingId=bid or f"syn-{i:03d}",
                baseH=round(base, 2), heightM=h, heightSource=src, floors=floors, roof=roof,
                roofSource="none" if roof == "unknown" else "tag", use=use, landmark=landmark)


buildings = [
    bld(1, 16, 16, 28, 28, 6.0, floors=2),
    bld(2, 32, 16, 40, 30, 9.0, floors=3, roof="pitched"),
    bld(3, 16, 76, 40, 88, 6.0, floors=2, roof="flat"),
    bld(4, 80, 80, 96, 96, 12.0, use="fortification", src="surface-model", landmark="keep"),
    bld(5, 96, 84, 104, 92, 5.0, use="fortification", src="default", bid="syn-004"),
    bld(6, 72, 20, 100, 40, 7.5, use="religious", src="surface-model", roof="pitched", landmark="church"),
]
roads = [
    feat("LineString", [[E0 - MARGIN, N0 + 64], [E0 + SIZE + MARGIN, N0 + 64]], id="syn-road-1",
         **{"class": "residential"}, widthM=8.0, widthSource="class-default", name="Calle Mayor", layer=0),
    feat("LineString", [[E0 + 56, N0 + 64], [E0 + 56, N0 + 110], [E0 + 80, N0 + 120]], id="syn-road-2",
         **{"class": "pedestrian"}, widthM=3.0, widthSource="tag", name="Subida al Castillo", layer=0),
]
landcover = [
    feat("Polygon", rect(44, 72, 68, 100), id="syn-lc-1", **{"class": "park"}, name="Jardín"),
    feat("Polygon", rect(104, 100, 136, 136), id="syn-lc-2", **{"class": "bare-rock"}, name=None),
]
trees = [feat("Point", [E0 + x, N0 + y], id=f"syn-tree-{i}", heightM=6.0, crownRadiusM=2.5, source="mapped")
         for i, (x, y) in enumerate([(48, 76), (56, 84), (64, 96)], 1)]

cell = 2.0
n = int((SIZE + 2 * MARGIN) / cell)
terrain = struct.pack(f"<{n * n}f", *[H0 + plane(-MARGIN + (c + 0.5) * cell, SIZE + MARGIN - (r + 0.5) * cell)
                                       for r in range(n) for c in range(n)])
SCENE.mkdir(parents=True, exist_ok=True)
(SCENE / "terrain.f32").write_bytes(terrain)

to_geo = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)


def poi(pid, name, kind, x, y, above=0.0, ref="", bounds_xy=None, alt=None):
    lon, lat = to_geo.transform(E0 + x, N0 + y)
    p = {"id": pid, "name": name, "kind": kind, "lat": round(lat, 7), "lon": round(lon, 7), "E": E0 + x, "N": N0 + y,
         "H": round(H0 + plane(x, y) + above, 3), "source": {"dataset": "synthetic", "ref": ref}}
    if alt:
        p["altNames"] = alt
    if bounds_xy:
        p["worldBounds"] = [E0 + bounds_xy[0], N0 + bounds_xy[1], E0 + bounds_xy[2], N0 + bounds_xy[3]]
    return p, bounds_xy


poi_defs = [
    poi("keep", "Torre del Homenaje", "landmark", 88, 88, above=12.0, ref="syn-004", alt=["Castillo"]),
    poi("church", "Iglesia de San Sintético", "church", 86, 30, above=7.5, ref="syn-006"),
    poi("garden", "Jardín", "park", 56, 86, ref="syn-lc-1"),
    poi("calle-mayor", "Calle Mayor", "street", 64, 64, ref="syn-road-1", bounds_xy=(0, 60, 128, 68)),
    poi("sw-corner", "Esquina suroeste", "other", 0, 0, ref="aoi"),
]
dump(SCENE / "pois.json", {"schemaVersion": "1.0", "cityId": "planeville", "pois": sorted((p for p, _ in poi_defs), key=lambda p: p["id"])})

layers = {"buildings": buildings, "roads": roads, "landcover": landcover, "trees": trees}
for name, feats in layers.items():
    dump(SCENE / f"{name}.geojson", fc(feats))

z_lo = min(plane(x, y) for x in (-MARGIN, SIZE + MARGIN) for y in (-MARGIN, SIZE + MARGIN))
z_hi = max(max(plane(x, y) for x in (-MARGIN, SIZE + MARGIN) for y in (-MARGIN, SIZE + MARGIN)),
           max(b["properties"]["baseH"] - H0 + b["properties"]["heightM"] + 6 for b in buildings))
zrange = {"zMin": math.floor(z_lo - 1), "zMax": math.ceil(z_hi + 1)}

dump(SCENE / "scene.json", {
    "schemaVersion": "1.0", "cityId": "planeville", "crs": crs, "aoi": aoi, "origin": origin, "zRange": zrange,
    "terrain": {"path": "terrain.f32", "width": n, "height": n, "cellSize": cell, "westE": E0 - MARGIN,
                "northN": N0 + SIZE + MARGIN, "dtype": "float32-le", "unit": "m", "sha256": sha(SCENE / "terrain.f32")},
    "layers": {k: {"path": f"{k}.geojson", "count": len(v), "sha256": sha(SCENE / f"{k}.geojson")} for k, v in layers.items()},
    "pois": {"path": "pois.json", "count": len(poi_defs), "sha256": sha(SCENE / "pois.json")},
    "provenance": [],
})

# ---------------------------------------------------------------- city config
attribution = [{"text": "Synthetic fixture data — not a real place"}]
dump(ROOT / "city-synthetic" / "city.json", {
    "schemaVersion": "1.0", "id": "planeville", "name": "Planeville (synthetic)", "crs": crs, "aoi": aoi, "origin": origin,
    "camera": {"headingDeg": HEADING, "pitchDeg": PITCH, "pixelsPerMetre": PPM},
    "tiles": {"tileSize": TILE, "tileOverlap": OVERLAP, "format": "png"},
    "datasets": "datasets.json", "attribution": attribution,
})
dump(ROOT / "city-synthetic" / "datasets.json", {"schemaVersion": "1.0", "cityId": "planeville", "datasets": [{
    "id": "synthetic", "provider": "this repository", "name": "Planeville", "version": "1", "acquisitionDate": "n/a",
    "coverage": "AOI", "url": "https://example.invalid/", "access": "direct", "resolution": "exact", "crs": "EPSG:25830",
    "license": {"name": "CC0-1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/", "attribution": "none required"},
    "redistribution": {"raw": True, "derivatives": True}, "sizeBytes": None, "sha256": None,
    "localPath": "scene-synthetic", "retrievedAt": None}]})

# ---------------------------------------------------------------- master image
corners = [uv(x, y, z) for x in (0, SIZE) for y in (0, SIZE) for z in (zrange["zMin"], zrange["zMax"])]
u0, v0 = math.floor(min(c[0] for c in corners)), math.floor(min(c[1] for c in corners))
W, H = math.ceil(max(c[0] for c in corners)) - u0, math.ceil(max(c[1] for c in corners)) - v0
tx, ty = -u0, -v0
k1, k2 = C1 * ca - C2 * sa, C1 * sa + C2 * ca


def pick_plane(X, Y):
    """Closed-form intersection of the pixel ray with the terrain plane -> local (x, y)."""
    a, q = (X - tx) / PPM, -(Y - ty) / PPM
    b = (q - a * k1 * cp) / (sp + k2 * cp)
    return a * ca + b * sa, -a * sa + b * ca


def ground_colour(x, y):
    if not (0 <= x < SIZE and 0 <= y < SIZE):
        return BG
    if 60 <= y < 68:
        return (0x8A, 0x8F, 0x98)  # the road
    return (0x6F, 0xA8, 0x5C) if (int(x // 8) + int(y // 8)) % 2 == 0 else (0x5C, 0x93, 0x4E)


img = [[ground_colour(*pick_plane(i + 0.5, j + 0.5)) for i in range(W)] for j in range(H)]

pois = []
for p, bxy in poi_defs:
    X, Y = uv(p["E"] - E0, p["N"] - N0, p["H"] - H0)
    p = dict(p, X=round(X + tx, 3), Y=round(Y + ty, 3))
    p.pop("worldBounds", None)
    if bxy:
        cs = [uv(x, y, p["H"] - H0) for x in (bxy[0], bxy[2]) for y in (bxy[1], bxy[3])]
        p["imageBounds"] = [round(min(c[0] for c in cs) + tx, 3), round(min(c[1] for c in cs) + ty, 3),
                            round(max(c[0] for c in cs) + tx, 3), round(max(c[1] for c in cs) + ty, 3)]
    pois.append(p)
    for d in range(-4, 5):  # red cross centred on the POI anchor so marker alignment is visible
        for i, j in ((int(p["X"]) + d, int(p["Y"])), (int(p["X"]), int(p["Y"]) + d)):
            if 0 <= i < W and 0 <= j < H:
                img[j][i] = (0xD9, 0x3A, 0x3A)  # = MARK in the fixture palette

# ---------------------------------------------------------------- render output (tile-export input)
RENDER = ROOT / "render-synthetic"
projection = {"headingDeg": HEADING, "pitchDeg": PITCH, "pixelsPerMetre": PPM, "origin": origin,
              "matrix": MATRIX, "translation": [tx, ty]}
ROAD = (0x8A, 0x8F, 0x98)
MARK = (0xD9, 0x3A, 0x3A)
dump(RENDER / "palette.json", {"schemaVersion": "1.0", "name": "planeville-fixture", "version": "1", "colors": [
    {"hex": "#%02x%02x%02x" % c, "role": r} for c, r in (((0x6F, 0xA8, 0x5C), "ground-light"),
                                                        ((0x5C, 0x93, 0x4E), "ground-dark"), (ROAD, "road"),
                                                        (MARK, "poi-anchor-mark"))]})
render_layers = [  # name, file, encoding, PNG colour type, decoded rows (the bytes pixelSha256 is computed over)
    ("color", "color.png", "rgba8-png", 6,
     [bytes(c for px in row for c in ((*px, 255) if px != BG else (0, 0, 0, 0))) for row in img]),
    ("class", "class.png", "index8-png", 3, [bytes(0 if px == BG else 2 if px == ROAD else 1 for px in row) for row in img]),
    ("buildingId", "buildingId.png", "rgb24-id-png", 2, [bytes(3 * W)] * H),
]
CLASS_PLTE = bytes([0, 0, 0, 90, 160, 80, 140, 140, 150, 200, 180, 150, 180, 80, 60, 40, 110, 50, 60, 120, 200, 230, 200, 60])
layer_entries = []
for name, fname, encoding, ctype, rows in render_layers:
    png(RENDER / fname, W, H, rows, ctype=ctype, plte=CLASS_PLTE if ctype == 3 else None)
    entry = {"name": name, "path": fname, "encoding": encoding, "sha256": sha(RENDER / fname),
             "pixelSha256": hashlib.sha256(b"".join(rows)).hexdigest()}
    if name == "buildingId":
        entry["index"] = "buildingId.json"
    layer_entries.append(entry)
dump(RENDER / "buildingId.json", [None])
dump(RENDER / "render.json", {
    "schemaVersion": "1.0", "cityId": "planeville", "image": {"width": W, "height": H}, "projection": projection,
    "zRange": zrange, "background": "#%02x%02x%02x" % BG, "sceneSha256": sha(SCENE / "scene.json"),
    "renderer": {"name": "make_fixtures", "version": "1"},
    "palette": {"path": "palette.json", "sha256": sha(RENDER / "palette.json")},
    "layers": layer_entries,
})

# ---------------------------------------------------------------- pyramid
TILES = ROOT / "tiles-synthetic"
max_level = math.ceil(math.log2(max(W, H)))
level_img, lw, lh = img, W, H
for level in range(max_level, -1, -1):
    for row in range(math.ceil(lh / TILE)):
        for col in range(math.ceil(lw / TILE)):
            x0, y0 = max(col * TILE - OVERLAP, 0), max(row * TILE - OVERLAP, 0)
            x1, y1 = min((col + 1) * TILE + OVERLAP, lw), min((row + 1) * TILE + OVERLAP, lh)
            png(TILES / "procedural" / str(level) / f"{col}_{row}.png", x1 - x0, y1 - y0,
                [bytes(c for px in level_img[j][x0:x1] for c in px) for j in range(y0, y1)])
    nw, nh = math.ceil(lw / 2), math.ceil(lh / 2)  # 2x box filter, edges replicated
    level_img = [[tuple((sum(level_img[min(2 * j + dj, lh - 1)][min(2 * i + di, lw - 1)][c]
                             for dj in (0, 1) for di in (0, 1)) + 2) // 4 for c in range(3))
                  for i in range(nw)] for j in range(nh)]
    lw, lh = nw, nh

# ---------------------------------------------------------------- published metadata
gcell = 4.0
gn = int((SIZE + 2 * MARGIN) / gcell)
(TILES / "height.u16").write_bytes(struct.pack(f"<{gn * gn}H", *[
    round((plane(-MARGIN + (c + 0.5) * gcell, SIZE + MARGIN - (r + 0.5) * gcell) - z_lo) / 0.01)
    for r in range(gn) for c in range(gn)]))

from_geo = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
fit_pts = [(E0 + SIZE * i / 4, N0 + SIZE * j / 4) for i in range(5) for j in range(5)]
ll = np.array([to_geo.transform(e, n_) for e, n_ in fit_pts])
lon0, lat0 = ll.mean(axis=0)  # centre the unknowns so the fit is well conditioned
A = np.column_stack([ll[:, 0] - lon0, ll[:, 1] - lat0, np.ones(len(ll))])
coef, *_ = np.linalg.lstsq(A, np.array(fit_pts), rcond=None)  # 3x2
geo_matrix = [[coef[0][k], coef[1][k], coef[2][k] - coef[0][k] * lon0 - coef[1][k] * lat0] for k in (0, 1)]
check = [(e, n_, *to_geo.transform(e, n_)) for e in np.linspace(E0, E0 + SIZE, 9) for n_ in np.linspace(N0, N0 + SIZE, 9)]
residual = max(math.hypot(m[0][0] * lo + m[0][1] * la + m[0][2] - e, m[1][0] * lo + m[1][1] * la + m[1][2] - n_)
               for e, n_, lo, la in check for m in [geo_matrix])

dump(TILES / "pois.json", {"schemaVersion": "1.0", "cityId": "planeville", "pois": sorted(pois, key=lambda p: p["id"])})
dump(TILES / "manifest.json", {
    "schemaVersion": "1.0", "cityId": "planeville", "name": "Planeville (synthetic)", "release": "fixture-1",
    "image": {"width": W, "height": H},
    "tiles": {"layout": "dzi", "tileSize": TILE, "tileOverlap": OVERLAP, "minLevel": 0, "maxLevel": max_level},
    "styles": [{"id": "procedural", "label": "Procedural", "tilesBase": "procedural", "format": "png"}],
    "projection": projection, "zRange": zrange,
    "geoToWorld": {"matrix": geo_matrix, "maxResidualM": round(residual + 5e-7, 6)},
    "heightGrid": {"path": "height.u16", "width": gn, "height": gn, "cellSize": gcell, "westE": E0 - MARGIN,
                   "northN": N0 + SIZE + MARGIN, "dtype": "uint16-le", "scale": 0.01, "offset": H0 + z_lo},
    "background": "#%02x%02x%02x" % BG, "pois": "pois.json", "attribution": attribution,
    "crs": crs, "renderSha256": sha(RENDER / "render.json"),
})

# Expected values that do not come from any implementation under test.
cases = []
for x, y in [(0, 0), (64, 64), (100, 20), (20, 100), (127, 127), (33.3, 77.7)]:
    z = plane(x, y)
    X, Y = uv(x, y, z)
    lon, lat = to_geo.transform(E0 + x, N0 + y)
    cases.append({"E": E0 + x, "N": N0 + y, "H": round(H0 + z, 6), "X": round(X + tx, 6), "Y": round(Y + ty, 6),
                  "lon": round(lon, 8), "lat": round(lat, 8)})
dump(TILES / "expected.json", {
    "description": "Ground points on the analytic terrain plane z = 0.10*x + 0.05*y (local metres). "
                   "forward(E,N,H) must give X,Y within 1e-3 px; terrainPick(X,Y) must give E,N within 0.05 m "
                   "(a property of this planar terrain: only the 0.01 m height quantisation matters; on real terrain the pick is "
                   "accurate to about cellSize/(2 tan pitch), see projection.md 5.2); lon/lat come from PROJ and the geoToWorld affine "
                   "must match them within manifest.geoToWorld.maxResidualM.",
    "groundPoints": cases,
    "referencePlane": {"description": "Reference-plane inverse (zr = 0) of pixel (X, Y), closed form.",
                       "cases": [{"X": X, "Y": Y, "E": round(E0 + a * ca + b * sa, 6), "N": round(N0 - a * sa + b * ca, 6)}
                                 for X, Y in [(0, 0), (W / 2, H / 2), (W, H)]
                                 for a, b in [((X - tx) / PPM, -(Y - ty) / PPM / sp)]]},
})
n_tiles = len(list((TILES / "procedural").rglob("*.png")))
total = sum(f.stat().st_size for f in ROOT.rglob("*") if f.is_file())
print(f"master image {W}x{H}, maxLevel {max_level}, {n_tiles} tiles, geo fit residual {residual:.2e} m, fixtures {total / 1024:.0f} KiB")
