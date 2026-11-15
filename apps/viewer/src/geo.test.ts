import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { cameraOf, forward, geoToWorld, inGrid, inverseAtHeight, parseGrid, pick, terrain, worldToGeo } from './geo'
import type { Manifest } from './types'

const FIX = new URL('../../../tests/fixtures/tiles-synthetic/', import.meta.url)
const VEC = new URL('../../../packages/geo-contracts/fixtures/projection-vectors.json', import.meta.url)
const read = (u: URL) => readFileSync(u)
const man: Manifest = JSON.parse(read(new URL('manifest.json', FIX)).toString())
const exp = JSON.parse(read(new URL('expected.json', FIX)).toString())
const vec = JSON.parse(read(VEC).toString())
const cam = cameraOf(man)
const gridBuf = read(new URL('height.u16', FIX))
const grid = parseGrid(man.heightGrid!, gridBuf.buffer.slice(gridBuf.byteOffset, gridBuf.byteOffset + gridBuf.byteLength))
const { zMin, zMax } = man.zRange

describe('forward', () => {
  test('fixture ground points within 1e-3 px', () => {
    for (const p of exp.groundPoints) {
      const [X, Y] = forward(cam, p.E, p.N, p.H)
      expect(Math.abs(X - p.X)).toBeLessThan(1e-3)
      expect(Math.abs(Y - p.Y)).toBeLessThan(1e-3)
    }
  })
  test('contract vectors (u, v) within 1e-6 with a matrix built from the camera', () => {
    for (const c of vec.cameras) {
      const a = (c.headingDeg * Math.PI) / 180, p = (c.pitchDeg * Math.PI) / 180, s = c.pixelsPerMetre
      const k = { E0: 0, N0: 0, H0: 0, t: [0, 0],
        m: [[s * Math.cos(a), -s * Math.sin(a), 0], [-s * Math.sin(a) * Math.sin(p), -s * Math.cos(a) * Math.sin(p), -s * Math.cos(p)]] }
      for (const pt of c.points) {
        const [u, v] = forward(k, ...(pt.xyz as [number, number, number]))
        expect(Math.abs(u - pt.u)).toBeLessThan(1e-6)
        expect(Math.abs(v - pt.v)).toBeLessThan(1e-6)
      }
    }
  })
})

describe('reference plane', () => {
  test('closed-form cases exact to 1e-6 m (zr = H0 - H0 = 0)', () => {
    for (const c of exp.referencePlane.cases) {
      const [E, N] = inverseAtHeight(cam, c.X, c.Y, 0)
      expect(Math.abs(E - c.E)).toBeLessThan(1e-6)
      expect(Math.abs(N - c.N)).toBeLessThan(1e-4)
    }
  })
  test('inverse(forward(P), z) = P', () => {
    const [X, Y] = forward(cam, 700033.3, 4270077.7, 507.215)
    const [E, N] = inverseAtHeight(cam, X, Y, 7.215)
    expect(Math.abs(E - 700033.3)).toBeLessThan(1e-6)
    expect(Math.abs(N - 4270077.7)).toBeLessThan(1e-6)
  })
})

describe('terrain pick', () => {
  test('recovers every fixture ground point within 0.05 m', () => {
    for (const p of exp.groundPoints) {
      const r = pick(cam, grid, zMin, zMax, p.X, p.Y)
      expect(r).not.toBeNull()
      expect(Math.abs(r!.E - p.E)).toBeLessThan(0.05)
      expect(Math.abs(r!.N - p.N)).toBeLessThan(0.05)
    }
  })
  test('background corners have no pick', () => {
    expect(pick(cam, grid, zMin, zMax, 0, 0)).toBeNull()
    expect(pick(cam, grid, zMin, zMax, 726, 0)).toBeNull()
    expect(pick(cam, grid, zMin, zMax, 0, 481)).toBeNull()
  })
  test('grid helpers', () => {
    expect(inGrid(grid, 700000, 4270000)).toBe(true)
    expect(inGrid(grid, 800000, 4270000)).toBe(false)
    expect(Math.abs(terrain(grid, 700100, 4270020) - 511.0)).toBeLessThan(0.02)
  })
  test('rejects a grid of the wrong size', () => {
    expect(() => parseGrid(man.heightGrid!, new ArrayBuffer(10))).toThrow()
  })
})

describe('geoToWorld', () => {
  test('lon/lat → E/N within the manifest residual, and the inverse round-trips', () => {
    for (const p of exp.groundPoints) {
      const [E, N] = geoToWorld(man.geoToWorld.matrix, p.lon, p.lat)
      expect(Math.hypot(E - p.E, N - p.N)).toBeLessThan(Math.max(man.geoToWorld.maxResidualM, 0.01))
      const g = worldToGeo(man.geoToWorld.matrix, p.E, p.N)
      expect(Math.abs(g.lon - p.lon)).toBeLessThan(2e-7)
      expect(Math.abs(g.lat - p.lat)).toBeLessThan(2e-7)
    }
  })
})
