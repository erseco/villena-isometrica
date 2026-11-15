// Scene -> render primitives (terrain cells, wall quads, roof polygons, tree spheres) and the
// top-down ground-class grid that drapes roads and landcover on the terrain.
import { cosDeg, forward, type Projection, sinDeg } from './projection.ts';
import { type Detail, type Part, type Ring, type Scene, terrainAt } from './scene.ts';

/** Sub-pixel grid of projected vertices: 1/256 px. */
export const SUB = 256;

/** Fixed sun direction (unit vector towards the sun): bearing 205 deg (SSW), elevation 45 deg. */
export const SUN: [number, number, number] = [sinDeg(205) * cosDeg(45), cosDeg(205) * cosDeg(45), sinDeg(45)];

/** Shade band 0 (sunlit) .. 3 (deep shade) from a unit normal. */
export function band(nx: number, ny: number, nz: number): number {
  const l = nx * SUN[0] + ny * SUN[1] + nz * SUN[2];
  return l >= 0.85 ? 0 : l >= 0.6 ? 1 : l >= 0.35 ? 2 : 3;
}

export enum Kind {
  Wall = 1,
  Roof = 2,
  Crown = 3,
  Trunk = 4,
  /** Detail body: sides of a solid and the vertical faces of its merlons. */
  Detail = 5,
  /** Detail top: the flat cap of a cylinder or frustum and its merlon tops. */
  DetailTop = 6,
}

export enum RoofTex {
  Tile = 0,
  Flat = 1,
  Stone = 2,
  /** Tops of the merlons of a `parapet: "battlement"` part: plain wall material. */
  Merlon = 3,
}

/** Where a detail surface sits on its solid, for shading and texture in stage 2. */
export interface DetailFace {
  /** Facet k of n around the axis; a pixel's arc fraction is (k + t) / n. */
  k: number;
  n: number;
  /** Half chord of a facet divided by the profile radius at the same height. */
  hc: number;
  /** Shade by the analytic surface normal (round solids) instead of the facet band. */
  round: boolean;
}

export interface Surface {
  kind: Kind;
  /** Part index (walls, roofs) or tree index (crowns, trunks). */
  owner: number;
  band: number;
  /** Walls: start vertex and unit direction along the wall, length, edge number. Roofs: row reference line. */
  ax: number;
  ay: number;
  ux: number;
  uy: number;
  len: number;
  edge: number;
  tex: RoofTex;
  /** Detail surfaces only. */
  face?: DetailFace;
}

