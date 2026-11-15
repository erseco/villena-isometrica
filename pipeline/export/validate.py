"""Validate a published tile directory (docs/contracts/render.md section 2), independently of export.build.

PYTHONPATH=pipeline uv run --project pipeline python -m export.validate <tiles dir> [--max-bytes N] [--render <dir>]

Exit code 0 when valid, 1 otherwise; every message names the offending file.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import jsonschema
import numpy as np
from PIL import Image
from pyproj import Transformer

SCHEMAS = Path(__file__).resolve().parents[2] / "packages" / "geo-contracts" / "schemas"
# Published lat/lon carry 7 decimals (<= 6 mm) and scene E/N 2 decimals (<= 7 mm), so comparing a POI's own
# lat/lon with its E/N through geoToWorld needs this allowance on top of maxResidualM (see the WP06 handoff).
ROUNDING_ALLOWANCE_M = 0.015
# tests/fixtures/tiles-synthetic/ keeps its independent expected values next to the manifest; export.pack
# refuses to archive it, so it can never reach a release (contract change request in the WP06 handoff).
FIXTURE_ORACLE = "expected.json"


def schema_errors(doc: object, schema: str, path: Path) -> list[str]:
    validator = jsonschema.Draft202012Validator(json.loads((SCHEMAS / f"{schema}.schema.json").read_text()))
    return [f"{path}: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in validator.iter_errors(doc)]


def read_json(path: Path, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as e:
        errors.append(f"{path}: {e}")
        return None


def camera_errors(p: dict, path: Path) -> list[str]:
    a, f, s = math.radians(p["headingDeg"]), math.radians(p["pitchDeg"]), p["pixelsPerMetre"]
    want = [[s * math.cos(a), -s * math.sin(a), 0.0],
            [-s * math.sin(a) * math.sin(f), -s * math.cos(a) * math.sin(f), -s * math.cos(f)]]
    return [f"{path}: projection.matrix[{i}][{j}] = {p['matrix'][i][j]!r}, camera parameters give {want[i][j]!r}"
            for i in range(2) for j in range(3) if abs(p["matrix"][i][j] - want[i][j]) > 1e-9]


def expected_tiles(m: dict) -> dict[str, tuple[int, tuple[int, int]]]:
    """Relative path -> (level, (width, height)) of every tile the manifest implies (projection.md section 4)."""
    width, height = m["image"]["width"], m["image"]["height"]
    t = m["tiles"]
    size, ov, top = t["tileSize"], t["tileOverlap"], t["maxLevel"]
    out = {}
    for style in m["styles"]:
        for level in range(t["minLevel"], top + 1):
            f = 2 ** (top - level)
            lw, lh = -(-width // f), -(-height // f)
            for col in range(-(-lw // size)):
                for row in range(-(-lh // size)):
                    tw = min(lw, (col + 1) * size + ov) - max(0, col * size - ov)
                    th = min(lh, (row + 1) * size + ov) - max(0, row * size - ov)
                    out[f"{style['tilesBase']}/{level}/{col}_{row}.{style['format']}"] = (level, (tw, th))
    return out


def check_tiles(root: Path, m: dict, errors: list[str]) -> dict[int, list[int]]:
    """Check every expected tile; return level -> [bytes per tile]."""
    width, height = m["image"]["width"], m["image"]["height"]
    if m["tiles"]["maxLevel"] != math.ceil(math.log2(max(width, height))):
        errors.append(f"{root / 'manifest.json'}: tiles.maxLevel {m['tiles']['maxLevel']} != "
                      f"ceil(log2(max({width}, {height})))")
        return {}
    if m["tiles"]["minLevel"] > m["tiles"]["maxLevel"]:
        errors.append(f"{root / 'manifest.json'}: tiles.minLevel > tiles.maxLevel")
        return {}
    for style in m["styles"]:
        if "://" in style["tilesBase"] or style["tilesBase"].startswith("/") or ".." in style["tilesBase"]:
            errors.append(f"{root / 'manifest.json'}: style {style['id']} tilesBase {style['tilesBase']!r} "
                          "is not a local relative directory; cannot validate")
            return {}
    sizes: dict[int, list[int]] = {}
    for rel, (level, dims) in sorted(expected_tiles(m).items()):
        path = root / rel
        if not path.is_file():
            errors.append(f"{path}: missing tile")
            continue
        sizes.setdefault(level, []).append(path.stat().st_size)
        try:
            with Image.open(path) as im:
                im.load()
                fmt, got, mode = im.format, im.size, im.mode
                transparent = "transparency" in im.info
        except Exception as e:  # noqa: BLE001 - any decoder failure is a broken tile
            errors.append(f"{path}: does not decode ({e})")
            continue
        if fmt != rel.rsplit(".", 1)[1].upper():
            errors.append(f"{path}: is {fmt}, expected {rel.rsplit('.', 1)[1]}")
        if got != dims:
            errors.append(f"{path}: {got[0]}x{got[1]} px, expected {dims[0]}x{dims[1]}")
        if mode not in ("RGB", "P", "L") or transparent:
            errors.append(f"{path}: not opaque (mode {mode})")
    return sizes


def check_pois(root: Path, m: dict, errors: list[str]) -> None:
    path = root / m["pois"]
    doc = read_json(path, errors)
    if doc is None:
        return
    errs = schema_errors(doc, "poi", path)
    if errs:
        errors.extend(errs)
        return
    if doc["cityId"] != m["cityId"]:
        errors.append(f"{path}: cityId {doc['cityId']} != manifest cityId {m['cityId']}")
    ids = [p["id"] for p in doc["pois"]]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        errors.append(f"{path}: POIs must be sorted by id with unique ids")
    p, (w, h) = m["projection"], (m["image"]["width"], m["image"]["height"])
    a, t, o = p["matrix"], p["translation"], p["origin"]
    g = m["geoToWorld"]["matrix"]
    tol = m["geoToWorld"]["maxResidualM"]
    to_geo = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
    for poi in doc["pois"]:
        x, y, z = poi["E"] - o["E0"], poi["N"] - o["N0"], poi["H"] - o["H0"]
        fx = a[0][0] * x + a[0][1] * y + a[0][2] * z + t[0]
        fy = a[1][0] * x + a[1][1] * y + a[1][2] * z + t[1]
        if not (0 <= poi["X"] < w and 0 <= poi["Y"] < h):
            errors.append(f"{path}: POI {poi['id']} at ({poi['X']}, {poi['Y']}) is outside the {w}x{h} image")
        if abs(fx - poi["X"]) > 1e-3 or abs(fy - poi["Y"]) > 1e-3:
            errors.append(f"{path}: POI {poi['id']} X,Y = ({poi['X']}, {poi['Y']}) but forward(E, N, H) = "
                          f"({fx:.3f}, {fy:.3f})")
        # the affine itself, against PROJ at the POI's own E, N: within maxResidualM
        lon, lat = to_geo.transform(poi["E"], poi["N"])
        de, dn = g[0][0] * lon + g[0][1] * lat + g[0][2] - poi["E"], g[1][0] * lon + g[1][1] * lat + g[1][2] - poi["N"]
        if math.hypot(de, dn) > tol:
            errors.append(f"{root / 'manifest.json'}: geoToWorld misses POI {poi['id']} by {math.hypot(de, dn):.6f} m "
                          f"> maxResidualM {tol}")
        # the POI's published lat/lon, through the affine, must land on its E, N
        lon, lat = poi["lon"], poi["lat"]
        de, dn = g[0][0] * lon + g[0][1] * lat + g[0][2] - poi["E"], g[1][0] * lon + g[1][1] * lat + g[1][2] - poi["N"]
        if math.hypot(de, dn) > tol + ROUNDING_ALLOWANCE_M:
            errors.append(f"{path}: POI {poi['id']} lat/lon map to {math.hypot(de, dn):.4f} m from its E,N "
                          f"(> maxResidualM + {ROUNDING_ALLOWANCE_M} m rounding allowance)")


def check_render(root: Path, m: dict, render_dir: Path, errors: list[str]) -> None:
    """With the render directory: the manifest points at it and every drawn color pixel is in the palette."""
    rpath = render_dir / "render.json"
    render = read_json(rpath, errors)
    if render is None:
        return
    if hashlib.sha256(rpath.read_bytes()).hexdigest() != m["renderSha256"]:
        errors.append(f"{root / 'manifest.json'}: renderSha256 does not match {rpath}")
    palette = read_json(render_dir / render["palette"]["path"], errors)
    color = next((layer for layer in render["layers"] if layer["name"] == "color"), None)
    if palette is None or color is None:
        errors.append(f"{rpath}: palette or color layer missing")
        return
    with Image.open(render_dir / color["path"]) as im:
        rgba = np.asarray(im.convert("RGBA")).astype(np.uint32)
    keys = (rgba[..., 0] << 16) | (rgba[..., 1] << 8) | rgba[..., 2]
    allowed = np.array([int(c["hex"][1:], 16) for c in palette["colors"]], dtype=np.uint32)
    bad = np.unique(keys[(rgba[..., 3] > 0) & ~np.isin(keys, allowed)])
    if bad.size:
        errors.append(f"{render_dir / color['path']}: {bad.size} drawn colours not in the palette, e.g. #{bad[0]:06x}")


def validate(root: Path, max_bytes: int | None = None, render_dir: Path | None = None) -> tuple[list[str], str]:
    """Return (errors, per-level size table)."""
    errors: list[str] = []
    mpath = root / "manifest.json"
    m = read_json(mpath, errors)
    if m is None:
        return errors, ""
    errs = schema_errors(m, "tile-manifest", mpath)
    if errs:
        return errs, ""
    errors += camera_errors(m["projection"], mpath)
    sizes = check_tiles(root, m, errors)
    check_pois(root, m, errors)
    known = {"manifest.json", m["pois"]} | {rel for rel in expected_tiles(m)}
    if "heightGrid" in m:
        hg = m["heightGrid"]
        known.add(hg["path"])
        hpath = root / hg["path"]
        if not hpath.is_file():
            errors.append(f"{hpath}: missing height grid")
        elif hpath.stat().st_size != hg["width"] * hg["height"] * 2:
            errors.append(f"{hpath}: {hpath.stat().st_size} bytes, expected {hg['width']}x{hg['height']}x2")
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = f.relative_to(root).as_posix()
        if rel == FIXTURE_ORACLE:
            print(f"note: {f} ignored (test oracle of the synthetic fixture; never published)", file=sys.stderr)
        elif rel not in known:
            errors.append(f"{f}: unexpected file")
    if render_dir is not None:
        check_render(root, m, render_dir, errors)

    total = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    lines = ["level  tiles       bytes   max tile"]
    lines += [f"{lvl:>5}  {len(s):>5}  {sum(s):>10}  {max(s):>9}" for lvl, s in sorted(sizes.items())]
    lines.append(f"total  {sum(map(len, sizes.values())):>5}  {total:>10}  (all files)")
    if max_bytes is not None and total > max_bytes:
        errors.append(f"{root}: total {total} bytes exceeds --max-bytes {max_bytes}")
    return errors, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tiles", type=Path)
    ap.add_argument("--max-bytes", type=int)
    ap.add_argument("--render", type=Path, help="render directory: also check renderSha256 and the palette")
    args = ap.parse_args(argv)
    errors, table = validate(args.tiles, args.max_bytes, args.render)
    if table:
        print(table)
    for e in errors:
        print(f"FAIL {e}", file=sys.stderr)
    print(f"{args.tiles}: {'INVALID, ' + str(len(errors)) + ' error(s)' if errors else 'valid'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
