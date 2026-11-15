"""Cut a render directory into the published tile set (docs/contracts/render.md section 2).

PYTHONPATH=pipeline uv run --project pipeline python -m export.build --render <dir> --scene <dir> --city <city.json>
    --out <dir> --release <string> [--style-id procedural] [--style-label Procedural] [--kernel mode|mean]
"""

import argparse
import hashlib
import io
import json
import math
import shutil
import sys
from pathlib import Path

import jsonschema
import numpy as np
from PIL import Image
from pyproj import Transformer

SCHEMAS = Path(__file__).resolve().parents[2] / "packages" / "geo-contracts" / "schemas"
PNG_ZLIB_LEVEL = 9
WEBP_METHOD = 6
HEIGHT_CELL_M = 4.0
HEIGHT_SCALE = 0.01
KERNELS = ("mode", "mean")
DEFAULT_KERNEL = "mode"  # docs/research/07-tile-encoding-benchmark.md


class ExportError(Exception):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, schema: str) -> dict:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise ExportError(f"{path}: {e}") from e
    check_doc(doc, schema, str(path))
    return doc


def check_doc(doc: dict, schema: str, what: str) -> None:
    validator = jsonschema.Draft202012Validator(json.loads((SCHEMAS / f"{schema}.schema.json").read_text()))
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in validator.iter_errors(doc)]
    if errors:
        raise ExportError(f"{what} does not validate against {schema}: " + "; ".join(errors[:5]))


def decode_layer(path: Path, encoding: str) -> np.ndarray:
    """Decoded samples of a render layer; .tobytes() is what pixelSha256 is computed over (render.md section 1)."""
    with Image.open(path) as im:
        if encoding == "rgba8-png":
            return np.asarray(im.convert("RGBA"))
        if encoding == "index8-png":
            if im.mode not in ("P", "L"):
                raise ExportError(f"{path}: index8 layer has mode {im.mode}")
            return np.asarray(im)
        if encoding == "rgb24-id-png":
            return np.asarray(im.convert("RGB"))
        if encoding == "gray16-png":
            return np.asarray(im).astype(">u2")
    raise ExportError(f"{path}: unknown encoding {encoding}")


