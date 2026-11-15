"""WP08 7.1: renderer -> exporter -> validator on the synthetic city, against ground truth that comes from the
fixtures (expected.json, buildings.geojson, city.json) and the closed-form projection in helpers.py."""

import json
import math

import helpers as H
import numpy as np
import pytest
from PIL import Image

FIXTURE_MANIFEST = H.jload(H.TILES_FIX / "manifest.json")
EXPECTED = H.jload(H.TILES_FIX / "expected.json")
SCENE_MANIFEST = H.jload(H.SCENE / "scene.json")
BUILDINGS = H.jload(H.SCENE / "buildings.geojson")["features"]
BACKGROUND_CLASS, GROUND, ROAD, WALL, ROOF = 0, 1, 2, 3, 4


def close(a, b, tol=1e-9):
    """Parsed JSON compared with a tolerance (scene.md: never as text)."""
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b, strict=True))
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) <= tol
    return a == b


def roof_centre(feature):
    """(x, y, z) local metres of the wall top above the footprint's bounding-box centre."""
    q, ring = feature["properties"], feature["geometry"]["coordinates"][0]
    xs, ys = [c[0] - H.E0 for c in ring], [c[1] - H.N0 for c in ring]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, q["baseH"] - H.H0 + q["heightM"], xs, ys


def test_image_size_levels_and_tile_count(run_a):
    w, h, translation = H.prism_size(H.CAM, SCENE_MANIFEST["aoi"]["bounds"], SCENE_MANIFEST["zRange"]["zMin"],
                                     SCENE_MANIFEST["zRange"]["zMax"])
    assert (w, h, translation) == (726, 481, (363, 470))
    render = H.jload(run_a.render / "render.json")
    m = H.jload(run_a.tiles / "manifest.json")
    assert render["image"] == m["image"] == {"width": 726, "height": 481}
    assert m["tiles"]["maxLevel"] == 10 == math.ceil(math.log2(726))
    assert (m["tiles"]["tileSize"], m["tiles"]["tileOverlap"], m["tiles"]["minLevel"]) == (256, 1, 0)

    want = H.tile_list(726, 481)
    assert len(want) == 17
    got = {}
    for f in sorted((run_a.tiles / "procedural").rglob("*.png")):
        col, row = map(int, f.stem.split("_"))
        with Image.open(f) as im:
            got[(int(f.parent.name), col, row)] = im.size
    assert got == want
    files = {p.relative_to(run_a.tiles).as_posix() for p in run_a.tiles.rglob("*") if p.is_file()}
    assert len(files) == 17 + 3  # tiles + manifest.json, pois.json, height.u16


def test_projection_is_the_fixtures(run_a):
    for doc in (H.jload(run_a.render / "render.json"), H.jload(run_a.tiles / "manifest.json")):
        assert close(doc["projection"], FIXTURE_MANIFEST["projection"], 1e-9), doc["projection"]
    city = H.jload(H.CITY)["camera"]
    assert (city["headingDeg"], city["pitchDeg"], city["pixelsPerMetre"]) == (H.CAM.heading, H.CAM.pitch, H.CAM.ppm)
    m = H.jload(run_a.tiles / "manifest.json")["projection"]
    for i in range(2):
        for j in range(3):
            assert m["matrix"][i][j] == pytest.approx(H.matrix()[i][j], abs=1e-9)


def test_ground_points_forward_projection(run_a):
    m = H.jload(run_a.tiles / "manifest.json")
    for p in EXPECTED["groundPoints"]:
        x, y, z = p["E"] - H.E0, p["N"] - H.N0, p["H"] - H.H0
        assert z == pytest.approx(H.plane(x, y), abs=1e-9)  # the points really are on the terrain plane
        X, Y = H.fwd(x, y, z, m["projection"]["translation"])
        assert abs(X - p["X"]) <= 1e-3 and abs(Y - p["Y"]) <= 1e-3, p


