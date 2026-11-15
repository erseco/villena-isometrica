"""The CNIG 0.5 m sheets are tagged EPSG:3042 (25830 with N,E axis order): read like 25830."""
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin

from geospatial.inputs import Grid, PipelineError, read_raster

GRID = Grid(685002, 4278008, 1.0, 6, 6)  # aligned with the source cells: rows 2..7, cols 2..7


def _write(path: Path, epsg: int) -> np.ndarray:
    data = np.arange(100, dtype="float32").reshape(10, 10)
    with rasterio.open(path, "w", driver="GTiff", width=10, height=10, count=1, dtype="float32",
                       crs=f"EPSG:{epsg}", transform=from_origin(685000, 4278010, 1, 1)) as dst:
        dst.write(data, 1)
    return data


@pytest.mark.parametrize("epsg", [25830, 3042])
def test_accepted_crs_reads_the_same_cells(tmp_path: Path, epsg: int) -> None:
    data = _write(tmp_path / "r.tif", epsg)
    out, _ = read_raster(tmp_path / "r.tif", GRID, Resampling.nearest, "EPSG:25830")
    np.testing.assert_array_equal(out, data[2:8, 2:8])


def test_other_crs_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "r.tif", 25831)
    with pytest.raises(PipelineError, match="expected EPSG:25830"):
        read_raster(tmp_path / "r.tif", GRID, Resampling.nearest, "EPSG:25830")
