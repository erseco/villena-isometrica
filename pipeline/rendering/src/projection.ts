// Canonical projection, docs/contracts/projection.md sections 2-3 (implemented here, not shared).
//
// Determinism: only IEEE-754 basic operations (+ - * / sqrt) are used anywhere in the render
// path. The built-in sine and cosine are "implementation-approximated" in ECMAScript and may differ by an ulp
// between platforms, so sin/cos of the camera angles come from the series below instead.

const DEG = Math.PI / 180;

// sin(x) for |x| <= pi/4 by its Taylor series (Horner form); error below 1 ulp at this range.
function sinSmall(x: number): number {
  const x2 = x * x;
  let t = 1;
  for (let n = 27; n >= 3; n -= 2) t = 1 - (x2 / (n * (n - 1))) * t;
  return x * t;
}

function cosSmall(x: number): number {
  const x2 = x * x;
  let t = 1;
  for (let n = 26; n >= 2; n -= 2) t = 1 - (x2 / (n * (n - 1))) * t;
  return t;
}

/** Deterministic sine of an angle in degrees. */
export function sinDeg(deg: number): number {
  let a = deg % 360;
  if (a < 0) a += 360;
  if (a > 180) return -sinDeg(a - 180);
  if (a > 90) a = 180 - a;
  return a > 45 ? cosSmall((90 - a) * DEG) : sinSmall(a * DEG);
}

/** Deterministic cosine of an angle in degrees. */
export function cosDeg(deg: number): number {
  return sinDeg(deg + 90);
}

export interface Camera {
  headingDeg: number;
  pitchDeg: number;
  pixelsPerMetre: number;
}

export interface Projection {
  camera: Camera;
  s: number;
  /** r, p, w unit vectors in the local frame (projection.md section 2). */
  r: [number, number, number];
  p: [number, number, number];
  w: [number, number, number];
  matrix: [[number, number, number], [number, number, number]];
  translation: [number, number];
  width: number;
  height: number;
}

/** Projection for a camera and the render prism (AOI rectangle in local metres x [zMin, zMax]). */
export function makeProjection(camera: Camera, aoiW: number, aoiH: number, zMin: number, zMax: number): Projection {
  const sa = sinDeg(camera.headingDeg);
  const ca = cosDeg(camera.headingDeg);
  const sf = sinDeg(camera.pitchDeg);
  const cf = cosDeg(camera.pitchDeg);
  const s = camera.pixelsPerMetre;
  const r: [number, number, number] = [ca, -sa, 0];
  const p: [number, number, number] = [sa * sf, ca * sf, cf];
  const w: [number, number, number] = [sa * cf, ca * cf, -sf];
  let uMin = Infinity;
  let uMax = -Infinity;
  let vMin = Infinity;
  let vMax = -Infinity;
  for (const x of [0, aoiW])
    for (const y of [0, aoiH])
      for (const z of [zMin, zMax]) {
        const u = s * (x * ca - y * sa);
        const v = -s * ((x * sa + y * ca) * sf + z * cf);
        uMin = Math.min(uMin, u);
        uMax = Math.max(uMax, u);
        vMin = Math.min(vMin, v);
        vMax = Math.max(vMax, v);
      }
  const u0 = Math.floor(uMin);
  const v0 = Math.floor(vMin);
  return {
    camera,
    s,
    r,
    p,
    w,
    matrix: [
      [s * ca, -s * sa, 0],
      [-s * sa * sf, -s * ca * sf, -s * cf],
    ],
    translation: [-u0, -v0],
    width: Math.ceil(uMax) - u0,
    height: Math.ceil(vMax) - v0,
  };
}

/** u, v (before the origin offset) and depth d of a local point, projection.md section 3. */
export function forwardUVD(pr: Projection, x: number, y: number, z: number): [number, number, number] {
  const { r, p, w, s } = pr;
  return [s * (x * r[0] + y * r[1]), -s * (x * p[0] + y * p[1] + z * p[2]), x * w[0] + y * w[1] + z * w[2]];
}

/** Image X, Y and depth d of a local point. */
export function forward(pr: Projection, x: number, y: number, z: number): [number, number, number] {
  const [u, v, d] = forwardUVD(pr, x, y, z);
  return [u + pr.translation[0], v + pr.translation[1], d];
}

/** Surface pick (projection.md section 5.3): local point from image X, Y and depth d. */
export function unproject(pr: Projection, X: number, Y: number, d: number): [number, number, number] {
  const a = (X - pr.translation[0]) / pr.s;
  const b = (Y - pr.translation[1]) / pr.s;
  const { r, p, w } = pr;
  return [a * r[0] - b * p[0] + d * w[0], a * r[1] - b * p[1] + d * w[1], -b * p[2] + d * w[2]];
}
