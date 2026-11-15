// Scene and city-config loading with validation at the boundary (docs/contracts/scene.md).
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';

const SCHEMAS = resolve(import.meta.dir, '../../../packages/geo-contracts/schemas');

export class InputError extends Error {}

export type Ring = [number, number][];

export interface Part {
  id: string;
  buildingId: string;
  /** Local coordinates; rings[0] exterior, others holes. */
  rings: Ring[];
  baseZ: number;
  heightM: number;
  ridgeHeightM: number | null;
  floors: number | null;
  roof: 'flat' | 'pitched' | 'unknown';
  use: string;
  landmark: string | null;
  /** Curated (v1.1): merlons along the wall tops. */
  parapet: boolean;
  /** Curated (v1.1): wall material overriding the style derived from `use`. */
  material: 'stone' | 'brick' | 'plaster' | null;
}

export type DetailMaterial = 'stone' | 'brick' | 'plaster' | 'tile' | 'slate' | 'metal';

/** Curated landmark solid (scene contract v1.1, `details` layer), in local coordinates. */
export interface Detail {
  id: string;
  kind: 'cylinder' | 'cone' | 'dome';
  x: number;
  y: number;
  baseZ: number;
  heightM: number;
  radiusM: number;
  topRadiusM: number;
  sides: 0 | 4;
  rotationDeg: number;
  material: DetailMaterial;
  parapet: boolean;
}

export interface Road {
  id: string;
  cls: string;
  widthM: number;
  layer: number;
  line: [number, number][];
}

export interface Cover {
  id: string;
  cls: string;
  rings: Ring[];
}

export interface Tree {
  id: string;
  x: number;
  y: number;
  heightM: number;
  crownRadiusM: number;
}

export interface Terrain {
  width: number;
  height: number;
  cellSize: number;
  /** Local x, y of the centre of sample (0, 0) (north-west). */
  x0: number;
  y0: number;
  /** Local heights (H - H0), row-major, first row northernmost. */
  z: Float64Array;
}

export interface City {
  id: string;
  camera: { headingDeg: number; pitchDeg: number; pixelsPerMetre: number };
  origin: { E0: number; N0: number; H0: number };
}

export interface Scene {
  cityId: string;
  sceneSha256: string;
  origin: { E0: number; N0: number; H0: number };
  aoiW: number;
  aoiH: number;
  zMin: number;
  zMax: number;
  terrain: Terrain;
  parts: Part[];
  roads: Road[];
  covers: Cover[];
  trees: Tree[];
  details: Detail[];
}

// biome-ignore lint/suspicious/noExplicitAny: parsed JSON is checked by the schema or by hand below
type Json = any;

function fail(path: string, msg: string): never {
  throw new InputError(`${path}: ${msg}`);
}

function readJson(path: string): Json {
  if (!existsSync(path)) fail(path, 'file not found');
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    fail(path, `invalid JSON (${(e as Error).message})`);
  }
}

function validate(doc: Json, schemaName: string, path: string): void {
  if (typeof doc?.schemaVersion !== 'string' || !doc.schemaVersion.startsWith('1.'))
    fail(path, `unsupported schemaVersion ${JSON.stringify(doc?.schemaVersion)} (expected 1.x)`);
  const ajv = new Ajv2020({ allErrors: true, strict: false, validateFormats: false });
  const check = ajv.compile(readJson(join(SCHEMAS, `${schemaName}.schema.json`)));
  if (!check(doc)) {
    const errs = (check.errors ?? []).map((e) => `${e.instancePath || '<root>'} ${e.message}`);
    fail(path, `does not validate against ${schemaName}.schema.json: ${errs.join('; ')}`);
  }
}

function sha256(buf: Uint8Array): string {
  return createHash('sha256').update(buf).digest('hex');
}

