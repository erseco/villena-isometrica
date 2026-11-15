"""Known-answer tests on the synthetic dataset in data/ (see data/make_data.py for the ground truth)."""

import hashlib
import json
import shutil
from pathlib import Path

import jsonschema
import pytest
import rasterio

from geospatial import build_scene
from geospatial.inputs import PipelineError, load_city

DATA = Path(__file__).parent / "data"
SCHEMA = Path(__file__).resolve().parents[3] / "packages/geo-contracts/schemas/scene-manifest.schema.json"
E0, N0 = 700000.0, 4270000.0


def ground(x, y):
    return 600.0 + 0.08 * x + 0.04 * y


def build(tmp_path, data=DATA, fallback=False, name="scene"):
    out = tmp_path / name
    build_scene.build(load_city(data / "city.json", data), out, fallback)
    return out


@pytest.fixture(scope="module")
def scene(tmp_path_factory):
    return build(tmp_path_factory.mktemp("full"))


def features(scene, layer):
    return {f["properties"]["id"]: f for f in json.loads((scene / f"{layer}.geojson").read_text())["features"]}


def tree_hash(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.iterdir())}


def test_manifest_validates(scene):
    manifest = json.loads((scene / "scene.json").read_text())
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(manifest)
    for name, layer in manifest["layers"].items():
        assert hashlib.sha256((scene / layer["path"]).read_bytes()).hexdigest() == layer["sha256"], name
    t = manifest["terrain"]
    assert (t["width"], t["height"], t["westE"], t["northN"]) == (240, 240, E0 - 20, N0 + 220)


def test_rerun_is_byte_identical(scene, tmp_path):
    assert tree_hash(build(tmp_path)) == tree_hash(scene)


def test_heights_and_sources(scene):
    b = features(scene, "buildings")
    p = {k: v["properties"] for k, v in b.items()}
    assert p["SYN0001_part1"]["heightSource"] == "surface-model" and p["SYN0001_part1"]["roof"] == "flat"
    # roof plane is ground(20, 20) + 7; baseH is the lowest terrain cell centre under the footprint
    assert p["SYN0001_part1"]["heightM"] == pytest.approx(ground(20, 20) + 7 - p["SYN0001_part1"]["baseH"], abs=0.3)
    assert p["SYN0001_part1"]["baseH"] == pytest.approx(ground(20.5, 20.5), abs=0.01)
    assert p["SYN0002_part1"]["roof"] == "pitched" and p["SYN0002_part1"]["roofSource"] == "surface-model"
    assert p["SYN0002_part1"]["heightM"] == pytest.approx(ground(50, 20) + 6 - p["SYN0002_part1"]["baseH"], abs=0.3)
    assert (p["SYN0003_part1"]["heightSource"], p["SYN0003_part1"]["heightM"]) == ("floors", 10.0)
    assert (p["SYN0004_part1"]["heightSource"], p["SYN0004_part1"]["heightM"], p["SYN0004_part1"]["floors"]) == \
        ("default", 3.0, None)
    assert p["SYN0003_part1"]["roof"] == "unknown" and p["SYN0003_part1"]["roofSource"] == "none"
    assert not any(k.startswith(("SYN0005", "SYN0006")) for k in p)  # open space and underground-only
    assert {v["use"] for k, v in p.items() if k.startswith("SYN0008")} == {"fortification"}


def test_part_straddling_the_clip_edge_is_clipped(scene):
    f = features(scene, "buildings")["SYN0007_part1"]
    xs = [x for x, _ in f["geometry"]["coordinates"][0]]
    assert min(xs) == E0 - 20 and max(xs) == E0 - 5
    p = f["properties"]
    assert p["heightM"] == pytest.approx(ground(-30, 100) + 4 - p["baseH"], abs=0.3)  # roof elevation is preserved


def test_landmark_is_zoned(scene):
    zones = {k: v["properties"] for k, v in features(scene, "buildings").items() if k.startswith("SYN0008")}
    assert "SYN0008_part1" not in zones and len(zones) == 2  # tower + walls; courtyard dropped as open ground
    by_height = sorted(zones.values(), key=lambda p: p["heightM"])
    walls, tower = by_height
    assert tower["baseH"] + tower["heightM"] == pytest.approx(ground(100, 100) + 18, abs=0.3)
    assert walls["baseH"] + walls["heightM"] == pytest.approx(ground(100, 100) + 8, abs=0.3)
    assert all(p["landmark"] == "keep" and p["heightSource"] == "surface-model" for p in zones.values())


