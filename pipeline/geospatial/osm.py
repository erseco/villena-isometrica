"""OpenStreetMap (Overpass JSON) -> roads, land cover, mapped trees, landmark structures, street POIs.

Ways may carry inline geometry (`out geom`) or node references (`out body; >; out skel`); `load`
normalises both, and resolves the member ways of multipolygon relations.

Kept separate from Catastro-derived data (ODbL; see docs/LICENSING.md).
"""

import json
import re
import unicodedata
from pathlib import Path

import shapely
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import nearest_points

from .inputs import PipelineError

TO_WORLD = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
TO_GEO = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)

ROAD_CLASS = {
    "motorway": "primary", "trunk": "primary", "primary": "primary", "motorway_link": "primary",
    "trunk_link": "primary", "primary_link": "primary", "secondary": "secondary", "secondary_link": "secondary",
    "tertiary": "secondary", "tertiary_link": "secondary", "residential": "residential",
    "unclassified": "residential", "living_street": "residential", "service": "service", "track": "service",
    "pedestrian": "pedestrian", "steps": "steps", "footway": "path", "path": "path", "cycleway": "path",
    "bridleway": "path",
}
RAIL = {"rail", "light_rail", "narrow_gauge"}
DEFAULT_WIDTH = {"primary": 9.0, "secondary": 7.5, "residential": 6.0, "service": 3.5, "pedestrian": 5.0,
                 "steps": 2.5, "path": 2.0, "rail": 3.0}
# land-cover classes in priority order: earlier classes win where polygons overlap
LANDCOVER = [
    ("water", [("natural", "water"), ("waterway", "riverbank"), ("landuse", "reservoir"), ("landuse", "basin")]),
    ("sports", [("leisure", "pitch"), ("leisure", "sports_centre"), ("leisure", "stadium"), ("leisure", "track")]),
    ("cemetery", [("landuse", "cemetery"), ("amenity", "grave_yard")]),
    ("park", [("leisure", "park"), ("leisure", "garden"), ("leisure", "playground"), ("landuse", "grass"),
              ("landuse", "recreation_ground"), ("landuse", "village_green")]),
    ("paved", [("highway", "pedestrian"), ("place", "square"), ("amenity", "parking")]),
    ("woodland", [("landuse", "forest"), ("natural", "wood")]),
    ("scrub", [("natural", "scrub"), ("natural", "heath"), ("natural", "grassland"), ("landuse", "meadow")]),
    ("farmland", [("landuse", "farmland"), ("landuse", "orchard"), ("landuse", "vineyard"),
                  ("landuse", "allotments"), ("landuse", "farmyard")]),
    ("bare-rock", [("natural", "bare_rock"), ("natural", "scree"), ("natural", "sand")]),
]
DEFAULT_TREE_HEIGHT, DEFAULT_CROWN_RADIUS = 6.0, 2.5
DEFAULT_WALL_WIDTH = 1.5


def load(path: Path) -> list[dict]:
    """Elements sorted by (type, id). Every way gets `geometry`; every relation gets `rings`:
    (role, geometry, way id) per member way."""
    data = json.loads(path.read_text())
    if "elements" not in data:
        raise PipelineError(f"{path}: not an Overpass JSON response")
    unique: dict[tuple, dict] = {}
    for e in data["elements"]:  # `>; out skel` repeats member ways and nodes without tags: keep the tagged copy
        key = (e["type"], e["id"])
        if key not in unique or (e.get("tags") and not unique[key].get("tags")):
            unique[key] = e
    elements = [unique[k] for k in sorted(unique)]
    nodes = {e["id"]: {"lat": e["lat"], "lon": e["lon"]} for e in elements if e["type"] == "node"}
    ways = {}
    for e in elements:
        if e["type"] == "way":
            if "geometry" not in e:
                pts = [nodes.get(n) for n in e.get("nodes", [])]
                e["geometry"] = pts if all(pts) else []  # a way reaching outside the extract cannot be resolved
            ways[e["id"]] = e
    for e in elements:
        if e["type"] == "relation":
            e["rings"] = [(m.get("role") or "outer", m.get("geometry") or ways.get(m["ref"], {}).get("geometry") or [],
                           m["ref"]) for m in e.get("members", []) if m["type"] == "way"]
    return elements


