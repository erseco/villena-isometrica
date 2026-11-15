"""WP08 7.3: bad inputs must fail loudly (non-zero exit, a message naming the problem), never produce output.
Renderer and exporter run as CLIs. Cases WP06 already tests for `export.validate` are not repeated."""

import json
import shutil

import helpers as H
import pytest
from PIL import Image


@pytest.fixture
def scene(tmp_path):
    return H.copy_scene(tmp_path / "scene")


def fails_render(scene, tmp_path, status, *needles):
    out = tmp_path / "out"
    p = H.render(scene, out)
    assert p.returncode == status, f"exit {p.returncode}\n{p.stdout}\n{p.stderr}"
    for n in needles:
        assert n in p.stderr, f"{n!r} not in:\n{p.stderr}"
    assert not (out / "color.png").exists(), "a failed render must not leave a colour layer behind"


# ---- renderer ----------------------------------------------------------------------------------------------------

def test_renderer_missing_layer_file(scene, tmp_path):
    (scene / "roads.geojson").unlink()
    fails_render(scene, tmp_path, 1, "roads.geojson")


def test_renderer_wrong_layer_sha256(scene, tmp_path):
    H.rewrite_json(scene / "scene.json", lambda m: m["layers"]["buildings"].update(sha256="0" * 64))
    fails_render(scene, tmp_path, 1, "buildings.geojson", "sha256")


def test_renderer_terrain_of_the_wrong_length(scene, tmp_path):
    data = (scene / "terrain.f32").read_bytes()
    (scene / "terrain.f32").write_bytes(data[:-4 * 100])
    H.reseal_layer(scene, "terrain")  # the hash is right: only the length is wrong
    fails_render(scene, tmp_path, 1, "terrain.f32")


def test_renderer_terrain_with_a_partial_float(scene, tmp_path):
    (scene / "terrain.f32").write_bytes((scene / "terrain.f32").read_bytes()[:-2])
    H.reseal_layer(scene, "terrain")
    fails_render(scene, tmp_path, 1, "terrain.f32")


@pytest.mark.xfail(strict=True, reason="WP08-D-01: the renderer accepts a polygon ring of 3 positions (exit 0)")
def test_renderer_polygon_with_fewer_than_four_coordinates(scene, tmp_path):
    doc = H.jload(scene / "buildings.geojson")
    doc["features"][0]["geometry"]["coordinates"][0] = doc["features"][0]["geometry"]["coordinates"][0][:3]
    (scene / "buildings.geojson").write_text(json.dumps(doc))
    H.reseal_layer(scene, "layers", "buildings")
    fails_render(scene, tmp_path, 1, "buildings.geojson", "syn-001_1")


def test_renderer_schema_version_2(scene, tmp_path):
    H.rewrite_json(scene / "scene.json", lambda m: m.update(schemaVersion="2.0"))
    fails_render(scene, tmp_path, 1, "scene.json", "2.0")


def test_renderer_non_finite_height(scene, tmp_path):
    """JSON has no NaN; Python's json writes the non-standard literal, which a consumer must refuse (scene.md Rules)."""
    text = (scene / "buildings.geojson").read_text().replace('"heightM": 6.0', '"heightM": NaN', 1)
    (scene / "buildings.geojson").write_text(text)
    H.reseal_layer(scene, "layers", "buildings")
    fails_render(scene, tmp_path, 1, "buildings.geojson")


# ---- exporter ----------------------------------------------------------------------------------------------------

@pytest.fixture
def render_dir(tmp_path):
    out = tmp_path / "render"
    H.ok(H.render(H.SCENE, out))
    return out


def fails_export(render_dir, scene, tmp_path, *needles):
    out = tmp_path / "tiles"
    p = H.export(render_dir, scene, out)
    assert p.returncode == 1, f"exit {p.returncode}\n{p.stdout}\n{p.stderr}"
    assert "Traceback" not in p.stderr, p.stderr  # a named error, not a crash
    for n in needles:
        assert n in p.stderr, f"{n!r} not in:\n{p.stderr}"
    assert not (out / "manifest.json").exists(), "a failed export must not leave a manifest behind"


def test_exporter_layer_of_the_wrong_size(render_dir, tmp_path):
    """A class layer that is a valid PNG with a matching hash but not image.width x image.height."""
    Image.new("P", (700, 481)).save(render_dir / "class.png")
    wrong = H.sha256(render_dir / "class.png")

    def edit(r):
        for layer in r["layers"]:
            if layer["name"] == "class":
                layer["sha256"] = wrong
    H.rewrite_json(render_dir / "render.json", edit)
    fails_export(render_dir, H.SCENE, tmp_path, "class.png", "700x481")


def test_exporter_layer_with_a_tampered_hash(render_dir, tmp_path):
    (render_dir / "color.png").write_bytes((render_dir / "color.png").read_bytes() + b"\0")
    fails_export(render_dir, H.SCENE, tmp_path, "color.png", "sha256")


def test_exporter_layer_pixels_that_do_not_match_pixelSha256(render_dir, tmp_path):
    Image.new("P", (726, 481), 3).save(render_dir / "class.png")
    h = H.sha256(render_dir / "class.png")
    H.rewrite_json(render_dir / "render.json", lambda r: [layer.update(sha256=h) for layer in r["layers"]
                                                          if layer["name"] == "class"])
    fails_export(render_dir, H.SCENE, tmp_path, "class.png", "pixelSha256")


