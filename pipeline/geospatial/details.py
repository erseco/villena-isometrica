"""Curated landmark details (scene contract v1.1, ADR 0008): cities/<city>/landmark-details.json -> scene."""
import json
from pathlib import Path

from shapely.geometry import Point

from .buildings import Part
from .inputs import PipelineError

KINDS = {"cylinder", "cone", "dome"}
MATERIALS = {"stone", "brick", "plaster", "tile", "slate", "metal"}
PART_MATERIALS = {"stone", "brick", "plaster"}
REPLACE_MARGIN = 1.5  # m: parts inside a replacing solid grown by this are dropped


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
            ok = (d.get("kind") in KINDS and d.get("material") in MATERIALS
                  and d.get("dimensionsSource") in ("surface-model", "estimated")
                  and all(isinstance(d.get(k), (int, float)) for k in ("E", "N", "baseH", "heightM", "radiusM"))
                  and d["heightM"] > 0 and d["radiusM"] > 0
                  and 0 <= d.get("topRadiusM", 0) < d["radiusM"] and d.get("sides", 0) in (0, 4)
                  and (d["kind"] == "cone" or not {"topRadiusM", "sides", "rotationDeg"} & d.keys())
                  and (d["kind"] == "cylinder" or "parapet" not in d)
                  and d.get("parapet", "battlement") == "battlement")
            if not ok:
                raise PipelineError(f"{w} is not a valid detail")
    return doc["landmarks"]


def apply(curated: dict, solids: list[Part], clip) -> tuple[list[dict], set[str], dict]:
    """Detail features, the ids of parts replaced by a solid, and counts. Sets parapet/material on landmark parts."""
    feats, replaced = [], set()
    for lm, entry in sorted(curated.items()):
        for p in solids:
            if p.landmark == lm:
                p.parapet, p.material = entry.get("parapet"), entry.get("material")
        for d in entry.get("details", []):
            pt = Point(round(d["E"], 2), round(d["N"], 2))
            if not clip.contains(pt.buffer(d["radiusM"])):
                raise PipelineError(f"detail {lm}-{d['name']} lies outside the clip rectangle")
            if d.get("replacesParts"):
                disc = pt.buffer(d["radiusM"] + REPLACE_MARGIN)
                replaced |= {p.id for p in solids if disc.contains(p.geom)}
            props = {"id": f"{lm}-{d['name']}", "landmark": lm, "kind": d["kind"], "baseH": round(d["baseH"], 2),
                     "heightM": round(d["heightM"], 2), "radiusM": round(d["radiusM"], 2), "material": d["material"],
                     "shapeSource": "reference", "dimensionsSource": d["dimensionsSource"]}
            props |= {k: d[k] for k in ("topRadiusM", "sides", "rotationDeg", "parapet") if k in d}
            feats.append({"geometry": pt, "properties": props})
    feats.sort(key=lambda f: f["properties"]["id"])
    if len({f["properties"]["id"] for f in feats}) != len(feats):
        raise PipelineError("duplicate detail ids")
    return feats, replaced, {"landmarks": len(curated), "details": len(feats), "partsReplaced": len(replaced)}