/** A planar polygon in image space: depth d = (c - a*nr + b*np) / nw, a = (X-tx)/s, b = (Y-ty)/s. */
export interface Poly {
  /** Rings of fixed-point image coordinates [X0, Y0, X1, Y1, ...] (units of 1/SUB px). */
  rings: Float64Array[];
  nr: number;
  np: number;
  nw: number;
  c: number;
  surf: number;
  clip: boolean;
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface TreePrim {
  surfCrown: number;
  surfTrunk: number;
  /** Crown centre image position and depth, radius in px and metres. */
  cX: number;
  cY: number;
  cD: number;
  rPx: number;
  rM: number;
  /** Trunk base image position and depth, top height above base (m), half width (px). */
  bX: number;
  bY: number;
  bD: number;
  trunkM: number;
  halfW: number;
  clip: boolean;
  /** Crown centre in local metres. */
  wx: number;
  wy: number;
  wz: number;
}

export interface Geometry {
  /** Terrain quads intersecting the AOI: cell index c + r * (width - 1). */
  cells: Int32Array;
  /** Fixed-point image X, Y of every terrain sample. */
  tX: Float64Array;
  tY: Float64Array;
  /** Shade band per terrain triangle (2 per quad). */
  tBand: Uint8Array;
  polys: Poly[];
  trees: TreePrim[];
  surfaces: Surface[];
  /** First surface id of `surfaces[0]`; terrain triangle t has id 1 + t. */
  surfBase: number;
}

const ROOF_ALLOWANCE = 6;
/** Battlement: merlon width, height, nominal gap and depth from the wall face, m. */
export const MERLON_W = 0.7;
export const MERLON_H = 0.9;
const MERLON_GAP = 0.7;
const MERLON_T = 0.5;

/**
 * Merlon spans [s0, s1] along a wall edge of length len, in metres from its start vertex: the
 * edge starts and ends with a merlon and the gaps are as close to 0.7 m as a whole count allows.
 * Depends only on the edge, so it is the same in every chunk and every run.
 */
export function merlonSpans(len: number): [number, number][] {
  if (len < MERLON_W / 2) return [];
  const m = Math.max(1, Math.round((len + MERLON_GAP) / (MERLON_W + MERLON_GAP)));
  if (m === 1) {
    const w = Math.min(MERLON_W, len);
    return [[(len - w) / 2, (len + w) / 2]];
  }
  const step = (len - MERLON_W) / (m - 1);
  return Array.from({ length: m }, (_, i) => [i * step, i * step + MERLON_W] as [number, number]);
}

/** Facets around the axis for a round solid of radius rPx pixels: about 3 px per facet. */
export function segmentsFor(rPx: number): number {
  return Math.max(8, Math.min(128, 4 * Math.ceil(rPx / 2)));
}

type V3 = [number, number, number];

/** Unit normal of a planar 3-D polygon by Newell's method (counter-clockwise seen from its front). */
function newell(pts: V3[]): V3 {
  let nx = 0;
  let ny = 0;
  let nz = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0, z0] = pts[i];
    const [x1, y1, z1] = pts[(i + 1) % pts.length];
    nx += (y0 - y1) * (z0 + z1);
    ny += (z0 - z1) * (x0 + x1);
    nz += (x0 - x1) * (y0 + y1);
  }
  const l = Math.sqrt(nx * nx + ny * ny + nz * nz);
  return [nx / l, ny / l, nz / l];
}
const PITCH = 1 / Math.sqrt(3); // tan 30 deg

function signedArea(r: Ring): number {
  let a = 0;
  for (let i = 0; i + 1 < r.length; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
  return a / 2;
}

/** Closed ring without the repeated last vertex, consecutive duplicates and collinear points. */
function cleanRing(r: Ring, ccw: boolean): Ring {
  let pts = r.slice(0, r.length - 1);
  if (signedArea(r) > 0 !== ccw) pts = pts.reverse();
  let changed = true;
  while (changed && pts.length > 3) {
    changed = false;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[(i + pts.length - 1) % pts.length];
      const b = pts[i];
      const c = pts[(i + 1) % pts.length];
      const cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
      if (Math.abs(cross) < 1e-9 && pts.length > 3) {
        pts.splice(i, 1);
        changed = true;
        break;
      }
    }
  }
  return pts;
}

function isConvexCCW(pts: Ring): boolean {
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i];
    const b = pts[(i + 1) % pts.length];
    const c = pts[(i + 2) % pts.length];
    if ((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) < 0) return false;
  }
  return true;
}

/** Sutherland-Hodgman: keep the part of a convex polygon where f(x, y) <= 0, f linear. */
function clipHalf(pts: Ring, f: (x: number, y: number) => number): Ring {
  const out: Ring = [];
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i];
    const b = pts[(i + 1) % pts.length];
    const fa = f(a[0], a[1]);
    const fb = f(b[0], b[1]);
    if (fa <= 0) out.push(a);
    if ((fa < 0 && fb > 0) || (fa > 0 && fb < 0)) {
      const t = fa / (fa - fb);
      out.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]);
    }
  }
  return out;
}

export interface Facet {
  pts: Ring;
  /** Plane z = z0 + k * dist to the line through (ax, ay) with direction (ux, uy); k = 0 for a flat top. */
  ax: number;
  ay: number;
  ux: number;
  uy: number;
  k: number;
  z0: number;
}

