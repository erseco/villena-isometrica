import { expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cosDeg, forward, forwardUVD, makeProjection, sinDeg, unproject } from '../src/projection.ts';

const ROOT = resolve(import.meta.dir, '../../..');
const json = (p: string) => JSON.parse(readFileSync(resolve(ROOT, p), 'utf8'));

test('forward projection reproduces every contract vector within 1e-6', () => {
  const vectors = json('packages/geo-contracts/fixtures/projection-vectors.json');
  let n = 0;
  for (const cam of vectors.cameras) {
    const pr = makeProjection(cam, 1, 1, 0, 1);
    for (const pt of cam.points) {
      const [u, v, d] = forwardUVD(pr, pt.xyz[0], pt.xyz[1], pt.xyz[2]);
      expect(Math.abs(u - pt.u)).toBeLessThan(1e-6);
      expect(Math.abs(v - pt.v)).toBeLessThan(1e-6);
      expect(Math.abs(d - pt.d)).toBeLessThan(1e-6);
      n++;
    }
  }
  expect(n).toBeGreaterThan(10);
});

test('deterministic sin/cos agree with the platform functions to a few ulp', () => {
  for (let deg = 0; deg <= 360; deg += 0.25) {
    expect(Math.abs(sinDeg(deg) - Math.sin((deg * Math.PI) / 180))).toBeLessThan(2e-15);
    expect(Math.abs(cosDeg(deg) - Math.cos((deg * Math.PI) / 180))).toBeLessThan(2e-15);
  }
  expect(sinDeg(0)).toBe(0);
  expect(sinDeg(90)).toBe(1);
  expect(cosDeg(90)).toBe(0);
});

test('synthetic city: image size, translation and matrix match projection.md section 3', () => {
  const city = json('tests/fixtures/city-synthetic/city.json');
  const scene = json('tests/fixtures/scene-synthetic/scene.json');
  const fixture = json('tests/fixtures/render-synthetic/render.json');
  const [minE, minN, maxE, maxN] = scene.aoi.bounds;
  const pr = makeProjection(city.camera, maxE - minE, maxN - minN, scene.zRange.zMin, scene.zRange.zMax);
  expect([pr.width, pr.height]).toEqual([726, 481]);
  expect(pr.translation).toEqual(fixture.projection.translation);
  for (let i = 0; i < 2; i++)
    for (let j = 0; j < 3; j++) expect(Math.abs(pr.matrix[i][j] - fixture.projection.matrix[i][j])).toBeLessThan(1e-9);
  // AOI south-west corner at z = 0 lands exactly at (-u0, -v0): no half-pixel shift.
  const [X, Y] = forward(pr, 0, 0, 0);
  expect([X, Y]).toEqual([363, 470]);
  // Independent check of the size: u spans +-128 * 4 * cos 45, v spans the prism height.
  const half = 128 * 4 * Math.SQRT1_2;
  expect(pr.width).toBe(Math.ceil(half) - Math.floor(-half));
});

test('surface pick inverts forward projection', () => {
  const pr = makeProjection({ headingDeg: 45, pitchDeg: 30, pixelsPerMetre: 8 }, 1000, 1000, -7, 163);
  for (const [x, y, z] of [
    [0, 0, 0],
    [123.45, 678.9, 55.5],
    [999, 1, -6],
  ]) {
    const [X, Y, d] = forward(pr, x, y, z);
    const [x2, y2, z2] = unproject(pr, X, Y, d);
    expect(Math.abs(x2 - x) + Math.abs(y2 - y) + Math.abs(z2 - z)).toBeLessThan(1e-6);
  }
});

test('render path uses no implementation-approximated Math functions', () => {
  for (const f of ['projection', 'geometry', 'raster', 'style', 'render', 'png', 'scene']) {
    const src = readFileSync(resolve(import.meta.dir, `../src/${f}.ts`), 'utf8');
    expect(
      src.match(/Math\.(sin|cos|tan|asin|acos|atan2?|pow|exp|expm1|log\w*|hypot|cbrt|sinh|cosh|tanh)\b|\s\*\*\s/g),
    ).toBe(null);
  }
});
