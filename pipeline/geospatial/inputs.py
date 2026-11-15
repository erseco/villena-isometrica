"""City config, dataset manifest and verified access to local input files."""

import email.parser
import hashlib
import json
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

WORLD_CRS = "EPSG:25830"

# Dataset ids the scene build looks for in cities/<city>/datasets.json (see README).
ROLES = {
    "buildings": "catastro-buildings",
    "terrain": "ign-mdt50cm",
    "surface": "ign-mds50cm",
    "terrain_fallback": "ign-mdt05-wcs",
    "osm": "osm-overpass",
}


class PipelineError(Exception):
    """An input or output problem that must stop the pipeline."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class City:
    path: Path
    config: dict
    datasets: dict[str, dict]
    data_root: Path

    @property
    def dir(self) -> Path:
        return self.path.parent

    def has_file(self, dataset_id: str) -> bool:
        entry = self.datasets.get(dataset_id)
        return entry is not None and (self.data_root / entry["localPath"]).is_file()

    def input(self, dataset_id: str) -> tuple[Path, str]:
        """Path and sha256 of a pinned, present, verified input. Raises PipelineError otherwise."""
        entry = self.datasets.get(dataset_id)
        if entry is None:
            raise PipelineError(f"dataset '{dataset_id}' is not in {self.dir / self.config['datasets']}")
        path = self.data_root / entry["localPath"]
        if entry.get("sha256") is None:
            raise PipelineError(f"dataset '{dataset_id}' has no pinned sha256 in the dataset manifest; "
                                f"run acquisition.fetch and pin the printed checksum")
        if not path.is_file():
            raise PipelineError(f"dataset '{dataset_id}' missing: {path} (run acquisition.fetch)")
        digest = sha256_file(path)
        if digest != entry["sha256"]:
            raise PipelineError(f"checksum mismatch for {path}: {digest} != pinned {entry['sha256']}")
        return path, digest


def load_city(city_path: Path, data_root: Path) -> City:
    config = json.loads(city_path.read_text())
    if config["crs"]["world"] != WORLD_CRS:
        raise PipelineError(f"{city_path}: world CRS must be {WORLD_CRS}")
    manifest = json.loads((city_path.parent / config["datasets"]).read_text())
    return City(city_path, config, {d["id"]: d for d in manifest["datasets"]}, data_root)


@dataclass(frozen=True)
class Grid:
    """Regular north-up grid in EPSG:25830; samples at cell centres; row 0 is the northernmost."""

    west: float
    north: float
    cell: float
    width: int
    height: int

    @classmethod
    def covering(cls, bounds: tuple[float, float, float, float], cell: float) -> "Grid":
        minx, miny, maxx, maxy = bounds
        return cls(minx, maxy, cell, round((maxx - minx) / cell), round((maxy - miny) / cell))

    @property
    def transform(self):
        return from_origin(self.west, self.north, self.cell, self.cell)

    def centres(self, r0: int, r1: int, c0: int, c1: int) -> tuple[np.ndarray, np.ndarray]:
        xs = self.west + (np.arange(c0, c1) + 0.5) * self.cell
        ys = self.north - (np.arange(r0, r1) + 0.5) * self.cell
        return np.meshgrid(xs, ys)

    def window(self, bounds) -> tuple[int, int, int, int]:
        """Row/col range of cells whose centres may fall inside bounds."""
        minx, miny, maxx, maxy = bounds
        c0 = max(int(np.floor((minx - self.west) / self.cell)), 0)
        c1 = min(int(np.ceil((maxx - self.west) / self.cell)), self.width)
        r0 = max(int(np.floor((self.north - maxy) / self.cell)), 0)
        r1 = min(int(np.ceil((self.north - miny) / self.cell)), self.height)
        return r0, r1, c0, c1

    def bilinear(self, arr: np.ndarray, e: float, n: float) -> float:
        fx = min(max((e - self.west) / self.cell - 0.5, 0.0), self.width - 1.0)
        fy = min(max((self.north - n) / self.cell - 0.5, 0.0), self.height - 1.0)
        c, r = min(int(fx), self.width - 2), min(int(fy), self.height - 2)
        tx, ty = fx - c, fy - r
        top = arr[r, c] * (1 - tx) + arr[r, c + 1] * tx
        bottom = arr[r + 1, c] * (1 - tx) + arr[r + 1, c + 1] * tx
        return float(top * (1 - ty) + bottom * ty)


RASTER_PARTS = {"application/asc": ".asc", "image/tiff": ".tif"}


def raster_bytes(path: Path) -> tuple[bytes, str] | None:
    """The coverage inside a multipart WCS 2.0 response (as served by servicios.idee.es), or None if not multipart."""
    data = path.read_bytes().lstrip()  # the IGN service sends a blank line before the first boundary
    if not data.startswith(b"--"):
        return None
    boundary = data.split(b"\n", 1)[0].strip()[2:].decode("ascii")
    msg = email.parser.BytesParser().parsebytes(
        f'Content-Type: multipart/mixed; boundary="{boundary}"\n\n'.encode() + data)
    for part in msg.walk():
        ext = RASTER_PARTS.get(part.get_content_type())
        if ext:
            return part.get_payload(decode=True), ext
    raise PipelineError(f"{path}: multipart response without a raster part")


def open_raster(path: Path, stack: ExitStack):
    inner = raster_bytes(path)
    if inner is None:
        return stack.enter_context(rasterio.open(path))
    return stack.enter_context(stack.enter_context(MemoryFile(inner[0], ext=inner[1])).open())


def read_raster(path: Path, grid: Grid, resampling: Resampling, declared_crs: str) -> tuple[np.ndarray, dict]:
    """Read band 1 onto `grid` (float32, NaN for no data). Returns the array and facts about the source."""
    with ExitStack() as stack:
        src = open_raster(path, stack)
        if src.crs is None:
            if "25830" not in declared_crs:
                raise PipelineError(f"{path} has no CRS and the manifest does not declare EPSG:25830")
            src_crs = WORLD_CRS
        elif src.crs.to_epsg() != 25830:
            raise PipelineError(f"{path} is in {src.crs}, expected {WORLD_CRS}")
        else:
            src_crs = src.crs
        t = src.transform
        if t.b != 0 or t.d != 0:
            raise PipelineError(f"{path} is rotated; not supported")
        res = (t.a, -t.e)
        aligned = (abs(res[0] - grid.cell) < 1e-9 and abs(res[1] - grid.cell) < 1e-9
                   and abs(((t.c - grid.west) / grid.cell) - round((t.c - grid.west) / grid.cell)) < 1e-6
                   and abs(((t.f - grid.north) / grid.cell) - round((t.f - grid.north) / grid.cell)) < 1e-6)
        src_bounds = src.bounds
        need = (grid.west, grid.north - grid.height * grid.cell, grid.west + grid.width * grid.cell, grid.north)
        if (src_bounds.left > need[0] + 1e-6 or src_bounds.bottom > need[1] + 1e-6
                or src_bounds.right < need[2] - 1e-6 or src_bounds.top < need[3] - 1e-6):
            raise PipelineError(f"{path} {tuple(src_bounds)} does not cover the required area {need}")
        out = np.full((grid.height, grid.width), np.nan, dtype="float32")
        reproject(source=rasterio.band(src, 1), destination=out, src_transform=t, src_crs=src_crs,
                  src_nodata=src.nodata, dst_transform=grid.transform, dst_crs=WORLD_CRS, dst_nodata=np.nan,
                  resampling=resampling)
    return out, {"resolution": res, "alignedWithGrid": aligned, "bounds": tuple(src_bounds)}
