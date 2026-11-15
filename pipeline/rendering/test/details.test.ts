// Scene contract v1.1: landmark details, battlement parts and curated materials.
import { afterAll, expect, test } from 'bun:test';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { loadPalette, type RenderResult, render, sha256 } from '../src/render.ts';
import { InputError, loadCity, loadScene } from '../src/scene.ts';
import { detailSpecs, ROOT, writeDetailScene } from './detail-scene.ts';

const CITY = resolve(ROOT, 'tests/fixtures/city-synthetic/city.json');
const GOLDEN = resolve(import.meta.dir, 'golden-details.json');
const tmp = mkdtempSync(join(tmpdir(), 'render-details-'));
afterAll(() => rmSync(tmp, { recursive: true, force: true }));

const city = loadCity(CITY);
const sceneDir = join(tmp, 'scene');
writeDetailScene(sceneDir);
const scene = loadScene(sceneDir, city);
const palette = loadPalette();
const run = (chunk?: number): RenderResult => render(scene, city, palette.doc, { chunk, depth: true });
const base = run();
const pixelHashes = (r: RenderResult) => Object.fromEntries(r.layers.map((l) => [l.name, sha256(l.samples)]));
const layer = (name: string) => base.layers.find((l) => l.name === name)?.samples as Uint8Array;
const W = base.projection.width;

test('detail scene loads: 7 details, parapet and material on parts', () => {
  expect(scene.details.map((d) => d.id)).toEqual(detailSpecs().map((d) => d.id));
  expect(scene.parts.filter((p) => p.parapet).map((p) => p.id)).toEqual(['syn-004_1', 'syn-005_1']);
  expect(scene.parts.find((p) => p.id === 'syn-006_1')?.material).toBe('plaster');
});

test('pixelSha256 of every layer matches test/golden-details.json', () => {
  if (process.env.UPDATE_GOLDEN === '1') writeFileSync(GOLDEN, `${JSON.stringify(pixelHashes(base), null, 2)}\n`);
  expect(pixelHashes(base)).toEqual(JSON.parse(readFileSync(GOLDEN, 'utf8')));
});

test('different chunk sizes give identical layers', () => {
  const want = pixelHashes(base);
  for (const chunk of [64, 300, 1000]) expect(pixelHashes(run(chunk))).toEqual(want);
});

test('detail pixels are class 7 and carry their detail id in the buildingId index', () => {
  const cls = layer('class');
  const bid = layer('buildingId');
  const nParts = scene.parts.length;
  expect(base.ids.slice(nParts)).toEqual(scene.details.map((d) => d.id));
  const perDetail = new Map<string, number>();
  for (let i = 0; i < cls.length; i++) {
    const id = (bid[3 * i] << 16) | (bid[3 * i + 1] << 8) | bid[3 * i + 2];
    expect(cls[i] === 7).toBe(id > nParts);
    if (cls[i] === 7) perDetail.set(base.ids[id - 1], (perDetail.get(base.ids[id - 1]) ?? 0) + 1);
  }
  for (const d of scene.details) expect(perDetail.get(d.id) ?? 0).toBeGreaterThan(20);
});

/** Image bounding box [left, top, right] of the pixels of one detail (px edges). */
function pixelBox(detailId: string): [number, number, number] {
  const bid = layer('buildingId');
  const want = base.ids.indexOf(detailId) + 1;
  let [l, t, r] = [Infinity, Infinity, -Infinity];
  for (let i = 0; i < bid.length / 3; i++)
    if (((bid[3 * i] << 16) | (bid[3 * i + 1] << 8) | bid[3 * i + 2]) === want) {
      const [X, Y] = [i % W, Math.floor(i / W)];
      [l, t, r] = [Math.min(l, X), Math.min(t, Y), Math.max(r, X + 1)];
    }
  return [l, t, r];
}

test('dome and square spire silhouettes match their projected extents (independent projection)', () => {
  // Projection written out from projection.md with the platform sin/cos (not renderer code).
  const { headingDeg, pitchDeg, pixelsPerMetre: s } = city.camera;
  const [sa, ca] = [Math.sin((headingDeg * Math.PI) / 180), Math.cos((headingDeg * Math.PI) / 180)];
  const [sf, cf] = [Math.sin((pitchDeg * Math.PI) / 180), Math.cos((pitchDeg * Math.PI) / 180)];
  const m = JSON.parse(readFileSync(join(sceneDir, 'scene.json'), 'utf8'));
  const [minE, minN, maxE, maxN] = m.aoi.bounds;
  const [aw, ah] = [maxE - minE, maxN - minN];
  const us: number[] = [];
  const vs: number[] = [];
  for (const x of [0, aw])
    for (const y of [0, ah])
      for (const z of [m.zRange.zMin, m.zRange.zMax]) {
        us.push(s * (x * ca - y * sa));
        vs.push(-s * ((x * sa + y * ca) * sf + z * cf));
      }
  const [tx, ty] = [-Math.floor(Math.min(...us)), -Math.floor(Math.min(...vs))];
  const X = (x: number, y: number) => s * (x * ca - y * sa) + tx;
  const Y = (x: number, y: number, z: number) => -s * ((x * sa + y * ca) * sf + z * cf) + ty;
  const spec = (id: string) => detailSpecs().find((d) => d.id === id) as ReturnType<typeof detailSpecs>[number];
  const close = (got: number, want: number) => expect(Math.abs(got - want)).toBeLessThan(1.5);

  // Dome: the circle of radius R projects to u +- sR; its top is the farthest point of the
  // half ellipsoid along the view's up direction: sqrt(R^2 sin^2 f + H^2 cos^2 f).
  const dome = spec('keep-dome');
  const [dx, dy] = dome.at;
  const dz = dome.baseH - 500;
  const [l, t, r] = pixelBox('keep-dome');
  close(l, X(dx, dy) - s * dome.radiusM);
  close(r, X(dx, dy) + s * dome.radiusM);
  close(t, Y(dx, dy, dz) - s * Math.sqrt((dome.radiusM * sf) ** 2 + (dome.heightM * cf) ** 2));

  // Square spire, rotationDeg 0: corners at (cx +- R, cy +- R); apex at the top.
  const sp = spec('church-spire');
  const [px, py] = sp.at;
  const R = sp.radiusM;
  const corners = [
    [px - R, py - R],
    [px + R, py - R],
    [px + R, py + R],
    [px - R, py + R],
  ].map(([x, y]) => X(x, y));
  const [l2, t2, r2] = pixelBox('church-spire');
  close(l2, Math.min(...corners));
  close(r2, Math.max(...corners));
  close(t2, Y(px, py, sp.baseH - 500 + sp.heightM));
});

