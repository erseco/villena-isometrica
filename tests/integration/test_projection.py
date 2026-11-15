"""WP08 7.4 and 7.6: the same cases through every implementation of the projection (renderer TS, viewer TS, exporter
Python, GIS Python), compared with independent closed-form values and with the fixtures; plus seeded property tests.
The TS implementations are evaluated by tests/integration/ts/dump.ts, which holds no expected values."""

import json
import math
import random
import subprocess

import helpers as H
import pytest
from export import build as export_build
from export import validate as export_validate
from geospatial import build_scene

VECTORS = H.jload(H.ROOT / "packages" / "geo-contracts" / "fixtures" / "projection-vectors.json")
EXPECTED = H.jload(H.TILES_FIX / "expected.json")
FIXTURE = H.jload(H.TILES_FIX / "manifest.json")
SCENE = H.jload(H.SCENE / "scene.json")
ZMIN, ZMAX = SCENE["zRange"]["zMin"], SCENE["zRange"]["zMax"]
ORIGIN = {"E0": 0.0, "N0": 0.0, "H0": 0.0}


def ts(tmp_path, payload: dict) -> dict:
    f = tmp_path / "in.json"
    f.write_text(json.dumps(payload))
    p = subprocess.run(["bun", str(H.ROOT / "tests" / "integration" / "ts" / "dump.ts"), str(f)], capture_output=True,
                       text=True, cwd=H.ROOT)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def cam_of(c) -> H.SimpleNamespace:
    return H.SimpleNamespace(heading=c["headingDeg"], pitch=c["pitchDeg"], ppm=c["pixelsPerMetre"])


def closed_form(cam, x, y, z):
    """u, v, d of projection.md section 3, written out term by term (not via helpers.matrix)."""
    a, f, s = math.radians(cam.heading), math.radians(cam.pitch), cam.ppm
    return (s * (x * math.cos(a) - y * math.sin(a)),
            -s * ((x * math.sin(a) + y * math.cos(a)) * math.sin(f) + z * math.cos(f)),
            (x * math.sin(a) + y * math.cos(a)) * math.cos(f) - z * math.sin(f))


# ---- 7.4 conformance table --------------------------------------------------------------------------------------

def test_vectors_through_every_implementation(tmp_path):
    cams = VECTORS["cameras"]
    out = ts(tmp_path, {
        "viewer": [{"matrix": H.matrix(cam_of(c)), "translation": [0, 0], "origin": ORIGIN,
                    "forward": [p["xyz"] for p in c["points"]]} for c in cams],
        "renderer": [{"camera": {k: c[k] for k in ("headingDeg", "pitchDeg", "pixelsPerMetre")}, "aoi": [1, 1],
                      "z": [0, 1], "forward": [p["xyz"] for p in c["points"]]} for c in cams],
    })
    n = 0
    for i, c in enumerate(cams):
        proj = {"matrix": H.matrix(cam_of(c)), "translation": [0, 0], "origin": ORIGIN}
        for j, p in enumerate(c["points"]):
            u, v, d = p["u"], p["v"], p["d"]
            # the vector file itself against the formula
            for got, want in zip(closed_form(cam_of(c), *p["xyz"]), (u, v, d), strict=True):
                assert got == pytest.approx(want, abs=1e-6)
            # viewer (matrix only: it has no camera -> matrix step), renderer (full: camera in, matrix out), exporter
            assert out["viewer"][i]["forward"][j] == pytest.approx([u, v], abs=1e-6), (c["name"], p["xyz"])
            assert out["renderer"][i]["uvd"][j][:2] == pytest.approx([u, v], abs=1e-6), (c["name"], p["xyz"])
            assert out["renderer"][i]["uvd"][j][2] == pytest.approx(d, abs=1e-6), (c["name"], p["xyz"])
            assert export_build.forward(proj, *p["xyz"]) == pytest.approx((u, v), abs=1e-6)
            n += 1
    assert n >= 20


