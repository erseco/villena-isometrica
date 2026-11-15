// Orchestration: scene -> chunked G-buffers -> styled layers -> render directory (render.md §1).
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { buildGeometry, buildGround } from './geometry.ts';
import { encodePng, ZLIB_LEVEL } from './png.ts';
import { makeProjection, type Projection } from './projection.ts';
import { makeGBuffer, rasterPolys, rasterTerrain, rasterTrees } from './raster.ts';
import type { City, Scene } from './scene.ts';
import { makeStyler, type Outputs, type PaletteDoc } from './style.ts';

export const RENDERER_NAME = 'villena-isometrica-render';
export const RENDERER_VERSION = '0.1.0';
export const PALETTE_PATH = resolve(import.meta.dir, '../palette.json');
export const BACKGROUND = '#1e2a35';
export const DEFAULT_CHUNK = 2048;

export interface Layer {
  name: 'color' | 'class' | 'buildingId' | 'depth';
  path: string;
  encoding: string;
  /** Decoded samples as defined in render.md §1. */
  samples: Uint8Array;
  png: { colorType: 0 | 2 | 3 | 6; bitDepth: 8 | 16; plte?: Uint8Array };
  extra?: Record<string, unknown>;
}

export interface RenderResult {
  projection: Projection;
  layers: Layer[];
  ids: string[];
}

/** Class colours for viewing class.png (PLTE only; the samples are the class codes). */
const CLASS_PLTE = Uint8Array.from([
  0, 0, 0, 200, 180, 140, 120, 120, 120, 240, 235, 220, 200, 100, 70, 120, 160, 80, 90, 150, 180, 220, 60, 60,
]);

export function loadPalette(): { doc: PaletteDoc; bytes: Buffer } {
  const bytes = readFileSync(PALETTE_PATH);
  return { doc: JSON.parse(bytes.toString('utf8')), bytes };
}

export function render(
  scene: Scene,
  city: City,
  palette: PaletteDoc,
  opts: { chunk?: number | undefined; depth?: boolean } = {},
): RenderResult {
  const chunk = opts.chunk ?? DEFAULT_CHUNK;
  if (!(Number.isInteger(chunk) && chunk >= 1)) throw new Error(`invalid chunk size ${chunk}`);
  const pr = makeProjection(city.camera, scene.aoiW, scene.aoiH, scene.zMin, scene.zMax);
  const { width, height } = pr;
  const geo = buildGeometry(scene, pr);
  const ground = buildGround(scene);
  const styler = makeStyler(scene, geo, ground, pr, palette);
  const prism = { aoiW: scene.aoiW, aoiH: scene.aoiH, zMin: scene.zMin, zMax: scene.zMax };
  const n = width * height;
  const out: Outputs = {
    width,
    pal: new Uint8Array(n),
    cls: new Uint8Array(n),
    bid: new Uint32Array(n),
    depth: opts.depth ? new Float64Array(n) : null,
  };
  for (let cy = 0; cy < height; cy += chunk)
    for (let cx = 0; cx < width; cx += chunk) {
      const cw = Math.min(chunk, width - cx);
      const ch = Math.min(chunk, height - cy);
      // One pixel of margin so outlines see their neighbours across chunk edges.
      const g = makeGBuffer(cx - 1, cy - 1, cw + 2, ch + 2);
      rasterTerrain(g, geo, pr, prism, scene.terrain);
      rasterPolys(g, geo.polys, pr, prism);
      rasterTrees(g, geo.trees, pr, prism);
      styler.styleChunk(g, cx, cy, cw, ch, out);
    }

  const rgb = palette.colors.map((c) => [1, 3, 5].map((k) => Number.parseInt(c.hex.slice(k, k + 2), 16)));
  const color = new Uint8Array(n * 4);
  const cls = out.cls;
  const bid = new Uint8Array(n * 3);
  for (let i = 0; i < n; i++) {
    const pi = out.pal[i];
    if (pi !== 0) {
      const [R, G, B] = rgb[pi - 1];
      color[4 * i] = R;
      color[4 * i + 1] = G;
      color[4 * i + 2] = B;
      color[4 * i + 3] = 255;
    }
    const b = out.bid[i];
    bid[3 * i] = b >>> 16;
    bid[3 * i + 1] = (b >>> 8) & 255;
    bid[3 * i + 2] = b & 255;
  }
  const layers: Layer[] = [
    { name: 'color', path: 'color.png', encoding: 'rgba8-png', samples: color, png: { colorType: 6, bitDepth: 8 } },
    {
      name: 'class',
      path: 'class.png',
      encoding: 'index8-png',
      samples: cls,
      png: { colorType: 3, bitDepth: 8, plte: CLASS_PLTE },
    },
    {
      name: 'buildingId',
      path: 'buildingId.png',
      encoding: 'rgb24-id-png',
      samples: bid,
      png: { colorType: 2, bitDepth: 8 },
      extra: { index: 'buildingId.json' },
    },
  ];
  if (out.depth) {
    let dMin = Infinity;
    let dMax = -Infinity;
    for (let i = 0; i < n; i++)
      if (out.pal[i] !== 0) {
        dMin = Math.min(dMin, out.depth[i]);
        dMax = Math.max(dMax, out.depth[i]);
      }
    if (dMin === Infinity) dMin = dMax = 0;
    const range = dMax - dMin;
    const samples = new Uint8Array(n * 2);
    for (let i = 0; i < n; i++)
      if (out.pal[i] !== 0) {
        const v = range > 0 ? Math.round(((out.depth[i] - dMin) / range) * 65535) : 0;
        samples[2 * i] = v >>> 8;
        samples[2 * i + 1] = v & 255;
      }
    layers.push({
      name: 'depth',
      path: 'depth.png',
      encoding: 'gray16-png',
      samples,
      png: { colorType: 0, bitDepth: 16 },
      extra: { offset: dMin, scale: range / 65535 },
    });
  }
  return { projection: pr, layers, ids: [...scene.parts.map((p) => p.id), ...scene.details.map((d) => d.id)] };
}

