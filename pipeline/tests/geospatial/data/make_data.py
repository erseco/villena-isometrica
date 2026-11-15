"""Regenerate the synthetic GIS test dataset in this directory.

Run: uv run --project pipeline python pipeline/tests/geospatial/data/make_data.py

A 200 m x 200 m town with known answers (local metres from the AOI's south-west corner;
terrain is the plane z = 600 + 0.08 x + 0.04 y):

  SYN0001  flat roof 7 m                         -> surface-model 7.0, roof flat
  SYN0002  gable, eaves 6 m, ridge +1.6 m        -> surface-model ~6.0 (eaves), roof pitched
  SYN0003  3 floors, no surface data             -> floors 3*3+1 = 10.0
  SYN0004  floors nil, no surface data           -> default 3.0
  SYN0005  0 floors, surface = ground            -> dropped (open space)
  SYN0006  0 floors above, 1 below               -> dropped (underground)
  SYN0007  straddles the clip edge, 4 m          -> clipped to x >= -20
  SYN0008  landmark: tower +18 m, walls +8 m,     -> zoned into tower and walls, courtyard dropped
           courtyard at ground
  tree     Gaussian crown, 8 m at (60, 150)       -> detected tree
  OSM      two named streets, a pedestrian way with width tag, a park, a mapped tree
  POIs     keep (in the tower), plaza
"""

import hashlib
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

HERE = Path(__file__).resolve().parent
E0, N0 = 700000.0, 4270000.0
SIZE, MARGIN = 200.0, 20.0
# rasters cover the clip rectangle plus 10 m
R_WEST, R_SOUTH, R_SIZE = -30.0, -30.0, 260.0
NODATA = -32767.0
TO_GEO = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)


def ground(x, y):
    return 600.0 + 0.08 * x + 0.04 * y


def rect_min_ground(x0, y0, x1, y1):
    return ground(x0, y0)  # the plane rises with x and y


BUILDINGS = [  # refcat, part, (x0, y0, x1, y1), floors above, floors below, use
    ("SYN0001", 1, (20, 20, 40, 40), 2, 0, "1_residential"),
    ("SYN0002", 1, (50, 20, 66, 40), 3, 0, "1_residential"),
    ("SYN0003", 1, (80, 20, 95, 35), 3, 0, "4_2_retail"),
    ("SYN0004", 1, (100, 20, 110, 30), None, 0, "3_industrial"),
    ("SYN0005", 1, (120, 20, 130, 30), 0, 0, "1_residential"),
    ("SYN0006", 1, (140, 20, 150, 30), 0, 1, "1_residential"),
    ("SYN0007", 1, (-30, 100, -5, 120), 1, 0, "2_agriculture"),
    ("SYN0008", 1, (100, 100, 140, 130), 3, 0, "4_3_publicServices"),
]
NO_SURFACE = {"SYN0003", "SYN0004"}


def surface():
    n = int(R_SIZE / 0.5)
    xs = R_WEST + (np.arange(n) + 0.5) * 0.5
    ys = R_SOUTH + R_SIZE - (np.arange(n) + 0.5) * 0.5
    x, y = np.meshgrid(xs, ys)
    terrain = ground(x, y)
    mds = terrain.copy()

    def inside(x0, y0, x1, y1):
        return (x >= x0) & (x < x1) & (y >= y0) & (y < y1)

    b = rect_min_ground(20, 20, 40, 40)
    mds[inside(20, 20, 40, 40)] = b + 7.0
    b = rect_min_ground(50, 20, 66, 40)
    m = inside(50, 20, 66, 40)
    mds[m] = b + 6.0 + 1.6 * (1 - np.abs(x[m] - 58.0) / 8.0)
    for x0, y0, x1, y1 in ((80, 20, 95, 35), (100, 20, 110, 30)):
        mds[inside(x0, y0, x1, y1)] = NODATA
    b = rect_min_ground(-30, 100, -5, 120)
    mds[inside(-30, 100, -5, 120)] = b + 4.0
    b = rect_min_ground(100, 100, 140, 130)
    mds[inside(100, 100, 140, 130)] = b + 8.0
    court = inside(110, 108, 130, 122)
    mds[court] = terrain[court]
    mds[inside(100, 100, 110, 110)] = b + 18.0
    tree = 8.0 * np.exp(-((x - 60.0) ** 2 + (y - 150.0) ** 2) / (2 * 2.0**2))
    mds = np.where(mds == NODATA, NODATA, np.maximum(mds, terrain + tree))
    return terrain.astype("float32"), mds.astype("float32")