def test_camera_to_matrix_agrees_across_implementations(tmp_path):
    """Renderer (own Taylor sin/cos) and exporter validator (math.sin/cos) against the closed form, 1e-9."""
    cams = VECTORS["cameras"] + [{"headingDeg": 45, "pitchDeg": 30, "pixelsPerMetre": 4},
                                 {"headingDeg": -30, "pitchDeg": 62.5, "pixelsPerMetre": 3}]
    out = ts(tmp_path, {"renderer": [{"camera": {k: c[k] for k in ("headingDeg", "pitchDeg", "pixelsPerMetre")},
                                      "aoi": [128, 128], "z": [-3, 31]} for c in cams]})
    for c, r in zip(cams, out["renderer"], strict=True):
        want = H.matrix(cam_of(c))
        assert sum(r["matrix"], []) == pytest.approx(sum(want, []), abs=1e-9), c
        proj = {k: c[k] for k in ("headingDeg", "pitchDeg", "pixelsPerMetre")} | {"matrix": want}
        assert export_validate.camera_errors(proj, H.Path("x")) == []
        proj["matrix"] = [[want[0][0] + 1e-6, *want[0][1:]], want[1]]
        assert export_validate.camera_errors(proj, H.Path("x"))  # and it does notice a perturbed matrix


def test_image_size_and_translation_agree_across_implementations(tmp_path):
    """Renderer (TS) and GIS image_size (Python) against the prism formula, on the fixture and on random cities."""
    rnd = random.Random(8)
    cases = [(H.CAM, SCENE["aoi"]["bounds"], ZMIN, ZMAX, (726, 481))]
    for _ in range(40):
        cam = H.SimpleNamespace(heading=rnd.uniform(0, 360), pitch=rnd.uniform(10, 80), ppm=rnd.choice([1, 2, 4, 8]))
        e0, n0 = rnd.uniform(6e5, 7e5), rnd.uniform(4.2e6, 4.3e6)
        b = [e0, n0, e0 + rnd.uniform(50, 1200), n0 + rnd.uniform(50, 1200)]
        zmin = rnd.uniform(-5, 600)
        cases.append((cam, b, zmin, zmin + rnd.uniform(10, 120), None))
    out = ts(tmp_path, {"renderer": [{"camera": {"headingDeg": c.heading, "pitchDeg": c.pitch,
                                                 "pixelsPerMetre": c.ppm},
                                      "aoi": [b[2] - b[0], b[3] - b[1]], "z": [zmin, zmax]}
                                     for c, b, zmin, zmax, _ in cases]})
    for (cam, b, zmin, zmax, known), r in zip(cases, out["renderer"], strict=True):
        w, h, tr = H.prism_size(cam, b, zmin, zmax)
        gis = build_scene.image_size({"camera": {"headingDeg": cam.heading, "pitchDeg": cam.pitch,
                                                 "pixelsPerMetre": cam.ppm}, "aoi": {"bounds": b}},
                                     {"zMin": zmin, "zMax": zmax})
        # an exact integer boundary may legitimately round either way for random floats: allow 1 px there
        assert abs(r["width"] - w) <= 1 and abs(r["height"] - h) <= 1, (cam, b)
        assert abs(gis[0] - w) <= 1 and abs(gis[1] - h) <= 1, (cam, b)
        if known:
            assert (w, h) == known == (r["width"], r["height"]) == tuple(gis)
            assert tuple(r["translation"]) == tr == (363, 470)


def test_ground_points_through_every_implementation(tmp_path):
    """expected.json ground points: viewer forward on the fixture manifest, renderer forward on its own matrix,
    exporter forward on the exported manifest; X, Y within 1e-3 px."""
    pts = EXPECTED["groundPoints"]
    out = ts(tmp_path, {
        "viewer": [{"matrix": FIXTURE["projection"]["matrix"], "translation": FIXTURE["projection"]["translation"],
                    "origin": FIXTURE["projection"]["origin"], "forward": [[p["E"], p["N"], p["H"]] for p in pts]}],
        "renderer": [{"camera": {"headingDeg": 45, "pitchDeg": 30, "pixelsPerMetre": 4}, "aoi": [128, 128],
                      "z": [ZMIN, ZMAX], "forward": [[p["E"] - H.E0, p["N"] - H.N0, p["H"] - H.H0] for p in pts]}],
    })
    for k, p in enumerate(pts):
        assert out["viewer"][0]["forward"][k] == pytest.approx([p["X"], p["Y"]], abs=1e-3), p
        assert out["renderer"][0]["forward"][k][:2] == pytest.approx([p["X"], p["Y"]], abs=1e-3), p
        assert export_build.forward(FIXTURE["projection"], p["E"], p["N"], p["H"]) == pytest.approx(
            [p["X"], p["Y"]], abs=1e-3), p