export function sha256(buf: Uint8Array): string {
  return createHash('sha256').update(buf).digest('hex');
}

/** JSON with sorted keys, one-space indent and a final newline (stable bytes). */
export function stableJson(v: unknown): string {
  const sort = (x: unknown): unknown =>
    Array.isArray(x)
      ? x.map(sort)
      : x !== null && typeof x === 'object'
        ? Object.fromEntries(
            Object.keys(x)
              .sort()
              .map((k) => [k, sort((x as Record<string, unknown>)[k])]),
          )
        : x;
  return `${JSON.stringify(sort(v), null, 1)}\n`;
}

/** Every file of the render directory, by name, plus the manifest object. */
export function renderFiles(
  result: RenderResult,
  scene: Scene,
  city: City,
  paletteBytes: Buffer,
): { files: Map<string, Uint8Array>; manifest: Record<string, unknown> } {
  const pr = result.projection;
  const files = new Map<string, Uint8Array>();
  const layerEntries = result.layers.map((l) => {
    const png = encodePng({ width: pr.width, height: pr.height, data: l.samples, ...l.png });
    files.set(l.path, png);
    return {
      encoding: l.encoding,
      name: l.name,
      path: l.path,
      pixelSha256: sha256(l.samples),
      sha256: sha256(png),
      ...l.extra,
    };
  });
  files.set('buildingId.json', Buffer.from(stableJson([null, ...result.ids])));
  files.set('palette.json', paletteBytes);
  const manifest = {
    background: BACKGROUND,
    cityId: scene.cityId,
    image: { height: pr.height, width: pr.width },
    layers: layerEntries,
    palette: { path: 'palette.json', sha256: sha256(paletteBytes) },
    projection: {
      headingDeg: city.camera.headingDeg,
      matrix: pr.matrix,
      origin: scene.origin,
      pitchDeg: city.camera.pitchDeg,
      pixelsPerMetre: city.camera.pixelsPerMetre,
      translation: pr.translation,
    },
    renderer: {
      name: RENDERER_NAME,
      version: `${RENDERER_VERSION} (software rasteriser; PNG: own encoder, filter Sub, zlib ${process.versions.zlib} level ${ZLIB_LEVEL}, Bun ${Bun.version})`,
    },
    sceneSha256: scene.sceneSha256,
    schemaVersion: '1.0',
    zRange: { zMax: scene.zMax, zMin: scene.zMin },
  };
  files.set('render.json', Buffer.from(stableJson(manifest)));
  return { files, manifest };
}
