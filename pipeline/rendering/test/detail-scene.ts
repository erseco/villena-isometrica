// Synthetic scene for the v1.1 landmark details: the Planeville fixture plus a battlemented keep,
// a church tower with a slate spire, a castle tower, a dome on a drum, a turret and a frustum.
// Written to a directory as a real scene so the loader and its validation are exercised.
import { createHash } from 'node:crypto';
import { cpSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

export const ROOT = resolve(import.meta.dir, '../../..');
export const FIXTURE = resolve(ROOT, 'tests/fixtures/scene-synthetic');
const E0 = 700000;
const N0 = 4270000;

// biome-ignore lint/suspicious/noExplicitAny: test data built by hand
type Json = any;

/** Base height of the fixture terrain near (x, y): the fixture slopes gently; 0.5 m sunk keeps the base hidden. */
function groundH(x: number, y: number): number {
  const t = JSON.parse(readFileSync(join(FIXTURE, 'scene.json'), 'utf8')).terrain;
  const buf = readFileSync(join(FIXTURE, t.path));
  const v = new DataView(buf.buffer, buf.byteOffset, buf.length);
  let lo = Infinity;
  for (const [dx, dy] of [
    [-4, -4],
    [4, -4],
    [-4, 4],
    [4, 4],
    [0, 0],
  ]) {
    const c = Math.round((E0 + x + dx - t.westE) / t.cellSize - 0.5);
    const r = Math.round((t.northN - (N0 + y + dy)) / t.cellSize - 0.5);
    lo = Math.min(lo, v.getFloat32(4 * (r * t.width + c), true));
  }
  return Math.round((lo - 0.5) * 100) / 100;
}

export interface DetailSpec {
  id: string;
  landmark: string;
  kind: string;
  at: [number, number];
  baseH: number;
  heightM: number;
  radiusM: number;
  [k: string]: unknown;
}

/** The details of the synthetic scene (local x, y in `at`). */
export function detailSpecs(): DetailSpec[] {
  const turretBase = groundH(36, 48);
  const drumBase = groundH(28, 108);
  return [
    {
      id: 'church-spire',
      landmark: 'church',
      kind: 'cone',
      at: [91, 43],
      baseH: 508.2 + 20,
      heightM: 11,
      radiusM: 3,
      sides: 4,
      rotationDeg: 0,
      material: 'slate',
    },
    {
      id: 'keep-dome',
      landmark: 'keep',
      kind: 'dome',
      at: [28, 108],
      baseH: drumBase + 5,
      heightM: 3.5,
      radiusM: 6,
      material: 'metal',
    },
    {
      id: 'keep-drum',
      landmark: 'keep',
      kind: 'cylinder',
      at: [28, 108],
      baseH: drumBase,
      heightM: 5,
      radiusM: 6,
      material: 'plaster',
    },
    {
      id: 'keep-frustum',
      landmark: 'keep',
      kind: 'cone',
      at: [20, 50],
      baseH: groundH(20, 50),
      heightM: 4,
      radiusM: 3,
      topRadiusM: 1.5,
      material: 'stone',
    },
    {
      id: 'keep-tower',
      landmark: 'keep',
      kind: 'cylinder',
      at: [80, 80],
      baseH: 512,
      heightM: 15,
      radiusM: 3.5,
      material: 'stone',
      parapet: 'battlement',
    },
    {
      id: 'keep-turret',
      landmark: 'keep',
      kind: 'cylinder',
      at: [36, 48],
      baseH: turretBase,
      heightM: 8,
      radiusM: 2,
      material: 'brick',
    },
    {
      id: 'keep-turret-roof',
      landmark: 'keep',
      kind: 'cone',
      at: [36, 48],
      baseH: turretBase + 8,
      heightM: 3.5,
      radiusM: 2.4,
      material: 'tile',
    },
  ];
}

const sha = (b: Uint8Array | string) => createHash('sha256').update(b).digest('hex');

/**
 * Copy the fixture to `dir` and add the v1.1 content. `edit` may change the details features or
 * the manifest before the hashes are written (for the validation tests).
 */
export function writeDetailScene(
  dir: string,
  edit: { details?: (fs: Json[]) => Json[]; manifest?: (m: Json) => void; skipDetailFile?: boolean } = {},
): void {
  cpSync(FIXTURE, dir, { recursive: true });
  const bpath = join(dir, 'buildings.geojson');
  const bfc = JSON.parse(readFileSync(bpath, 'utf8'));
  for (const f of bfc.features) {
    if (f.properties.id === 'syn-004_1' || f.properties.id === 'syn-005_1') f.properties.parapet = 'battlement';
    if (f.properties.id === 'syn-006_1') f.properties.material = 'plaster';
  }
  bfc.features.push({
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [E0 + 88, N0 + 40],
          [E0 + 94, N0 + 40],
          [E0 + 94, N0 + 46],
          [E0 + 88, N0 + 46],
          [E0 + 88, N0 + 40],
        ],
      ],
    },
    properties: {
      baseH: 508.2,
      buildingId: 'syn-006',
      floors: null,
      heightM: 20,
      heightSource: 'surface-model',
      id: 'syn-007_1',
      landmark: 'church',
      material: 'stone',
      roof: 'flat',
      roofSource: 'none',
      use: 'religious',
    },
  });
  const btext = `${JSON.stringify(bfc)}\n`;
  writeFileSync(bpath, btext);

  let feats: Json[] = detailSpecs().map(({ at, ...p }) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [E0 + at[0], N0 + at[1]] },
    properties: { ...p, dimensionsSource: 'estimated', shapeSource: 'reference' },
  }));
  if (edit.details) feats = edit.details(feats);
  const dtext = `${JSON.stringify({ type: 'FeatureCollection', features: feats })}\n`;
  if (!edit.skipDetailFile) writeFileSync(join(dir, 'details.geojson'), dtext);

  const mpath = join(dir, 'scene.json');
  const m = JSON.parse(readFileSync(mpath, 'utf8'));
  m.schemaVersion = '1.1';
  m.layers.buildings = { count: bfc.features.length, path: 'buildings.geojson', sha256: sha(btext) };
  m.layers.details = { count: feats.length, path: 'details.geojson', sha256: sha(dtext) };
  m.zRange.zMax = 41;
  edit.manifest?.(m);
  writeFileSync(mpath, `${JSON.stringify(m, null, 1)}\n`);
}
