// Projection, terrain-aware picking and the geographic affine (projection.md §3, §5, §6).
// Dependency-free on purpose; it is the viewer's own implementation of the contract.
import type { HeightGridMeta, Manifest } from './types'

export interface Camera {
  m: number[][]; t: number[] // image = m · (x,y,z) + t, local metres
  E0: number; N0: number; H0: number
}
export interface Grid { meta: HeightGridMeta; data: Uint16Array }
export interface Pick { E: number; N: number; H: number }

export function cameraOf(man: Manifest): Camera {
  const { matrix, translation, origin } = man.projection
  return { m: matrix, t: translation, ...origin }
}

/** §3 forward: world (E, N, H) → image (X, Y). */
export function forward(c: Camera, E: number, N: number, H: number): [number, number] {
  const x = E - c.E0, y = N - c.N0, z = H - c.H0
  return [c.m[0][0] * x + c.m[0][1] * y + c.m[0][2] * z + c.t[0],
    c.m[1][0] * x + c.m[1][1] * y + c.m[1][2] * z + c.t[1]]
}

// Camera angles and scale recovered from the matrix (the manifest matrix is authoritative).
function angles(c: Camera) {
  const s = Math.hypot(c.m[0][0], c.m[0][1])
  return {
    s, cosA: c.m[0][0] / s, sinA: -c.m[0][1] / s,
    sinP: Math.hypot(c.m[1][0], c.m[1][1]) / s, cosP: -c.m[1][2] / s,
  }
}

/** §5.1 reference-plane inverse at local height zr (metres above H0). Returns world E, N. */
export function inverseAtHeight(c: Camera, X: number, Y: number, zr: number): [number, number] {
  const { s, cosA, sinA, sinP, cosP } = angles(c)
  const a = (X - c.t[0]) / s
  const b = (-(Y - c.t[1]) / s - zr * cosP) / sinP
  return [c.E0 + a * cosA + b * sinA, c.N0 - a * sinA + b * cosA]
}

export function parseGrid(meta: HeightGridMeta, buf: ArrayBuffer): Grid {
  if (buf.byteLength !== meta.width * meta.height * 2) {
    throw new Error(`height grid has ${buf.byteLength} bytes, expected ${meta.width * meta.height * 2}`)
  }
  const dv = new DataView(buf) // little-endian regardless of platform
  const data = new Uint16Array(meta.width * meta.height)
  for (let i = 0; i < data.length; i++) data[i] = dv.getUint16(i * 2, true)
  return { meta, data }
}

export function inGrid(g: Grid, E: number, N: number): boolean {
  const m = g.meta
  return E >= m.westE && E <= m.westE + m.width * m.cellSize &&
    N <= m.northN && N >= m.northN - m.height * m.cellSize
}

/** Bilinear between cell centres, clamped to the nearest centre in the border. Row 0 is north. */
export function terrain(g: Grid, E: number, N: number): number {
  const m = g.meta
  const clamp = (v: number, hi: number) => Math.min(Math.max(v, 0), hi)
  const fx = clamp((E - m.westE) / m.cellSize - 0.5, m.width - 1)
  const fy = clamp((m.northN - N) / m.cellSize - 0.5, m.height - 1)
  const i = Math.min(Math.floor(fx), m.width - 2), j = Math.min(Math.floor(fy), m.height - 2)
  const u = fx - i, v = fy - j
  const at = (ii: number, jj: number) => g.data[Math.max(jj, 0) * m.width + Math.max(ii, 0)]
  const q = Math.max(i, 0), r = Math.max(j, 0) // grids of one cell: degenerate but defined
  const val = (at(q, r) * (1 - u) + at(q + 1, r) * u) * (1 - v) + (at(q, r + 1) * (1 - u) + at(q + 1, r + 1) * u) * v
  return m.offset + m.scale * val
}

/** §5.2 terrain-aware pick; null = no pick (ray never meets the grid). */
export function pick(c: Camera, g: Grid, zMin: number, zMax: number, X: number, Y: number): Pick | null {
  const { s, cosA, sinA, sinP, cosP } = angles(c)
  const m = g.meta
  const a = (X - c.t[0]) / s, q = -(Y - c.t[1]) / s
  const px = (b: number) => c.E0 + a * cosA + b * sinA
  const py = (b: number) => c.N0 - a * sinA + b * cosA
  const zOf = (b: number) => (q - b * sinP) / cosP + c.H0 // absolute height of the ray
  // b interval inside the grid rectangle (slab test; direction is (sinA, cosA) in (E, N))
  let lo = -Infinity, hi = Infinity
  const slab = (p0: number, d: number, min: number, max: number) => {
    if (Math.abs(d) < 1e-12) { if (p0 < min || p0 > max) hi = -Infinity; return }
    const t1 = (min - p0) / d, t2 = (max - p0) / d
    lo = Math.max(lo, Math.min(t1, t2)); hi = Math.min(hi, Math.max(t1, t2))
  }
  slab(px(0), sinA, m.westE, m.westE + m.width * m.cellSize)
  slab(py(0), cosA, m.northN - m.height * m.cellSize, m.northN)
  const start = Math.max(lo, (q - zMax * cosP) / sinP)
  const end = Math.min(hi, (q - zMin * cosP) / sinP)
  if (!(start <= end)) return null
  const above = (b: number) => zOf(b) > terrain(g, px(b), py(b))
  if (!above(start)) return finish(start)
  const step = 0.5 * m.cellSize
  let prev = start
  for (let b = start + step; ; b += step) {
    const cur = Math.min(b, end)
    if (!above(cur)) {
      let l = prev, h = cur
      while (h - l > 0.01) { const mid = (l + h) / 2; if (above(mid)) l = mid; else h = mid }
      return finish((l + h) / 2)
    }
    if (cur >= end) return null
    prev = cur
  }
  function finish(b: number): Pick { return { E: px(b), N: py(b), H: terrain(g, px(b), py(b)) } }
}

/** geoToWorld: (lon, lat) → (E, N) and its algebraic inverse. */
export function geoToWorld(mat: number[][], lon: number, lat: number): [number, number] {
  return [mat[0][0] * lon + mat[0][1] * lat + mat[0][2], mat[1][0] * lon + mat[1][1] * lat + mat[1][2]]
}
export function worldToGeo(mat: number[][], E: number, N: number): { lon: number; lat: number } {
  const [[a, b, c], [d, e, f]] = mat
  const det = a * e - b * d
  const x = E - c, y = N - f
  return { lon: (e * x - b * y) / det, lat: (-d * x + a * y) / det }
}