/**
 * Hipped roof over a convex CCW footprint: facet i is the region closer to edge i than to any
 * other edge, rising inward at slope k from the eaves. The ridge direction follows from the
 * shape (procedural); the height is `ridge` when given, else 30 deg pitch capped at 6 m.
 */
export function hipRoof(pts: Ring, eaves: number, ridge: number | null): Facet[] {
  const n = pts.length;
  const lines = pts.map((a, i) => {
    const b = pts[(i + 1) % n];
    const len = Math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]));
    return { ax: a[0], ay: a[1], ux: (b[0] - a[0]) / len, uy: (b[1] - a[1]) / len };
  });
  const dist = (i: number, x: number, y: number) => {
    const l = lines[i];
    return l.ux * (y - l.ay) - l.uy * (x - l.ax);
  };
  const regions = lines.map((_, i) => {
    let poly = pts;
    for (let j = 0; j < n && poly.length >= 3; j++)
      if (j !== i) poly = clipHalf(poly, (x, y) => dist(i, x, y) - dist(j, x, y));
    return poly;
  });
  let dMax = 0;
  regions.forEach((poly, i) => {
    for (const [x, y] of poly) dMax = Math.max(dMax, dist(i, x, y));
  });
  if (dMax <= 0) return [];
  const k = ridge !== null ? (ridge - eaves) / dMax : PITCH;
  const capD = ridge !== null ? Infinity : Math.min(dMax, ROOF_ALLOWANCE / PITCH);
  const facets: Facet[] = [];
  regions.forEach((poly, i) => {
    const p = capD < dMax ? clipHalf(poly, (x, y) => dist(i, x, y) - capD) : poly;
    if (p.length >= 3) facets.push({ pts: p, ...lines[i], k, z0: eaves });
  });
  if (capD < dMax) {
    let top = pts;
    for (let j = 0; j < n && top.length >= 3; j++) top = clipHalf(top, (x, y) => capD - dist(j, x, y));
    if (top.length >= 3) facets.push({ pts: top, ...lines[0], k: 0, z0: eaves + k * capD });
  }
  return facets;
}

/** Rasterisable 2-D footprint geometry of one part. */
function partRings(part: Part): Ring[] {
  return part.rings.map((r, i) => cleanRing(r, i === 0)).filter((r) => r.length >= 3);
}

export function longestEdge(r: Ring): { ax: number; ay: number; ux: number; uy: number } {
  let best = { ax: 0, ay: 0, ux: 1, uy: 0 };
  let bestLen = -1;
  for (let i = 0; i < r.length; i++) {
    const a = r[i];
    const b = r[(i + 1) % r.length];
    const len = Math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]));
    if (len > bestLen) {
      bestLen = len;
      best = { ax: a[0], ay: a[1], ux: (b[0] - a[0]) / len, uy: (b[1] - a[1]) / len };
    }
  }
  return best;
}