def test_exporter_scene_sha256_mismatch(render_dir, tmp_path):
    scene = H.copy_scene(tmp_path / "scene")
    (scene / "scene.json").write_text((scene / "scene.json").read_text() + " ")
    fails_export(render_dir, scene, tmp_path, "sceneSha256")


def test_exporter_poi_outside_the_image(render_dir, tmp_path):
    scene = H.copy_scene(tmp_path / "scene")
    H.rewrite_json(scene / "pois.json", lambda d: d["pois"][0].update(E=d["pois"][0]["E"] + 5000))
    H.reseal_layer(scene, "pois")
    H.rewrite_json(render_dir / "render.json", lambda r: r.update(sceneSha256=H.sha256(scene / "scene.json")))
    fails_export(render_dir, scene, tmp_path, "outside")


def test_exporter_missing_layer_file(render_dir, tmp_path):
    (render_dir / "buildingId.png").unlink()
    fails_export(render_dir, H.SCENE, tmp_path, "buildingId.png")


def test_exporter_palette_colour_outside_the_palette(render_dir, tmp_path):
    """A drawn pixel whose colour is not in palette.json (render.md: the exporter rejects it)."""
    img = Image.open(render_dir / "color.png").convert("RGBA")
    px = img.load()
    for x in range(img.width):
        for y in range(img.height):
            if px[x, y][3] == 255:
                px[x, y] = (1, 2, 3, 255)
                break
        else:
            continue
        break
    img.save(render_dir / "color.png")
    new = H.jload(render_dir / "render.json")
    import hashlib

    import numpy as np
    pix = hashlib.sha256(np.asarray(Image.open(render_dir / "color.png").convert("RGBA")).tobytes()).hexdigest()
    for layer in new["layers"]:
        if layer["name"] == "color":
            layer["sha256"], layer["pixelSha256"] = H.sha256(render_dir / "color.png"), pix
    (render_dir / "render.json").write_text(json.dumps(new))
    fails_export(render_dir, H.SCENE, tmp_path, "palette")


# ---- validator: only what WP06's tests (pipeline/tests/export) do not already cover ---------------------------------

@pytest.fixture
def tiles(tmp_path):
    out = tmp_path / "tiles"
    shutil.copytree(H.TILES_FIX, out)
    (out / "expected.json").unlink()
    return out


def fails_validate(tiles, *needles):
    p = H.validate(tiles)
    assert p.returncode == 1, f"exit {p.returncode}\n{p.stdout}\n{p.stderr}"
    assert "Traceback" not in p.stderr, p.stderr
    for n in needles:
        assert n in p.stderr, f"{n!r} not in:\n{p.stderr}"


def test_validator_missing_manifest(tiles):
    (tiles / "manifest.json").unlink()
    fails_validate(tiles, "manifest.json")


def test_validator_manifest_that_is_not_json(tiles):
    (tiles / "manifest.json").write_text("{ not json")
    fails_validate(tiles, "manifest.json")


def test_validator_height_grid_of_the_wrong_size(tiles):
    (tiles / "height.u16").write_bytes((tiles / "height.u16").read_bytes()[:-2])
    fails_validate(tiles, "height.u16")


def test_validator_missing_height_grid(tiles):
    (tiles / "height.u16").unlink()
    fails_validate(tiles, "height.u16")


def test_validator_poi_outside_the_image(tiles):
    H.rewrite_json(tiles / "pois.json", lambda d: d["pois"][0].update(X=9999.0))
    fails_validate(tiles, "outside the 726x481 image")


def test_validator_unsorted_pois(tiles):
    H.rewrite_json(tiles / "pois.json", lambda d: d["pois"].reverse())
    fails_validate(tiles, "sorted")


def test_validator_tile_that_does_not_decode(tiles):
    (tiles / "procedural" / "10" / "0_0.png").write_bytes(b"not a png")
    fails_validate(tiles, "0_0.png", "does not decode")


def test_validator_transparent_tile(tiles):
    Image.new("RGBA", (257, 257), (0, 0, 0, 0)).save(tiles / "procedural" / "10" / "0_0.png")
    fails_validate(tiles, "0_0.png")


def test_validator_geo_to_world_residual_above_the_limit(tiles):
    H.rewrite_json(tiles / "manifest.json", lambda m: m["geoToWorld"].update(maxResidualM=0.2))
    fails_validate(tiles, "manifest.json")


def test_validator_wrong_max_level(tiles):
    H.rewrite_json(tiles / "manifest.json", lambda m: m["tiles"].update(maxLevel=9))
    fails_validate(tiles, "maxLevel")


def test_validator_render_with_a_palette_violation(run_a, tmp_path):
    """--render: colour pixels outside palette.json."""
    render = tmp_path / "render"
    shutil.copytree(run_a.render, render)
    pal = H.jload(render / "palette.json")
    pal["colors"] = pal["colors"][:2]
    (render / "palette.json").write_text(json.dumps(pal))
    p = H.validate(run_a.tiles, "--render", render)
    assert p.returncode == 1 and "palette" in p.stderr, p.stderr
