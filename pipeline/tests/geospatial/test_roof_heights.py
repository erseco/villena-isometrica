"""Eaves/ridge are only split when the samples look like one simple pitched roof."""
import numpy as np
from shapely.geometry import box

from geospatial.buildings import Part, set_roof_heights


def _part() -> Part:
    p = Part("p", "b", box(0, 0, 10, 10), 2, "residential")
    p.base_h, p.roof = 500.0, "pitched"
    return p


def test_simple_pitched_roof_keeps_eaves_and_ridge() -> None:
    p = _part()
    set_roof_heights(p, np.linspace(506.0, 509.0, 101))  # eaves 6 m, ridge 9 m
    assert p.roof == "pitched" and abs(p.height - 6.15) < 0.01 and abs(p.ridge - 8.85) < 0.01


def test_ground_samples_are_not_eaves() -> None:
    p = _part()
    set_roof_heights(p, np.r_[np.full(10, 500.0), np.linspace(506.0, 509.0, 90)])
    assert p.roof == "unknown" and p.ridge is None and 7.5 < p.height < 9


def test_two_level_part_is_not_one_pitched_roof() -> None:
    p = _part()
    set_roof_heights(p, np.r_[np.full(30, 512.0), np.full(70, 536.0)])  # wing 12 m, tower 36 m
    assert p.roof == "unknown" and p.ridge is None and p.height == 36.0
