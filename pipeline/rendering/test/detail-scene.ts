// Synthetic scene for the v1.1 landmark details: the Planeville fixture plus a battlemented keep,
// a church (gable nave, stone tower, slate spire; rotated 70 deg), a castle tower, a small
// bullring (arcaded drum, tile roof ring, metal dome), a turret and a frustum.
// Written to a directory as a real scene so the loader and its validation are exercised.
import { createHash } from 'node:crypto';
import { cpSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { cosDeg, sinDeg } from '../src/projection.ts';

export const ROOT = resolve(import.meta.dir, '../../..');
export const FIXTURE = resolve(ROOT, 'tests/fixtures/scene-synthetic');
const E0 = 700000;
const N0 = 4270000;

// biome-ignore lint/suspicious/noExplicitAny: test data built by hand
type Json = any;

/**
 * Base height of the fixture terrain within r m of (x, y): the lowest of a few samples, 0.5 m
 * sunk so the base stays hidden on the gentle slope.
 */
function groundH(x: number, y: number, r = 4): number {
  const t = JSON.parse(readFileSync(join(FIXTURE, 'scene.json'), 'utf8')).terrain;
  const buf = readFileSync(join(FIXTURE, t.path));
  const v = new DataView(buf.buffer, buf.byteOffset, buf.length);
  let lo = Infinity;
  for (const [dx, dy] of [
    [-r, -r],
    [r, -r],
    [-r, r],
    [r, r],
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
  [k: string]: unknown;
}

/** The church, rotated so that its faces and its ridge have bearing CHURCH_ROT (deg). */
export const CHURCH_ROT = 70;
const [cl, cw] = [sinDeg(CHURCH_ROT), cosDeg(CHURCH_ROT)];
/** Nave centre; the tower stands beside it on the north side, towards the east end. */
export const NAVE_AT: [number, number] = [70, 46];
export const TOWER_AT: [number, number] = [NAVE_AT[0] + 6 * cl - 7 * cw, NAVE_AT[1] + 6 * cw + 7 * cl];
const NAVE_BASE = groundH(NAVE_AT[0], NAVE_AT[1], 11);
export const TOWER_BASE = groundH(TOWER_AT[0], TOWER_AT[1]);

/** The details of the synthetic scene (local x, y in `at`). */
export function detailSpecs(): DetailSpec[] {
  const turretBase = groundH(36, 48);
  const ringBase = groundH(28, 108, 12);
  return [
    {
      id: 'church-nave',
      landmark: 'church',
      kind: 'gable',
      at: NAVE_AT,
      baseH: NAVE_BASE,
      heightM: 12,
      lengthM: 22,
      widthM: 8,
      wallHeightM: 9,
      rotationDeg: CHURCH_ROT,
      material: 'stone',
      roofMaterial: 'tile',
    },
    {
      id: 'church-spire',
      landmark: 'church',
      kind: 'cone',
      at: TOWER_AT,
      baseH: TOWER_BASE + 20,
      heightM: 11,
      radiusM: 3,
      sides: 4,
      rotationDeg: CHURCH_ROT,
      material: 'slate',
    },
    {
      id: 'ring-dome',
      landmark: 'bullring',
      kind: 'dome',
      at: [28, 108],
      baseH: ringBase + 11.5,
      heightM: 2.5,
      radiusM: 6.3,
      material: 'metal',
    },
    {
      id: 'ring-drum',
      landmark: 'bullring',
      kind: 'cylinder',
      at: [28, 108],
      baseH: ringBase,
      heightM: 9,
      radiusM: 12,
      material: 'plaster',
      openings: 'arcade',
    },
    {
      id: 'ring-roof',
      landmark: 'bullring',
      kind: 'cone',
      at: [28, 108],
      baseH: ringBase + 9,
      heightM: 2.5,
      radiusM: 12.4,
      topRadiusM: 6.5,
      material: 'tile',
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
      // Square 6 m tower whose face normals point at CHURCH_ROT + 90 k (corners 45 deg off).
      coordinates: [
        [0, 1, 2, 3, 0].map((k) => {
          const b = CHURCH_ROT + 45 - 90 * k;
          return [E0 + TOWER_AT[0] + 3 * Math.SQRT2 * sinDeg(b), N0 + TOWER_AT[1] + 3 * Math.SQRT2 * cosDeg(b)];
        }),
      ],
    },
    properties: {
      baseH: TOWER_BASE,
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
