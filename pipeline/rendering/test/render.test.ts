import { expect, test } from 'bun:test';
import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { hipRoof } from '../src/geometry.ts';
import { decodePng } from '../src/png.ts';
import { forward } from '../src/projection.ts';
import { loadPalette, type RenderResult, render, renderFiles, sha256 } from '../src/render.ts';
import { loadCity, loadScene } from '../src/scene.ts';

const ROOT = resolve(import.meta.dir, '../../..');
const SCENE_DIR = resolve(ROOT, 'tests/fixtures/scene-synthetic');
const CITY = resolve(ROOT, 'tests/fixtures/city-synthetic/city.json');
const GOLDEN = resolve(import.meta.dir, 'golden.json');

const city = loadCity(CITY);
const scene = loadScene(SCENE_DIR, city);
const palette = loadPalette();
const run = (chunk?: number): RenderResult => render(scene, city, palette.doc, { chunk, depth: true });
const base = run();
const { files, manifest } = renderFiles(base, scene, city, palette.bytes);
const layer = (name: string) => base.layers.find((l) => l.name === name)?.samples as Uint8Array;
const pixelHashes = (r: RenderResult) => Object.fromEntries(r.layers.map((l) => [l.name, sha256(l.samples)]));
const W = base.projection.width;

test('render.json and palette.json validate against their schemas', () => {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  const schema = (n: string) =>
    JSON.parse(readFileSync(resolve(ROOT, `packages/geo-contracts/schemas/${n}.schema.json`), 'utf8'));
  const checkRender = ajv.compile(schema('render-manifest'));
  expect(checkRender(manifest)).toBe(true);
  expect(ajv.validate(schema('palette'), JSON.parse(palette.bytes.toString()))).toBe(true);
  expect(palette.doc.colors.length).toBeLessThanOrEqual(64);
  expect([manifest.image]).toEqual([{ width: 726, height: 481 }]);
});

test('pixelSha256 of every layer matches the committed golden file', () => {
  expect(pixelHashes(base)).toEqual(JSON.parse(readFileSync(GOLDEN, 'utf8')));
});

test('different chunk sizes give identical layers', () => {
  const want = pixelHashes(base);
  for (const chunk of [64, 300, 1000]) expect(pixelHashes(run(chunk))).toEqual(want);
});

test('two runs give byte-identical files', () => {
  const again = renderFiles(run(), scene, city, palette.bytes).files;
  expect([...again.keys()].sort()).toEqual([...files.keys()].sort());
  for (const [name, bytes] of files) expect(sha256(again.get(name) as Uint8Array)).toBe(sha256(bytes));
});

test('decoded PNG samples hash to the declared pixelSha256', () => {
  const layers = manifest.layers as { path: string; pixelSha256: string; sha256: string }[];
  expect(layers.map((l) => l.path)).toEqual(['color.png', 'class.png', 'buildingId.png', 'depth.png']);
  for (const l of layers) {
    const png = files.get(l.path) as Uint8Array;
    expect(sha256(png)).toBe(l.sha256);
    const img = decodePng(png);
    expect([img.width, img.height]).toEqual([726, 481]);
    expect(sha256(img.data)).toBe(l.pixelSha256);
  }
});

test('every drawn colour pixel is a palette colour with alpha 0 or 255', () => {
  const allowed = new Set(palette.doc.colors.map((c) => c.hex));
  const color = layer('color');
  const cls = layer('class');
  let drawn = 0;
  for (let i = 0; i < color.length / 4; i++) {
    const a = color[4 * i + 3];
    expect(a === 0 || a === 255).toBe(true);
    expect(a === 0).toBe(cls[i] === 0);
    if (a === 0) continue;
    drawn++;
    const hex = `#${[0, 1, 2].map((k) => color[4 * i + k].toString(16).padStart(2, '0')).join('')}`;
    if (!allowed.has(hex)) throw new Error(`pixel ${i} has colour ${hex} outside the palette`);
  }
  // The AOI diamond covers roughly half of the image rectangle.
  expect(drawn).toBeGreaterThan((0.4 * color.length) / 4);
});