function readChecked(dir: string, ref: { path: string; sha256: string }): Buffer {
  const path = join(dir, ref.path);
  if (!existsSync(path)) fail(path, 'file referenced by scene.json not found');
  const buf = readFileSync(path);
  if (sha256(buf) !== ref.sha256) fail(path, 'sha256 does not match scene.json');
  return buf;
}

function num(v: Json, path: string, what: string): number {
  if (typeof v !== 'number' || !Number.isFinite(v)) fail(path, `${what} must be a finite number`);
  return v;
}

function features(buf: Buffer, path: string, type: string): Json[] {
  let fc: Json;
  try {
    fc = JSON.parse(buf.toString('utf8'));
  } catch (e) {
    fail(path, `invalid JSON (${(e as Error).message})`);
  }
  if (fc?.type !== 'FeatureCollection' || !Array.isArray(fc.features)) fail(path, 'not a FeatureCollection');
  for (const f of fc.features) {
    if (f?.geometry?.type !== type) fail(path, `feature ${f?.properties?.id}: geometry must be ${type}`);
    if (typeof f.properties?.id !== 'string') fail(path, 'feature without a string id');
  }
  return fc.features;
}

export function loadCity(path: string): City {
  const city = readJson(path);
  validate(city, 'city-config', path);
  return city;
}

