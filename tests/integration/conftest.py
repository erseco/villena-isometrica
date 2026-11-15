"""Integration test setup. Run: uv run --project pipeline pytest tests/integration -q (from the repository root).

Everything is offline. The pipeline stages run as the CLIs the Makefile uses, in temporary directories."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "pipeline"), str(Path(__file__).parent)]  # export.*, geospatial.*, helpers

import helpers as H  # noqa: E402


@pytest.fixture(scope="session")
def run_a(tmp_path_factory):
    """Synthetic scene -> render -> tiles, validated. Built once per session."""
    return H.full_pipeline(tmp_path_factory.mktemp("run-a"))


@pytest.fixture(scope="session")
def run_b(tmp_path_factory):
    """The same pipeline a second time, for reproducibility."""
    return H.full_pipeline(tmp_path_factory.mktemp("run-b"))