def write_tif(path, arr, cell):
    profile = {"driver": "GTiff", "dtype": "float32", "count": 1, "width": arr.shape[1], "height": arr.shape[0],
               "crs": "EPSG:25830", "transform": from_origin(E0 + R_WEST, N0 + R_SOUTH + R_SIZE, cell, cell),
               "nodata": NODATA, "compress": "deflate", "predictor": 3, "zlevel": 9}
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)


def write_asc(path):
    """5 m terrain without CRS, like the IGN WCS ASCII grid output."""
    n = int(R_SIZE / 5)
    rows = [" ".join(f"{ground(R_WEST + (c + 0.5) * 5, R_SOUTH + R_SIZE - (r + 0.5) * 5):.2f}" for c in range(n))
            for r in range(n)]
    header = (f"ncols {n}\nnrows {n}\nxllcorner {E0 + R_WEST:.1f}\nyllcorner {N0 + R_SOUTH:.1f}\n"
              f"cellsize 5.0\nNODATA_value -9999\n")
    path.write_text(header + "\n".join(rows) + "\n")


NS = ('xmlns:base="urn:x-inspire:specification:gmlas:BaseTypes:3.2" '
      'xmlns:bu-core2d="http://inspire.jrc.ec.europa.eu/schemas/bu-core2d/2.0" '
      'xmlns:bu-ext2d="http://inspire.jrc.ec.europa.eu/schemas/bu-ext2d/2.0" '
      'xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink" '
      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')


def poslist(x0, y0, x1, y1):
    pts = [(x0, y0), (x0, y1), (x1, y1), (x1, y0), (x0, y0)]  # clockwise, as Catastro often is
    return " ".join(f"{E0 + x:.2f} {N0 + y:.2f}" for x, y in pts)


def surface_xml(fid, r):
    return (f'<bu-ext2d:geometry><bu-core2d:BuildingGeometry><bu-core2d:geometry>'
            f'<gml:Surface gml:id="Surface_{fid}" srsName="urn:ogc:def:crs:EPSG::25830"><gml:patches><gml:PolygonPatch>'
            f'<gml:exterior><gml:LinearRing><gml:posList srsDimension="2" count="5">{poslist(*r)}</gml:posList>'
            f'</gml:LinearRing></gml:exterior></gml:PolygonPatch></gml:patches></gml:Surface>'
            f'</bu-core2d:geometry></bu-core2d:BuildingGeometry></bu-ext2d:geometry>')


def gml(members):
    return (f'<?xml version="1.0" encoding="ISO-8859-1"?>\n<gml:FeatureCollection gml:id="ES.SDGC.BU" {NS}>\n'
            + "".join(f"<gml:featureMember>{m}</gml:featureMember>\n" for m in members) + "</gml:FeatureCollection>\n")


def nil(tag):
    return f'<{tag} xsi:nil="true" nilReason="other:unpopulated"></{tag}>'


def catastro_zip(path):
    parts, buildings = [], []
    for ref, n, r, above, below, use in BUILDINGS:
        fid = f"ES.SDGC.BU.{ref}_part{n}"
        floors = nil("bu-ext2d:numberOfFloorsAboveGround") if above is None else \
            f"<bu-ext2d:numberOfFloorsAboveGround>{above}</bu-ext2d:numberOfFloorsAboveGround>"
        parts.append(f'<bu-ext2d:BuildingPart gml:id="{fid}"><bu-core2d:inspireId><base:Identifier>'
                     f'<base:localId>{ref}_part{n}</base:localId><base:namespace>ES.SDGC.BU</base:namespace>'
                     f'</base:Identifier></bu-core2d:inspireId>{surface_xml(fid, r)}{floors}'
                     f'<bu-ext2d:numberOfFloorsBelowGround>{below}</bu-ext2d:numberOfFloorsBelowGround>'
                     f'</bu-ext2d:BuildingPart>')
        bid = f"ES.SDGC.BU.{ref}"
        buildings.append(f'<bu-ext2d:Building gml:id="{bid}"><bu-core2d:inspireId><base:Identifier>'
                         f'<base:localId>{ref}</base:localId><base:namespace>ES.SDGC.BU</base:namespace>'
                         f'</base:Identifier></bu-core2d:inspireId>{surface_xml(bid, r)}'
                         f'<bu-ext2d:currentUse>{use}</bu-ext2d:currentUse>'
                         f'{nil("bu-ext2d:numberOfFloorsAboveGround")}</bu-ext2d:Building>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in (("A.ES.SDGC.BU.99999.building.gml", gml(buildings)),
                           ("A.ES.SDGC.BU.99999.buildingpart.gml", gml(parts))):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, body.encode("iso-8859-1"))


