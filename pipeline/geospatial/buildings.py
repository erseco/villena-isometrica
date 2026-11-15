"""Catastro BuildingPart footprints -> scene building parts with honest height estimates.

Thresholds and heuristics are documented in pipeline/geospatial/README.md; change them there too.
"""

import math
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyogrio
import shapely
from rasterio.features import shapes
from shapely.geometry import Polygon, box, shape
from shapely.geometry.polygon import orient

from .inputs import Grid, PipelineError

pyogrio.set_gdal_config_options({"GML_DOWNLOAD_SCHEMA": "NO"})

METRES_PER_FLOOR, FLOOR_OFFSET, DEFAULT_HEIGHT = 3.0, 1.0, 3.0
SHRINK_HEIGHT, SHRINK_SLOPE = 0.75, 1.25  # m, inward buffer before sampling the surface model
MIN_SAMPLES, MIN_MEASURED = 20, 2.0  # samples; m of normalised height for a measurement to count
FLAT_SLOPE, PITCHED_SLOPE = 0.06, 0.15  # median roof gradient (m/m)
ZONE_AREA, ZONE_SPREAD, ZONE_STEP = 300.0, 4.0, 3.0  # m2; m (p90-p10 of nDSM); m bins
ZONE_MIN_AREA, ZONE_MIN_HEIGHT = 9.0, 1.5  # m2; m (median nDSM below this = open ground)
MIN_PART_AREA = 1.0
ROOF_ALLOWANCE = 6.0  # m a procedural roof may add when no ridge was measured
RIDGE_MIN_RISE = 0.3
STRUCTURE_MIN_SHARE, STRUCTURE_MIN_AREA = 0.25, 4.0  # share of an OSM outline not in Catastro; m2 per piece
USE = {"1_residential": "residential", "2_agriculture": "agricultural", "3_industrial": "industrial",
       "4_1_office": "commercial", "4_2_retail": "commercial", "4_3_publicServices": "civic"}
LANDMARK_KINDS = {"landmark", "church", "civic", "museum"}
LANDMARK_SNAP = 25.0  # m; Villena's castle node is 15.6 m from the only Catastro part (the keep)
FORTIFICATION = re.compile(r"castillo|torre|muralla|alcazaba", re.IGNORECASE)


@dataclass
class Surface:
    """IGN surface and terrain models on a common 0.5 m grid (full mode only)."""

    grid: Grid
    mds: np.ndarray
    ndsm: np.ndarray
    slope: np.ndarray

    @classmethod
    def build(cls, grid: Grid, mdt: np.ndarray, mds: np.ndarray) -> "Surface":
        k = np.ones((3, 3)) / 9.0
        padded = np.pad(mds, 1, mode="edge")
        smooth = sum(padded[i:i + mds.shape[0], j:j + mds.shape[1]] * k[i, j] for i in range(3) for j in range(3))
        gy, gx = np.gradient(smooth, grid.cell)
        return cls(grid, mds, mds - mdt, np.hypot(gx, gy).astype("float32"))


@dataclass
class Part:
    id: str
    building_id: str
    geom: Polygon
    floors: int | None
    use: str
    base_h: float = 0.0
    height: float = 0.0
    height_source: str = "default"
    roof: str = "unknown"
    roof_source: str = "none"
    landmark: str | None = None
    ridge: float | None = None  # highest point of a measured pitched roof above base_h
    zoned: bool = False
    stats: dict = field(default_factory=dict)

    def properties(self) -> dict:
        props = {"id": self.id, "buildingId": self.building_id, "baseH": round(self.base_h, 2),
                 "heightM": round(self.height, 2), "heightSource": self.height_source, "floors": self.floors,
                 "roof": self.roof, "roofSource": self.roof_source, "use": self.use, "landmark": self.landmark}
        if self.ridge is not None:
            props["ridgeHeightM"] = round(self.ridge, 2)
        return props

    @property
    def top(self) -> float:
        """Highest elevation the renderer may draw for this part (docs/contracts/scene.md, zRange)."""
        return self.base_h + (self.ridge if self.ridge is not None else self.height + ROOF_ALLOWANCE)


