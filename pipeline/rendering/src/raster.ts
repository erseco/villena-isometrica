// Stage 1: software rasteriser into integer-addressed G-buffers (surface id + depth).
//
// Coverage: vertices are snapped to a 1/256 px grid; a pixel is covered when its centre lies
// inside the polygon by the even-odd rule, with half-open edge spans ([top, bottom) rows,
// [left, right) columns) so pixels on a shared edge belong to exactly one of the two polygons.
// Depth is evaluated from the exact plane at each pixel centre in absolute image coordinates,
// never incrementally, so the result does not depend on how the image is chunked.
import { type Geometry, type Poly, SUB, type TreePrim } from './geometry.ts';
import type { Projection } from './projection.ts';

export interface GBuffer {
  /** Absolute image position of element 0. */
  x0: number;
  y0: number;
  w: number;
  h: number;
  depth: Float64Array;
  surf: Uint32Array;
}

export interface Prism {
  aoiW: number;
  aoiH: number;
  zMin: number;
  zMax: number;
}

export function makeGBuffer(x0: number, y0: number, w: number, h: number): GBuffer {
  return { x0, y0, w, h, depth: new Float64Array(w * h).fill(Infinity), surf: new Uint32Array(w * h) };
}

const HALF = SUB / 2;
let xs = new Float64Array(64);

function fill(
  g: GBuffer,
  pr: Projection,
  prism: Prism | null,
  rings: Float64Array[],
  minY: number,
  maxY: number,
  nr: number,
  np: number,
  nw: number,
  c: number,
  surf: number,
): void {
  const j0 = Math.max(Math.ceil((minY - HALF) / SUB), g.y0);
  const j1 = Math.min(Math.ceil((maxY - HALF) / SUB), g.y0 + g.h);
  const { s, r, p, w } = pr;
  const [tx, ty] = pr.translation;
  const gx1 = g.x0 + g.w;
  for (let j = j0; j < j1; j++) {
    const yc = j * SUB + HALF;
    let n = 0;
    for (const ring of rings) {
      const m = ring.length;
      for (let k = 0; k < m; k += 2) {
        let ax = ring[k];
        let ay = ring[k + 1];
        let bx = ring[(k + 2) % m];
        let by = ring[(k + 3) % m];
        if (ay === by) continue;
        if (ay > by) {
          const t0 = ax;
          const t1 = ay;
          ax = bx;
          ay = by;
          bx = t0;
          by = t1;
        }
        if (yc < ay || yc >= by) continue;
        if (n === xs.length) {
          const bigger = new Float64Array(n * 2);
          bigger.set(xs);
          xs = bigger;
        }
        xs[n++] = ax + ((yc - ay) * (bx - ax)) / (by - ay);
      }
    }
    for (let a = 1; a < n; a++) {
      const v = xs[a];
      let b = a - 1;
      while (b >= 0 && xs[b] > v) {
        xs[b + 1] = xs[b];
        b--;
      }
      xs[b + 1] = v;
    }
    const bb = (j + 0.5 - ty) / s;
    const row = (j - g.y0) * g.w - g.x0;
    for (let k = 0; k + 1 < n; k += 2) {
      const i0 = Math.max(Math.ceil((xs[k] - HALF) / SUB), g.x0);
      const i1 = Math.min(Math.ceil((xs[k + 1] - HALF) / SUB), gx1);
      for (let i = i0; i < i1; i++) {
        const aa = (i + 0.5 - tx) / s;
        const d = (c - aa * nr + bb * np) / nw;
        const idx = row + i;
        if (!(d < g.depth[idx])) continue;
        if (prism) {
          const x = aa * r[0] - bb * p[0] + d * w[0];
          const y = aa * r[1] - bb * p[1] + d * w[1];
          const z = -bb * p[2] + d * w[2];
          if (x < 0 || x > prism.aoiW || y < 0 || y > prism.aoiH || z < prism.zMin || z > prism.zMax) continue;
        }
        g.depth[idx] = d;
        g.surf[idx] = surf;
      }
    }
  }
}

function overlaps(g: GBuffer, minX: number, maxX: number, minY: number, maxY: number): boolean {
  return maxX >= g.x0 * SUB && minX <= (g.x0 + g.w) * SUB && maxY >= g.y0 * SUB && minY <= (g.y0 + g.h) * SUB;
}

const tri = new Float64Array(6);

