// Minimal PNG encoder/decoder. Fixed choices for byte stability within one toolchain: one
// IDAT chunk, filter type 1 (Sub) on every row, zlib level 9, no ancillary chunks or metadata.
import { deflateSync, inflateSync } from 'node:zlib';

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(buf: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type: string, data: Uint8Array): Buffer {
  const out = Buffer.alloc(12 + data.length);
  out.writeUInt32BE(data.length, 0);
  out.write(type, 4, 'latin1');
  out.set(data, 8);
  out.writeUInt32BE(crc32(out.subarray(4, 8 + data.length)), 8 + data.length);
  return out;
}

const CHANNELS: Record<number, number> = { 0: 1, 2: 3, 3: 1, 6: 4 };

export interface PngImage {
  width: number;
  height: number;
  /** 0 gray, 2 RGB, 3 palette, 6 RGBA. */
  colorType: 0 | 2 | 3 | 6;
  bitDepth: 8 | 16;
  /** Unfiltered samples, row-major, big-endian for 16-bit. */
  data: Uint8Array;
  /** RGB triples for colour type 3. */
  plte?: Uint8Array;
}

export const ZLIB_LEVEL = 9;

export function encodePng(img: PngImage): Buffer {
  const bpp = (CHANNELS[img.colorType] * img.bitDepth) / 8;
  const stride = img.width * bpp;
  const raw = Buffer.alloc((stride + 1) * img.height);
  for (let y = 0; y < img.height; y++) {
    const src = y * stride;
    const dst = y * (stride + 1);
    raw[dst] = 1;
    for (let i = 0; i < stride; i++)
      raw[dst + 1 + i] = (img.data[src + i] - (i >= bpp ? img.data[src + i - bpp] : 0)) & 0xff;
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(img.width, 0);
  ihdr.writeUInt32BE(img.height, 4);
  ihdr[8] = img.bitDepth;
  ihdr[9] = img.colorType;
  const parts = [Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr)];
  if (img.plte) parts.push(chunk('PLTE', img.plte));
  parts.push(chunk('IDAT', deflateSync(raw, { level: ZLIB_LEVEL })), chunk('IEND', new Uint8Array(0)));
  return Buffer.concat(parts);
}

/** Decoder for non-interlaced PNGs (all five filter types); used by tests and checks. */
export function decodePng(buf: Uint8Array): PngImage {
  const b = Buffer.from(buf.buffer, buf.byteOffset, buf.length);
  if (b.readUInt32BE(0) !== 0x89504e47) throw new Error('not a PNG');
  let pos = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 8;
  let colorType = 0;
  let plte: Uint8Array | undefined;
  const idat: Buffer[] = [];
  while (pos < b.length) {
    const len = b.readUInt32BE(pos);
    const type = b.toString('latin1', pos + 4, pos + 8);
    const data = b.subarray(pos + 8, pos + 8 + len);
    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
      if (data[12] !== 0) throw new Error('interlaced PNG not supported');
    } else if (type === 'PLTE') plte = new Uint8Array(data);
    else if (type === 'IDAT') idat.push(data);
    pos += 12 + len;
  }
  const bpp = (CHANNELS[colorType] * bitDepth) / 8;
  const stride = width * bpp;
  const raw = inflateSync(Buffer.concat(idat));
  const out = new Uint8Array(stride * height);
  for (let y = 0; y < height; y++) {
    const f = raw[y * (stride + 1)];
    const src = y * (stride + 1) + 1;
    const dst = y * stride;
    for (let i = 0; i < stride; i++) {
      const a = i >= bpp ? out[dst + i - bpp] : 0;
      const up = y > 0 ? out[dst - stride + i] : 0;
      const c = y > 0 && i >= bpp ? out[dst - stride + i - bpp] : 0;
      let pred = 0;
      if (f === 1) pred = a;
      else if (f === 2) pred = up;
      else if (f === 3) pred = (a + up) >> 1;
      else if (f === 4) {
        const pa = Math.abs(up - c);
        const pb = Math.abs(a - c);
        const pc = Math.abs(a + up - 2 * c);
        pred = pa <= pb && pa <= pc ? a : pb <= pc ? up : c;
      } else if (f !== 0) throw new Error(`bad filter ${f}`);
      out[dst + i] = (raw[src + i] + pred) & 0xff;
    }
  }
  const img: PngImage = { width, height, colorType: colorType as 0, bitDepth: bitDepth as 8, data: out };
  if (plte) img.plte = plte;
  return img;
}