def test_polygons_are_ccw_and_rounded(scene):
    from shapely.geometry import Polygon
    for f in features(scene, "buildings").values():
        ring = f["geometry"]["coordinates"][0]
        assert Polygon(ring).exterior.is_ccw
        assert all(round(v, 2) == v for pt in ring for v in pt)


def test_trees(scene):
    t = {v["properties"]["source"]: v for v in features(scene, "trees").values()}
    x, y = t["surface-model"]["geometry"]["coordinates"]
    assert abs(x - (E0 + 60)) <= 0.5 and abs(y - (N0 + 150)) <= 0.5
    assert t["surface-model"]["properties"]["heightM"] == pytest.approx(8.0, abs=0.3)
    assert t["mapped"]["properties"]["id"] == "osm-node-9001"


def test_roads_and_landcover(scene):
    r = {k: v["properties"] for k, v in features(scene, "roads").items()}
    assert set(r) == {"osm-way-1001", "osm-way-1002", "osm-way-1003"}  # construction way ignored
    assert (r["osm-way-1003"]["widthM"], r["osm-way-1003"]["widthSource"]) == (3.0, "tag")
    assert r["osm-way-1001"]["widthSource"] == "class-default"
    xs = [x for x, _ in features(scene, "roads")["osm-way-1001"]["geometry"]["coordinates"]]
    assert min(xs) == E0 - 20 and max(xs) == E0 + 220
    assert [v["properties"]["class"] for v in features(scene, "landcover").values()] == ["park"]


def test_pois(scene):
    pois = {p["id"]: p for p in json.loads((scene / "pois.json").read_text())["pois"]}
    assert set(pois) == {"keep", "plaza", "street-calle-mayor", "street-calle-nueva", "street-subida-al-castillo"}
    assert pois["keep"]["H"] == pytest.approx(ground(100, 100) + 18, abs=0.3)  # on the tower roof
    assert pois["plaza"]["H"] == pytest.approx(ground(60, 90), abs=0.05)  # on the ground
    s = pois["street-calle-mayor"]
    assert (s["E"], s["N"]) == pytest.approx((E0 + 100, N0 + 70), abs=0.05)
    assert s["worldBounds"] == pytest.approx([E0, N0 + 70, E0 + 200, N0 + 70], abs=0.05)
    assert s["source"] == {"dataset": "osm", "ref": "way/1001"} and "X" not in s


def test_fallback_mode(tmp_path):
    out = build(tmp_path, fallback=True)
    p = {k: v["properties"] for k, v in features(out, "buildings").items()}
    assert {v["heightSource"] for v in p.values()} <= {"floors", "default"}
    assert {v["roof"] for v in p.values()} == {"unknown"}
    assert p["SYN0001_part1"]["heightM"] == 7.0 and "SYN0008_part1" in p
    assert [v["properties"]["source"] for v in features(out, "trees").values()] == ["mapped"]
    ids = [d["datasetId"] for d in json.loads((out / "scene.json").read_text())["provenance"]]
    assert "ign-mdt05-wcs" in ids and "ign-mds50cm" not in ids


def copy_data(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA, data)
    return data


def repin(data, dataset_id):
    m = json.loads((data / "datasets.json").read_text())
    for d in m["datasets"]:
        if d["id"] == dataset_id:
            d["sha256"] = hashlib.sha256((data / d["localPath"]).read_bytes()).hexdigest()
    (data / "datasets.json").write_text(json.dumps(m))


def test_wrong_crs_is_rejected(tmp_path):
    data = copy_data(tmp_path)
    with rasterio.open(data / "mdt.tif", "r+") as ds:
        ds.crs = "EPSG:3857"
    repin(data, "ign-mdt50cm")
    with pytest.raises(PipelineError, match="EPSG:3857"):
        build(tmp_path, data)


