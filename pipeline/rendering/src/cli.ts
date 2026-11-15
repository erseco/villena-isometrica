// bun run render --scene <dir> --city <city.json> --out <dir> [--depth] [--chunk <px>]
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import { DEFAULT_CHUNK, loadPalette, render, renderFiles } from './render.ts';
import { InputError, loadCity, loadScene } from './scene.ts';

const USAGE = 'usage: bun run render --scene <dir> --city <city.json> --out <dir> [--depth] [--chunk <px>]';

function main(argv: string[]): number {
  let values: { scene?: string; city?: string; out?: string; depth?: boolean; chunk?: string };
  try {
    ({ values } = parseArgs({
      args: argv,
      options: {
        scene: { type: 'string' },
        city: { type: 'string' },
        out: { type: 'string' },
        depth: { type: 'boolean' },
        chunk: { type: 'string' },
      },
    }));
  } catch (e) {
    console.error(`${(e as Error).message}\n${USAGE}`);
    return 2;
  }
  if (!values.scene || !values.city || !values.out) {
    console.error(USAGE);
    return 2;
  }
  const chunk = values.chunk === undefined ? DEFAULT_CHUNK : Number(values.chunk);
  if (!Number.isInteger(chunk) || chunk < 1) {
    console.error(`--chunk must be a positive integer, got ${values.chunk}\n${USAGE}`);
    return 2;
  }
  const t0 = performance.now();
  try {
    const city = loadCity(values.city);
    const scene = loadScene(values.scene, city);
    const palette = loadPalette();
    const result = render(scene, city, palette.doc, { chunk, depth: values.depth === true });
    const { files } = renderFiles(result, scene, city, palette.bytes);
    mkdirSync(values.out, { recursive: true });
    for (const [name, bytes] of files) writeFileSync(join(values.out, name), bytes);
    if (!files.has('depth.png')) rmSync(join(values.out, 'depth.png'), { force: true });
    const secs = ((performance.now() - t0) / 1000).toFixed(1);
    const peakMb = Math.round(process.resourceUsage().maxRSS / 1024);
    console.error(
      `rendered ${result.projection.width}x${result.projection.height} px, ${scene.parts.length} parts, ` +
        `${scene.trees.length} trees, ${scene.details.length} details -> ${values.out} in ${secs} s, peak RSS ${peakMb} MB`,
    );
    return 0;
  } catch (e) {
    if (e instanceof InputError) {
      console.error(`error: ${e.message}`);
      return 1;
    }
    throw e;
  }
}

process.exit(main(Bun.argv.slice(2)));