def test_exported_manifest_projection_through_the_viewer(run_a, tmp_path):
    """The manifest the exporter wrote (copied from render.json written by the renderer) is what the viewer reads:
    the viewer's forward on it reproduces expected.json too, and its reference-plane inverse the closed form."""
    m = H.jload(run_a.tiles / "manifest.json")
    pr = m["projection"]
    refs = EXPECTED["referencePlane"]["cases"]
    pts = EXPECTED["groundPoints"]
    out = ts(tmp_path, {"viewer": [{"matrix": pr["matrix"], "translation": pr["translation"], "origin": pr["origin"],
                                    "forward": [[p["E"], p["N"], p["H"]] for p in pts],
                                    "inverse": [[c["X"], c["Y"], 0.0] for c in refs]}]})
    for k, p in enumerate(pts):
        assert out["viewer"][0]["forward"][k] == pytest.approx([p["X"], p["Y"]], abs=1e-3)
    for k, c in enumerate(refs):
        assert out["viewer"][0]["inverse"][k] == pytest.approx([c["E"], c["N"]], abs=1e-4)


# ---- 7.6 properties ---------------------------------------------------------------------------------------------

CAMERAS = [H.CAM, cam_of(VECTORS["cameras"][1]), cam_of(VECTORS["cameras"][3])]  # fixture, 8 px/m dimetric, oblique


def test_inverse_of_forward_is_identity_for_random_points(tmp_path):
    rnd = random.Random(20261115)
    payload_v, payload_r, truth = [], [], []
    for cam in CAMERAS:
        pts = [(rnd.uniform(0, 500), rnd.uniform(0, 500), rnd.uniform(-10, 120)) for _ in range(1000)]
        uvd = [closed_form(cam, *p) for p in pts]
        tr = (363.0, 470.0)
        payload_v.append({"matrix": H.matrix(cam), "translation": tr, "origin": ORIGIN,
                          "inverse": [[u + tr[0], v + tr[1], p[2]] for (u, v, _), p in zip(uvd, pts, strict=True)]})
        payload_r.append({"camera": {"headingDeg": cam.heading, "pitchDeg": cam.pitch, "pixelsPerMetre": cam.ppm},
                          "aoi": [500, 500], "z": [-10, 120], "forward": [list(p) for p in pts], "unproject": []})
        truth.append((pts, uvd))
    # unproject needs the renderer's own translation: ask for it first (it depends only on the camera and prism)
    first = ts(tmp_path, {"renderer": payload_r})
    for k, (_, uvd) in enumerate(truth):
        t0 = first["renderer"][k]["translation"]
        payload_r[k]["unproject"] = [[u + t0[0], v + t0[1], d] for u, v, d in uvd]
    out = ts(tmp_path, {"viewer": payload_v, "renderer": payload_r})
    for k, (pts, uvd) in enumerate(truth):
        t0 = out["renderer"][k]["translation"]
        for i, p in enumerate(pts):
            # viewer: reference-plane inverse at the point's own height (projection.md 5.1) returns E, N
            assert out["viewer"][k]["inverse"][i] == pytest.approx([p[0], p[1]], abs=1e-6), (k, p)
            # renderer: forward matches the closed form, and the surface pick returns the 3-D point
            X, Y, d = out["renderer"][k]["forward"][i]
            assert (X - t0[0], Y - t0[1], d) == pytest.approx(uvd[i], abs=1e-6), (k, p)
            assert out["renderer"][k]["unproject"][i] == pytest.approx(list(p), abs=1e-6), (k, p)