export function loadScene(dir: string, city: City): Scene {
  const manifestPath = join(dir, 'scene.json');
  const raw = existsSync(manifestPath) ? readFileSync(manifestPath) : fail(manifestPath, 'file not found');
  const m = readJson(manifestPath);
  validate(m, 'scene-manifest', manifestPath);
  if (m.cityId !== city.id) fail(manifestPath, `cityId ${m.cityId} differs from city config id ${city.id}`);
  for (const k of ['E0', 'N0', 'H0'] as const)
    if (m.origin[k] !== city.origin[k]) fail(manifestPath, `origin.${k} differs from the city config`);
  const { E0, N0, H0 } = m.origin;
  const [minE, minN, maxE, maxN] = m.aoi.bounds;
  if (minE !== E0 || minN !== N0) fail(manifestPath, 'origin E0, N0 must be the AOI south-west corner');
  if (!(maxE > minE && maxN > minN)) fail(manifestPath, 'empty AOI');
  if (!(m.zRange.zMax > m.zRange.zMin)) fail(manifestPath, 'zRange.zMax must exceed zMin');

  const t = m.terrain;
  const tbuf = readChecked(dir, t);
  if (tbuf.length !== t.width * t.height * 4) fail(join(dir, t.path), `expected ${t.width * t.height * 4} bytes`);
  const view = new DataView(tbuf.buffer, tbuf.byteOffset, tbuf.length);
  const z = new Float64Array(t.width * t.height);
  for (let i = 0; i < z.length; i++) {
    const h = view.getFloat32(4 * i, true);
    if (!Number.isFinite(h)) fail(join(dir, t.path), `non-finite sample at index ${i}`);
    z[i] = h - H0;
  }
  const terrain: Terrain = {
    width: t.width,
    height: t.height,
    cellSize: t.cellSize,
    x0: t.westE + t.cellSize / 2 - E0,
    y0: t.northN - t.cellSize / 2 - N0,
    z,
  };

  const L = m.layers;
  const ring = (r: Json, path: string): Ring =>
    r.map((c: Json) => [num(c[0], path, 'coordinate') - E0, num(c[1], path, 'coordinate') - N0]);
  const partsOf = (ref: Json): Part[] => {
    if (!ref) return [];
    const path = join(dir, ref.path);
    return features(readChecked(dir, ref), path, 'Polygon').map((f) => {
      const q = f.properties;
      const heightM = num(q.heightM, path, `${q.id} heightM`);
      if (heightM <= 0) fail(path, `${q.id}: heightM must be > 0`);
      const ridge = q.ridgeHeightM == null ? null : num(q.ridgeHeightM, path, `${q.id} ridgeHeightM`);
      if (ridge !== null && !(ridge > heightM)) fail(path, `${q.id}: ridgeHeightM must exceed heightM`);
      if (!['flat', 'pitched', 'unknown'].includes(q.roof)) fail(path, `${q.id}: unknown roof ${q.roof}`);
      if (q.parapet !== undefined && q.parapet !== 'battlement')
        fail(path, `${q.id}: parapet must be "battlement", got ${JSON.stringify(q.parapet)}`);
      if (q.material !== undefined && !PART_MATERIALS.includes(q.material))
        fail(path, `${q.id}: material must be one of ${PART_MATERIALS.join(', ')}, got ${JSON.stringify(q.material)}`);
      return {
        id: q.id,
        buildingId: String(q.buildingId),
        rings: f.geometry.coordinates.map((r: Json) => ring(r, path)),
        baseZ: num(q.baseH, path, `${q.id} baseH`) - H0,
        heightM,
        ridgeHeightM: ridge,
        floors: Number.isInteger(q.floors) && q.floors > 0 ? q.floors : null,
        roof: q.roof,
        use: String(q.use),
        landmark: q.landmark ?? null,
        parapet: q.parapet === 'battlement',
        material: q.material ?? null,
      };
    });
  };
  const parts = [...partsOf(L.buildings), ...partsOf(L.structures)];
  const ids = new Set<string>();
  for (const p of parts) {
    if (ids.has(p.id)) fail(manifestPath, `duplicate building/structure part id ${p.id}`);
    ids.add(p.id);
  }

  const roadsPath = join(dir, L.roads.path);
  const roads: Road[] = features(readChecked(dir, L.roads), roadsPath, 'LineString').map((f) => ({
    id: f.properties.id,
    cls: String(f.properties.class),
    widthM: num(f.properties.widthM, roadsPath, `${f.properties.id} widthM`),
    layer: Number.isInteger(f.properties.layer) ? f.properties.layer : 0,
    line: ring(f.geometry.coordinates, roadsPath),
  }));
  const coverPath = join(dir, L.landcover.path);
  const covers: Cover[] = features(readChecked(dir, L.landcover), coverPath, 'Polygon').map((f) => ({
    id: f.properties.id,
    cls: String(f.properties.class),
    rings: f.geometry.coordinates.map((r: Json) => ring(r, coverPath)),
  }));
  const trees: Tree[] = [];
  if (L.trees) {
    const path = join(dir, L.trees.path);
    for (const f of features(readChecked(dir, L.trees), path, 'Point')) {
      const [e, n] = f.geometry.coordinates;
      trees.push({
        id: f.properties.id,
        x: num(e, path, 'coordinate') - E0,
        y: num(n, path, 'coordinate') - N0,
        heightM: num(f.properties.heightM, path, `${f.properties.id} heightM`),
        crownRadiusM: num(f.properties.crownRadiusM, path, `${f.properties.id} crownRadiusM`),
      });
    }
  }
  const details: Detail[] = L.details ? loadDetails(dir, L.details, E0, N0, H0) : [];
  return {
    cityId: m.cityId,
    sceneSha256: sha256(raw),
    origin: m.origin,
    aoiW: maxE - minE,
    aoiH: maxN - minN,
    zMin: m.zRange.zMin,
    zMax: m.zRange.zMax,
    terrain,
    parts,
    roads,
    covers,
    trees,
    details,
  };
}

const PART_MATERIALS = ['stone', 'brick', 'plaster'];
const DETAIL_MATERIALS: DetailMaterial[] = ['stone', 'brick', 'plaster', 'tile', 'slate', 'metal'];
const DETAIL_KEYS = new Set([
  'id',
  'landmark',
  'kind',
  'baseH',
  'heightM',
  'radiusM',
  'topRadiusM',
  'sides',
  'rotationDeg',
  'material',
  'parapet',
  'shapeSource',
  'dimensionsSource',
]);

