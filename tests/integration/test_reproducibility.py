"""WP08 7.2: same input, same bytes; cross-platform identity on decoded pixels (ADR 0007)."""

import importlib.util
import os
import shutil
import subprocess
import sys

import helpers as H
import pytest


def test_whole_pipeline_twice_gives_identical_files(run_a, run_b):
    for part in ("render", "tiles"):
        a, b = H.tree_hashes(getattr(run_a, part)), H.tree_hashes(getattr(run_b, part))
        assert a.keys() == b.keys() and len(a) > 4
        assert a == b, [k for k in a if a[k] != b[k]]


def test_render_chunk_size_does_not_change_pixels(run_a, tmp_path):
    """projection.md section 7.4: output independent of the renderer's internal chunk size (also via the CLI)."""
    H.ok(H.render(H.SCENE, tmp_path / "r", "--chunk", "100"))
    want = {entry["name"]: entry["pixelSha256"] for entry in H.jload(run_a.render / "render.json")["layers"]}
    got = {entry["name"]: entry["pixelSha256"] for entry in H.jload(tmp_path / "r" / "render.json")["layers"]}
    assert got == want


def test_fixture_generator_reproduces_the_committed_fixtures(tmp_path):
    """`make fixtures` into a scratch directory (FIXTURES_OUT), compared with the committed tree by content on any
    platform (scripts/check_fixtures.py rules); the committed tree itself is never written."""
    spec = importlib.util.spec_from_file_location("check_fixtures", H.ROOT / "scripts" / "check_fixtures.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)
    out = tmp_path / "fixtures"
    run = subprocess.run([sys.executable, str(H.ROOT / "scripts" / "make_fixtures.py")], cwd=H.ROOT,
                         env={**os.environ, "FIXTURES_OUT": str(out)}, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    committed = H.tree_hashes(H.FIX)
    fresh = H.tree_hashes(out)
    assert committed.keys() == fresh.keys()
    problems = []
    for name in committed:
        if committed[name] == fresh[name]:
            continue
        a, b = (H.FIX / name).read_bytes(), (out / name).read_bytes()
        if name.endswith(".json"):
            import json
            problems += chk.differences(json.loads(a), json.loads(b), name)
        elif name.endswith(".png"):
            problems += [] if chk.png_pixels(a) == chk.png_pixels(b) else [f"{name}: pixels differ"]
        else:
            problems.append(f"{name}: bytes differ")
    assert problems == []


def _docker_ready() -> str | None:
    """None when usable, else the reason to skip. Never pulls an image: the suite is offline."""
    if shutil.which("docker") is None:
        return "docker is not installed"
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        return "the docker daemon is not running"
    if subprocess.run(["docker", "image", "inspect", "oven/bun:1.4"], capture_output=True).returncode != 0:
        return "image oven/bun:1.4 is not present locally (the suite never pulls)"
    return None


@pytest.mark.skipif(_docker_ready() is not None, reason=f"Docker variant skipped: {_docker_ready()}")
def test_linux_amd64_container_gives_the_same_pixels(run_a, tmp_path):
    """Renderer in a linux/amd64 container (emulated on arm64 hosts) vs the host: identical decoded pixels
    (`pixelSha256`, the cross-platform identity; file hashes are only stable per toolchain). The container mounts the
    repository read-only, including the host's node_modules (pure JavaScript, no install step needed offline).
    ponytail: the Python exporter is not run in the container, its wheels cannot be installed offline."""
    out = tmp_path / "container-render"
    out.mkdir()
    cmd = ["docker", "run", "--rm", "--pull", "never", "--platform", "linux/amd64",
           "-v", f"{H.ROOT}:/w:ro", "-v", f"{out}:/out", "-w", "/w/pipeline/rendering", "oven/bun:1.4",
           "bun", "src/cli.ts", "--scene", "/w/tests/fixtures/scene-synthetic",
           "--city", "/w/tests/fixtures/city-synthetic/city.json", "--out", "/out"]
    run = subprocess.run(cmd, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    host = {e["name"]: e["pixelSha256"] for e in H.jload(run_a.render / "render.json")["layers"]}
    box = {e["name"]: e["pixelSha256"] for e in H.jload(out / "render.json")["layers"]}
    assert box == host
