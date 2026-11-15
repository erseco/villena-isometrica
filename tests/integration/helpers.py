"""Shared helpers for the integration tests. Expected values never come from here: only plumbing."""

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
SCENE, CITY, TILES_FIX = FIX / "scene-synthetic", FIX / "city-synthetic" / "city.json", FIX / "tiles-synthetic"
RENDERING = ROOT / "pipeline" / "rendering"
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "pipeline")}


def jload(path: Path):
    return json.loads(Path(path).read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(Path(root).rglob("*")) if p.is_file()}


def sh(cmd: list, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=ENV, capture_output=True, text=True)


def render(scene: Path, out: Path, *extra, city: Path = CITY) -> subprocess.CompletedProcess:
    return sh(["bun", "run", "render", "--scene", scene, "--city", city, "--out", out, *extra], cwd=RENDERING)


def export(render_dir: Path, scene: Path, out: Path, city: Path = CITY) -> subprocess.CompletedProcess:
    return sh([sys.executable, "-m", "export.build", "--render", render_dir, "--scene", scene, "--city", city,
               "--out", out, "--release", "wp08"])


def validate(tiles: Path, *extra) -> subprocess.CompletedProcess:
    return sh([sys.executable, "-m", "export.validate", tiles, *extra])


def ok(p: subprocess.CompletedProcess) -> subprocess.CompletedProcess:
    assert p.returncode == 0, f"{p.args}\nexit {p.returncode}\n{p.stdout}\n{p.stderr}"
    return p


def full_pipeline(root: Path) -> SimpleNamespace:
    r, t = root / "render", root / "tiles"
    ok(render(SCENE, r))
    ok(export(r, SCENE, t))
    ok(validate(t, "--render", r))
    return SimpleNamespace(render=r, tiles=t)


def copy_scene(dst: Path) -> Path:
    shutil.copytree(SCENE, dst)
    return dst


def rewrite_json(path: Path, edit) -> None:
    doc = jload(path)
    edit(doc)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def reseal_layer(scene: Path, key: str, name: str | None = None) -> None:
    """Record the current sha256 of a scene file in scene.json, so that only the *content*
    problem under test remains."""
    def edit(m):
        entry = m[key] if name is None else m[key][name]
        entry["sha256"] = sha256(scene / entry["path"])
    rewrite_json(scene / "scene.json", edit)


# ---- independent maths (closed form from docs/contracts/projection.md; no product code) -------------------------

CAM = SimpleNamespace(heading=45.0, pitch=30.0, ppm=4.0)  # tests/fixtures/city-synthetic/city.json
E0, N0, H0 = 700000.0, 4270000.0, 500.0


def plane(x: float, y: float) -> float:
    """The synthetic terrain, local metres (scripts/make_fixtures.py header)."""
    return 0.10 * x + 0.05 * y


def matrix(cam=CAM):
    a, f, s = math.radians(cam.heading), math.radians(cam.pitch), cam.ppm
    return [[s * math.cos(a), -s * math.sin(a), 0.0], [-s * math.sin(a) * math.sin(f), -s * math.cos(a) * math.sin(f),
                                                       -s * math.cos(f)]]


def fwd(x: float, y: float, z: float, translation=(363.0, 470.0), cam=CAM) -> tuple[float, float]:
    """Image (X, Y) of a local point. Default translation = -(floor(min u), floor(min v)) of the synthetic prism."""
    m = matrix(cam)
    return (m[0][0] * x + m[0][1] * y + m[0][2] * z + translation[0],
            m[1][0] * x + m[1][1] * y + m[1][2] * z + translation[1])


def prism_size(cam, bounds, z_min, z_max):
    """Master-image size and translation by projection.md section 3, from the eight prism corners."""
    m = matrix(cam)
    w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]
    us = [m[0][0] * x + m[0][1] * y for x in (0, w) for y in (0, h)]
    vs = [m[1][0] * x + m[1][1] * y + m[1][2] * z for x in (0, w) for y in (0, h) for z in (z_min, z_max)]
    u0, v0 = math.floor(min(us)), math.floor(min(vs))
    return math.ceil(max(us)) - u0, math.ceil(max(vs)) - v0, (-u0, -v0)


def level_sizes(width: int, height: int):
    top = math.ceil(math.log2(max(width, height)))
    return top, {lv: (-(-width // 2 ** (top - lv)), -(-height // 2 ** (top - lv))) for lv in range(top + 1)}


def tile_list(width, height, size=256, overlap=1) -> dict[tuple[int, int, int], tuple[int, int]]:
    """(level, col, row) -> (w, h) of every tile file, projection.md section 4."""
    top, sizes = level_sizes(width, height)
    out = {}
    for lv, (lw, lh) in sizes.items():
        for col in range(-(-lw // size)):
            for row in range(-(-lh // size)):
                x0, x1 = max(col * size - overlap, 0), min((col + 1) * size + overlap, lw)
                y0, y1 = max(row * size - overlap, 0), min((row + 1) * size + overlap, lh)
                out[(lv, col, row)] = (x1 - x0, y1 - y0)
    return out


def layer(render_dir: Path, name: str) -> np.ndarray:
    with Image.open(Path(render_dir) / f"{name}.png") as im:
        return np.asarray(im.convert("RGBA") if name == "color" else im.convert("RGB") if name == "buildingId" else im)


def building_id(img: np.ndarray, X: float, Y: float) -> int:
    r, g, b = (int(v) for v in img[int(Y), int(X)])
    return (r << 16) | (g << 8) | b
