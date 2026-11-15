"""Build the scene directory (docs/contracts/scene.md) for one city.

uv run --project pipeline python -m geospatial.build_scene --city cities/villena/city.json \
    --out build/villena/scene [--data-root .] [--terrain-fallback] \
    [--report cities/villena/scene-report.md] [--preview cities/villena/scene-preview.png]
"""

import argparse
import hashlib
import json
import math
import shutil
import sys
import time
import warnings
from pathlib import Path

import jsonschema
import numpy as np
import rasterio
from numpy.lib.stride_tricks import sliding_window_view
from pyproj import Transformer
from rasterio.features import geometry_mask, rasterize
from rasterio.fill import fillnodata
from rasterio.warp import Resampling
from shapely.geometry import LineString, Point, Polygon, box

from . import buildings, osm
from .inputs import ROLES, City, Grid, PipelineError, load_city, read_raster

SCHEMAS = Path(__file__).resolve().parents[2] / "packages" / "geo-contracts" / "schemas"
TO_WORLD = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
CANOPY_MIN, CANOPY_WINDOW, TREE_SPACING, BUILDING_BUFFER = 2.5, 7, 3.0, 1.5  # m; cells (3 m at 0.5 m); m; m
STRUCTURE_KINDS = {"landmark", "church", "civic", "museum"}


def _json(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def _coords(geom) -> list:
    def r(seq):
        return [[round(x, 2), round(y, 2)] for x, y, *_ in seq]
    if isinstance(geom, Polygon):
        return [r(geom.exterior.coords), *[r(i.coords) for i in geom.interiors]]
    if isinstance(geom, LineString):
        return r(geom.coords)
    return r([(geom.x, geom.y)])[0]


def feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": f["geometry"].geom_type, "coordinates": _coords(f["geometry"])},
         "properties": f["properties"]} for f in sorted(features, key=lambda f: f["properties"]["id"])]}


def terrain_grid(city: City, clip_bounds, fallback: bool) -> tuple[Grid, np.ndarray, dict]:
    grid = Grid.covering(clip_bounds, 1.0)
    role = ROLES["terrain_fallback" if fallback else "terrain"]
    path, _ = city.input(role)
    arr, info = read_raster(path, grid, Resampling.bilinear if fallback else Resampling.average,
                            city.datasets[role]["crs"])
    holes = int(np.isnan(arr).sum())
    if holes:
        arr = fillnodata(np.nan_to_num(arr), mask=(~np.isnan(arr)).astype("uint8"), max_search_distance=200)
    if not np.isfinite(arr).all():
        raise PipelineError("terrain still has gaps after filling")
    info["filledCells"] = holes
    return grid, np.round(arr, 3).astype("float32"), info


def surface_model(city: City, clip_bounds) -> tuple[buildings.Surface, dict]:
    grid = Grid.covering(clip_bounds, 0.5)
    mdt, mdt_info = read_raster(city.input(ROLES["terrain"])[0], grid, Resampling.bilinear,
                                city.datasets[ROLES["terrain"]]["crs"])
    mds, mds_info = read_raster(city.input(ROLES["surface"])[0], grid, Resampling.bilinear,
                                city.datasets[ROLES["surface"]]["crs"])
    same_grid = mdt_info["resolution"] == mds_info["resolution"] and \
        mdt_info["alignedWithGrid"] == mds_info["alignedWithGrid"]
    return buildings.Surface.build(grid, mdt, mds), {"mdtAligned": mdt_info["alignedWithGrid"],
                                                     "mdsAligned": mds_info["alignedWithGrid"],
                                                     "sameResolution": same_grid}