def _metres(value: str | None) -> float | None:
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*(m)?\s*", value or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _line(way: dict) -> LineString | None:
    pts = [TO_WORLD.transform(p["lon"], p["lat"]) for p in way.get("geometry") or [] if p]
    return LineString(pts) if len(pts) >= 2 else None


def _ring(geom: list) -> Polygon | None:
    if len(geom) < 4 or geom[0] != geom[-1]:
        return None
    return shapely.make_valid(Polygon([TO_WORLD.transform(p["lon"], p["lat"]) for p in geom]))


def polygon_of(e: dict):
    """Area of a closed way or of a multipolygon relation whose member ways are closed rings; else None."""
    if e["type"] == "way":
        return _ring(e.get("geometry") or [])
    if e["type"] != "relation" or e.get("tags", {}).get("type") != "multipolygon":
        return None
    rings = [(role, _ring(geom)) for role, geom, _ in e.get("rings", [])]
    if not rings or any(r is None for _, r in rings):
        return None  # ponytail: rings split over several open ways are not stitched; add line-merging if needed
    outer = shapely.union_all([r for role, r in rings if role != "inner"])
    inner = shapely.union_all([r for role, r in rings if role == "inner"])
    return outer.difference(inner)


def _pieces(geom, kind) -> list:
    return [g for g in shapely.get_parts(shapely.set_precision(geom, 0.01)) if isinstance(g, kind) and not g.is_empty]


def roads(elements: list[dict], clip_bounds) -> tuple[list[dict], dict]:
    clip = box(*clip_bounds)
    out, counts = [], {"ways": 0, "ignored": 0}
    for e in elements:
        tags = e.get("tags", {})
        if e["type"] != "way" or not ("highway" in tags or "railway" in tags):
            continue
        counts["ways"] += 1
        if "highway" in tags and tags.get("area") != "yes":
            cls = ROAD_CLASS.get(tags["highway"])
        elif tags.get("railway") in RAIL:
            cls = "rail"
        else:
            cls = None
        line = _line(e)
        if cls is None or line is None:
            counts["ignored"] += 1
            continue
        width = _metres(tags.get("width"))
        try:
            layer = int(tags["layer"])
        except (KeyError, ValueError):
            layer = 1 if tags.get("bridge", "no") != "no" else -1 if tags.get("tunnel", "no") != "no" else 0
        pieces = _pieces(line.intersection(clip), LineString)
        for i, g in enumerate(pieces, 1):
            out.append({"geometry": g, "properties": {
                "id": f"osm-way-{e['id']}" + (f"-{i}" if len(pieces) > 1 else ""), "class": cls,
                "widthM": width or DEFAULT_WIDTH[cls], "widthSource": "tag" if width else "class-default",
                "name": tags.get("name"), "layer": layer}})
    return out, counts


def landcover(elements: list[dict], clip_bounds) -> tuple[list[dict], dict]:
    clip = box(*clip_bounds)
    taken = Polygon()
    out, counts = [], {"relationsUnresolved": 0}
    for cls, rules in LANDCOVER:
        for e in elements:
            tags = e.get("tags", {})
            if not any(tags.get(k) == v for k, v in rules):
                continue
            if cls == "paved" and tags.get("highway") == "pedestrian" and tags.get("area") != "yes":
                continue
            if e["type"] == "node":
                continue
            poly = polygon_of(e)
            if poly is None:
                counts["relationsUnresolved"] += e["type"] == "relation"
                continue
            free = poly.intersection(clip).difference(taken)
            taken = taken.union(poly.intersection(clip))
            pieces = [orient(p, 1.0) for p in _pieces(free, Polygon) if p.area >= 1.0]
            for i, g in enumerate(pieces, 1):
                out.append({"geometry": g, "properties": {
                    "id": f"osm-{e['type']}-{e['id']}" + (f"-{i}" if len(pieces) > 1 else ""), "class": cls,
                    "name": tags.get("name")}})
    return out, counts