def samples(grid: Grid, arr: np.ndarray, geom) -> np.ndarray:
    """Values of arr at cell centres inside geom, NaN dropped."""
    if geom.is_empty:
        return np.empty(0, dtype=arr.dtype)
    r0, r1, c0, c1 = grid.window(geom.bounds)
    if r0 >= r1 or c0 >= c1:
        return np.empty(0, dtype=arr.dtype)
    xs, ys = grid.centres(r0, r1, c0, c1)
    vals = arr[r0:r1, c0:c1][shapely.contains_xy(geom, xs, ys)]
    return vals[~np.isnan(vals)]


def clean(geom, clip: Polygon) -> list[Polygon]:
    """Valid, clipped, single-part polygons at 0.01 m precision with CCW exterior rings."""
    geom = shapely.make_valid(geom).intersection(clip)
    out = []
    for g in shapely.get_parts(shapely.set_precision(geom, 0.01)):
        if isinstance(g, Polygon) and g.area >= MIN_PART_AREA:
            out.append(orient(g, 1.0))
    return sorted(out, key=lambda p: (round(p.bounds[0], 2), round(p.bounds[1], 2)))


def read_catastro(zip_path: Path, clip: Polygon) -> tuple[list[Part], dict]:
    names = zipfile.ZipFile(zip_path).namelist()

    def member(suffix: str) -> str:
        found = [n for n in names if n.endswith(suffix)]
        if len(found) != 1:
            raise PipelineError(f"{zip_path}: expected one *{suffix}, found {found}")
        return f"/vsizip/{zip_path}/{found[0]}"

    bbox = clip.bounds
    parts_df = pyogrio.read_dataframe(member(".buildingpart.gml"), bbox=bbox,
                                      columns=["localId", "numberOfFloorsAboveGround", "numberOfFloorsBelowGround"])
    bld_df = pyogrio.read_dataframe(member(".building.gml"), bbox=bbox, columns=["localId", "currentUse"],
                                    read_geometry=False)
    if parts_df.crs is None or parts_df.crs.to_epsg() != 25830:
        raise PipelineError(f"{zip_path}: BuildingPart CRS is {parts_df.crs}, expected EPSG:25830")
    use_by_ref = {r: u for r, u in zip(bld_df["localId"], bld_df["currentUse"], strict=True)}

    def intval(v):
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else int(v)

    parts, counts = [], {"read": len(parts_df), "underground": 0, "zeroFloors": 0, "tooSmall": 0}
    for local_id, above, below, geom in sorted(zip(parts_df["localId"], parts_df["numberOfFloorsAboveGround"],
                                                   parts_df["numberOfFloorsBelowGround"], parts_df.geometry,
                                                   strict=True), key=lambda t: t[0]):
        above, below = intval(above), intval(below)
        if above == 0 and (below or 0) > 0:
            counts["underground"] += 1
            continue
        pieces = clean(geom, clip)
        if not pieces:
            counts["tooSmall"] += 1
            continue
        ref = local_id.split("_part")[0]
        use = USE.get(use_by_ref.get(ref) or "", "other")
        for i, g in enumerate(pieces, 1):
            pid = local_id if len(pieces) == 1 else f"{local_id}-{i}"
            parts.append(Part(pid, ref, g, above, use))
    return parts, counts


def classify_roof(slopes: np.ndarray) -> str:
    if len(slopes) < MIN_SAMPLES:
        return "unknown"
    med = float(np.median(slopes))
    return "flat" if med < FLAT_SLOPE else "pitched" if med > PITCHED_SLOPE else "unknown"


def set_roof_heights(part: Part, mds: np.ndarray) -> None:
    """Wall top (eaves for pitched roofs) and, for pitched roofs, the measured ridge."""
    part.height = float(np.percentile(mds, 5 if part.roof == "pitched" else 80)) - part.base_h
    if part.roof == "pitched":
        ridge = float(np.percentile(mds, 95)) - part.base_h
        part.ridge = ridge if ridge - part.height >= RIDGE_MIN_RISE else None


