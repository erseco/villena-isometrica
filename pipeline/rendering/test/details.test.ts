// Scene contract v1.1: landmark details, battlement parts and curated materials.
import { afterAll, expect, test } from 'bun:test';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { loadPalette, type RenderResult, render, sha256 } from '../src/render.ts';
import { InputError, loadCity, loadScene } from '../src/scene.ts';
import { type DetailSpec, detailSpecs, ROOT, writeDetailScene } from './detail-scene.ts';

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

test('detail scene loads: 9 details, parapet and material on parts', () => {
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

// Projection written out from projection.md with the platform sin/cos (not renderer code).
const DEG = Math.PI / 180;
const { headingDeg, pitchDeg, pixelsPerMetre: s } = city.camera;
const [sa, ca] = [Math.sin(headingDeg * DEG), Math.cos(headingDeg * DEG)];
const [sf, cf] = [Math.sin(pitchDeg * DEG), Math.cos(pitchDeg * DEG)];
const sceneJson = JSON.parse(readFileSync(join(sceneDir, 'scene.json'), 'utf8'));
const [tx, ty] = (() => {
  const [minE, minN, maxE, maxN] = sceneJson.aoi.bounds;
  const us: number[] = [];
  const vs: number[] = [];
  for (const x of [0, maxE - minE])
    for (const y of [0, maxN - minN])
      for (const z of [sceneJson.zRange.zMin, sceneJson.zRange.zMax]) {
        us.push(s * (x * ca - y * sa));
        vs.push(-s * ((x * sa + y * ca) * sf + z * cf));
      }
  return [-Math.floor(Math.min(...us)), -Math.floor(Math.min(...vs))];
})();
const PX = (x: number, y: number) => s * (x * ca - y * sa) + tx;
const PY = (x: number, y: number, z: number) => -s * ((x * sa + y * ca) * sf + z * cf) + ty;
const spec = (id: string) => detailSpecs().find((d) => d.id === id) as DetailSpec;
const close = (got: number, want: number) => expect(Math.abs(got - want)).toBeLessThan(1.5);
/** [left, top, right] of projected local points [x, y, z] (z relative to H0). */
const extent = (pts: number[][]): [number, number, number] => [
  Math.min(...pts.map(([x, y]) => PX(x, y))),
  Math.min(...pts.map(([x, y, z]) => PY(x, y, z))),
  Math.max(...pts.map(([x, y]) => PX(x, y))),
];

test('dome silhouette matches its projected extent (independent projection)', () => {
  // The circle of radius R projects to u +- sR; the top is the farthest point of the half
  // ellipsoid along the view's up direction: sqrt(R^2 sin^2 f + H^2 cos^2 f).
  const dome = spec('ring-dome');
  const [dx, dy] = dome.at;
  const R = dome.radiusM as number;
  const [l, t, r] = pixelBox('ring-dome');
  close(l, PX(dx, dy) - s * R);
  close(r, PX(dx, dy) + s * R);
  close(t, PY(dx, dy, dome.baseH - 500) - s * Math.sqrt((R * sf) ** 2 + (dome.heightM * cf) ** 2));
});

test('rotationDeg turns the square spire and the gable the right way (a sign flip is caught)', () => {
  // Square spire: face normal at bearing rot, so corners at bearings rot + 45 + 90k, R*sqrt2
  // from the axis; apex on the axis. The lowest pixels are at the front base corner, whose
  // image X a mirrored rotation would move to the other side of the axis.
  const sp = spec('church-spire');
  const [px, py] = sp.at;
  const z0 = sp.baseH - 500;
  const spire = (rot: number) => {
    const corners = [0, 1, 2, 3].map((k) => {
      const b = (rot + 45 + 90 * k) * DEG;
      const d = (sp.radiusM as number) * Math.SQRT2;
      return [px + d * Math.sin(b), py + d * Math.cos(b), z0];
    });
    const front = corners.reduce((a, c) => (PY(c[0], c[1], z0) > PY(a[0], a[1], z0) ? c : a));
    return { box: extent([...corners, [px, py, z0 + sp.heightM]]), frontX: PX(front[0], front[1]) };
  };
  const rot = sp.rotationDeg as number;
  expect(rot).not.toBe(0);
  const [l, t, r] = pixelBox('church-spire');
  const want = spire(rot);
  close(l, want.box[0]);
  close(t, want.box[1]);
  close(r, want.box[2]);
  // Mean X of the bottom row of spire pixels.
  const bid = layer('buildingId');
  const id = base.ids.indexOf('church-spire') + 1;
  let [bottom, xs] = [-1, [] as number[]];
  for (let i = 0; i < bid.length / 3; i++)
    if (((bid[3 * i] << 16) | (bid[3 * i + 1] << 8) | bid[3 * i + 2]) === id) {
      const Y = Math.floor(i / W);
      if (Y > bottom) [bottom, xs] = [Y, []];
      if (Y === bottom) xs.push((i % W) + 0.5);
    }
  const frontX = xs.reduce((a, b) => a + b, 0) / xs.length;
  close(frontX, want.frontX);
  expect(Math.abs(spire(-rot).frontX - frontX)).toBeGreaterThan(3);

  // Gable: ridge along bearing rot; 8 wall corners and the 2 ridge ends.
  const nave = spec('church-nave');
  const [nx, ny] = nave.at;
  const n0 = nave.baseH - 500;
  const gable = (bearing: number) => {
    const [lx, ly] = [Math.sin(bearing * DEG), Math.cos(bearing * DEG)];
    const [hl, hw] = [(nave.lengthM as number) / 2, (nave.widthM as number) / 2];
    const pts: number[][] = [];
    for (const a of [-1, 1]) {
      for (const b of [-1, 1])
        for (const z of [n0, n0 + (nave.wallHeightM as number)])
          pts.push([nx + a * hl * lx + b * hw * ly, ny + a * hl * ly - b * hw * lx, z]);
      pts.push([nx + a * hl * lx, ny + a * hl * ly, n0 + nave.heightM]);
    }
    return extent(pts);
  };
  const g = pixelBox('church-nave');
  const wantG = gable(nave.rotationDeg as number);
  for (let k = 0; k < 3; k++) close(g[k], wantG[k]);
  const flipped = gable(-(nave.rotationDeg as number));
  expect(Math.max(...[0, 1, 2].map((k) => Math.abs(flipped[k] - g[k])))).toBeGreaterThan(3);
});

/** Palette indices (1-based, as in Outputs.pal) of the colours of a role family. */
const roleIndex = (prefix: string) =>
  new Set(palette.doc.colors.flatMap((c, i) => (c.role === prefix || c.role.startsWith(`${prefix}-`) ? [i] : [])));

/** RGBA colour indices of the pixels of one building part or detail id. */
function colourIndices(id: string): number[] {
  const bid = layer('buildingId');
  const color = layer('color');
  const want = base.ids.indexOf(id) + 1;
  const hex = palette.doc.colors.map((c) => c.hex.toLowerCase());
  const out: number[] = [];
  for (let i = 0; i < bid.length / 3; i++)
    if (((bid[3 * i] << 16) | (bid[3 * i + 1] << 8) | bid[3 * i + 2]) === want) {
      const h = `#${[0, 1, 2].map((k) => color[4 * i + k].toString(16).padStart(2, '0')).join('')}`;
      out.push(hex.indexOf(h));
    }
  return out;
}

test('a stone part is coursed masonry without windows or doors; the arcade has dark openings', () => {
  const win = new Set([...roleIndex('window'), ...roleIndex('door')]);
  const tower = colourIndices('syn-007_1');
  expect(tower.length).toBeGreaterThan(200);
  expect(tower.filter((c) => win.has(c)).length).toBe(0);
  const drum = colourIndices('ring-drum');
  const dark = drum.filter((c) => win.has(c)).length / drum.length;
  expect(dark).toBeGreaterThan(0.08);
  expect(dark).toBeLessThan(0.4);
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
  expectInvalid({ details: setProp('ring-drum', 'kind', 'pyramid') }, 'detail ring-drum: unknown kind "pyramid"');
  expectInvalid(
    { details: setProp('ring-dome', 'radiusM', -2) },
    'detail ring-dome: radiusM must be a finite number > 0',
  );
  expectInvalid({ details: setProp('ring-dome', 'parapet', 'battlement') }, 'detail ring-dome: parapet');
  expectInvalid({ details: setProp('ring-drum', 'sides', 4) }, 'detail ring-drum: topRadiusM and sides');
  expectInvalid({ details: setProp('church-spire', 'sides', 6) }, 'detail church-spire: sides must be 0 or 4');
  expectInvalid({ details: setProp('keep-tower', 'material', 'gold') }, 'detail keep-tower: unknown material');
  expectInvalid({ details: setProp('keep-tower', 'shapeSource', 'surface-model') }, 'detail keep-tower: shapeSource');
  expectInvalid({ details: setProp('keep-tower', 'colour', 'red') }, 'detail keep-tower: unknown property colour');
  // Gable: its own size properties, never radiusM; and those properties nowhere else.
  expectInvalid({ details: setProp('church-nave', 'radiusM', 3) }, 'detail church-nave: radiusM is not allowed');
  expectInvalid({ details: setProp('church-nave', 'widthM', 0) }, 'detail church-nave: widthM must be');
  expectInvalid({ details: setProp('church-nave', 'lengthM', undefined) }, 'detail church-nave: lengthM must be');
  expectInvalid({ details: setProp('church-nave', 'wallHeightM', 12) }, 'detail church-nave: wallHeightM must be <');
  expectInvalid({ details: setProp('church-nave', 'roofMaterial', 'stone') }, 'detail church-nave: roofMaterial');
  expectInvalid({ details: setProp('ring-drum', 'wallHeightM', 3) }, 'detail ring-drum: wallHeightM is only');
  expectInvalid({ details: setProp('ring-drum', 'roofMaterial', 'tile') }, 'detail ring-drum: roofMaterial is only');
  // Arcade: only "arcade", only on a cylinder.
  expectInvalid({ details: setProp('ring-drum', 'openings', 'windows') }, 'detail ring-drum: openings must be');
  expectInvalid({ details: setProp('ring-roof', 'openings', 'arcade') }, 'detail ring-roof: openings');
});

test('a missing, altered or miscounted details layer is rejected', () => {
  expectInvalid({ skipDetailFile: true }, 'details.geojson: file referenced by scene.json not found');
  expectInvalid({}, 'details.geojson: sha256 does not match scene.json', (dir) => {
    const p = join(dir, 'details.geojson');
    writeFileSync(p, readFileSync(p, 'utf8').replace('"heightM":15', '"heightM":16'));
  });
  expectInvalid({ manifest: (m) => (m.layers.details.count = 3) }, 'details.geojson: 9 features, scene.json says 3');
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
