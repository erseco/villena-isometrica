"""export.build / validate / pack against the synthetic Planeville fixtures (tests/fixtures/, made by
scripts/make_fixtures.py, independent of this package)."""

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from export import build as B
from export.pack import pack
from export.validate import validate

FIX = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
RENDER, SCENE, CITY, TILES = (FIX / "render-synthetic", FIX / "scene-synthetic", FIX / "city-synthetic" / "city.json",
                              FIX / "tiles-synthetic")


def run(out: Path, **kw) -> dict:
    return B.build(RENDER, SCENE, CITY, out, "fixture-1", **kw)


def rgb(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def published_fixture(tmp_path: Path) -> Path:
    """The fixture tile set without its test oracle, as it would be published."""
    out = tmp_path / "fixture"
    shutil.copytree(TILES, out)
    (out / "expected.json").unlink()
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("tiles") / "t"
    run(out)
    return out


def test_build_passes_validate(built):
    errors, table = validate(built, max_bytes=262144000, render_dir=RENDER)
    assert errors == []
    assert "total" in table


def test_same_tiles_as_fixture_and_max_level_pixel_identical(built):
    want = {k for k in tree(TILES) if k.startswith("procedural/")}
    got = {k for k in tree(built) if k.startswith("procedural/")}
    assert got == want and len(got) == 17
    for rel in sorted(got):
        a, b = rgb(built / rel), rgb(TILES / rel)
        assert a.shape == b.shape, rel
        if rel.startswith("procedural/10/"):
            assert np.array_equal(a, b), rel


def test_mean_kernel_reproduces_every_fixture_level(tmp_path):
    run(tmp_path / "t", kernel="mean")
    for rel in tree(TILES):
        if rel.startswith("procedural/"):
            assert np.array_equal(rgb(tmp_path / "t" / rel), rgb(TILES / rel)), rel


def test_mode_kernel_keeps_palette_and_breaks_ties_top_left_first():
    red, green, blue, grey = (255, 0, 0), (0, 255, 0), (0, 0, 255), (9, 9, 9)
    img = np.array([[red, green, blue, blue],
                    [grey, green, grey, red],
                    [red, green, red, red]], dtype=np.uint8)  # 4x3: last row is replicated for the 2x reduction
    out = B.reduce2(img, "mode")
    assert out.shape == (2, 2, 3)
    assert out[0, 0].tolist() == list(green)  # green x2 beats red, grey
    assert out[0, 1].tolist() == list(blue)   # blue x2
    assert out[1, 0].tolist() == list(red)    # red, green, red, green: tie -> top-left
    assert out[1, 1].tolist() == list(red)


def test_manifest_and_pois_match_fixture(built):
    got, want = (json.loads((d / "manifest.json").read_text()) for d in (built, TILES))
    for key in ("projection", "image", "tiles", "zRange", "crs", "renderSha256", "background", "attribution"):
        assert got[key] == want[key], key
    np.testing.assert_allclose(got["geoToWorld"]["matrix"], want["geoToWorld"]["matrix"], rtol=1e-6)
    assert got["geoToWorld"]["maxResidualM"] < 0.1
    gp, wp = (json.loads((d / "pois.json").read_text())["pois"] for d in (built, TILES))
    assert [p["id"] for p in gp] == [p["id"] for p in wp]
    for g, w in zip(gp, wp, strict=True):
        assert abs(g["X"] - w["X"]) <= 1e-3 and abs(g["Y"] - w["Y"]) <= 1e-3, g["id"]
        assert set(g) == set(w), g["id"]
        if "imageBounds" in w:
            np.testing.assert_allclose(g["imageBounds"], w["imageBounds"], atol=1e-3)


def test_height_grid_samples_the_terrain_plane(built):
    hg = json.loads((built / "manifest.json").read_text())["heightGrid"]
    values = np.frombuffer((built / "height.u16").read_bytes(), dtype="<u2").reshape(hg["height"], hg["width"])
    col, row = np.meshgrid(np.arange(hg["width"]), np.arange(hg["height"]))
    x = hg["westE"] + (col + 0.5) * hg["cellSize"] - 700000.0
    y = hg["northN"] - (row + 0.5) * hg["cellSize"] - 4270000.0
    expected = 500.0 + 0.10 * x + 0.05 * y  # the fixture's analytic terrain
    assert hg["cellSize"] == 4.0 and hg["scale"] == 0.01 and hg["offset"] == np.floor(expected.min())
    assert np.abs(hg["offset"] + hg["scale"] * values - expected).max() <= 0.006


def test_geo_to_world_matches_expected_ground_points(built):
    m = json.loads((built / "manifest.json").read_text())["geoToWorld"]
    g = np.array(m["matrix"])
    for p in json.loads((TILES / "expected.json").read_text())["groundPoints"]:
        e, n = g @ [p["lon"], p["lat"], 1.0]
        assert np.hypot(e - p["E"], n - p["N"]) <= m["maxResidualM"] + 0.002  # lon/lat given to 8 decimals


def test_build_and_pack_are_reproducible(built, tmp_path):
    run(tmp_path / "again")
    assert tree(tmp_path / "again") == tree(built)
    a, b = pack(built, tmp_path / "a.tar.gz"), pack(tmp_path / "again", tmp_path / "b.tar.gz")
    assert a["sha256"] == b["sha256"] and a["sizeBytes"] == b["sizeBytes"]


def test_png_and_webp_decode_identically(built, tmp_path):
    m = run(tmp_path / "webp", fmt="webp")
    assert m["styles"][0]["format"] == "webp"
    assert validate(tmp_path / "webp")[0] == []
    for rel in tree(built):
        if rel.startswith("procedural/10/"):
            assert np.array_equal(rgb(built / rel), rgb(tmp_path / "webp" / rel.replace(".png", ".webp"))), rel


def test_validate_passes_on_fixture_unchanged():
    assert validate(TILES)[0] == []


@pytest.mark.parametrize("damage, message", [
    ("delete-tile", "procedural/10/1_1.png: missing tile"),
    ("extra-file", "stray.txt: unexpected file"),
    ("wrong-dims", "procedural/10/0_0.png: 256x256 px, expected 257x257"),
    ("poi-moved", "POI keep X,Y = (365.0, 133.803) but forward(E, N, H) = (363.000, 133.803)"),
    ("matrix", "manifest.json: projection.matrix[0][0] = 2.9"),
    ("budget", "exceeds --max-bytes 1000"),
])
def test_validate_rejects(tmp_path, damage, message):
    root = published_fixture(tmp_path)
    max_bytes = None
    if damage == "delete-tile":
        (root / "procedural/10/1_1.png").unlink()
    elif damage == "extra-file":
        (root / "stray.txt").write_text("x")
    elif damage == "wrong-dims":
        Image.new("RGB", (256, 256)).save(root / "procedural/10/0_0.png")
    elif damage in ("poi-moved", "matrix"):
        name = "pois.json" if damage == "poi-moved" else "manifest.json"
        doc = json.loads((root / name).read_text())
        if damage == "poi-moved":
            next(p for p in doc["pois"] if p["id"] == "keep")["X"] += 2
        else:
            doc["projection"]["matrix"][0][0] = 2.9
        (root / name).write_text(json.dumps(doc))
    else:
        max_bytes = 1000
    errors, _ = validate(root, max_bytes=max_bytes)
    assert any(message in e for e in errors), errors


def test_build_refuses_a_scene_that_does_not_match_the_render(tmp_path):
    scene = tmp_path / "scene"
    shutil.copytree(SCENE, scene)
    (scene / "scene.json").write_text((scene / "scene.json").read_text() + " ")
    with pytest.raises(B.ExportError, match="sceneSha256"):
        B.build(RENDER, scene, CITY, tmp_path / "out", "x")


def test_build_refuses_a_poi_outside_the_image(tmp_path):
    render, scene = tmp_path / "render", tmp_path / "scene"
    shutil.copytree(SCENE, scene)
    shutil.copytree(RENDER, render)
    pois = json.loads((scene / "pois.json").read_text())
    pois["pois"][0]["H"] += 1000  # 1 km up: far above the top edge
    (scene / "pois.json").write_text(json.dumps(pois))
    manifest = json.loads((scene / "scene.json").read_text())
    manifest["pois"]["sha256"] = hashlib.sha256((scene / "pois.json").read_bytes()).hexdigest()
    (scene / "scene.json").write_text(json.dumps(manifest))
    r = json.loads((render / "render.json").read_text())
    r["sceneSha256"] = hashlib.sha256((scene / "scene.json").read_bytes()).hexdigest()
    (render / "render.json").write_text(json.dumps(r))
    with pytest.raises(B.ExportError, match="POI calle-mayor projects to .* outside"):
        B.build(render, scene, CITY, tmp_path / "out", "x")
