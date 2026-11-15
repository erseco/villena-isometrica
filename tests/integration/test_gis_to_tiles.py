"""WP08 7.5: the GIS pipeline's own output, on WP03's tiny synthetic input, goes through the renderer and the
exporter. WP03's tests already cover clipping, CRS mismatch, heightSource and the default height, so this only adds
what no single package can test: that the three stages agree on the contract."""

import json

import helpers as H
import pytest
from geospatial import build_scene
from geospatial.inputs import load_city
from PIL import Image

DATA = H.ROOT / "pipeline" / "tests" / "geospatial" / "data"


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    root = tmp_path_factory.mktemp("gis")
    scene, rend, tiles = root / "scene", root / "render", root / "tiles"
    build_scene.build(load_city(DATA / "city.json", DATA), scene, False)
    city = DATA / "city.json"
    H.ok(H.render(scene, rend, city=city))
    H.ok(H.export(rend, scene, tiles, city=city))
    H.ok(H.validate(tiles, "--render", rend))
    return scene, rend, tiles, city


def test_gis_scene_renders_and_exports_with_the_projection_the_gis_stage_predicted(chain):
    scene, rend, tiles, _ = chain
    manifest = H.jload(scene / "scene.json")
    size = build_scene.image_size(H.jload(DATA / "city.json"), manifest["zRange"])
    for doc in (H.jload(rend / "render.json"), H.jload(tiles / "manifest.json")):
        assert [doc["image"]["width"], doc["image"]["height"]] == size


def test_every_building_part_reaches_the_building_id_index_in_scene_order(chain):
    scene, rend, _, _ = chain
    parts = [f["properties"]["id"] for f in H.jload(scene / "buildings.geojson")["features"]]
    index = H.jload(rend / "buildingId.json")
    assert index[0] is None and index[1:1 + len(parts)] == parts


def test_gis_poi_positions_survive_the_export(chain):
    scene, _, tiles, _ = chain
    m = H.jload(tiles / "manifest.json")
    for p in H.jload(tiles / "pois.json")["pois"]:
        x, y, z = p["E"] - m["projection"]["origin"]["E0"], p["N"] - m["projection"]["origin"]["N0"], \
            p["H"] - m["projection"]["origin"]["H0"]
        a = m["projection"]["matrix"]
        t = m["projection"]["translation"]
        assert p["X"] == pytest.approx(a[0][0] * x + a[0][1] * y + a[0][2] * z + t[0], abs=1e-3), p["id"]
        assert p["Y"] == pytest.approx(a[1][0] * x + a[1][1] * y + a[1][2] * z + t[1], abs=1e-3), p["id"]


def test_the_rendered_buildings_stand_where_the_gis_scene_puts_them(chain):
    """The wall top of each part, projected with the closed form, resolves to that part in the buildingId layer.
    Parts in the margin only (SYN0007) are outside the render prism (projection.md section 3): nothing is drawn."""
    scene, rend, _, _ = chain
    rj = H.jload(rend / "render.json")
    ids, cls, color = H.layer(rend, "buildingId"), H.layer(rend, "class"), H.layer(rend, "color")
    index = H.jload(rend / "buildingId.json")
    city = H.jload(DATA / "city.json")
    cam = H.SimpleNamespace(heading=city["camera"]["headingDeg"], pitch=city["camera"]["pitchDeg"],
                            ppm=city["camera"]["pixelsPerMetre"])
    o, (w, s, e, n) = city["origin"], city["aoi"]["bounds"]
    seen = set()
    for f in H.jload(scene / "buildings.geojson")["features"]:
        q, ring = f["properties"], f["geometry"]["coordinates"][0]
        xs, ys = [c[0] - o["E0"] for c in ring], [c[1] - o["N0"] for c in ring]
        # the NE-most corner pulled 1 m inwards is the point least likely to be hidden by a neighbour
        px, py = max(xs) - 1, max(ys) - 1
        X, Y = H.fwd(px, py, q["baseH"] - o["H0"] + q["heightM"], rj["projection"]["translation"], cam)
        inside = w <= px + o["E0"] < e and s <= py + o["N0"] < n
        got = index[H.building_id(ids, X, Y)]
        if inside:
            assert got == q["id"], q["id"]
            assert cls[int(Y), int(X)] == 4 and color[int(Y), int(X), 3] == 255, q["id"]
        else:
            assert got is None and color[int(Y), int(X), 3] == 0, q["id"]
        seen.add(inside)
    assert seen == {True, False}  # the data has both kinds


def test_gis_exports_a_complete_pyramid(chain):
    _, _, tiles, _ = chain
    m = H.jload(tiles / "manifest.json")
    want = H.tile_list(m["image"]["width"], m["image"]["height"], m["tiles"]["tileSize"], m["tiles"]["tileOverlap"])
    for (lv, col, row), size in want.items():
        with Image.open(tiles / "procedural" / str(lv) / f"{col}_{row}.png") as im:
            assert im.size == size
    json.loads((tiles / "pois.json").read_text())
