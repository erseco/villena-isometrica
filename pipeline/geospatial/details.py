"""Curated landmark details (scene contract v1.1, ADR 0008): cities/<city>/landmark-details.json -> scene."""
import json
from pathlib import Path

from shapely.affinity import rotate
from shapely.geometry import Point, box

from .buildings import Part
from .inputs import PipelineError

KINDS = {"cylinder", "cone", "dome", "gable"}
ROOF_MATERIALS = {"tile", "slate", "metal"}
MATERIALS = {"stone", "brick", "plaster", "tile", "slate", "metal"}
PART_MATERIALS = {"stone", "brick", "plaster"}
REPLACE_MARGIN = 1.5  # m: parts lying mostly (> half their area) inside a replacing solid grown by this are dropped


COMMON = {"name", "kind", "E", "N", "baseH", "heightM", "material", "dimensionsSource", "replacesParts"}
EXTRA = {"cylinder": {"radiusM", "parapet", "openings"}, "dome": {"radiusM"},
         "cone": {"radiusM", "topRadiusM", "sides", "rotationDeg"},
         "gable": {"lengthM", "widthM", "wallHeightM", "roofMaterial", "rotationDeg"}}
SIZES = {"gable": ("lengthM", "widthM", "wallHeightM")}


def _valid(d: dict) -> bool:
    kind = d.get("kind")
    if kind not in KINDS or set(d) - COMMON - EXTRA[kind]:
        return False
    numbers = ("E", "N", "baseH", "heightM", *SIZES.get(kind, ("radiusM",)))
    if not all(isinstance(d.get(k), (int, float)) for k in numbers) or not all(d[k] > 0 for k in numbers[3:]):
        return False
    if kind == "gable":
        shape_ok = d["wallHeightM"] < d["heightM"] and d.get("roofMaterial") in ROOF_MATERIALS
    else:
        shape_ok = 0 <= d.get("topRadiusM", 0) < d["radiusM"] and d.get("sides", 0) in (0, 4)
    return (shape_ok and d.get("material") in MATERIALS and d.get("dimensionsSource") in ("surface-model", "estimated")
            and d.get("parapet", "battlement") == "battlement" and d.get("openings", "arcade") == "arcade")


def load(path: Path, poi_ids: set[str]) -> dict:
    """The curated file, checked. {} when the city has none."""
    if not path.exists():
        return {}
    doc = json.loads(path.read_text())
    for lm, entry in doc["landmarks"].items():
        where = f"{path}: {lm}"
        if lm not in poi_ids:
            raise PipelineError(f"{where} is not a selected POI")
        if not entry.get("references"):
            raise PipelineError(f"{where} has no references")
        if entry.get("parapet", "battlement") != "battlement" or entry.get("material", "stone") not in PART_MATERIALS:
            raise PipelineError(f"{where} has an unknown parapet or material")
        for d in entry.get("details", []):
            w = f"{where}/{d.get('name')}"
            ok = _valid(d)
            if not ok:
                raise PipelineError(f"{w} is not a valid detail")
    return doc["landmarks"]


def apply(curated: dict, solids: list[Part], clip) -> tuple[list[dict], set[str], list, dict]:
    """Detail features, ids of the parts a solid replaces, the solids' footprints, and counts.
    Sets parapet/material on landmark parts."""
    feats, replaced, footprints = [], set(), []
    for lm, entry in sorted(curated.items()):
        for p in solids:
            if p.landmark == lm:
                p.parapet, p.material = entry.get("parapet"), entry.get("material")
        for d in entry.get("details", []):
            pt = Point(round(d["E"], 2), round(d["N"], 2))
            if d["kind"] == "gable":
                solid = rotate(box(pt.x - d["widthM"] / 2, pt.y - d["lengthM"] / 2, pt.x + d["widthM"] / 2,
                                   pt.y + d["lengthM"] / 2), -d.get("rotationDeg", 0), origin=pt)
            else:
                solid = pt.buffer(d["radiusM"])
            if not clip.contains(solid):
                raise PipelineError(f"detail {lm}-{d['name']} lies outside the clip rectangle")
            if d.get("replacesParts"):
                grown = solid.buffer(REPLACE_MARGIN)
                replaced |= {p.id for p in solids if grown.intersection(p.geom).area > 0.5 * p.geom.area}
            footprints.append(solid)
            props = {"id": f"{lm}-{d['name']}", "landmark": lm, "kind": d["kind"], "baseH": round(d["baseH"], 2),
                     "heightM": round(d["heightM"], 2), "material": d["material"],
                     "shapeSource": "reference", "dimensionsSource": d["dimensionsSource"]}
            props |= {k: round(d[k], 2) for k in ("radiusM", "lengthM", "widthM", "wallHeightM") if k in d}
            optional = ("topRadiusM", "sides", "rotationDeg", "parapet", "openings", "roofMaterial")
            props |= {k: d[k] for k in optional if k in d}
            feats.append({"geometry": pt, "properties": props})
    feats.sort(key=lambda f: f["properties"]["id"])
    if len({f["properties"]["id"] for f in feats}) != len(feats):
        raise PipelineError("duplicate detail ids")
    counts = {"landmarks": len(curated), "details": len(feats), "partsReplaced": len(replaced)}
    return feats, replaced, footprints, counts
