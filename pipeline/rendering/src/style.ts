// Stage 2: styling. A pure function of the G-buffers, the scene attributes and the palette.
// Every texture is anchored to world coordinates or absolute image coordinates, so chunking
// cannot change it; variation comes from hashes of feature ids, never from iteration order.
import { band, type Geometry, GRID_RES, GROUND, type GroundGrid, Kind, RoofTex, SUN } from './geometry.ts';
import type { Projection } from './projection.ts';
import type { GBuffer } from './raster.ts';
import type { Detail, DetailMaterial, Part, Scene } from './scene.ts';

export interface PaletteDoc {
  colors: { hex: string; role: string }[];
}

export interface Outputs {
  width: number;
  /** Palette index + 1 per pixel; 0 = nothing drawn. */
  pal: Uint8Array;
  cls: Uint8Array;
  /** Index into the buildingId index (part index + 1); 0 = no building. */
  bid: Uint32Array;
  depth: Float64Array | null;
}

export const CLASS = {
  background: 0,
  ground: 1,
  road: 2,
  wall: 3,
  roof: 4,
  vegetation: 5,
  water: 6,
  landmarkDetail: 7,
} as const;

/** Ordered dither amplitude on the light term of round details (softens the band steps). */
const ROUND_DITHER = 0.06;

const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];

export function hashStr(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193);
  return h >>> 0;
}

export function mix(h: number, v: number): number {
  let x = Math.imul(h ^ (v | 0), 0x9e3779b1);
  x ^= x >>> 15;
  x = Math.imul(x, 0x85ebca6b);
  x ^= x >>> 13;
  return x >>> 0;
}

type Shades = number[];

interface PartStyle {
  wall: Shades;
  /** Window layout family. */
  family: 'house' | 'shop' | 'civic' | 'church' | 'barn' | 'works' | 'fort';
  plinth: boolean;
  floors: number;
  floorH: number;
  hash: number;
}

export interface Styler {
  styleChunk(g: GBuffer, cx: number, cy: number, cw: number, ch: number, out: Outputs): void;
}