def test_semantics_road_roof_and_outside(run_a):
    cls, ids, color = (H.layer(run_a.render, n) for n in ("class", "buildingId", "color"))
    index = H.jload(run_a.render / "buildingId.json")
    assert index[0] is None

    # Calle Mayor centre line at local (100, 64) is on the plane
    X, Y = H.fwd(100, 64, H.plane(100, 64))
    assert cls[int(Y), int(X)] == ROAD
    assert H.building_id(ids, X, Y) == 0

    # the roof of each building (wall top above the footprint centre) resolves to that building ...
    part_to_building = {f["properties"]["id"]: f["properties"]["buildingId"] for f in BUILDINGS}
    # ... except the annex syn-005_1: its roof centre (100, 88, 18.8) lies behind the 24 m keep (the ray towards the
    # camera is at (96, 84, 22.0) when it crosses the keep's east wall, below its roof), so the pixel is the keep's.
    hidden_by = {"syn-005_1": "syn-004_1"}
    for f in BUILDINGS:
        q = f["properties"]
        cx, cy, cz, xs, ys = roof_centre(f)
        for X, Y, expect in ((*H.fwd(cx, cy, cz), hidden_by.get(q["id"], q["id"])),
                             # the north-east corner region is the farthest from the camera: never hidden
                             (*H.fwd(max(xs) - 1, max(ys) - 1, cz), q["id"])):
            idx = H.building_id(ids, X, Y)
            assert idx > 0, q["id"]
            assert index[idx] == expect, q["id"]
            assert cls[int(Y), int(X)] in (WALL, ROOF), q["id"]
        assert part_to_building[index[idx]] in {q["buildingId"], part_to_building[expect]}

    # two parts, one building: syn-004 = the keep + the annex syn-005_1 (R-20: the fixture has one such case)
    assert part_to_building["syn-005_1"] == part_to_building["syn-004_1"] == "syn-004"

    # 2 m south-west of the AOI corner, on the plane, nothing is drawn
    X, Y = H.fwd(-2, -2, H.plane(-2, -2))
    assert 0 <= X < 726 and 0 <= Y < 481
    assert color[int(Y), int(X), 3] == 0 and cls[int(Y), int(X)] == BACKGROUND_CLASS


def test_the_keep_hides_the_ground_behind_it(run_a):
    """Walk from the keep's roof centre along the viewing direction until the plane: that ground point projects onto
    the very same pixel, which therefore shows the keep (a 12 m flat-roofed block), not the ground."""
    keep_f = next(f for f in BUILDINGS if f["properties"]["landmark"] == "keep")
    keep = keep_f["properties"]
    assert keep["heightM"] == 12.0
    cx, cy, cz, _, _ = roof_centre(keep_f)
    a, f = math.radians(H.CAM.heading), math.radians(H.CAM.pitch)
    w = (math.sin(a) * math.cos(f), math.cos(a) * math.cos(f), -math.sin(f))  # projection.md section 2, into the scene
    # cz + t*wz = plane(cx + t*wx, cy + t*wy)  ->  linear in t
    t = (cz - H.plane(cx, cy)) / (H.plane(w[0], w[1]) - w[2])
    gx, gy = cx + t * w[0], cy + t * w[1]
    gz = H.plane(gx, gy)
    assert t > 0 and gz == pytest.approx(cz + t * w[2], abs=1e-9)
    assert 0 < gx < 128 and 0 < gy < 128  # behind the keep, still inside the AOI

    X, Y = H.fwd(gx, gy, gz)
    X0, Y0 = H.fwd(cx, cy, cz)
    assert abs(X - X0) < 1e-9 and abs(Y - Y0) < 1e-9  # same pixel: it is occluded
    cls, ids = H.layer(run_a.render, "class"), H.layer(run_a.render, "buildingId")
    index = H.jload(run_a.render / "buildingId.json")
    assert cls[int(Y), int(X)] in (WALL, ROOF)
    assert index[H.building_id(ids, X, Y)] == keep["id"]


