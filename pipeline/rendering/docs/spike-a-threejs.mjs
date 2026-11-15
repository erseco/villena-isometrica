// WP04 backend spike, candidate A (docs/decisions/0006-render-backend.md). Not part of the
// package: run it in a throwaway directory, outside the repository:
//   npm install three@0.187.0 playwright@1.65.1 && npx playwright install chromium-headless-shell
//   cp -r <repo>/tests/fixtures/scene-synthetic scene && node spike-a-threejs.mjs ./scene 512 256 100
//   docker run --rm --platform linux/amd64 -v "$PWD":/w -w /w mcr.microsoft.com/playwright:v1.65.1-noble \
//     node spike-a-threejs.mjs ./scene 512 256 100
// Three.js r187 in Playwright's headless Chromium (SwiftShader) renders a face-id G-buffer of the
// synthetic scene (terrain + building boxes) in chunks with setViewOffset and prints the sha256
// of the stitched RGBA id buffer per chunk size.
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const here = dirname(fileURLToPath(import.meta.url));
const sceneDir = process.argv[2];
const scene = JSON.parse(readFileSync(join(sceneDir, 'scene.json')));
const t = scene.terrain, E0 = scene.origin.E0, N0 = scene.origin.N0, H0 = scene.origin.H0;
const tb = readFileSync(join(sceneDir, t.path)); const f32 = new Float32Array(tb.buffer, tb.byteOffset, tb.length / 4);
const pos = [], ids = [];
let nid = 1;
const tri = (a, b, c, id) => { pos.push(...a, ...b, ...c); for (let i = 0; i < 3; i++) ids.push(id); };
for (let r = 0; r + 1 < t.height; r++) for (let c = 0; c + 1 < t.width; c++) {
  const P = (cc, rr) => [t.westE + (cc + 0.5) * t.cellSize - E0, t.northN - (rr + 0.5) * t.cellSize - N0, f32[rr * t.width + cc] - H0];
  const id = nid++;
  tri(P(c, r), P(c, r + 1), P(c + 1, r + 1), id); tri(P(c, r), P(c + 1, r + 1), P(c + 1, r), id);
}
const bl = JSON.parse(readFileSync(join(sceneDir, scene.layers.buildings.path)));
for (const f of bl.features) {
  const ring = f.geometry.coordinates[0].map(([e, n]) => [e - E0, n - N0]);
  const z0 = f.properties.baseH - H0, z1 = z0 + f.properties.heightM;
  for (let i = 0; i + 1 < ring.length; i++) {
    const [a, b] = [ring[i], ring[i + 1]]; const id = nid++;
    tri([...a, z0], [...b, z0], [...b, z1], id); tri([...a, z0], [...b, z1], [...a, z1], id);
  }
  const id = nid++; // roof (rectangles in the fixture: fan is fine)
  for (let i = 1; i + 2 < ring.length; i++) tri([...ring[0], z1], [...ring[i], z1], [...ring[i + 1], z1], id);
}
const cam = { a: 45, f: 30, s: 4 }; // planeville city.json
const chunks = process.argv.slice(3).map(Number);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader-webgl', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage();
await page.route('https://spike.local/**', (route) => {
  const p = new URL(route.request().url()).pathname;
  if (p === '/') return route.fulfill({ contentType: 'text/html', body: '<!doctype html><script type="importmap">{"imports":{"three":"/three.module.js"}}</script>' });
  route.fulfill({ contentType: 'text/javascript', body: readFileSync(join(here, 'node_modules/three/build', p.slice(1))) });
});
await page.goto('https://spike.local/');
const out = await page.evaluate(async ({ pos, ids, cam, chunks, zr, aoi }) => {
  const THREE = await import('three');
  const rad = Math.PI / 180, a = cam.a * rad, f = cam.f * rad, s = cam.s;
  const r = new THREE.Vector3(Math.cos(a), -Math.sin(a), 0), p = new THREE.Vector3(Math.sin(a) * Math.sin(f), Math.cos(a) * Math.sin(f), Math.cos(f));
  const w = new THREE.Vector3(Math.sin(a) * Math.cos(f), Math.cos(a) * Math.cos(f), -Math.sin(f));
  let umin = Infinity, umax = -Infinity, vmin = Infinity, vmax = -Infinity;
  for (const x of [0, aoi]) for (const y of [0, aoi]) for (const z of [zr[0], zr[1]]) {
    const P = new THREE.Vector3(x, y, z), u = s * r.dot(P), v = -s * p.dot(P);
    umin = Math.min(umin, u); umax = Math.max(umax, u); vmin = Math.min(vmin, v); vmax = Math.max(vmax, v);
  }
  const u0 = Math.floor(umin), v0 = Math.floor(vmin), W = Math.ceil(umax) - u0, H = Math.ceil(vmax) - v0;
  const canvas = document.createElement('canvas');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false });
  const gl = renderer.getContext(), ext = gl.getExtension('WEBGL_debug_renderer_info');
  const rendererString = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const col = new Float32Array(ids.length * 3);
  ids.forEach((id, i) => { col[3 * i] = (id >> 16) & 255; col[3 * i + 1] = (id >> 8) & 255; col[3 * i + 2] = id & 255; });
  g.setAttribute('fid', new THREE.BufferAttribute(col, 3));
  const mat = new THREE.RawShaderMaterial({ glslVersion: THREE.GLSL3, side: THREE.DoubleSide,
    vertexShader: 'in vec3 position; in vec3 fid; flat out vec3 vId; uniform mat4 modelViewMatrix, projectionMatrix; void main(){ vId=fid; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: 'precision highp float; flat in vec3 vId; out vec4 o; void main(){ o=vec4(vId/255.0,1.0);}' });
  const scene = new THREE.Scene(); scene.add(new THREE.Mesh(g, mat));
  const camera = new THREE.OrthographicCamera(u0 / s, (u0 + W) / s, -v0 / s, -(v0 + H) / s, 1, 20000);
  const C = w.clone().multiplyScalar(-5000);
  camera.matrix.makeBasis(r, p, w.clone().negate()).setPosition(C); camera.matrix.decompose(camera.position, camera.quaternion, camera.scale);
  const results = [];
  for (const cs of chunks) {
    const full = new Uint8Array(W * H * 4);
    for (let y0 = 0; y0 < H; y0 += cs) for (let x0 = 0; x0 < W; x0 += cs) {
      const cw = Math.min(cs, W - x0), ch = Math.min(cs, H - y0);
      camera.setViewOffset(W, H, x0, y0, cw, ch);
      const rt = new THREE.WebGLRenderTarget(cw, ch, { samples: 0, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false, depthBuffer: true });
      renderer.setRenderTarget(rt); renderer.setClearColor(0x000000, 0); renderer.clear(); renderer.render(scene, camera);
      const buf = new Uint8Array(cw * ch * 4); renderer.readRenderTargetPixels(rt, 0, 0, cw, ch, buf);
      for (let j = 0; j < ch; j++) full.set(buf.subarray((ch - 1 - j) * cw * 4, (ch - j) * cw * 4), ((y0 + j) * W + x0) * 4);
      rt.dispose();
    }
    const h = new Uint8Array(await crypto.subtle.digest('SHA-256', full));
    results.push({ ids: new Set(Array.from({length: W*H}, (_, i) => (full[4*i]<<16)|(full[4*i+1]<<8)|full[4*i+2])).size, chunk: cs, sha: [...h].map((b) => b.toString(16).padStart(2, '0')).join(''), drawn: full.filter((_, i) => i % 4 === 3 && full[i] > 0).length });
  }
  return { rendererString, W, H, results };
}, { pos, ids, cam, chunks, zr: [scene.zRange.zMin, scene.zRange.zMax], aoi: scene.aoi.bounds[2] - scene.aoi.bounds[0] });
console.log(JSON.stringify(out, null, 1));
await browser.close();
