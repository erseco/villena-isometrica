// bun test/contact-sheet.ts [out.png] — renders the detail scene at 8 px/m and writes crops of the
// castle tower, the church spire and the dome on its drum side by side, magnified 2x
// (nearest neighbour). Default output: docs/landmark-details-2x.png.
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { encodePng } from '../src/png.ts';
import { forward } from '../src/projection.ts';
import { loadPalette, render } from '../src/render.ts';
import { loadCity, loadScene } from '../src/scene.ts';
import { ROOT, writeDetailScene } from './detail-scene.ts';

const out = process.argv[2] ?? resolve(import.meta.dir, '../docs/landmark-details-2x.png');
const dir = mkdtempSync(join(tmpdir(), 'contact-'));
writeDetailScene(dir);
const cityDoc = JSON.parse(readFileSync(resolve(ROOT, 'tests/fixtures/city-synthetic/city.json'), 'utf8'));
cityDoc.camera.pixelsPerMetre = 8;
writeFileSync(join(dir, 'city.json'), JSON.stringify(cityDoc));
const city = loadCity(join(dir, 'city.json'));
const scene = loadScene(dir, city);
const palette = loadPalette();
const res = render(scene, city, palette.doc);
const color = res.layers[0].samples;
const W = res.projection.width;
rmSync(dir, { recursive: true, force: true });

// Local boxes [x0, y0, z0, x1, y1, z1] (m, z relative to H0) around each showcase object.
const boxes = [
  [74, 74, 10, 98, 98, 30],
  [70, 18, 6, 102, 48, 41],
  [20, 100, 6, 36, 116, 20],
  [14, 42, 2, 42, 56, 20],
];
const crops = boxes.map(([x0, y0, z0, x1, y1, z1]) => {
  let [X0, Y0, X1, Y1] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const x of [x0, x1])
    for (const y of [y0, y1])
      for (const z of [z0, z1]) {
        const [X, Y] = forward(res.projection, x, y, z);
        [X0, Y0, X1, Y1] = [Math.min(X0, X), Math.min(Y0, Y), Math.max(X1, X), Math.max(Y1, Y)];
      }
  return { X0: Math.floor(X0), Y0: Math.floor(Y0), w: Math.ceil(X1 - X0), h: Math.ceil(Y1 - Y0) };
});
const Z = 2;
const gap = 8;
const sheetW = crops.reduce((a, c) => a + c.w * Z + gap, gap);
const sheetH = Math.max(...crops.map((c) => c.h * Z)) + 2 * gap;
const sheet = new Uint8Array(sheetW * sheetH * 4);
for (let i = 0; i < sheetW * sheetH; i++) sheet.set([0x1e, 0x2a, 0x35, 255], 4 * i);
let ox = gap;
for (const c of crops) {
  for (let y = 0; y < c.h * Z; y++)
    for (let x = 0; x < c.w * Z; x++) {
      const si = 4 * ((c.Y0 + Math.floor(y / Z)) * W + c.X0 + Math.floor(x / Z));
      if (color[si + 3] === 0) continue;
      sheet.set(color.subarray(si, si + 4), 4 * ((gap + y) * sheetW + ox + x));
    }
  ox += c.w * Z + gap;
}
writeFileSync(out, encodePng({ width: sheetW, height: sheetH, data: sheet, colorType: 6, bitDepth: 8 }));
console.error(`wrote ${out} (${sheetW}x${sheetH})`);
