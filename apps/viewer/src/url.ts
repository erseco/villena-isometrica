// Shareable position: #map=<zoom>/<lat>/<lon> (projection.md §6).
export interface MapHash { zoom: number; lat: number; lon: number }

const NUM = '(-?\\d+(?:\\.\\d+)?)'
const RE = new RegExp(`^#?map=${NUM}/${NUM}/${NUM}$`)

export function parseHash(hash: string): MapHash | null {
  const m = RE.exec(hash)
  if (!m) return null
  const [zoom, lat, lon] = [Number(m[1]), Number(m[2]), Number(m[3])]
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null
  return { zoom, lat, lon }
}

export function formatHash(h: MapHash): string {
  return `#map=${h.zoom.toFixed(2)}/${h.lat.toFixed(6)}/${h.lon.toFixed(6)}`
}
