# 0001 — Stack and repository layout

Status: accepted (2026-11-15). Evidence: `docs/research/04-rendering-viewer-toolchain.md`.

## Context
The brief proposed TypeScript + Bun + Vite + OpenSeadragon for the viewer, Python for GIS,
Three.js or Blender for rendering, one repository, optional Docker.

## Decision
- Viewer: Vite 8, TypeScript (strict), OpenSeadragon 6, vanilla DOM, Bun as package manager;
  Playwright runs on Node.
- GIS and export: Python 3.13 with `uv`, wheels only (GeoPandas, pyogrio, Rasterio, Shapely,
  PyProj, NumPy, Pillow). No system GDAL, no PDAL, no Docker.
- Renderer: TypeScript (ADR 0002).
- JS packages are standalone, each with its own lockfile; one Python project in `pipeline/`;
  the optional ML harness is a separate environment.
- Each component implements the ~20-line projection itself and is tested against shared
  vectors, instead of sharing a cross-language library.

## Options rejected
- Bun workspace / monorepo tooling: one shared lockfile would make parallel agents conflict.
- Docker for the GIS stack: wheels bundle GDAL on both target platforms; Alpine has no wheels.
- A UI framework: nothing in the viewer needs one.
- Leaflet / MapLibre / deck.gl: a single deep-zoom image is OpenSeadragon's native model.

## Consequences
- pyogrio and Rasterio wheels bundle different GDAL builds in one process; acceptable, watch
  for it in WP03.
- TypeScript 7 has no programmatic API until 7.1: lint tooling may need the compatibility
  package (WP05/WP04 decide).