def test_published_pois_match_the_fixture(run_a):
    got = H.jload(run_a.tiles / "pois.json")["pois"]
    want = H.jload(H.TILES_FIX / "pois.json")["pois"]
    assert [p["id"] for p in got] == [p["id"] for p in want] == sorted(p["id"] for p in want)
    for g, w in zip(got, want, strict=True):
        assert abs(g["X"] - w["X"]) <= 1e-3 and abs(g["Y"] - w["Y"]) <= 1e-3, g["id"]
        X, Y = H.fwd(g["E"] - H.E0, g["N"] - H.N0, g["H"] - H.H0)  # and against the closed form
        assert abs(g["X"] - X) <= 1e-3 and abs(g["Y"] - Y) <= 1e-3, g["id"]


def test_exported_tiles_assemble_to_the_render(run_a):
    """Level maxLevel tiles, with their overlap removed, rebuild the flattened colour layer exactly."""
    color = H.layer(run_a.render, "color")
    bg = H.jload(run_a.render / "render.json")["background"]
    bg = tuple(int(bg[i:i + 2], 16) for i in (1, 3, 5))
    flat = np.where(color[..., 3:4] == 255, color[..., :3], np.array(bg, dtype=np.uint8))
    out = np.zeros_like(flat)
    for (lv, col, row), _ in H.tile_list(726, 481).items():
        if lv != 10:
            continue
        with Image.open(run_a.tiles / "procedural" / "10" / f"{col}_{row}.png") as im:
            tile = np.asarray(im.convert("RGB"))
        ox, oy = (1 if col else 0), (1 if row else 0)
        nw, nh = min(256, 726 - col * 256), min(256, 481 - row * 256)
        out[row * 256:row * 256 + nh, col * 256:col * 256 + nw] = tile[oy:oy + nh, ox:ox + nw]
    assert np.array_equal(out, flat)


def test_depth_layer_agrees_with_the_geometry(tmp_path):
    """--depth: decode d (render.md section 1) at the keep's roof centre pixel and apply the surface pick (projection.md
    5.3); the resulting point must lie on the roof plane. The exporter must accept a render that has a depth layer."""
    r, t = tmp_path / "render", tmp_path / "tiles"
    H.ok(H.render(H.SCENE, r, "--depth"))
    layers = {entry["name"]: entry for entry in H.jload(r / "render.json")["layers"]}
    assert layers["depth"]["encoding"] == "gray16-png"
    H.ok(H.export(r, H.SCENE, t))
    H.ok(H.validate(t, "--render", r))

    with Image.open(r / "depth.png") as im:
        depth = np.asarray(im)
    assert depth.dtype == np.uint16
    keep = next(f for f in BUILDINGS if f["properties"]["landmark"] == "keep")
    cx, cy, cz, xs, ys = roof_centre(keep)
    X, Y = H.fwd(cx, cy, cz)
    px, py = int(X), int(Y)
    d = layers["depth"]["offset"] + layers["depth"]["scale"] * int(depth[py, px])
    s, a, f = H.CAM.ppm, math.radians(H.CAM.heading), math.radians(H.CAM.pitch)
    u, v = px + 0.5 - 363, py + 0.5 - 470  # pixel centre, image offset removed
    r_ = (math.cos(a), -math.sin(a), 0)
    p_ = (math.sin(a) * math.sin(f), math.cos(a) * math.sin(f), math.cos(f))
    w_ = (math.sin(a) * math.cos(f), math.cos(a) * math.cos(f), -math.sin(f))
    P = [(u / s) * r_[i] + (-v / s) * p_[i] + d * w_[i] for i in range(3)]
    assert P[2] == pytest.approx(cz, abs=0.01)  # on the flat roof plane
    assert min(xs) <= P[0] <= max(xs) and min(ys) <= P[1] <= max(ys)


def test_manifest_json_is_sorted_and_free_of_timestamps(run_a):
    for name in ("manifest.json", "pois.json"):
        text = (run_a.tiles / name).read_text()
        assert text == json.dumps(json.loads(text), indent=1, sort_keys=True, ensure_ascii=False) + "\n", name