export function rasterTerrain(g: GBuffer, geo: Geometry, pr: Projection, prism: Prism, t: TerrainLike): void {
  const W = t.width;
  const qw = W - 1;
  const cs = t.cellSize;
  const { tX, tY } = geo;
  for (let n = 0; n < geo.cells.length; n++) {
    const q = geo.cells[n];
    const r = (q / qw) | 0;
    const c = q - r * qw;
    const iA = r * W + c;
    const iB = iA + 1;
    const iC = iA + W;
    const iD = iC + 1;
    const minX = Math.min(tX[iA], tX[iB], tX[iC], tX[iD]);
    const maxX = Math.max(tX[iA], tX[iB], tX[iC], tX[iD]);
    const minY = Math.min(tY[iA], tY[iB], tY[iC], tY[iD]);
    const maxY = Math.max(tY[iA], tY[iB], tY[iC], tY[iD]);
    if (!overlaps(g, minX, maxX, minY, maxY)) continue;
    const xw = t.x0 + c * cs;
    const yn = t.y0 - r * cs;
    const zA = t.z[iA];
    const zB = t.z[iB];
    const zC = t.z[iC];
    const zD = t.z[iD];
    const clip =
      xw < 0 ||
      xw + cs > prism.aoiW ||
      yn - cs < 0 ||
      yn > prism.aoiH ||
      Math.min(zA, zB, zC, zD) < prism.zMin ||
      Math.max(zA, zB, zC, zD) > prism.zMax;
    // Triangle 0 = A C D, triangle 1 = A D B (diagonal NW-SE); normals as in geometry.ts.
    for (let k = 0; k < 2; k++) {
      const nx = k === 0 ? zC - zD : zA - zB;
      const ny = k === 0 ? zC - zA : zD - zB;
      const [i1, i2] = k === 0 ? [iC, iD] : [iD, iB];
      tri[0] = tX[iA];
      tri[1] = tY[iA];
      tri[2] = tX[i1];
      tri[3] = tY[i1];
      tri[4] = tX[i2];
      tri[5] = tY[i2];
      const nr = nx * pr.r[0] + ny * pr.r[1] + cs * pr.r[2];
      const np = nx * pr.p[0] + ny * pr.p[1] + cs * pr.p[2];
      const nw = nx * pr.w[0] + ny * pr.w[1] + cs * pr.w[2];
      const cc = nx * xw + ny * yn + cs * zA;
      fill(g, pr, clip ? prism : null, [tri], minY, maxY, nr, np, nw, cc, 1 + 2 * q + k);
    }
  }
}

export interface TerrainLike {
  width: number;
  cellSize: number;
  x0: number;
  y0: number;
  z: Float64Array;
}

export function rasterPolys(g: GBuffer, polys: Poly[], pr: Projection, prism: Prism): void {
  for (const q of polys) {
    if (!overlaps(g, q.minX, q.maxX, q.minY, q.maxY)) continue;
    fill(g, pr, q.clip ? prism : null, q.rings, q.minY, q.maxY, q.nr, q.np, q.nw, q.c, q.surf);
  }
}

function inPrism(pr: Projection, prism: Prism, X: number, Y: number, d: number): boolean {
  const a = (X - pr.translation[0]) / pr.s;
  const b = (Y - pr.translation[1]) / pr.s;
  const x = a * pr.r[0] - b * pr.p[0] + d * pr.w[0];
  const y = a * pr.r[1] - b * pr.p[1] + d * pr.w[1];
  const z = -b * pr.p[2] + d * pr.w[2];
  return x >= 0 && x <= prism.aoiW && y >= 0 && y <= prism.aoiH && z >= prism.zMin && z <= prism.zMax;
}

/** Trees: a sphere (crown) and a vertical segment of fixed pixel width (trunk). */
export function rasterTrees(g: GBuffer, trees: TreePrim[], pr: Projection, prism: Prism): void {
  const cf = pr.p[2];
  for (const t of trees) {
    // Trunk first; the crown in front of it wins on depth.
    if (cf > 0) {
      const i0 = Math.max(Math.ceil(t.bX - t.halfW - 0.5), g.x0);
      const i1 = Math.min(Math.floor(t.bX + t.halfW - 0.5) + 1, g.x0 + g.w);
      const top = t.bY - t.trunkM * pr.s * cf;
      const j0 = Math.max(Math.ceil(top - 0.5), g.y0);
      const j1 = Math.min(Math.floor(t.bY - 0.5) + 1, g.y0 + g.h);
      for (let j = j0; j < j1; j++) {
        const z = (t.bY - (j + 0.5)) / (pr.s * cf);
        if (z < 0 || z > t.trunkM) continue;
        const d = t.bD + z * pr.w[2];
        for (let i = i0; i < i1; i++) {
          if (Math.abs(i + 0.5 - t.bX) > t.halfW) continue;
          const idx = (j - g.y0) * g.w + (i - g.x0);
          if (!(d < g.depth[idx])) continue;
          if (t.clip && !inPrism(pr, prism, i + 0.5, j + 0.5, d)) continue;
          g.depth[idx] = d;
          g.surf[idx] = t.surfTrunk;
        }
      }
    }
    const r2 = t.rPx * t.rPx;
    const i0 = Math.max(Math.ceil(t.cX - t.rPx - 0.5), g.x0);
    const i1 = Math.min(Math.floor(t.cX + t.rPx - 0.5) + 1, g.x0 + g.w);
    const j0 = Math.max(Math.ceil(t.cY - t.rPx - 0.5), g.y0);
    const j1 = Math.min(Math.floor(t.cY + t.rPx - 0.5) + 1, g.y0 + g.h);
    const s2 = pr.s * pr.s;
    for (let j = j0; j < j1; j++)
      for (let i = i0; i < i1; i++) {
        const dx = i + 0.5 - t.cX;
        const dy = j + 0.5 - t.cY;
        const q = dx * dx + dy * dy;
        if (q > r2) continue;
        const d = t.cD - Math.sqrt(Math.max(t.rM * t.rM - q / s2, 0));
        const idx = (j - g.y0) * g.w + (i - g.x0);
        if (!(d < g.depth[idx])) continue;
        if (t.clip && !inPrism(pr, prism, i + 0.5, j + 0.5, d)) continue;
        g.depth[idx] = d;
        g.surf[idx] = t.surfCrown;
      }
  }
}
