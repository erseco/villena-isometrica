"""Curated landmark details: validation, part replacement, properties."""
import json
from pathlib import Path

import pytest
from shapely.geometry import box

from geospatial import details
from geospatial.buildings import Part
from geospatial.inputs import PipelineError

CLIP = box(0, 0, 100, 100)


def _file(tmp_path: Path, **override) -> Path:
    d = {"name": "drum", "kind": "cylinder", "E": 50, "N": 50, "baseH": 500, "heightM": 10, "radiusM": 10,
         "material": "stone", "dimensionsSource": "surface-model", "replacesParts": True} | override
    doc = {"landmarks": {"ring": {"references": ["https://example.org/photo"], "parapet": "battlement",
                                  "material": "stone", "details": [d]}}}
    (tmp_path / "landmark-details.json").write_text(json.dumps(doc))
    return tmp_path / "landmark-details.json"


def test_absent_file_means_no_details(tmp_path: Path) -> None:
    assert details.load(tmp_path / "landmark-details.json", set()) == {}


def test_replaces_inner_parts_and_tags_landmark_parts(tmp_path: Path) -> None:
    inside = Part("in", "b", box(46, 46, 54, 54), None, "other", landmark="ring")
    outside = Part("out", "b", box(70, 70, 80, 80), None, "other", landmark="ring")
    other = Part("x", "c", box(5, 5, 9, 9), None, "other")
    feats, replaced, _, counts = details.apply(details.load(_file(tmp_path), {"ring"}), [inside, outside, other], CLIP)
    assert replaced == {"in"} and counts == {"landmarks": 1, "details": 1, "partsReplaced": 1}
    assert outside.parapet == "battlement" and outside.material == "stone" and other.parapet is None
    assert outside.properties()["parapet"] == "battlement" and "parapet" not in other.properties()
    p = feats[0]["properties"]
    assert p["id"] == "ring-drum" and p["shapeSource"] == "reference" and "replacesParts" not in p


@pytest.mark.parametrize("override", [
    {"kind": "cube"}, {"radiusM": 0}, {"material": "gold"}, {"sides": 3, "kind": "cone"}, {"topRadiusM": 2},
    {"dimensionsSource": "guess"}, {"kind": "dome", "parapet": "battlement"}, {"kind": "gable"},
    {"lengthM": 5}, {"kind": "cone", "openings": "arcade"}])
def test_invalid_details_are_rejected(tmp_path: Path, override: dict) -> None:
    with pytest.raises(PipelineError):
        details.load(_file(tmp_path, **override), {"ring"})


def test_unknown_landmark_and_out_of_area_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(PipelineError):
        details.load(_file(tmp_path), {"somewhere-else"})
    with pytest.raises(PipelineError):
        details.apply(details.load(_file(tmp_path, E=95), {"ring"}), [], CLIP)


def test_gable_replaces_parts_under_its_rotated_rectangle(tmp_path: Path) -> None:
    gable = {"name": "nave", "kind": "gable", "E": 50, "N": 50, "lengthM": 40, "widthM": 10, "wallHeightM": 8,
             "heightM": 11, "rotationDeg": 90, "roofMaterial": "tile"}
    path = _file(tmp_path, **gable)
    doc = json.loads(path.read_text())
    del doc["landmarks"]["ring"]["details"][0]["radiusM"]
    path.write_text(json.dumps(doc))
    along = Part("along", "b", box(35, 47, 65, 53), None, "other")   # inside the east-west hall
    across = Part("across", "b", box(47, 35, 53, 65), None, "other")  # would fit only if the ridge ran north-south
    feats, replaced, shapes, _ = details.apply(details.load(path, {"ring"}), [along, across], CLIP)
    assert replaced == {"along"} and "radiusM" not in feats[0]["properties"]
    assert feats[0]["properties"]["lengthM"] == 40 and round(shapes[0].area) == 400