def hex_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def pack_rgb(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.uint32)
    return (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def load_render(render_dir: Path, scene_dir: Path) -> tuple[dict, dict, np.ndarray]:
    """Validate render + scene and return (render manifest, scene manifest, flattened opaque RGB master image)."""
    render = load_json(render_dir / "render.json", "render-manifest")
    scene = load_json(scene_dir / "scene.json", "scene-manifest")
    if render["sceneSha256"] != sha256(scene_dir / "scene.json"):
        raise ExportError(f"{render_dir / 'render.json'}: sceneSha256 does not match {scene_dir / 'scene.json'}")
    if render["cityId"] != scene["cityId"]:
        raise ExportError(f"render cityId {render['cityId']} != scene cityId {scene['cityId']}")
    palette_path = render_dir / render["palette"]["path"]
    if sha256(palette_path) != render["palette"]["sha256"]:
        raise ExportError(f"{palette_path}: sha256 does not match render.json")
    palette = load_json(palette_path, "palette")
    width, height = render["image"]["width"], render["image"]["height"]
    color = None
    for layer in render["layers"]:
        path = render_dir / layer["path"]
        if not path.is_file():
            raise ExportError(f"{path}: layer file missing")
        if sha256(path) != layer["sha256"]:
            raise ExportError(f"{path}: sha256 does not match render.json")
        pixels = decode_layer(path, layer["encoding"])
        if pixels.shape[:2] != (height, width):
            raise ExportError(f"{path}: {pixels.shape[1]}x{pixels.shape[0]} px, render.json says {width}x{height}")
        if hashlib.sha256(pixels.tobytes()).hexdigest() != layer["pixelSha256"]:
            raise ExportError(f"{path}: pixelSha256 does not match render.json")
        if layer["name"] == "color":
            color = pixels
    if color is None:
        raise ExportError(f"{render_dir / 'render.json'}: no color layer")
    alpha = color[..., 3]
    if not np.isin(alpha, (0, 255)).all():
        raise ExportError(f"{render_dir}: color layer has alpha other than 0 and 255")
    drawn = alpha == 255
    allowed = pack_rgb(np.array([hex_rgb(c["hex"]) for c in palette["colors"]], dtype=np.uint8))
    off = ~np.isin(pack_rgb(color[..., :3]), allowed) & drawn
    if off.any():
        j, i = np.argwhere(off)[0]
        raise ExportError(f"{render_dir}: color pixel ({i}, {j}) = {tuple(color[j, i, :3])} is not in the palette")
    flat = np.where(drawn[..., None], color[..., :3], np.array(hex_rgb(render["background"]), dtype=np.uint8))
    return render, scene, np.ascontiguousarray(flat, dtype=np.uint8)


def reduce2(img: np.ndarray, kernel: str) -> np.ndarray:
    """2x reduction, size rounded up, edges replicated (projection.md section 4)."""
    h, w = img.shape[:2]
    img = np.pad(img, ((0, h % 2), (0, w % 2), (0, 0)), mode="edge")
    quads = [img[0::2, 0::2], img[0::2, 1::2], img[1::2, 0::2], img[1::2, 1::2]]  # TL, TR, BL, BR
    if kernel == "mean":
        return ((sum(q.astype(np.uint16) for q in quads) + 2) // 4).astype(np.uint8)
    if kernel == "mode":
        keys = [pack_rgb(q) for q in quads]
        counts = np.stack([sum((k == other) for other in keys) for k in keys])  # each includes itself
        pick = np.argmax(counts, axis=0)  # first maximum wins: tie-break TL > TR > BL > BR
        return np.choose(pick[..., None], quads).astype(np.uint8)
    raise ExportError(f"unknown kernel {kernel}")


def encode(tile: np.ndarray, fmt: str) -> bytes:
    """Deterministic lossless encoding; no ancillary chunks, metadata or timestamps."""
    buf = io.BytesIO()
    if fmt == "png":
        keys = pack_rgb(tile)
        colours = np.unique(keys)
        if len(colours) <= 256:
            im = Image.fromarray(np.searchsorted(colours, keys).astype(np.uint8), "P")
            im.putpalette(np.stack([colours >> 16, (colours >> 8) & 255, colours & 255], 1).astype(np.uint8).tobytes())
        else:
            im = Image.fromarray(tile, "RGB")
        im.save(buf, format="PNG", compress_level=PNG_ZLIB_LEVEL, optimize=False)
    elif fmt == "webp":
        Image.fromarray(tile, "RGB").save(buf, format="WEBP", lossless=True, quality=100, method=WEBP_METHOD,
                                          exact=True)
    else:
        raise ExportError(f"unknown tile format {fmt}")
    return buf.getvalue()


def pyramid(master: np.ndarray, tile_size: int, overlap: int, kernel: str):
    """Yield (level, col, row, tile pixels) for every tile, from maxLevel down to 0."""
    max_level = math.ceil(math.log2(max(master.shape[0], master.shape[1])))
    img = master
    for level in range(max_level, -1, -1):
        h, w = img.shape[:2]
        for row in range(math.ceil(h / tile_size)):
            for col in range(math.ceil(w / tile_size)):
                x0, y0 = max(col * tile_size - overlap, 0), max(row * tile_size - overlap, 0)
                x1, y1 = min((col + 1) * tile_size + overlap, w), min((row + 1) * tile_size + overlap, h)
                yield level, col, row, img[y0:y1, x0:x1]
        if level:
            img = reduce2(img, kernel)


def forward(proj: dict, e: float, n: float, h: float) -> tuple[float, float]:
    m, t, o = proj["matrix"], proj["translation"], proj["origin"]
    x, y, z = e - o["E0"], n - o["N0"], h - o["H0"]
    return (m[0][0] * x + m[0][1] * y + m[0][2] * z + t[0], m[1][0] * x + m[1][1] * y + m[1][2] * z + t[1])


def publish_pois(scene_dir: Path, scene: dict, render: dict) -> dict:
    path = scene_dir / scene["pois"]["path"]
    if sha256(path) != scene["pois"]["sha256"]:
        raise ExportError(f"{path}: sha256 does not match scene.json")
    doc = load_json(path, "scene-pois")
    proj, width, height = render["projection"], render["image"]["width"], render["image"]["height"]
    out = []
    for p in doc["pois"]:
        p = dict(p)
        x, y = forward(proj, p["E"], p["N"], p["H"])
        if not (0 <= x < width and 0 <= y < height):
            raise ExportError(f"{path}: POI {p['id']} projects to ({x:.3f}, {y:.3f}), "
                              f"outside the {width}x{height} image")
        p["X"], p["Y"] = round(x, 3), round(y, 3)
        if "worldBounds" in p:
            e0, n0, e1, n1 = p.pop("worldBounds")
            cs = [forward(proj, e, n, p["H"]) for e in (e0, e1) for n in (n0, n1)]
            p["imageBounds"] = [round(min(c[0] for c in cs), 3), round(min(c[1] for c in cs), 3),
                                round(max(c[0] for c in cs), 3), round(max(c[1] for c in cs), 3)]
        out.append(p)
    pois = {"schemaVersion": "1.0", "cityId": doc["cityId"], "pois": sorted(out, key=lambda p: p["id"])}
    check_doc(pois, "poi", "pois.json")
    return pois


def geo_to_world(scene: dict) -> dict:
    """Least-squares affine (lon, lat, 1) -> (E, N) over AOI + margin; residual measured on a denser grid."""
    if scene["crs"]["world"] != "EPSG:25830" or scene["crs"]["geographic"] != "EPSG:4326":
        raise ExportError(f"unexpected CRS {scene['crs']}")
    to_geo = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
    (w, s, e, n), margin = scene["aoi"]["bounds"], scene["aoi"]["marginM"]
    w, s, e, n = w - margin, s - margin, e + margin, n + margin

    def grid(k: int) -> tuple[np.ndarray, np.ndarray]:
        ee, nn = np.meshgrid(np.linspace(w, e, k), np.linspace(s, n, k))
        return ee.ravel(), nn.ravel()

    fe, fn = grid(9)
    lon, lat = (np.asarray(v) for v in to_geo.transform(fe, fn))
    lon0, lat0 = lon.mean(), lat.mean()
    a = np.column_stack([lon - lon0, lat - lat0, np.ones_like(lon)])
    matrix = []
    for target in (fe, fn):
        c, *_ = np.linalg.lstsq(a, target - target.mean(), rcond=None)
        matrix.append([float(c[0]), float(c[1]), float(c[2] + target.mean() - c[0] * lon0 - c[1] * lat0)])
    ce, cn = grid(33)
    clon, clat = (np.asarray(v) for v in to_geo.transform(ce, cn))
    m = np.array(matrix)
    residual = float(np.max(np.hypot(m[0, 0] * clon + m[0, 1] * clat + m[0, 2] - ce,
                                     m[1, 0] * clon + m[1, 1] * clat + m[1, 2] - cn)))
    max_residual = math.ceil(residual * 1e6) / 1e6
    if max_residual >= 0.1:
        raise ExportError(f"geoToWorld affine residual {residual:.4f} m >= 0.1 m")
    return {"matrix": matrix, "maxResidualM": max_residual}


def height_grid(scene_dir: Path, scene: dict) -> tuple[dict, bytes]:
    """Bilinear resample of terrain.f32 to 4 m cell centres over the same rectangle, uint16-le."""
    t = scene["terrain"]
    path = scene_dir / t["path"]
    if sha256(path) != t["sha256"]:
        raise ExportError(f"{path}: sha256 does not match scene.json")
    raw = np.fromfile(path, dtype="<f4")
    if raw.size != t["width"] * t["height"]:
        raise ExportError(f"{path}: {raw.size} samples, scene.json says {t['width']}x{t['height']}")
    terrain = raw.reshape(t["height"], t["width"]).astype(np.float64)
    if not np.isfinite(terrain).all():
        raise ExportError(f"{path}: non-finite heights")
    gw = math.ceil(t["width"] * t["cellSize"] / HEIGHT_CELL_M)
    gh = math.ceil(t["height"] * t["cellSize"] / HEIGHT_CELL_M)
    # target centres in source pixel units (source sample (c, r) sits at (c + 0.5) * cellSize from the edge)
    fc = np.clip((np.arange(gw) + 0.5) * HEIGHT_CELL_M / t["cellSize"] - 0.5, 0, t["width"] - 1)
    fr = np.clip((np.arange(gh) + 0.5) * HEIGHT_CELL_M / t["cellSize"] - 0.5, 0, t["height"] - 1)
    c0, r0 = np.minimum(fc.astype(int), t["width"] - 2), np.minimum(fr.astype(int), t["height"] - 2)
    dc, dr = (fc - c0)[None, :], (fr - r0)[:, None]
    q = terrain[np.ix_(r0, c0)] * (1 - dc) + terrain[np.ix_(r0, c0 + 1)] * dc
    q2 = terrain[np.ix_(r0 + 1, c0)] * (1 - dc) + terrain[np.ix_(r0 + 1, c0 + 1)] * dc
    grid = q * (1 - dr) + q2 * dr
    offset = math.floor(grid.min())
    values = np.rint((grid - offset) / HEIGHT_SCALE)
    if values.max() > 65535:
        raise ExportError(f"{path}: height range {grid.min():.2f}..{grid.max():.2f} m overflows uint16 at 0.01 m")
    meta = {"path": "height.u16", "width": gw, "height": gh, "cellSize": HEIGHT_CELL_M, "westE": t["westE"],
            "northN": t["northN"], "dtype": "uint16-le", "scale": HEIGHT_SCALE, "offset": float(offset)}
    return meta, values.astype("<u2").tobytes()


def write_json(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def build(render_dir: Path, scene_dir: Path, city_path: Path, out: Path, release: str, style_id: str = "procedural",
          style_label: str = "Procedural", kernel: str = DEFAULT_KERNEL, fmt: str | None = None) -> dict:
    city = load_json(city_path, "city-config")
    render, scene, master = load_render(render_dir, scene_dir)
    if city["id"] != render["cityId"]:
        raise ExportError(f"{city_path}: city id {city['id']} != render cityId {render['cityId']}")
    if kernel not in KERNELS:
        raise ExportError(f"unknown kernel {kernel}")
    fmt = fmt or city["tiles"]["format"]
    tile_size, overlap = city["tiles"]["tileSize"], city["tiles"]["tileOverlap"]
    pois = publish_pois(scene_dir, scene, render)
    geo = geo_to_world(scene)
    hmeta, hbytes = height_grid(scene_dir, scene)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    max_level = 0
    for level, col, row, tile in pyramid(master, tile_size, overlap, kernel):
        max_level = max(max_level, level)
        path = out / style_id / str(level) / f"{col}_{row}.{fmt}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(tile, fmt))
    (out / hmeta["path"]).write_bytes(hbytes)
    write_json(out / "pois.json", pois)
    manifest = {
        "schemaVersion": "1.0", "cityId": city["id"], "name": city["name"], "release": release,
        "image": render["image"],
        "tiles": {"layout": "dzi", "tileSize": tile_size, "tileOverlap": overlap, "minLevel": 0, "maxLevel": max_level},
        "styles": [{"id": style_id, "label": style_label, "tilesBase": style_id, "format": fmt}],
        "projection": render["projection"], "zRange": render["zRange"], "geoToWorld": geo, "heightGrid": hmeta,
        "background": render["background"], "pois": "pois.json", "attribution": city["attribution"],
        "crs": scene["crs"], "renderSha256": sha256(render_dir / "render.json"),
    }
    check_doc(manifest, "tile-manifest", "manifest.json")
    write_json(out / "manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", type=Path, required=True)
    ap.add_argument("--scene", type=Path, required=True)
    ap.add_argument("--city", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--release", required=True)
    ap.add_argument("--style-id", default="procedural")
    ap.add_argument("--style-label", default="Procedural")
    ap.add_argument("--kernel", choices=KERNELS, default=DEFAULT_KERNEL)
    args = ap.parse_args(argv)
    try:
        m = build(args.render, args.scene, args.city, args.out, args.release, args.style_id, args.style_label,
                  args.kernel)
    except ExportError as e:
        print(f"export.build: {e}", file=sys.stderr)
        return 1
    n = sum(1 for p in args.out.rglob(f"*.{m['styles'][0]['format']}"))
    print(f"wrote {args.out}: {m['image']['width']}x{m['image']['height']} px, levels 0..{m['tiles']['maxLevel']}, "
          f"{n} tiles, kernel {args.kernel}, geoToWorld residual {m['geoToWorld']['maxResidualM']} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