export function buildGeometry(scene: Scene, pr: Projection): Geometry {
  const t = scene.terrain;
  const { aoiW, aoiH, zMin, zMax } = scene;
  const toFixed = (x: number, y: number, z: number): [number, number] => {
    const [X, Y] = forward(pr, x, y, z);
    return [Math.round(X * SUB), Math.round(Y * SUB)];
  };
  const inPrism = (x0: number, x1: number, y0: number, y1: number, z0: number, z1: number) =>
    x0 >= 0 && x1 <= aoiW && y0 >= 0 && y1 <= aoiH && z0 >= zMin && z1 <= zMax;

  // Terrain.
  const nS = t.width * t.height;
  const tX = new Float64Array(nS);
  const tY = new Float64Array(nS);
  for (let r = 0; r < t.height; r++)
    for (let c = 0; c < t.width; c++) {
      const i = r * t.width + c;
      const [X, Y] = toFixed(t.x0 + c * t.cellSize, t.y0 - r * t.cellSize, t.z[i]);
      tX[i] = X;
      tY[i] = Y;
    }
  const qw = t.width - 1;
  const cellList: number[] = [];
  const tBand = new Uint8Array(qw * (t.height - 1) * 2);
  const cs = t.cellSize;
  for (let r = 0; r + 1 < t.height; r++)
    for (let c = 0; c < qw; c++) {
      const xw = t.x0 + c * cs;
      const yn = t.y0 - r * cs;
      if (xw + cs < 0 || xw > aoiW || yn < 0 || yn - cs > aoiH) continue;
      const q = r * qw + c;
      cellList.push(q);
      const zA = t.z[r * t.width + c];
      const zB = t.z[r * t.width + c + 1];
      const zC = t.z[(r + 1) * t.width + c];
      const zD = t.z[(r + 1) * t.width + c + 1];
      // Triangle 0 = A C D (south-west half), triangle 1 = A D B; diagonal NW-SE.
      for (const [tri, nx, ny] of [
        [0, zC - zD, zC - zA],
        [1, zA - zB, zD - zB],
      ] as const) {
        const len = Math.sqrt(nx * nx + ny * ny + cs * cs);
        tBand[q * 2 + tri] = band(nx / len, ny / len, cs / len);
      }
    }

  const surfaces: Surface[] = [];
  const surfBase = 1 + tBand.length;
  const addSurface = (s: Surface) => surfBase + surfaces.push(s) - 1;
  const polys: Poly[] = [];
  const nrOf = (nx: number, ny: number, nz: number) => nx * pr.r[0] + ny * pr.r[1] + nz * pr.r[2];
  const npOf = (nx: number, ny: number, nz: number) => nx * pr.p[0] + ny * pr.p[1] + nz * pr.p[2];
  const nwOf = (nx: number, ny: number, nz: number) => nx * pr.w[0] + ny * pr.w[1] + nz * pr.w[2];
  const addPoly = (rings3: [number, number, number][][], n: [number, number, number], surf: number) => {
    const nw = nwOf(...n);
    if (Math.abs(nw) < 1e-9) return;
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    let wx0 = Infinity;
    let wx1 = -Infinity;
    let wy0 = Infinity;
    let wy1 = -Infinity;
    let wz0 = Infinity;
    let wz1 = -Infinity;
    const rings = rings3.map((ring) => {
      const out = new Float64Array(ring.length * 2);
      ring.forEach(([x, y, z], i) => {
        const [X, Y] = toFixed(x, y, z);
        out[2 * i] = X;
        out[2 * i + 1] = Y;
        minX = Math.min(minX, X);
        maxX = Math.max(maxX, X);
        minY = Math.min(minY, Y);
        maxY = Math.max(maxY, Y);
        wx0 = Math.min(wx0, x);
        wx1 = Math.max(wx1, x);
        wy0 = Math.min(wy0, y);
        wy1 = Math.max(wy1, y);
        wz0 = Math.min(wz0, z);
        wz1 = Math.max(wz1, z);
      });
      return out;
    });
    const [a0, b0, c0] = rings3[0][0];
    const c = n[0] * a0 + n[1] * b0 + n[2] * c0;
    polys.push({
      rings,
      nr: nrOf(...n),
      np: npOf(...n),
      nw,
      c,
      surf,
      clip: !inPrism(wx0, wx1, wy0, wy1, wz0, wz1),
      minX,
      maxX,
      minY,
      maxY,
    });
  };

  /**
   * Vertical prism over a CCW footprint from z0 to z1: side faces facing the camera, then the
   * top. `side` returns the surface id of the face on footprint edge i.
   */
  const addPrism = (
    foot: [number, number][],
    z0: number,
    z1: number,
    side: (i: number, nx: number, ny: number, ux: number, uy: number, len: number) => number,
    top: number,
  ) => {
    for (let i = 0; i < foot.length; i++) {
      const a = foot[i];
      const b = foot[(i + 1) % foot.length];
      const dx = b[0] - a[0];
      const dy = b[1] - a[1];
      const len = Math.sqrt(dx * dx + dy * dy);
      const nx = dy / len;
      const ny = -dx / len;
      if (nx * pr.w[0] + ny * pr.w[1] >= 0) continue;
      const quad: V3[] = [
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
      ];
      addPoly([quad], [nx, ny, 0], side(i, nx, ny, dx / len, dy / len, len));
    }
    addPoly([foot.map(([x, y]) => [x, y, z1] as V3)], [0, 0, 1], top);
  };

  scene.parts.forEach((part, pi) => {
    const rings = partRings(part);
    if (rings.length === 0) return;
    const z0 = part.baseZ;
    const z1 = part.baseZ + part.heightM;
    // Walls: outward normal (dy, -dx) with the exterior CCW and holes CW; back faces culled.
    let edgeNo = 0;
    for (const ring of rings)
      for (let i = 0; i < ring.length; i++, edgeNo++) {
        const a = ring[i];
        const b = ring[(i + 1) % ring.length];
        const dx = b[0] - a[0];
        const dy = b[1] - a[1];
        const len = Math.sqrt(dx * dx + dy * dy);
        const nx = dy / len;
        const ny = -dx / len;
        if (nx * pr.w[0] + ny * pr.w[1] >= 0) continue;
        const surf = addSurface({
          kind: Kind.Wall,
          owner: pi,
          band: band(nx, ny, 0),
          ax: a[0],
          ay: a[1],
          ux: dx / len,
          uy: dy / len,
          len,
          edge: edgeNo,
          tex: RoofTex.Flat,
        });
        addPoly(
          [
            [
              [a[0], a[1], z0],
              [b[0], b[1], z0],
              [b[0], b[1], z1],
              [a[0], a[1], z1],
            ],
          ],
          [nx, ny, 0],
          surf,
        );
      }
    const ref = longestEdge(rings[0]);
    // Battlement: a box per merlon on the inner side of every wall edge (holes included).
    if (part.parapet) {
      const top = addSurface({
        kind: Kind.Roof,
        owner: pi,
        band: band(0, 0, 1),
        ...ref,
        len: 0,
        edge: 0,
        tex: RoofTex.Merlon,
      });
      let e = 0;
      for (const ring of rings)
        for (let i = 0; i < ring.length; i++, e++) {
          const a = ring[i];
          const b = ring[(i + 1) % ring.length];
          const dx = b[0] - a[0];
          const dy = b[1] - a[1];
          const len = Math.sqrt(dx * dx + dy * dy);
          const [ux, uy] = [dx / len, dy / len];
          // Inward is the left of the edge (exterior CCW, holes CW).
          const [ix, iy] = [-uy * MERLON_T, ux * MERLON_T];
          const edgeNo = e;
          for (const [s0, s1] of merlonSpans(len)) {
            const p0: [number, number] = [a[0] + ux * s0, a[1] + uy * s0];
            const p1: [number, number] = [a[0] + ux * s1, a[1] + uy * s1];
            const foot: [number, number][] = [p0, p1, [p1[0] + ix, p1[1] + iy], [p0[0] + ix, p0[1] + iy]];
            addPrism(
              foot,
              z1,
              z1 + MERLON_H,
              (_i, nx, ny, fx, fy, flen) =>
                addSurface({
                  kind: Kind.Wall,
                  owner: pi,
                  band: band(nx, ny, 0),
                  ax: a[0],
                  ay: a[1],
                  ux: fx,
                  uy: fy,
                  len: flen,
                  edge: edgeNo,
                  tex: RoofTex.Flat,
                }),
              top,
            );
          }
        }
    }
    // Roof.
    const flatTex =
      part.use === 'fortification'
        ? RoofTex.Stone
        : part.roof === 'flat' || part.use === 'industrial'
          ? RoofTex.Flat
          : RoofTex.Tile;
    const facets =
      part.roof === 'pitched' && rings.length === 1 && isConvexCCW(rings[0])
        ? hipRoof(rings[0], z1, part.ridgeHeightM === null ? null : z0 + part.ridgeHeightM)
        : [];
    if (facets.length === 0) {
      const surf = addSurface({
        kind: Kind.Roof,
        owner: pi,
        band: band(0, 0, 1),
        ...ref,
        len: 0,
        edge: 0,
        tex: flatTex,
      });
      addPoly(
        rings.map((r) => r.map(([x, y]) => [x, y, z1] as [number, number, number])),
        [0, 0, 1],
        surf,
      );
      return;
    }
    for (const f of facets) {
      const n: [number, number, number] = [f.k * f.uy, -f.k * f.ux, 1];
      const nl = Math.sqrt(n[0] * n[0] + n[1] * n[1] + 1);
      const surf = addSurface({
        kind: Kind.Roof,
        owner: pi,
        band: band(n[0] / nl, n[1] / nl, 1 / nl),
        ax: f.ax,
        ay: f.ay,
        ux: f.ux,
        uy: f.uy,
        len: 0,
        edge: 0,
        tex: RoofTex.Tile,
      });
      const zOf = (x: number, y: number) => f.z0 + f.k * (f.ux * (y - f.ay) - f.uy * (x - f.ax));
      addPoly([f.pts.map(([x, y]) => [x, y, zOf(x, y)] as [number, number, number])], n, surf);
    }
  });

  const trees: TreePrim[] = [];
  scene.trees.forEach((tree, ti) => {
    const zg = terrainAt(t, tree.x, tree.y);
    const rM = tree.crownRadiusM;
    const cz = zg + tree.heightM - rM;
    const [cX, cY, cD] = forward(pr, tree.x, tree.y, cz);
    const [bX, bY, bD] = forward(pr, tree.x, tree.y, zg);
    const surfCrown = addSurface({
      kind: Kind.Crown,
      owner: ti,
      band: 0,
      ax: 0,
      ay: 0,
      ux: 0,
      uy: 0,
      len: 0,
      edge: 0,
      tex: 0,
    });
    const surfTrunk = addSurface({
      kind: Kind.Trunk,
      owner: ti,
      band: 0,
      ax: 0,
      ay: 0,
      ux: 0,
      uy: 0,
      len: 0,
      edge: 0,
      tex: 0,
    });
    trees.push({
      surfCrown,
      surfTrunk,
      cX,
      cY,
      cD,
      rPx: rM * pr.s,
      rM,
      bX,
      bY,
      bD,
      trunkM: Math.max(cz - zg, 0),
      halfW: Math.max(0.5, 0.2 * pr.s),
      clip: !inPrism(tree.x - rM, tree.x + rM, tree.y - rM, tree.y + rM, zg, cz + rM),
      wx: tree.x,
      wy: tree.y,
      wz: cz,
    });
  });

  for (let di = 0; di < scene.details.length; di++) addDetail(scene.details[di], di);

  return { cells: Int32Array.from(cellList), tX, tY, tBand, polys, trees, surfaces, surfBase };

  /** A detail solid as planar facets around its axis (rings from the base up), plus merlons. */
  function addDetail(det: Detail, di: number): void {
    const { x: cx, y: cy, baseZ: z0, heightM: H, radiusM: R } = det;
    const square = det.kind === 'cone' && det.sides === 4;
    const n = square ? 4 : segmentsFor(R * pr.s);
    // Math angle (CCW from east) of vertex k; a square's corners sit 45 deg off a face normal.
    const ang = (k: number) => (square ? 90 - det.rotationDeg + 45 + 90 * k : (360 * k) / n);
    const scale = square ? Math.SQRT2 : 1;
    const cosA = Array.from({ length: n + 1 }, (_, k) => cosDeg(ang(k % n)));
    const sinA = Array.from({ length: n + 1 }, (_, k) => sinDeg(ang(k % n)));
    const profile: [number, number][] = [];
    if (det.kind === 'dome') {
      const m = Math.max(2, Math.ceil(n / 4));
      for (let j = 0; j <= m; j++) profile.push([R * cosDeg((90 * j) / m), H * sinDeg((90 * j) / m)]);
    } else profile.push([R, 0], [det.kind === 'cone' ? det.topRadiusM : R, H]);
    const ringPts = profile.map(([r, z]) =>
      cosA.map((c, k) => [cx + r * scale * c, cy + r * scale * sinA[k], z0 + z] as V3),
    );
    const face = (k: number, round: boolean): DetailFace => ({
      k,
      n,
      hc: square ? 1 : sinDeg(180 / n),
      round,
    });
    const surfOf = (kind: Kind, nrm: V3, k: number, f: DetailFace | undefined, a: V3, b: V3) => {
      const dx = b[0] - a[0];
      const dy = b[1] - a[1];
      const l = Math.sqrt(dx * dx + dy * dy) || 1;
      return addSurface({
        kind,
        owner: di,
        band: band(...nrm),
        ax: cx,
        ay: cy,
        ux: dx / l,
        uy: dy / l,
        len: 0,
        edge: k,
        tex: RoofTex.Flat,
        ...(f ? { face: f } : {}),
      });
    };
    for (let j = 0; j + 1 < ringPts.length; j++) {
      const lo = ringPts[j];
      const hi = ringPts[j + 1];
      const apex = profile[j + 1][0] === 0;
      for (let k = 0; k < n; k++) {
        const pts: V3[] = apex ? [lo[k], lo[k + 1], hi[k]] : [lo[k], lo[k + 1], hi[k + 1], hi[k]];
        const nrm = newell(pts);
        if (nrm[0] * pr.w[0] + nrm[1] * pr.w[1] + nrm[2] * pr.w[2] >= 0) continue;
        addPoly([pts], nrm, surfOf(Kind.Detail, nrm, k, face(k, !square), lo[k], lo[k + 1]));
      }
    }
    const topR = profile[profile.length - 1][0];
    if (topR > 0) {
      const top = ringPts[ringPts.length - 1].slice(0, n);
      addPoly([top], [0, 0, 1], surfOf(Kind.DetailTop, [0, 0, 1], 0, undefined, top[0], top[1]));
    }
    if (!det.parapet) return;
    // Merlons around the rim of a cylinder: about 0.7 m wide with 0.7 m gaps, MERLON_T deep.
    const m = Math.max(6, Math.round((2 * Math.PI * R) / (MERLON_W + MERLON_GAP)));
    const wDeg = Math.min((360 * MERLON_W) / (2 * Math.PI * R), 180 / m + 90 / m);
    const rIn = R - Math.min(MERLON_T, R / 2);
    const topSurf = surfOf(Kind.DetailTop, [0, 0, 1], 0, undefined, [0, 0, 0], [1, 0, 0]);
    for (let k = 0; k < m; k++) {
      const a0 = (360 * k) / m;
      const a1 = a0 + wDeg;
      const [c0, s0, c1, s1] = [cosDeg(a0), sinDeg(a0), cosDeg(a1), sinDeg(a1)];
      const foot: [number, number][] = [
        [cx + R * c0, cy + R * s0],
        [cx + R * c1, cy + R * s1],
        [cx + rIn * c1, cy + rIn * s1],
        [cx + rIn * c0, cy + rIn * s0],
      ];
      addPrism(
        foot,
        z0 + H,
        z0 + H + MERLON_H,
        (i, nx, ny) => {
          const a: V3 = [...foot[i], 0];
          const b: V3 = [...foot[(i + 1) % 4], 0];
          return surfOf(
            Kind.Detail,
            [nx, ny, 0],
            k,
            i === 0 ? { k, n: m, hc: sinDeg(wDeg / 2), round: true } : undefined,
            a,
            b,
          );
        },
        topSurf,
      );
    }
  }
}