test('class and buildingId layers are registered with each other', () => {
  const cls = layer('class');
  const bid = layer('buildingId');
  const counts = new Map<number, number>();
  for (let i = 0; i < cls.length; i++) {
    const id = (bid[3 * i] << 16) | (bid[3 * i + 1] << 8) | bid[3 * i + 2];
    expect(cls[i] === 3 || cls[i] === 4).toBe(id !== 0);
    expect(id).toBeLessThanOrEqual(base.ids.length);
    counts.set(cls[i], (counts.get(cls[i]) ?? 0) + 1);
  }
  // ground, road, wall, roof and vegetation are all present.
  for (const c of [1, 2, 3, 4, 5]) expect(counts.get(c) ?? 0).toBeGreaterThan(50);
});

test('the pixel at each building roof centre carries that building', () => {
  const bid = layer('buildingId');
  const index = JSON.parse(Buffer.from(files.get('buildingId.json') as Uint8Array).toString());
  expect(index[0]).toBe(null);
  const features = JSON.parse(readFileSync(join(SCENE_DIR, 'buildings.geojson'), 'utf8')).features;
  const buildingOfPart = new Map(
    features.map((f: { properties: { id: string; buildingId: string } }) => [f.properties.id, f.properties.buildingId]),
  );
  for (const f of features) {
    const q = f.properties;
    const ring: number[][] = f.geometry.coordinates[0];
    const xs = ring.map((c) => c[0] - 700000);
    const ys = ring.map((c) => c[1] - 4270000);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    // Hipped roof on a rectangle: apex = half the short side at 30 deg, at most 6 m.
    const rise = q.roof === 'pitched' ? Math.min((Math.min(x1 - x0, y1 - y0) / 2) * Math.tan(Math.PI / 6), 6) : 0;
    const [X, Y] = forward(base.projection, (x0 + x1) / 2, (y0 + y1) / 2, q.baseH - 500 + q.heightM + rise);
    const i = Math.floor(Y) * W + Math.floor(X);
    const id = (bid[3 * i] << 16) | (bid[3 * i + 1] << 8) | bid[3 * i + 2];
    expect(buildingOfPart.get(index[id])).toBe(q.buildingId);
  }
});

test('hipped roof reaches exactly ridgeHeightM when given, else 30 deg capped at 6 m', () => {
  const rect: [number, number][] = [
    [0, 0],
    [20, 0],
    [20, 8],
    [0, 8],
  ];
  const top = (fs: ReturnType<typeof hipRoof>) =>
    Math.max(...fs.flatMap((f) => f.pts.map(([x, y]) => f.z0 + f.k * (f.ux * (y - f.ay) - f.uy * (x - f.ax)))));
  expect(top(hipRoof(rect, 10, 13.5))).toBeCloseTo(13.5, 12);
  expect(top(hipRoof(rect, 10, null))).toBeCloseTo(10 + 4 * Math.tan(Math.PI / 6), 12);
  const big: [number, number][] = [
    [0, 0],
    [60, 0],
    [60, 40],
    [0, 40],
  ];
  expect(top(hipRoof(big, 10, null))).toBeCloseTo(16, 12);
});

test('CLI rejects invalid input with a clear message and a non-zero exit', () => {
  const dir = mkdtempSync(join(tmpdir(), 'render-bad-'));
  cpSync(SCENE_DIR, dir, { recursive: true });
  const m = JSON.parse(readFileSync(join(dir, 'scene.json'), 'utf8'));
  delete m.terrain;
  writeFileSync(join(dir, 'scene.json'), JSON.stringify(m));
  const cli = resolve(import.meta.dir, '../src/cli.ts');
  const r = spawnSync(process.execPath, [cli, '--scene', dir, '--city', CITY, '--out', join(dir, 'out')]);
  expect(r.status).toBe(1);
  expect(r.stderr.toString()).toContain('scene-manifest.schema.json');
  const usage = spawnSync(process.execPath, [cli, '--scene', dir]);
  expect(usage.status).toBe(2);
  rmSync(dir, { recursive: true, force: true });
});