/** The optional `details` layer, validated strictly: any bad property fails with the detail id. */
function loadDetails(dir: string, ref: Json, E0: number, N0: number, H0: number): Detail[] {
  const path = join(dir, ref.path);
  const feats = features(readChecked(dir, ref), path, 'Point');
  if (feats.length !== ref.count) fail(path, `${feats.length} features, scene.json says ${ref.count}`);
  const ids = new Set<string>();
  return feats.map((f) => {
    const q = f.properties;
    const id: string = q.id;
    const bad = (msg: string): never => fail(path, `detail ${id}: ${msg}`);
    if (ids.has(id)) bad('duplicate id');
    ids.add(id);
    for (const k of Object.keys(q)) if (!DETAIL_KEYS.has(k)) bad(`unknown property ${k}`);
    if (typeof q.landmark !== 'string' || q.landmark === '') bad('landmark must be a POI id');
    if (!['cylinder', 'cone', 'dome'].includes(q.kind)) bad(`unknown kind ${JSON.stringify(q.kind)}`);
    if (!DETAIL_MATERIALS.includes(q.material)) bad(`unknown material ${JSON.stringify(q.material)}`);
    if (q.shapeSource !== 'reference') bad('shapeSource must be "reference"');
    if (!['surface-model', 'estimated'].includes(q.dimensionsSource))
      bad(`unknown dimensionsSource ${JSON.stringify(q.dimensionsSource)}`);
    const positive = (k: string): number => {
      if (typeof q[k] !== 'number' || !Number.isFinite(q[k]) || !(q[k] > 0)) bad(`${k} must be a finite number > 0`);
      return q[k];
    };
    const heightM = positive('heightM');
    const radiusM = positive('radiusM');
    if (typeof q.baseH !== 'number' || !Number.isFinite(q.baseH)) bad('baseH must be a finite number');
    if (q.kind !== 'cone' && (q.topRadiusM !== undefined || q.sides !== undefined))
      bad('topRadiusM and sides are only allowed on a cone');
    const topRadiusM = q.topRadiusM ?? 0;
    if (typeof topRadiusM !== 'number' || !Number.isFinite(topRadiusM) || topRadiusM < 0)
      bad('topRadiusM must be a finite number >= 0');
    const sides = q.sides ?? 0;
    if (sides !== 0 && sides !== 4) bad(`sides must be 0 or 4, got ${JSON.stringify(q.sides)}`);
    const rotationDeg = q.rotationDeg ?? 0;
    if (typeof rotationDeg !== 'number' || !Number.isFinite(rotationDeg)) bad('rotationDeg must be a finite number');
    if (q.parapet !== undefined && (q.parapet !== 'battlement' || q.kind !== 'cylinder'))
      bad('parapet must be "battlement" and is only allowed on a cylinder');
    const [e, n] = f.geometry.coordinates ?? [];
    return {
      id,
      kind: q.kind,
      x: num(e, path, `${id} coordinate`) - E0,
      y: num(n, path, `${id} coordinate`) - N0,
      baseZ: q.baseH - H0,
      heightM,
      radiusM,
      topRadiusM,
      sides,
      rotationDeg,
      material: q.material,
      parapet: q.parapet === 'battlement',
    };
  });
}

/** Bilinear terrain height at local (x, y), clamped to the outermost sample centres. */
export function terrainAt(t: Terrain, x: number, y: number): number {
  const fc = Math.min(Math.max((x - t.x0) / t.cellSize, 0), t.width - 1);
  const fr = Math.min(Math.max((t.y0 - y) / t.cellSize, 0), t.height - 1);
  const c = Math.min(Math.floor(fc), t.width - 2);
  const r = Math.min(Math.floor(fr), t.height - 2);
  const a = fc - c;
  const b = fr - r;
  const z = t.z;
  const i = r * t.width + c;
  return z[i] * (1 - a) * (1 - b) + z[i + 1] * a * (1 - b) + z[i + t.width] * (1 - a) * b + z[i + t.width + 1] * a * b;
}