def detect_trees(surface: buildings.Surface, parts: list[buildings.Part], mapped: list[dict]) -> list[dict]:
    """Canopy peaks of the normalised surface model outside buildings and structures."""
    g = surface.grid
    nd = np.nan_to_num(surface.ndsm, nan=-1.0)
    blocked = ~geometry_mask([p.geom.buffer(BUILDING_BUFFER) for p in parts], (g.height, g.width), g.transform) \
        if parts else np.zeros(nd.shape, bool)
    half = CANOPY_WINDOW // 2
    local_max = sliding_window_view(np.pad(nd, half, constant_values=-1.0), (CANOPY_WINDOW, CANOPY_WINDOW)).max(
        axis=(2, 3))
    rows, cols = np.nonzero((nd >= CANOPY_MIN) & ~blocked & (nd == local_max))
    order = sorted(zip(-nd[rows, cols], rows, cols, strict=True))
    taken = [(f["geometry"].x, f["geometry"].y) for f in mapped]
    cell: dict[tuple[int, int], list] = {}
    for x, y in taken:
        cell.setdefault((int(x // TREE_SPACING), int(y // TREE_SPACING)), []).append((x, y))
    out = []
    for neg_h, r, c in order:
        x, y = g.west + (c + 0.5) * g.cell, g.north - (r + 0.5) * g.cell
        kx, ky = int(x // TREE_SPACING), int(y // TREE_SPACING)
        near = [q for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in cell.get((kx + dx, ky + dy), [])]
        if any(math.hypot(x - qx, y - qy) < TREE_SPACING for qx, qy in near):
            continue
        cell.setdefault((kx, ky), []).append((x, y))
        h = float(-neg_h)
        out.append({"geometry": Point(x, y), "properties": {
            "id": f"dsm-{round(x * 10)}-{round(y * 10)}", "heightM": round(h, 2),
            "crownRadiusM": round(min(max(0.35 * h, 1.0), 6.0), 2), "source": "surface-model"}})
    return out


def selected_pois(city: City, aoi_bounds) -> list[dict]:
    path = city.dir / "poi-selection.json"
    if not path.is_file():
        raise PipelineError(f"{path} missing (produced by WP01)")
    aoi = box(*aoi_bounds)
    out = []
    for p in json.loads(path.read_text()):
        e, n = TO_WORLD.transform(p["lon"], p["lat"])
        if not aoi.contains(Point(e, n)):
            raise PipelineError(f"POI {p['id']} ({p['lat']}, {p['lon']}) is outside the AOI")
        poi = {k: p[k] for k in ("id", "name", "kind", "lat", "lon", "source")}
        if p.get("altNames"):
            poi["altNames"] = p["altNames"]
        out.append(poi | {"E": round(e, 2), "N": round(n, 2)})
    return out


def check_schema(name: str, doc: dict) -> None:
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    errors = [f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
              for e in jsonschema.Draft202012Validator(schema).iter_errors(doc)]
    if errors:
        raise PipelineError(f"output does not validate against {name}: " + "; ".join(errors[:5]))


def validate(layers: dict[str, list[dict]], pois: list[dict], clip_bounds, aoi_bounds, terrain: np.ndarray) -> None:
    lo = box(*clip_bounds).buffer(0.011, join_style="mitre")
    for name, feats in layers.items():
        ids = [f["properties"]["id"] for f in feats]
        if len(ids) != len(set(ids)):
            raise PipelineError(f"duplicate ids in {name}")
        for f in feats:
            g = f["geometry"]
            if not lo.contains(g):
                raise PipelineError(f"{name} {f['properties']['id']} lies outside the clip rectangle")
            if isinstance(g, Polygon) and not Polygon(*[_coords(g)[0], _coords(g)[1:]]).is_valid:
                raise PipelineError(f"{name} {f['properties']['id']} is invalid after rounding")
    for f in layers["buildings"] + layers.get("structures", []):
        h, ridge = f["properties"]["heightM"], f["properties"].get("ridgeHeightM")
        if not 0 < h <= 80 or (ridge is not None and not h < ridge <= 80):
            raise PipelineError(f"{f['properties']['id']} has heightM {h}, ridgeHeightM {ridge}")
    if not np.isfinite(terrain).all():
        raise PipelineError("terrain contains NaN")
    aoi = box(*aoi_bounds)
    for p in pois:
        if not aoi.covers(Point(p["E"], p["N"])):
            raise PipelineError(f"POI {p['id']} is outside the AOI")


def build(city: City, out: Path, fallback: bool) -> dict:
    t0 = time.time()
    cfg = city.config
    aoi_bounds = tuple(cfg["aoi"]["bounds"])
    m = cfg["aoi"]["marginM"]
    clip_bounds = (aoi_bounds[0] - m, aoi_bounds[1] - m, aoi_bounds[2] + m, aoi_bounds[3] + m)
    if not fallback and not (city.has_file(ROLES["terrain"]) and city.has_file(ROLES["surface"])):
        raise PipelineError("IGN MDT50cm/MDS50cm not present; follow cities/<city>/ACQUISITION.md, "
                            "or run with --terrain-fallback for a lower-quality scene")
    used = {ROLES["buildings"], ROLES["osm"], ROLES["terrain_fallback" if fallback else "terrain"]}
    if not fallback:
        used.add(ROLES["surface"])
    provenance = [{"datasetId": d, "sha256": city.input(d)[1]} for d in sorted(used)]

    tgrid, terrain, tinfo = terrain_grid(city, clip_bounds, fallback)
    surface, sinfo = (None, {}) if fallback else surface_model(city, clip_bounds)
    pois = selected_pois(city, aoi_bounds)
    parts, bcounts = buildings.build(city.input(ROLES["buildings"])[0], clip_bounds, tgrid, terrain, surface, pois)
    elements = osm.load(city.input(ROLES["osm"])[0])
    road_feats, rcounts = osm.roads(elements, clip_bounds)
    lc_feats, lcounts = osm.landcover(elements, clip_bounds)
    structs, scounts = buildings.build_structures(osm.structures(elements, clip_bounds, pois), parts, clip_bounds,
                                                  tgrid, terrain, surface, pois)
    solids = parts + structs
    trees = osm.mapped_trees(elements, clip_bounds)
    if surface is not None:
        trees += detect_trees(surface, solids, trees)

    for p in pois:
        hit = next((b for b in solids if b.geom.covers(Point(p["E"], p["N"]))), None) \
            if p["kind"] in STRUCTURE_KINDS else None
        p["H"] = round(hit.base_h + hit.height if hit else tgrid.bilinear(terrain, p["E"], p["N"]), 2)
    pois += osm.street_pois(road_feats, aoi_bounds, lambda e, n: tgrid.bilinear(terrain, e, n))
    pois.sort(key=lambda p: p["id"])
    if len({p["id"] for p in pois}) != len(pois):
        raise PipelineError("duplicate POI ids (selected POI id collides with a street POI?)")

    layers = {"buildings": [{"geometry": p.geom, "properties": p.properties()} for p in parts],
              "roads": road_feats, "landcover": lc_feats, "trees": trees}
    if structs:  # optional layer: written only when there is something in it
        layers["structures"] = [{"geometry": p.geom, "properties": p.properties()} for p in structs]
    validate(layers, pois, clip_bounds, aoi_bounds, terrain)
    pois_doc = {"schemaVersion": "1.0", "cityId": cfg["id"], "pois": pois}
    check_schema("scene-pois", pois_doc)

    h0 = cfg["origin"]["H0"]
    tops = [p.top for p in solids]
    tops += [tgrid.bilinear(terrain, t["geometry"].x, t["geometry"].y) + t["properties"]["heightM"] for t in trees]
    z_range = {"zMin": math.floor(float(terrain.min()) - 1 - h0),
               "zMax": math.ceil(max([float(terrain.max())] + tops) + 1 - h0)}

    if out.exists():
        if any(out.iterdir()) and not (out / "scene.json").exists():
            raise PipelineError(f"{out} is not empty and is not a scene directory; refusing to overwrite")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = {"terrain.f32": terrain.astype("<f4").tobytes(),
             "pois.json": _json(pois_doc)}
    for name, feats in layers.items():
        files[f"{name}.geojson"] = _json(feature_collection(feats))
    for name, data in files.items():
        (out / name).write_bytes(data)

    def sha(name):
        return hashlib.sha256(files[name]).hexdigest()

    manifest = {
        "schemaVersion": "1.0", "cityId": cfg["id"], "crs": cfg["crs"], "aoi": cfg["aoi"], "origin": cfg["origin"],
        "zRange": z_range,
        "terrain": {"path": "terrain.f32", "width": tgrid.width, "height": tgrid.height, "cellSize": tgrid.cell,
                    "westE": tgrid.west, "northN": tgrid.north, "dtype": "float32-le", "unit": "m",
                    "sha256": sha("terrain.f32")},
        "layers": {n: {"path": f"{n}.geojson", "count": len(f), "sha256": sha(f"{n}.geojson")}
                   for n, f in layers.items()},
        "pois": {"path": "pois.json", "count": len(pois), "sha256": sha("pois.json")},
        "provenance": provenance,
    }
    check_schema("scene-manifest", manifest)
    (out / "scene.json").write_bytes(_json(manifest))

    sources: dict[str, int] = {}
    roofs: dict[str, int] = {}
    for p in parts:
        sources[p.height_source] = sources.get(p.height_source, 0) + 1
        roofs[p.roof] = roofs.get(p.roof, 0) + 1
    disagreements = sorted(
        ((p.height - (p.floors * buildings.METRES_PER_FLOOR + buildings.FLOOR_OFFSET), p.id, p.floors, p.height)
         for p in parts if p.height_source == "surface-model" and p.floors), key=lambda t: (-abs(t[0]), t[1]))[:30]
    return {"mode": "fallback" if fallback else "full", "seconds": round(time.time() - t0, 1),
            "provenance": provenance, "terrain": tinfo | {"min": float(terrain.min()), "max": float(terrain.max())},
            "surface": sinfo, "buildings": bcounts, "heightSources": sources, "roofs": roofs,
            "disagreements": disagreements, "roads": rcounts | {"features": len(road_feats)},
            "landcover": lcounts | {"features": len(lc_feats)}, "structures": scounts,
            "trees": {s: sum(t["properties"]["source"] == s for t in trees) for s in ("mapped", "surface-model")},
            "pois": len(pois), "zRange": z_range, "imageSize": image_size(cfg, z_range),
            "landmarks": {p.id: (p.landmark, round(p.base_h, 2), round(p.height, 2), p.height_source)
                          for p in solids if p.landmark}}


def image_size(cfg: dict, z_range: dict) -> list[int]:
    """Master-image size per docs/contracts/projection.md section 3."""
    cam = cfg["camera"]
    a, f, s = math.radians(cam["headingDeg"]), math.radians(cam["pitchDeg"]), cam["pixelsPerMetre"]
    x0, y0, x1, y1 = cfg["aoi"]["bounds"]
    w, h = x1 - x0, y1 - y0
    us, vs = [], []
    for x in (0.0, w):
        for y in (0.0, h):
            for z in (z_range["zMin"], z_range["zMax"]):
                us.append(s * (x * math.cos(a) - y * math.sin(a)))
                vs.append(-s * ((x * math.sin(a) + y * math.cos(a)) * math.sin(f) + z * math.cos(f)))
    return [math.ceil(max(us)) - math.floor(min(us)), math.ceil(max(vs)) - math.floor(min(vs))]


def write_report(stats: dict, path: Path) -> None:
    lines = [f"# Scene report — {stats['mode']} mode", "",
             "Generated by `geospatial.build_scene`. Regenerate rather than edit.", "",
             "| Item | Value |", "|---|---|"]
    for k in ("mode", "seconds", "heightSources", "roofs", "buildings", "structures", "roads", "landcover", "trees",
              "pois",
              "zRange", "imageSize", "terrain", "surface"):
        lines.append(f"| {k} | `{json.dumps(stats[k], sort_keys=True)}` |")
    lines += ["", "## Inputs", "", "| Dataset | sha256 |", "|---|---|"]
    lines += [f"| {p['datasetId']} | `{p['sha256']}` |" for p in stats["provenance"]]
    lines += ["", "## Landmark parts", "", "| Part | Landmark | baseH | heightM | Source |", "|---|---|---|---|---|"]
    lines += [f"| {k} | {v[0]} | {v[1]} | {v[2]} | {v[3]} |" for k, v in sorted(stats["landmarks"].items())]
    lines += ["", "## Largest disagreements: surface-model height vs floors estimate", "",
              "| Part | Floors | heightM | Difference |", "|---|---|---|---|"]
    lines += [f"| {pid} | {fl} | {h:.2f} | {d:+.2f} |" for d, pid, fl, h in stats["disagreements"]]
    path.write_text("\n".join(lines) + "\n")


def write_preview(scene: Path, path: Path, cell: float = 2.0) -> None:
    """Top-down sanity image: hill-shaded terrain, buildings coloured by height (yellow low, red high)."""
    m = json.loads((scene / "scene.json").read_text())
    t = m["terrain"]
    terrain = np.frombuffer((scene / "terrain.f32").read_bytes(), "<f4").reshape(t["height"], t["width"])
    step = max(int(cell / t["cellSize"]), 1)
    z = terrain[::step, ::step]
    gy, gx = np.gradient(z, cell)
    shade = np.clip(0.75 + (gx - gy) * 1.5, 0.35, 1.0)
    rgb = np.stack([shade * 205, shade * 195, shade * 170]).astype("float32")
    grid = Grid(t["westE"], t["northN"], cell, z.shape[1], z.shape[0])
    feats = json.loads((scene / "buildings.geojson").read_text())["features"]
    if (scene / "structures.geojson").exists():
        feats += json.loads((scene / "structures.geojson").read_text())["features"]
    if feats:
        hs = rasterize(((f["geometry"], f["properties"]["heightM"]) for f in feats), out_shape=z.shape,
                       transform=grid.transform, fill=0, dtype="float32")
        k = np.clip(hs / 25.0, 0, 1)
        on = hs > 0
        for band, (low, high) in enumerate(((250, 200), (220, 40), (120, 30))):
            rgb[band][on] = low + (high - low) * k[on]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", rasterio.errors.NotGeoreferencedWarning)
        with rasterio.open(path, "w", driver="PNG", width=z.shape[1], height=z.shape[0], count=3,
                           dtype="uint8") as dst:
            dst.write(np.clip(rgb, 0, 255).astype("uint8"))
    aux = path.with_name(path.name + ".aux.xml")
    if aux.exists():
        aux.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--city", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, default=Path("."),
                    help="directory that dataset localPath values are relative to (default: current directory)")
    ap.add_argument("--terrain-fallback", action="store_true", help="MDT05 terrain, no surface model")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args(argv)
    try:
        stats = build(load_city(args.city, args.data_root), args.out, args.terrain_fallback)
    except PipelineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.report:
        write_report(stats, args.report)
    if args.preview:
        write_preview(args.out, args.preview)
    print(json.dumps({k: stats[k] for k in ("mode", "seconds", "heightSources", "zRange", "imageSize")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