def structures(elements: list[dict], clip_bounds, pois: list[dict]) -> list[dict]:
    """Landmark structures Catastro does not model: the OSM building polygon around a `landmark` POI, and walls.

    Returns dicts with id, geometry (clipped), landmark (POI id or None), name. docs/contracts/scene.md.
    """
    clip = box(*clip_bounds)
    landmarks = [(p["id"], Point(p["E"], p["N"])) for p in sorted(pois, key=lambda p: p["id"])
                 if p["kind"] == "landmark"]
    out, areas, outer_members = [], [], set()
    for e in elements:  # relations sort before ways, so a relation is seen before its member ways
        tags = e.get("tags", {})
        if e["type"] == "node" or tags.get("building", "no") == "no":
            continue
        if e["type"] == "way" and e["id"] in outer_members:
            continue  # the outer ring of an accepted multipolygon is that same building without its holes
        poly = polygon_of(e)
        hit = next((pid for pid, pt in landmarks if poly is not None and poly.contains(pt)), None)
        if hit:
            outer_members.update(ref for role, _, ref in e.get("rings", []) if role != "inner")
            areas.append((hit, poly))
            out.append({"id": f"osm-{e['type']}-{e['id']}", "geometry": poly.intersection(clip), "landmark": hit,
                        "name": tags.get("name")})
    for e in elements:
        tags = e.get("tags", {})
        if e["type"] != "way" or tags.get("barrier") not in ("city_wall", "wall") or e["id"] in outer_members:
            continue  # (the outer ring of an accepted polygon is its own boundary, not another wall)
        line = _line(e)
        if line is None:
            continue
        inside = next((pid for pid, poly in areas if poly.buffer(1.0).contains(line)), None)
        if tags["barrier"] == "wall" and inside is None and "historic" not in tags:
            continue  # garden and property walls are not landmarks
        width = _metres(tags.get("width")) or DEFAULT_WALL_WIDTH
        out.append({"id": f"osm-way-{e['id']}", "geometry": line.buffer(width / 2, cap_style="flat").intersection(clip),
                    "landmark": inside, "name": tags.get("name")})
    return [s for s in out if not s["geometry"].is_empty]


def mapped_trees(elements: list[dict], clip_bounds) -> list[dict]:
    clip = box(*clip_bounds)
    out = []
    for e in elements:
        tags = e.get("tags", {})
        if e["type"] != "node" or tags.get("natural") != "tree":
            continue
        x, y = TO_WORLD.transform(e["lon"], e["lat"])
        if not clip.contains(Point(x, y)):
            continue
        crown = _metres(tags.get("diameter_crown"))
        out.append({"geometry": Point(round(x, 2), round(y, 2)), "properties": {
            "id": f"osm-node-{e['id']}", "heightM": _metres(tags.get("height")) or DEFAULT_TREE_HEIGHT,
            "crownRadiusM": crown / 2 if crown else DEFAULT_CROWN_RADIUS, "source": "mapped"}})
    return out


def slug(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def street_pois(road_features: list[dict], aoi_bounds, terrain_at) -> list[dict]:
    """One POI per distinct street name inside the AOI (railways excluded)."""
    aoi = box(*aoi_bounds)
    by_name: dict[str, list[dict]] = {}
    for f in road_features:
        p = f["properties"]
        if p["name"] and p["class"] != "rail" and f["geometry"].intersects(aoi):
            by_name.setdefault(p["name"], []).append(f)
    out, used = [], set()
    for name in sorted(by_name):
        feats = by_name[name]
        merged = shapely.line_merge(shapely.union_all([f["geometry"] for f in feats])).intersection(aoi)
        if merged.is_empty or merged.length == 0:
            continue
        anchor = nearest_points(merged, merged.centroid)[0]
        longest = max(feats, key=lambda f: (f["geometry"].intersection(aoi).length, f["properties"]["id"]))
        way_id = longest["properties"]["id"].removeprefix("osm-way-").split("-")[0]
        pid = "street-" + slug(name)
        while pid in used:
            pid += "-2"
        used.add(pid)
        lon, lat = TO_GEO.transform(anchor.x, anchor.y)
        b = merged.bounds
        out.append({"id": pid, "name": name, "kind": "street", "lat": round(lat, 7), "lon": round(lon, 7),
                    "E": round(anchor.x, 2), "N": round(anchor.y, 2), "H": round(terrain_at(anchor.x, anchor.y), 2),
                    "worldBounds": [round(v, 2) for v in b], "source": {"dataset": "osm", "ref": f"way/{way_id}"}})
    return out
