// POI search: case- and accent-insensitive substring match, prefix matches first (WP05 §7.4).
import type { Poi } from './types'

export const norm = (s: string): string => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()

const KIND_ORDER = ['landmark', 'church', 'museum', 'square', 'street', 'transport', 'civic', 'park', 'other']
const kindRank = (k: string) => {
  const i = KIND_ORDER.indexOf(k)
  return i < 0 ? KIND_ORDER.length : i
}

export function search(pois: Poi[], query: string, limit = 10): Poi[] {
  const q = norm(query.trim())
  if (!q) return []
  const hits: { p: Poi; prefix: boolean }[] = []
  for (const p of pois) {
    const names = [p.name, ...(p.altNames ?? [])].map(norm)
    if (!names.some((n) => n.includes(q))) continue
    hits.push({ p, prefix: names.some((n) => n.startsWith(q)) })
  }
  hits.sort(
    (x, y) =>
      Number(y.prefix) - Number(x.prefix) ||
      kindRank(x.p.kind) - kindRank(y.p.kind) ||
      x.p.name.localeCompare(y.p.name, 'es') ||
      (x.p.id < y.p.id ? -1 : 1),
  )
  return hits.slice(0, limit).map((h) => h.p)
}