def measure(part: Part, terrain_grid: Grid, terrain: np.ndarray, surface: Surface | None,
            thin: bool = False) -> None:
    """Fill base_h, height, sources and roof of one part. `thin`: sample unshrunk when shrinking leaves too little
    (walls narrower than the usual inward buffer)."""
    ground = samples(terrain_grid, terrain, part.geom)
    rep = part.geom.representative_point()
    part.base_h = float(ground.min()) if len(ground) else terrain_grid.bilinear(terrain, rep.x, rep.y)
    if surface is not None:
        inner = part.geom.buffer(-SHRINK_HEIGHT)
        mds = samples(surface.grid, surface.mds, inner)
        if thin and len(mds) < MIN_SAMPLES:
            inner = part.geom
            mds = samples(surface.grid, surface.mds, inner)
        ndsm = samples(surface.grid, surface.ndsm, inner)
        part.stats = {"samples": len(mds)}
        if len(mds) >= MIN_SAMPLES and len(ndsm) >= MIN_SAMPLES and np.percentile(ndsm, 80) >= MIN_MEASURED:
            part.roof = classify_roof(samples(surface.grid, surface.slope, part.geom.buffer(-SHRINK_SLOPE)))
            part.roof_source = "none" if part.roof == "unknown" else "surface-model"
            set_roof_heights(part, mds)
            part.height_source = "surface-model"
            part.stats["spread"] = float(np.percentile(ndsm, 90) - np.percentile(ndsm, 10))
            if part.height > 0:
                return
    if part.floors is not None and part.floors >= 1:
        part.height, part.height_source = part.floors * METRES_PER_FLOOR + FLOOR_OFFSET, "floors"
    else:
        part.height, part.height_source = DEFAULT_HEIGHT, "default"
    part.roof, part.roof_source, part.ridge = "unknown", "none", None


def zone(part: Part, terrain_grid: Grid, terrain: np.ndarray, surface: Surface) -> list[Part]:
    """Split a part into zones of similar measured height. Returns [] if zoning finds nothing usable."""
    g = surface.grid
    r0, r1, c0, c1 = g.window(part.geom.bounds)
    xs, ys = g.centres(r0, r1, c0, c1)
    inside = shapely.contains_xy(part.geom, xs, ys)
    mds = surface.mds[r0:r1, c0:c1]
    valid = inside & ~np.isnan(mds)
    if valid.sum() < MIN_SAMPLES:
        return []
    bins = np.where(valid, np.floor(np.nan_to_num(mds) / ZONE_STEP), -1).astype("int32")
    transform = g.transform @ g.transform.translation(c0, r0)
    polys = []
    for geom, value in shapes(bins, mask=valid, transform=transform):
        if value < 0:
            continue
        poly = shape(geom).simplify(g.cell, preserve_topology=True)
        for piece in clean(poly, part.geom):
            if piece.area >= ZONE_MIN_AREA:
                polys.append(piece)
    zones = []
    for poly in sorted(polys, key=lambda p: (round(p.bounds[0], 2), round(p.bounds[1], 2), round(p.area, 2))):
        ndsm = samples(g, surface.ndsm, poly)
        mds_z = samples(g, surface.mds, poly)
        if len(mds_z) < 4 or float(np.median(ndsm)) < ZONE_MIN_HEIGHT:
            continue
        z = Part("", part.building_id, poly, None, part.use, landmark=part.landmark, zoned=True)
        ground = samples(terrain_grid, terrain, poly)
        rep = poly.representative_point()
        z.base_h = float(ground.min()) if len(ground) else terrain_grid.bilinear(terrain, rep.x, rep.y)
        inner = poly.buffer(-SHRINK_SLOPE)
        z.roof = classify_roof(samples(g, surface.slope, inner)) if not inner.is_empty else "unknown"
        z.roof_source = "none" if z.roof == "unknown" else "surface-model"
        set_roof_heights(z, mds_z)
        z.height_source = "surface-model"
        if z.height > 0:
            zones.append(z)
    for i, z in enumerate(zones, 1):
        z.id = f"{part.id}_z{i}"
    return zones