def test_tampered_input_is_rejected(tmp_path):
    data = copy_data(tmp_path)
    (data / "overpass.json").write_text((data / "overpass.json").read_text().replace("Calle Mayor", "Calle Mayer"))
    with pytest.raises(PipelineError, match="checksum mismatch"):
        build(tmp_path, data)


def test_unpinned_input_is_rejected(tmp_path):
    data = copy_data(tmp_path)
    m = json.loads((data / "datasets.json").read_text())
    m["datasets"][0]["sha256"] = None
    (data / "datasets.json").write_text(json.dumps(m))
    with pytest.raises(PipelineError, match="no pinned sha256"):
        build(tmp_path, data)


def test_missing_surface_model_requires_fallback_flag(tmp_path):
    data = copy_data(tmp_path)
    (data / "mds.tif").unlink()
    with pytest.raises(PipelineError, match="--terrain-fallback"):
        build(tmp_path, data)


def test_poi_outside_aoi_is_rejected(tmp_path):
    data = copy_data(tmp_path)
    pois = json.loads((data / "poi-selection.json").read_text())
    pois[1]["lat"] += 0.01  # about 1.1 km north
    (data / "poi-selection.json").write_text(json.dumps(pois))
    with pytest.raises(PipelineError, match="outside the AOI"):
        build(tmp_path, data)


def test_refuses_to_overwrite_foreign_directory(tmp_path):
    out = tmp_path / "scene"
    out.mkdir()
    (out / "precious.txt").write_text("keep me")
    with pytest.raises(PipelineError, match="refusing"):
        build_scene.build(load_city(DATA / "city.json", DATA), out, False)
    assert (out / "precious.txt").exists()


def test_cli_report_and_preview(tmp_path):
    rc = build_scene.main(["--city", str(DATA / "city.json"), "--data-root", str(DATA), "--out", str(tmp_path / "s"),
                           "--report", str(tmp_path / "r.md"), "--preview", str(tmp_path / "p.png")])
    assert rc == 0
    assert "full mode" in (tmp_path / "r.md").read_text()
    assert (tmp_path / "p.png").read_bytes()[:4] == b"\x89PNG"
    assert not (tmp_path / "p.png.aux.xml").exists()


def test_multipart_wcs_response_is_read(tmp_path):
    """servicios.idee.es answers GetCoverage with multipart/related (grid + aux.xml + prj); see README."""
    from rasterio.warp import Resampling

    from geospatial.inputs import Grid, read_raster
    grid_text = (DATA / "mdt05.asc").read_text()
    body = (f"\n--wcs\nContent-Type: application/asc\nContent-ID: coverage/out.asc\n\n{grid_text}\n"
            "--wcs\nContent-Type: application/octet-stream\nContent-ID: coverage/out.prj\n\nPROJCS[...]\n--wcs--\n")
    (tmp_path / "wcs.asc").write_bytes(body.replace("\n", "\r\n").encode())  # CRLF, leading blank line: as served
    grid = Grid.covering((E0 - 20, N0 - 20, E0 + 220, N0 + 220), 1.0)
    arr, _ = read_raster(tmp_path / "wcs.asc", grid, Resampling.bilinear, "EPSG:25830")
    assert arr[-1, 0] == pytest.approx(ground(-19.5, -19.5), abs=0.05)
    assert arr[0, -1] == pytest.approx(ground(219.5, 219.5), abs=0.05)


def test_landmark_snaps_to_nearest_building_only():
    from shapely.geometry import box

    from geospatial.buildings import Part, tag_landmarks
    keep = Part("K_part1", "K", box(0, 0, 14, 14), 3, "other")  # a keep 15.6 m from the castle node
    keep2 = Part("K_part2", "K", box(-10, 0, -2, 8), 1, "other")
    house = Part("H_part1", "H", box(40, 40, 50, 50), 2, "residential")
    tag_landmarks([keep, keep2, house], [{"id": "castle", "kind": "landmark", "name": "Castillo de la Atalaya",
                                          "E": 14 + 11.03, "N": 14 + 11.03}])
    assert (keep.landmark, keep2.landmark, house.landmark) == ("castle", "castle", None)
    assert keep.use == keep2.use == "fortification" and house.use == "residential"
