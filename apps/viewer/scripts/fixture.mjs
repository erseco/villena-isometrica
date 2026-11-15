// Copy the synthetic fixture tiles to public/tiles/planeville/ (git-ignored).
import { cpSync, mkdirSync, rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const src = fileURLToPath(new URL('../../../tests/fixtures/tiles-synthetic/', import.meta.url))
const dst = fileURLToPath(new URL('../public/tiles/planeville/', import.meta.url))
rmSync(dst, { recursive: true, force: true })
mkdirSync(dst, { recursive: true })
for (const f of ['manifest.json', 'pois.json', 'height.u16', 'procedural'])
  cpSync(src + f, dst + f, { recursive: true })
console.log(`fixture copied to ${dst}`)