def test_terrain_pick_recovers_random_ground_points_on_the_plane(run_a, tmp_path):
    rnd = random.Random(8)
    pts = [(rnd.uniform(1, 127), rnd.uniform(1, 127)) for _ in range(200)]
    tr = H.jload(run_a.tiles / "manifest.json")["projection"]["translation"]
    xy = [H.fwd(x, y, H.plane(x, y), tr) for x, y in pts]
    out = ts(tmp_path, {"pick": {"dir": str(run_a.tiles), "points": [list(p) for p in xy]}})
    for (x, y), got in zip(pts, out["pick"], strict=True):
        assert got is not None, (x, y)
        assert (got["E"] - H.E0, got["N"] - H.N0) == pytest.approx((x, y), abs=0.05), (x, y)
        assert got["H"] - H.H0 == pytest.approx(H.plane(x, y), abs=0.02)


def test_background_pixels_have_no_pick(run_a, tmp_path):
    """Image corners and the strip outside the AOI diamond are background: no pick (projection.md 5.2)."""
    corners = [[0.5, 0.5], [725.5, 0.5], [0.5, 480.5], [725.5, 480.5], [100.5, 100.5], [600.5, 400.5]]
    out = ts(tmp_path, {"pick": {"dir": str(run_a.tiles), "points": corners}})
    assert out["pick"] == [None] * len(corners)


def test_every_pixel_of_every_level_is_covered_once_after_removing_the_overlap(run_a):
    """On the exported tiles: the non-overlapping interiors tile each level exactly."""
    import numpy as np
    from PIL import Image
    top, sizes = H.level_sizes(726, 481)
    for lv, (lw, lh) in sizes.items():
        cover = np.zeros((lh, lw), dtype=np.int32)
        for f in sorted((run_a.tiles / "procedural" / str(lv)).glob("*.png")):
            col, row = map(int, f.stem.split("_"))
            with Image.open(f) as im:
                tw, th = im.size
            ox, oy = (1 if col else 0), (1 if row else 0)
            nw, nh = min(256, lw - col * 256), min(256, lh - row * 256)
            right = 1 if (col + 1) * 256 < lw else 0
            bottom = 1 if (row + 1) * 256 < lh else 0
            assert (tw, th) == (ox + nw + right, oy + nh + bottom), f
            cover[row * 256:row * 256 + nh, col * 256:col * 256 + nw] += 1
        assert (cover == 1).all(), lv


def test_tile_enumeration_matches_the_formula_for_random_images():
    """export.validate.expected_tiles (its own enumeration) against helpers.tile_list on random sizes, and the
    interiors cover every pixel of every level exactly once."""
    import numpy as np
    rnd = random.Random(11)
    for _ in range(60):
        w, h = rnd.randint(1, 3000), rnd.randint(1, 3000)
        size, ov = rnd.choice([64, 128, 256]), rnd.choice([0, 1, 2])
        top = math.ceil(math.log2(max(w, h))) if max(w, h) > 1 else 0
        m = {"image": {"width": w, "height": h}, "tiles": {"tileSize": size, "tileOverlap": ov, "minLevel": 0,
                                                              "maxLevel": top},
             "styles": [{"tilesBase": "s", "format": "png"}]}
        got = {(lv, *map(int, rel.rsplit("/", 1)[1].split(".")[0].split("_"))): dims
               for rel, (lv, dims) in export_validate.expected_tiles(m).items()}
        assert got == H.tile_list(w, h, size, ov), (w, h, size, ov)
        _, sizes = H.level_sizes(w, h)
        for lv, (lw, lh) in sizes.items():
            cover = np.zeros((lh, lw), dtype=np.int32)
            for (level, col, row), (tw, th) in got.items():
                if level != lv:
                    continue
                x0, y0 = col * size, row * size
                x1, y1 = min(x0 + size, lw), min(y0 + size, lh)
                assert tw >= x1 - x0 and th >= y1 - y0
                cover[y0:y1, x0:x1] += 1
            assert (cover == 1).all(), (w, h, size, ov, lv)
