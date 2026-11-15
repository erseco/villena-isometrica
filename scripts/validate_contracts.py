# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4.21"]
# ///
"""Validate JSON documents against the contracts. Run: `uv run scripts/validate_contracts.py [file ...]`.

Without arguments it validates the schemas themselves, every committed fixture and every
cities/*/city.json + datasets.json. With arguments it validates those files; the schema is
chosen from the file name (city.json, datasets.json, scene.json, render.json, manifest.json,
pois.json — scene-pois when it sits next to a scene.json —, palette.json, *.job.json). Beyond the schema it checks that a manifest's projection matrix agrees
with its camera parameters (docs/contracts/projection.md section 3).
"""
import json
import math
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "packages" / "geo-contracts" / "schemas"
BY_NAME = {"city.json": "city-config", "datasets.json": "dataset-manifest", "scene.json": "scene-manifest",
           "render.json": "render-manifest", "manifest.json": "tile-manifest", "pois.json": "poi",
           "palette.json": "palette"}


def schema_for(path):
    if path.name == "pois.json" and (path.parent / "scene.json").exists():
        return "scene-pois"  # a scene's POIs have no image coordinates yet
    return "generation-job" if path.name.endswith(".job.json") else BY_NAME.get(path.name)


def not_finite(token):
    raise ValueError(f"non-finite number {token} is not JSON")


def projection_errors(p):
    a, f, s = math.radians(p["headingDeg"]), math.radians(p["pitchDeg"]), p["pixelsPerMetre"]
    want = [[s * math.cos(a), -s * math.sin(a), 0.0],
            [-s * math.sin(a) * math.sin(f), -s * math.cos(a) * math.sin(f), -s * math.cos(f)]]
    return [f"projection.matrix[{i}][{j}] = {p['matrix'][i][j]!r}, camera parameters give {want[i][j]!r}"
            for i in range(2) for j in range(3) if abs(p["matrix"][i][j] - want[i][j]) > 1e-9]


def validate(path):
    name = schema_for(path)
    if name is None:
        return [f"no schema known for file name {path.name}"]
    try:
        doc = json.loads(path.read_text(), parse_constant=not_finite)
    except ValueError as e:
        return [str(e)]
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
              for e in jsonschema.Draft202012Validator(schema).iter_errors(doc)]
    if not errors and "projection" in doc:
        errors += projection_errors(doc["projection"])
    if not errors and name == "city-config" and not (path.parent / doc["datasets"]).is_file():
        errors.append(f"datasets: {doc['datasets']} does not exist next to this file")
    if not errors and name in ("scene-pois", "poi"):
        ids = [p["id"] for p in doc["pois"]]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            errors.append("pois must be sorted by id and ids must be unique")
    return errors


def main(argv):
    failed = False
    if argv:
        files = [Path(a) for a in argv]
    else:
        for s in sorted(SCHEMAS.glob("*.schema.json")):
            jsonschema.Draft202012Validator.check_schema(json.loads(s.read_text()))
        files = sorted(p for base in (ROOT / "tests" / "fixtures", ROOT / "cities") if base.exists()
                       for p in base.rglob("*.json") if schema_for(p))
    for path in files:
        errors = validate(path)
        failed |= bool(errors)
        print(("FAIL " if errors else "ok   ") + str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path))
        for e in errors:
            print("     " + e)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