def lonlat(x, y):
    lon, lat = TO_GEO.transform(E0 + x, N0 + y)
    return {"lat": round(lat, 7), "lon": round(lon, 7)}


def overpass(path):
    def way(wid, pts, **tags):
        return {"type": "way", "id": wid, "nodes": list(range(len(pts))), "geometry": [lonlat(*p) for p in pts],
                "tags": tags}
    park = [(40, 140), (80, 140), (80, 170), (40, 170), (40, 140)]
    elements = [
        {"type": "node", "id": 9001, **lonlat(45, 145), "tags": {"natural": "tree"}},
        way(1001, [(-40, 70), (100, 70), (240, 70)], highway="residential", name="Calle Mayor"),
        way(1002, [(20, 80), (20, 180)], highway="residential", name="Calle Nueva"),
        way(1003, [(150, 80), (150, 180)], highway="pedestrian", name="Subida al Castillo", width="3 m"),
        way(1004, [(160, 80), (170, 90)], highway="construction"),
        way(2001, park, leisure="park", name="Jardín"),
    ]
    data = {"version": 0.6, "generator": "synthetic", "osm3s": {"timestamp_osm_base": "2026-01-01T00:00:00Z"},
            "elements": elements}
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def city_and_datasets():
    crs = {"world": "EPSG:25830", "geographic": "EPSG:4326", "verticalDatum": "synthetic"}
    city = {"schemaVersion": "1.0", "id": "synthville", "name": "Synthville (GIS test data)", "crs": crs,
            "aoi": {"bounds": [E0, N0, E0 + SIZE, N0 + SIZE], "marginM": MARGIN},
            "origin": {"E0": E0, "N0": N0, "H0": 600.0},
            "camera": {"headingDeg": 45, "pitchDeg": 30, "pixelsPerMetre": 4},
            "tiles": {"tileSize": 256, "tileOverlap": 1, "format": "png"},
            "datasets": "datasets.json", "attribution": [{"text": "Synthetic test data"}]}
    rows = [  # id, file, access, resolution, crs
        ("catastro-buildings", "catastro-bu.zip", "direct", "vector", "EPSG:25830"),
        ("ign-mdt50cm", "mdt.tif", "manual", "0.5 m", "EPSG:25830"),
        ("ign-mds50cm", "mds.tif", "manual", "0.5 m", "EPSG:25830"),
        ("ign-mdt05-wcs", "mdt05.asc", "ogc-service", "5 m", "EPSG:25830"),
        ("osm-overpass", "overpass.json", "direct", "vector", "EPSG:4326"),
    ]
    datasets = [{"id": i, "provider": "synthetic", "name": f, "version": "1", "acquisitionDate": "2026-01-01",
                 "coverage": "AOI + margin", "url": "https://example.invalid/" + f, "access": a, "resolution": res,
                 "crs": c, "license": {"name": "CC0-1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/",
                                       "attribution": "none"},
                 "redistribution": {"raw": True, "derivatives": True}, "sizeBytes": (HERE / f).stat().st_size,
                 "sha256": hashlib.sha256((HERE / f).read_bytes()).hexdigest(), "localPath": f,
                 "retrievedAt": "2026-01-01"} for i, f, a, res, c in rows]
    for name, obj in (("city.json", city), ("datasets.json", {"schemaVersion": "1.0", "cityId": "synthville",
                                                               "datasets": datasets})):
        (HERE / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def main():
    terrain, mds = surface()
    write_tif(HERE / "mdt.tif", terrain, 0.5)
    write_tif(HERE / "mds.tif", mds, 0.5)
    write_asc(HERE / "mdt05.asc")
    catastro_zip(HERE / "catastro-bu.zip")
    overpass(HERE / "overpass.json")
    pois = [
        {"id": "keep", "name": "Torre del Homenaje", "altNames": ["Castillo"], "kind": "landmark",
         "source": {"dataset": "synthetic", "ref": "poi-1"}, **lonlat(105, 105)},
        {"id": "plaza", "name": "Plaza Sintética", "altNames": [], "kind": "square",
         "source": {"dataset": "synthetic", "ref": "poi-2"}, **lonlat(60, 90)},
    ]
    (HERE / "poi-selection.json").write_text(json.dumps(pois, indent=1, ensure_ascii=False) + "\n")
    city_and_datasets()
    print("written; total", sum(f.stat().st_size for f in HERE.iterdir() if f.is_file()) // 1024, "KiB")
    print("expected tower roof H =", rect_min_ground(100, 100, 140, 130) + 18.0,
          "| keep ground", round(ground(105, 105), 3), "| sanity", math.isclose(ground(0, 0), 600.0))


if __name__ == "__main__":
    main()