export function makeStyler(
  scene: Scene,
  geo: Geometry,
  ground: GroundGrid,
  pr: Projection,
  palette: PaletteDoc,
): Styler {
  const roles = new Map(palette.colors.map((c, i) => [c.role, i + 1]));
  const mat = (name: string): Shades => {
    const out: number[] = [];
    for (let i = 0; roles.has(`${name}-${i}`); i++) out.push(roles.get(`${name}-${i}`) as number);
    if (out.length === 0 && roles.has(name)) out.push(roles.get(name) as number);
    if (out.length === 0) throw new Error(`palette has no role ${name}`);
    return out;
  };
  const M = {
    outline: mat('outline'),
    ground: mat('ground'),
    asphalt: mat('asphalt'),
    paving: mat('paving'),
    grass: mat('grass'),
    scrub: mat('scrub'),
    farmland: mat('farmland'),
    rock: mat('rock'),
    water: mat('water'),
    sports: mat('sports'),
    limewash: mat('limewash'),
    ochre: mat('ochre'),
    stone: mat('stone'),
    concrete: mat('concrete'),
    terracotta: mat('terracotta'),
    flatroof: mat('flatroof'),
    window: mat('window'),
    door: mat('door'),
    olive: mat('olive'),
    pine: mat('pine'),
    trunk: mat('trunk'),
    slate: mat('slate'),
  };
  const MATERIAL: Record<DetailMaterial, Shades> = {
    stone: M.stone,
    brick: M.terracotta,
    plaster: M.limewash,
    tile: M.terracotta,
    slate: M.slate,
    metal: M.concrete,
  };
  const pick = (m: Shades, b: number) => m[b < 0 ? 0 : b >= m.length ? m.length - 1 : b];

  const styles: PartStyle[] = scene.parts.map((part: Part) => {
    const h = hashStr(part.buildingId);
    const floors = part.floors ?? Math.max(1, Math.round(part.heightM / 3));
    const base = { floors, floorH: part.heightM / floors, hash: hashStr(part.id), plinth: false };
    const st = partStyle(part, h, base);
    // Curated material (scene v1.1) replaces the wall colours; the opening layout stays.
    return part.material === null ? st : { ...st, wall: MATERIAL[part.material], plinth: false };
  });

  function partStyle(part: Part, h: number, base: Omit<PartStyle, 'wall' | 'family'>): PartStyle {
    if (part.use === 'fortification') return { ...base, wall: M.stone, family: 'fort' };
    const landmark = part.landmark !== null;
    switch (part.use) {
      case 'religious':
        return { ...base, wall: landmark ? M.stone : M.ochre, family: 'church' };
      case 'civic':
        return { ...base, wall: M.stone, family: 'civic' };
      case 'industrial':
        return { ...base, wall: M.concrete, family: 'works' };
      case 'agricultural':
        return { ...base, wall: M.ochre, family: 'barn' };
      case 'commercial':
        return { ...base, wall: landmark ? M.stone : M.limewash, family: 'shop', plinth: !landmark };
      default: {
        const ochre = h % 100 < 30;
        return {
          ...base,
          wall: landmark ? M.stone : ochre ? M.ochre : M.limewash,
          family: 'house',
          plinth: !landmark && !ochre,
        };
      }
    }
  }

  // Outline key: one per part's walls, its roof, a tree's crown, its trunk, a detail's body and its top.
  const surfKey = new Int32Array(geo.surfaces.length);
  const detailKey0 = 2 + scene.parts.length * 2 + scene.trees.length * 2;
  geo.surfaces.forEach((s, i) => {
    surfKey[i] =
      s.kind === Kind.Wall || s.kind === Kind.Roof
        ? 2 + s.owner * 2 + (s.kind === Kind.Roof ? 1 : 0)
        : s.kind === Kind.Detail || s.kind === Kind.DetailTop
          ? detailKey0 + s.owner * 2 + (s.kind === Kind.DetailTop ? 1 : 0)
          : 2 + scene.parts.length * 2 + s.owner * 2 + (s.kind === Kind.Trunk ? 1 : 0);
  });
  const treeCentre = geo.trees.map((t) => [t.wx, t.wy, t.wz]);
  const treeHash = scene.trees.map((t) => hashStr(t.id));
  const { s: S, r, p, w } = pr;
  const [tx, ty] = pr.translation;
  // Size of one pixel in metres: vertically on a wall, and horizontally on the ground.
  const pxV = p[2] > 0 ? 1 / (S * p[2]) : 1;
  const surfBase = geo.surfBase;

  function groundColour(x: number, y: number, b: number, X: number, Y: number): [number, number] {
    const gx = Math.min(Math.max(Math.floor(x / GRID_RES), 0), ground.w - 1);
    const gy = Math.min(Math.max(Math.floor(y / GRID_RES), 0), ground.h - 1);
    const code = ground.code[gy * ground.w + gx];
    const bay = BAYER[(X & 3) + 4 * (Y & 3)];
    const cell = mix(mix(code + 7, Math.floor(x * 2)), Math.floor(y * 2)) & 15;
    const speckle = (m: Shades, bb: number, strong: boolean) =>
      pick(m, bay < 8 && cell >= (strong ? 11 : 13) ? bb + 1 : bay < 8 && cell <= 1 ? bb - 1 : bb);
    switch (code) {
      case GROUND.paved:
      case GROUND.cemetery:
      case GROUND.paving: {
        const fx = x - Math.floor(x);
        const fy = y - Math.floor(y);
        return [pick(M.paving, fx < 0.1 || fy < 0.1 ? b + 1 : b), CLASS[code === GROUND.paving ? 'road' : 'ground']];
      }
      case GROUND.park:
        return [speckle(M.grass, b, true), CLASS.vegetation];
      case GROUND.scrub:
        return [speckle(M.scrub, b, true), CLASS.vegetation];
      case GROUND.woodland:
        return [speckle(M.scrub, b + 1, true), CLASS.vegetation];
      case GROUND.farmland:
        return [pick(M.farmland, Math.floor(y) % 2 === 0 && bay < 8 ? b + 1 : b), CLASS.vegetation];
      case GROUND['bare-rock']:
        return [speckle(M.rock, b, true), CLASS.ground];
      case GROUND.water: {
        const ripple = mix(mix(31, Math.floor(x / 1.5)), Math.floor(y * 2)) & 7;
        return [pick(M.water, ripple === 0 ? 0 : 1), CLASS.water];
      }
      case GROUND.sports:
        return [pick(M.sports, b), CLASS.ground];
      case GROUND.asphalt:
        return [speckle(M.asphalt, b, false), CLASS.road];
      case GROUND.dirt:
        return [speckle(M.ground, b + 1, false), CLASS.road];
      case GROUND.rail:
        return [speckle(M.rock, b + 1, true), CLASS.road];
      default:
        return [speckle(M.ground, b, false), CLASS.ground];
    }
  }

  function wallColour(si: number, x: number, y: number, z: number): number {
    const s = geo.surfaces[si];
    const part = scene.parts[s.owner];
    const st = styles[s.owner];
    const sa = (x - s.ax) * s.ux + (y - s.ay) * s.uy;
    const sb = z - part.baseZ;
    const b = s.band;
    const glass = pick(M.window, b <= 1 ? 0 : 1);
    if (st.family === 'fort') {
      const row = Math.floor(sb / 0.6);
      const off = row % 2 === 0 ? 0 : 0.6;
      const pxH = 1 / (S * Math.max(Math.abs(s.ux * r[0] + s.uy * r[1]), 0.3));
      const joint = sb - row * 0.6 < pxV || sa + off - Math.floor((sa + off) / 1.2) * 1.2 < pxH;
      return pick(st.wall, joint ? b + 1 : b);
    }
    const fi = Math.floor(sb / st.floorH);
    const within = sb - fi * st.floorH;
    const bayW = st.family === 'church' ? 5 : st.family === 'barn' ? 6 : st.family === 'house' ? 3 : 3.5;
    const nb = Math.floor(s.len / bayW);
    if (nb >= 1 && fi >= 0 && fi < st.floors) {
      const bw = s.len / nb;
      const bi = Math.min(Math.max(Math.floor(sa / bw), 0), nb - 1);
      const dx = Math.abs(sa - (bi + 0.5) * bw);
      const doorBay = mix(mix(st.hash, s.edge), bi) % 3 === 0;
      switch (st.family) {
        case 'works':
          if (fi === 0 && bi === mix(st.hash, s.edge) % nb && dx <= 1.5 && within < Math.min(3.5, st.floorH * 0.85))
            return pick(M.door, 0);
          if (within >= st.floorH * 0.5 && within <= st.floorH * 0.78 && sa >= 0.4 && sa <= s.len - 0.4) return glass;
          break;
        case 'church':
          if (fi === 0 && doorBay && dx <= 0.7 && within < Math.min(3, st.floorH * 0.8)) return pick(M.door, 0);
          if (dx <= 0.5 && sb >= part.heightM * 0.35 && sb <= part.heightM * 0.75) return glass;
          break;
        default: {
          if (fi === 0 && st.family === 'shop' && dx <= bw / 2 - 0.5 && within >= 0.3 && within <= st.floorH * 0.8)
            return glass;
          if (fi === 0 && doorBay && dx <= 0.55 && within < Math.min(2.2, st.floorH * 0.8)) return pick(M.door, 0);
          const half = st.family === 'civic' ? 0.55 : 0.45;
          if (dx <= half && within >= st.floorH * 0.33 && within <= st.floorH * 0.78) return glass;
        }
      }
    }
    return pick(st.wall, st.plinth && sb < 0.45 ? b + 1 : b);
  }

  function distToBoundary(part: Part, x: number, y: number): number {
    let best = Infinity;
    for (const ring of part.rings)
      for (let i = 0; i + 1 < ring.length; i++) {
        const [ax, ay] = ring[i];
        const dx = ring[i + 1][0] - ax;
        const dy = ring[i + 1][1] - ay;
        const l2 = dx * dx + dy * dy;
        let t = l2 > 0 ? ((x - ax) * dx + (y - ay) * dy) / l2 : 0;
        t = Math.min(Math.max(t, 0), 1);
        const ex = x - ax - t * dx;
        const ey = y - ay - t * dy;
        best = Math.min(best, ex * ex + ey * ey);
      }
    return Math.sqrt(best);
  }

  function roofColour(si: number, x: number, y: number): number {
    const s = geo.surfaces[si];
    const b = s.band;
    if (s.tex === RoofTex.Tile) {
      const t = s.ux * (y - s.ay) - s.uy * (x - s.ax);
      const along = (x - s.ax) * s.ux + (y - s.ay) * s.uy;
      const row = Math.floor(t / 0.45);
      if (t - row * 0.45 < 0.13) return pick(M.terracotta, b + 1);
      return pick(M.terracotta, (mix(mix(5, row), Math.floor(along / 0.3)) & 15) === 0 ? b - 1 : b);
    }
    const fx = x - Math.floor(x);
    const fy = y - Math.floor(y);
    const joint = fx < 0.07 || fy < 0.07;
    if (s.tex === RoofTex.Stone) return pick(M.stone, joint ? b + 1 : b);
    if (s.tex === RoofTex.Merlon) return pick(styles[s.owner].wall, b);
    if (distToBoundary(scene.parts[s.owner], x, y) < 0.3) return pick(M.flatroof, b);
    return pick(M.flatroof, joint ? b + 2 : b + 1);
  }

  function treeColour(si: number, x: number, y: number, z: number): number {
    const s = geo.surfaces[si];
    if (s.kind === Kind.Trunk) return pick(M.trunk, 0);
    const [cx, cy, cz] = treeCentre[s.owner];
    const rM = scene.trees[s.owner].crownRadiusM;
    const bb = band((x - cx) / rM, (y - cy) / rM, (z - cz) / rM);
    const leaf = mix(mix(mix(treeHash[s.owner], Math.floor(x / 0.6)), Math.floor(y / 0.6)), Math.floor(z / 0.6)) & 15;
    const m = treeHash[s.owner] % 5 < 3 ? M.olive : M.pine;
    return pick(m, Math.min(bb, 2) + (leaf >= 12 ? 1 : 0));
  }

  /** Profile radius of a detail at height zr above its base (m). */
  function radiusAt(det: Detail, zr: number): number {
    if (det.kind === 'cylinder') return det.radiusM;
    if (det.kind === 'cone')
      return det.radiusM + ((det.topRadiusM - det.radiusM) * Math.min(Math.max(zr, 0), det.heightM)) / det.heightM;
    const q = zr / det.heightM;
    return det.radiusM * Math.sqrt(Math.max(1 - q * q, 0));
  }

  function detailColour(si: number, x: number, y: number, z: number, X: number, Y: number): number {
    const s = geo.surfaces[si];
    const det = scene.details[s.owner];
    const m = MATERIAL[det.material];
    const zr = z - det.baseZ;
    const dx = x - det.x;
    const dy = y - det.y;
    let b = s.band;
    if (s.kind === Kind.DetailTop) {
      if (det.material !== 'stone' && det.material !== 'brick') return pick(m, b);
      const fx = x - Math.floor(x);
      const fy = y - Math.floor(y);
      return pick(m, fx < 0.07 || fy < 0.07 ? b + 1 : b);
    }
    const f = s.face;
    if (!f) return pick(m, b);
    if (f.round) {
      // Analytic normal of the solid at this point, then the shade band with an ordered dither.
      let nx = dx;
      let ny = dy;
      let nz = 0;
      if (det.kind === 'cone') nz = (Math.sqrt(dx * dx + dy * dy) * (det.radiusM - det.topRadiusM)) / det.heightM;
      else if (det.kind === 'dome') {
        const r2 = det.radiusM * det.radiusM;
        const h2 = det.heightM * det.heightM;
        nx = dx / r2;
        ny = dy / r2;
        nz = Math.max(zr, 0) / h2;
      }
      const nl = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
      const l =
        (nx * SUN[0] + ny * SUN[1] + nz * SUN[2]) / nl + (BAYER[(X & 3) + 4 * (Y & 3)] / 16 - 0.47) * ROUND_DITHER;
      b = l >= 0.85 ? 0 : l >= 0.6 ? 1 : l >= 0.35 ? 2 : 3;
    }
    // Texture: u = metres around the solid at this height, zr = metres above its base.
    const rz = radiusAt(det, zr);
    const t = rz > 0 ? Math.min(Math.max((dx * s.ux + dy * s.uy) / (2 * f.hc * rz) + 0.5, 0), 0.999) : 0.5;
    const u = ((f.k + t) / f.n) * rz * (det.sides === 4 ? 8 : 2 * Math.PI);
    const pxH = 1 / S;
    const course = (h: number, w: number) => {
      const row = Math.floor(zr / h);
      const off = row % 2 === 0 ? 0 : w / 2;
      return zr - row * h < pxV || u + off - Math.floor((u + off) / w) * w < pxH;
    };
    switch (det.material) {
      case 'stone':
        return pick(m, course(0.6, 1.2) ? b + 1 : b);
      case 'brick':
        return pick(m, course(0.5, 1) ? b + 1 : b);
      case 'slate':
        return pick(m, course(0.6, 1) ? b + 1 : b);
      case 'tile': {
        const row = Math.floor(zr / 0.45);
        if (zr - row * 0.45 < 0.13) return pick(m, b + 1);
        return pick(m, (mix(mix(5, row), Math.floor(u / 0.3)) & 15) === 0 ? b - 1 : b);
      }
      case 'metal':
        return pick(m, u - Math.floor(u / 1.2) * 1.2 < pxH ? b + 1 : b);
      default:
        return pick(m, b);
    }
  }

  return {
    styleChunk(g, cx, cy, cw, ch, out) {
      const { depth, surf } = g;
      for (let Y = cy; Y < cy + ch; Y++) {
        const bb = (Y + 0.5 - ty) / S;
        for (let X = cx; X < cx + cw; X++) {
          const gi = (Y - g.y0) * g.w + (X - g.x0);
          const oi = Y * out.width + X;
          const sid = surf[gi];
          if (sid === 0) {
            out.pal[oi] = 0;
            out.cls[oi] = CLASS.background;
            out.bid[oi] = 0;
            continue;
          }
          const d = depth[gi];
          const aa = (X + 0.5 - tx) / S;
          const x = aa * r[0] - bb * p[0] + d * w[0];
          const y = aa * r[1] - bb * p[1] + d * w[1];
          const z = -bb * p[2] + d * w[2];
          let colour: number;
          let cls: number;
          let bid = 0;
          let key: number;
          if (sid < surfBase) {
            key = 1;
            [colour, cls] = groundColour(x, y, geo.tBand[sid - 1], X, Y);
          } else {
            const si = sid - surfBase;
            const kind = geo.surfaces[si].kind;
            key = surfKey[si];
            if (kind === Kind.Wall) {
              colour = wallColour(si, x, y, z);
              cls = CLASS.wall;
              bid = geo.surfaces[si].owner + 1;
            } else if (kind === Kind.Roof) {
              colour = roofColour(si, x, y);
              cls = CLASS.roof;
              bid = geo.surfaces[si].owner + 1;
            } else if (kind === Kind.Detail || kind === Kind.DetailTop) {
              colour = detailColour(si, x, y, z, X, Y);
              cls = CLASS.landmarkDetail;
              bid = scene.parts.length + geo.surfaces[si].owner + 1;
            } else {
              colour = treeColour(si, x, y, z);
              cls = CLASS.vegetation;
            }
          }
          // 1 px outline on the nearer side of silhouettes and object boundaries.
          for (const n of [gi - 1, gi + 1, gi - g.w, gi + g.w]) {
            const sn = surf[n];
            if (sn === 0 || ((sn < surfBase ? 1 : surfKey[sn - surfBase]) !== key && depth[n] > d)) {
              colour = M.outline[0];
              break;
            }
          }
          out.pal[oi] = colour;
          out.cls[oi] = cls;
          out.bid[oi] = bid;
          if (out.depth) out.depth[oi] = d;
        }
      }
    },
  };
}