/** Ground material codes of the ground grid. */
export const GROUND = {
  default: 0,
  paved: 1,
  park: 2,
  scrub: 3,
  woodland: 4,
  farmland: 5,
  'bare-rock': 6,
  water: 7,
  sports: 8,
  cemetery: 9,
  asphalt: 10,
  paving: 11,
  dirt: 12,
  rail: 13,
} as const;

const ROAD: Record<string, { code: number; order: number }> = {
  rail: { code: GROUND.rail, order: 0 },
  path: { code: GROUND.dirt, order: 1 },
  steps: { code: GROUND.paving, order: 2 },
  service: { code: GROUND.asphalt, order: 3 },
  pedestrian: { code: GROUND.paving, order: 4 },
  residential: { code: GROUND.asphalt, order: 5 },
  secondary: { code: GROUND.asphalt, order: 6 },
  primary: { code: GROUND.asphalt, order: 7 },
};

export const GRID_RES = 0.25;

export interface GroundGrid {
  w: number;
  h: number;
  /** Row 0 is the southernmost row (y grows north). */
  code: Uint8Array;
}

/** Rasterise landcover (even-odd) and buffered roads into a top-down grid over the AOI. */
export function buildGround(scene: Scene): GroundGrid {
  const w = Math.ceil(scene.aoiW / GRID_RES);
  const h = Math.ceil(scene.aoiH / GRID_RES);
  const code = new Uint8Array(w * h);
  for (const cover of scene.covers) {
    const value = (GROUND as Record<string, number>)[cover.cls];
    if (value === undefined) continue;
    let y0 = Infinity;
    let y1 = -Infinity;
    for (const r of cover.rings)
      for (const [, y] of r) {
        y0 = Math.min(y0, y);
        y1 = Math.max(y1, y);
      }
    const g0 = Math.max(0, Math.ceil(y0 / GRID_RES - 0.5));
    const g1 = Math.min(h - 1, Math.floor(y1 / GRID_RES - 0.5));
    for (let gy = g0; gy <= g1; gy++) {
      const yc = (gy + 0.5) * GRID_RES;
      const xs: number[] = [];
      for (const r of cover.rings)
        for (let i = 0; i + 1 < r.length; i++) {
          let [ax, ay] = r[i];
          let [bx, by] = r[i + 1];
          if (ay === by) continue;
          if (ay > by) [ax, ay, bx, by] = [bx, by, ax, ay];
          if (yc >= ay && yc < by) xs.push(ax + ((yc - ay) * (bx - ax)) / (by - ay));
        }
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const i0 = Math.max(0, Math.ceil(xs[k] / GRID_RES - 0.5));
        const i1 = Math.min(w, Math.ceil(xs[k + 1] / GRID_RES - 0.5));
        code.fill(value, gy * w + i0, gy * w + Math.max(i0, i1));
      }
    }
  }
  const roads = scene.roads
    .filter((r) => r.layer >= 0 && ROAD[r.cls])
    .sort((a, b) => ROAD[a.cls].order - ROAD[b.cls].order || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  for (const road of roads) {
    const hw = road.widthM / 2;
    const value = ROAD[road.cls].code;
    for (let i = 0; i + 1 < road.line.length; i++) {
      const [ax, ay] = road.line[i];
      const [bx, by] = road.line[i + 1];
      const dx = bx - ax;
      const dy = by - ay;
      const l2 = dx * dx + dy * dy;
      const gx0 = Math.max(0, Math.floor((Math.min(ax, bx) - hw) / GRID_RES));
      const gx1 = Math.min(w - 1, Math.floor((Math.max(ax, bx) + hw) / GRID_RES));
      const gy0 = Math.max(0, Math.floor((Math.min(ay, by) - hw) / GRID_RES));
      const gy1 = Math.min(h - 1, Math.floor((Math.max(ay, by) + hw) / GRID_RES));
      for (let gy = gy0; gy <= gy1; gy++)
        for (let gx = gx0; gx <= gx1; gx++) {
          const cx = (gx + 0.5) * GRID_RES - ax;
          const cy = (gy + 0.5) * GRID_RES - ay;
          let tt = l2 > 0 ? (cx * dx + cy * dy) / l2 : 0;
          tt = Math.min(Math.max(tt, 0), 1);
          const ex = cx - tt * dx;
          const ey = cy - tt * dy;
          if (ex * ex + ey * ey <= hw * hw) code[gy * w + gx] = value;
        }
    }
  }
  return { w, h, code };
}
