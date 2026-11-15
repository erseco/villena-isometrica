// Evaluates the TypeScript implementations of the projection on inputs chosen by the Python tests, which hold
// every expected value. Usage: bun dump.ts <input.json>  (writes JSON to stdout). No expected value lives here.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { forward as viewerForward, inverseAtHeight, parseGrid, pick } from '../../../apps/viewer/src/geo.ts'
import { forward as rendererForward, forwardUVD, makeProjection, unproject } from '../../../pipeline/rendering/src/projection.ts'

const input = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const out: Record<string, unknown> = {}

// viewer: forward and reference-plane inverse from a manifest-style camera (matrix + translation + origin)
out.viewer = (input.viewer ?? []).map((c: any) => {
  const cam = { m: c.matrix, t: c.translation, E0: c.origin.E0, N0: c.origin.N0, H0: c.origin.H0 }
  return {
    forward: (c.forward ?? []).map(([E, N, H]: number[]) => viewerForward(cam, E, N, H)),
    inverse: (c.inverse ?? []).map(([X, Y, zr]: number[]) => inverseAtHeight(cam, X, Y, zr)),
  }
})

// renderer: camera + prism -> matrix, translation, size; forward (X, Y, d) and forwardUVD (u, v, d, no origin offset); surface pick (X, Y, d) -> local x, y, z
out.renderer = (input.renderer ?? []).map((c: any) => {
  const pr = makeProjection(c.camera, c.aoi[0], c.aoi[1], c.z[0], c.z[1])
  return {
    matrix: pr.matrix, translation: pr.translation, width: pr.width, height: pr.height,
    forward: (c.forward ?? []).map(([x, y, z]: number[]) => rendererForward(pr, x, y, z)),
    uvd: (c.forward ?? []).map(([x, y, z]: number[]) => forwardUVD(pr, x, y, z)),
    unproject: (c.unproject ?? []).map(([X, Y, d]: number[]) => unproject(pr, X, Y, d)),
  }
})

// viewer: terrain-aware pick on a published tile directory
if (input.pick) {
  const dir = resolve(input.pick.dir)
  const man = JSON.parse(readFileSync(`${dir}/manifest.json`, 'utf8'))
  const buf = readFileSync(`${dir}/${man.heightGrid.path}`)
  const grid = parseGrid(man.heightGrid, buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength))
  const cam = { m: man.projection.matrix, t: man.projection.translation, ...man.projection.origin }
  out.pick = input.pick.points.map(([X, Y]: number[]) => pick(cam, grid, man.zRange.zMin, man.zRange.zMax, X, Y))
}
console.log(JSON.stringify(out))