def tag_landmarks(parts: list[Part], pois: list[dict]) -> None:
    """A landmark POI tags the part containing it (else the nearest within LANDMARK_SNAP) and the other parts
    of that building."""
    for poi in sorted(pois, key=lambda p: p["id"]):
        if poi["kind"] not in LANDMARK_KINDS:
            continue
        pt = shapely.Point(poi["E"], poi["N"])
        hit = next((p for p in parts if p.geom.contains(pt)), None)
        if hit is None:
            near = sorted((p.geom.distance(pt), p.id, p) for p in parts if p.geom.distance(pt) <= LANDMARK_SNAP)
            hit = near[0][2] if near else None
        if hit is None:
            continue
        for p in parts:
            if p.building_id == hit.building_id:
                p.landmark = poi["id"]
                if poi["kind"] == "church":
                    p.use = "religious"
                elif poi["kind"] in ("civic", "museum"):
                    p.use = "civic"
                elif FORTIFICATION.search(poi["name"]):
                    p.use = "fortification"


def needs_zoning(part: Part) -> bool:
    return part.height_source == "surface-model" and (
        part.landmark is not None or (part.geom.area > ZONE_AREA and part.stats.get("spread", 0.0) > ZONE_SPREAD))


def build(zip_path: Path, clip_bounds, terrain_grid: Grid, terrain: np.ndarray, surface: Surface | None,
          pois: list[dict]) -> tuple[list[Part], dict]:
    clip = box(*clip_bounds)
    parts, counts = read_catastro(zip_path, clip)
    for p in parts:
        measure(p, terrain_grid, terrain, surface)
    tag_landmarks(parts, pois)
    kept, counts["zeroFloorsDropped"], counts["zonedParts"] = [], 0, 0
    for p in parts:
        if p.floors == 0 and p.height_source != "surface-model":
            counts["zeroFloorsDropped"] += 1  # Catastro: nothing built above ground, and nothing measured
            continue
        if surface is not None and needs_zoning(p):
            zones = zone(p, terrain_grid, terrain, surface)
            if zones:
                counts["zonedParts"] += 1
                kept.extend(zones)
                continue
        kept.append(p)
    counts["kept"] = len(kept)
    return kept, counts


def build_structures(found: list[dict], parts: list[Part], clip_bounds, terrain_grid: Grid, terrain: np.ndarray,
                     surface: Surface | None, pois: list[dict]) -> tuple[list[Part], dict]:
    """OSM landmark structures (osm.structures) -> parts, minus what Catastro already covers.

    With a surface model a structure is kept only where the model measures it (>= MIN_MEASURED): an OSM outline
    says where a wall is, not that it still stands or how tall it is. Without one it gets the labelled default.
    """
    clip = box(*clip_bounds)
    taken = shapely.union_all([p.geom for p in parts]) if parts else Polygon()  # Catastro, then earlier structures
    names = {p["id"]: p["name"] for p in pois}
    kept, counts = [], {"found": len(found), "alreadyCovered": 0, "unmeasuredDropped": 0, "zoned": 0}
    for s in sorted(found, key=lambda s: s["id"]):
        rest = s["geometry"].difference(taken)
        if rest.area < STRUCTURE_MIN_SHARE * s["geometry"].area:
            counts["alreadyCovered"] += 1  # Catastro models this building; what is left are digitising slivers
            continue
        pieces = [g for g in clean(rest, clip) if g.area >= STRUCTURE_MIN_AREA]
        taken = taken.union(s["geometry"])
        for i, g in enumerate(pieces, 1):
            fortified = s["id"].startswith("osm-way-") and s["landmark"] is None or \
                FORTIFICATION.search(names.get(s["landmark"], "") + " " + (s["name"] or "")) is not None
            p = Part(s["id"] if len(pieces) == 1 else f"{s['id']}-{i}", s["id"], g, None,
                     "fortification" if fortified else "other", landmark=s["landmark"])
            measure(p, terrain_grid, terrain, surface, thin=True)
            if surface is not None and p.height_source != "surface-model":
                counts["unmeasuredDropped"] += 1
                continue
            zones = zone(p, terrain_grid, terrain, surface) if surface is not None and needs_zoning(p) else []
            counts["zoned"] += bool(zones)
            kept.extend(zones or [p])
    counts["kept"] = len(kept)
    return kept, counts