test('battlement parts draw merlons above the wall top', () => {
  // Wall pixels of the keep above its 12 m wall top exist only because of the merlons.
  const noParapet = render({ ...scene, parts: scene.parts.map((p) => ({ ...p, parapet: false })) }, city, palette.doc);
  const count = (r: RenderResult) => {
    const bid = r.layers[2].samples;
    const keep = r.ids.indexOf('syn-004_1') + 1;
    let n = 0;
    for (let i = 0; i < bid.length / 3; i++)
      if (((bid[3 * i] << 16) | (bid[3 * i + 1] << 8) | bid[3 * i + 2]) === keep) n++;
    return n;
  };
  expect(count(base)).toBeGreaterThan(count(noParapet) + 100);
});

function expectInvalid(
  edit: Parameters<typeof writeDetailScene>[1],
  message: string,
  after?: (dir: string) => void,
): void {
  const dir = mkdtempSync(join(tmp, 'bad-'));
  writeDetailScene(dir, edit);
  after?.(dir);
  expect(() => loadScene(dir, city)).toThrow(InputError);
  expect(() => loadScene(dir, city)).toThrow(message);
}

const setProp = (id: string, k: string, v: unknown) => (fs: { properties: Record<string, unknown> }[]) => {
  for (const f of fs) if (f.properties.id === id) f.properties[k] = v;
  return fs;
};

test('invalid details fail loudly with the offending id', () => {
  expectInvalid({ details: setProp('keep-drum', 'kind', 'pyramid') }, 'detail keep-drum: unknown kind "pyramid"');
  expectInvalid(
    { details: setProp('keep-dome', 'radiusM', -2) },
    'detail keep-dome: radiusM must be a finite number > 0',
  );
  expectInvalid({ details: setProp('keep-dome', 'parapet', 'battlement') }, 'detail keep-dome: parapet');
  expectInvalid({ details: setProp('keep-drum', 'sides', 4) }, 'detail keep-drum: topRadiusM and sides');
  expectInvalid({ details: setProp('church-spire', 'sides', 6) }, 'detail church-spire: sides must be 0 or 4');
  expectInvalid({ details: setProp('keep-tower', 'material', 'gold') }, 'detail keep-tower: unknown material');
  expectInvalid({ details: setProp('keep-tower', 'shapeSource', 'surface-model') }, 'detail keep-tower: shapeSource');
  expectInvalid({ details: setProp('keep-tower', 'colour', 'red') }, 'detail keep-tower: unknown property colour');
});

test('a missing, altered or miscounted details layer is rejected', () => {
  expectInvalid({ skipDetailFile: true }, 'details.geojson: file referenced by scene.json not found');
  expectInvalid({}, 'details.geojson: sha256 does not match scene.json', (dir) => {
    const p = join(dir, 'details.geojson');
    writeFileSync(p, readFileSync(p, 'utf8').replace('"heightM":15', '"heightM":16'));
  });
  expectInvalid({ manifest: (m) => (m.layers.details.count = 3) }, 'details.geojson: 7 features, scene.json says 3');
});

test('invalid parapet or material on a part is rejected', () => {
  const editBuildings = (k: string, v: string) => (dir: string) => {
    const p = join(dir, 'buildings.geojson');
    const fc = JSON.parse(readFileSync(p, 'utf8'));
    fc.features[0].properties[k] = v;
    const text = JSON.stringify(fc);
    writeFileSync(p, text);
    const mp = join(dir, 'scene.json');
    const m = JSON.parse(readFileSync(mp, 'utf8'));
    m.layers.buildings.sha256 = sha256(Buffer.from(text));
    writeFileSync(mp, JSON.stringify(m));
  };
  expectInvalid({}, 'syn-001_1: parapet must be "battlement"', editBuildings('parapet', 'machicolation'));
  expectInvalid({}, 'syn-001_1: material must be one of', editBuildings('material', 'glass'));
});
