import OpenSeadragon from 'openseadragon'
import './style.css'
import {
  cameraOf,
  forward,
  geoToWorld,
  inGrid,
  inverseAtHeight,
  parseGrid,
  pick,
  terrain,
  worldToGeo,
  type Camera,
  type Grid,
} from './geo'
import { assertMajor1 } from './schema'
import { search } from './search'
import { t } from './strings'
import type { Manifest, Poi, Style } from './types'
import { formatHash, parseHash } from './url'

const env = import.meta.env
const BASE = new URL(env.BASE_URL, location.href)
const MANIFEST_URL = new URL(env.VITE_MANIFEST || 'tiles/villena/manifest.json', BASE)
const REPO_URL: string | undefined = env.VITE_REPO_URL || undefined
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches

async function getJson<T>(url: URL): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url.pathname}: HTTP ${r.status}`)
  return (await r.json()) as T
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  ...kids: (Node | string)[]
) {
  const e = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v)
  e.append(...kids)
  return e
}

function fail(err: unknown) {
  console.warn(err)
  const s = document.getElementById('status')!
  s.classList.add('error')
  s.replaceChildren(el('strong', {}, t.loadError), el('br'), t.loadErrorHint)
}

async function boot() {
  const man = await getJson<Manifest>(MANIFEST_URL)
  assertMajor1(man, 'manifest')
  document.body.style.background = man.background
  document.title = `${man.name} · ${t.title}`
  const cam = cameraOf(man)

  // Optional inputs: a failure degrades (no terrain pick / no search) but never blocks the map.
  let grid: Grid | null = null
  if (man.heightGrid) {
    try {
      const r = await fetch(new URL(man.heightGrid.path, MANIFEST_URL))
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      grid = parseGrid(man.heightGrid, await r.arrayBuffer())
    } catch (e) {
      console.warn('height grid unavailable, using the reference plane', e)
    }
  }
  let pois: Poi[] = []
  if (man.pois) {
    try {
      const f = await getJson<{ schemaVersion: string; pois: Poi[] }>(new URL(man.pois, MANIFEST_URL))
      assertMajor1(f, 'pois')
      pois = f.pois
    } catch (e) {
      console.warn('pois unavailable', e)
    }
  }

  const { width: W, height: H } = man.image
  const app = document.getElementById('app')!
  const mapEl = document.getElementById('map')!
  document.getElementById('status')!.remove()
  mapEl.setAttribute('aria-label', t.mapLabel)

  const credits = el('footer', { class: 'credits', 'aria-label': t.attribution })
  man.attribution.forEach((a, i) => {
    if (i) credits.append(' · ')
    credits.append(a.url ? el('a', { href: a.url, rel: 'noopener' }, a.text) : el('span', {}, a.text))
  })

  // No height grid: positions come from the reference plane and are approximate (projection.md 5.2).
  if (!grid) credits.append(' · ', el('span', { class: 'approx', 'data-testid': 'approx' }, t.approxPosition))
  app.append(credits) // laid out before the viewer measures its container

  // ---- tile source -------------------------------------------------------------------------
  const tileSource = (s: Style) => {
    const base = new URL(s.tilesBase.replace(/\/?$/, '/'), MANIFEST_URL).href // relative or absolute https
    // OSD accepts a custom getTileUrl in the options object; its typings omit it, hence the cast.
    return {
      width: W,
      height: H,
      tileSize: man.tiles.tileSize,
      tileOverlap: man.tiles.tileOverlap,
      minLevel: man.tiles.minLevel,
      maxLevel: man.tiles.maxLevel,
      getTileUrl: (level: number, x: number, y: number) => `${base}${level}/${x}_${y}.${s.format}`,
    } as unknown as OpenSeadragon.TileSourceOptions
  }
  let style = man.styles[0]
  const viewer = OpenSeadragon({
    element: mapEl,
    tileSources: tileSource(style),
    prefixUrl: '',
    drawer: 'canvas',
    imageSmoothingEnabled: false,
    smoothTileEdgesMinZoom: Infinity,
    maxZoomPixelRatio: 8,
    minZoomImageRatio: 0.9,
    visibilityRatio: 0.6,
    constrainDuringPan: true,
    showNavigationControl: false,
    keyboardNavEnabled: false,
    gestureSettingsMouse: { clickToZoom: false },
    animationTime: reduced ? 0.01 : 1,
    immediateRender: false,
    crossOriginPolicy: false,
    loadTilesWithAjax: false,
  })
  const vp = viewer.viewport
  mapEl.style.imageRendering = 'pixelated'
  const toVp = (X: number, Y: number) => new OpenSeadragon.Point(X / W, Y / W) // OSD: image width = 1
  const cssZoom = () => (vp.getZoom(true) * viewer.container.clientWidth) / W // CSS px per image px
  const setCssZoom = (z: number, now = false) => vp.zoomTo((z * W) / viewer.container.clientWidth, undefined, now)
  const centre = (): [number, number] => {
    const c = vp.getCenter(true)
    return [c.x * W, c.y * W]
  }

  // ---- positions ---------------------------------------------------------------------------
  const pickAt = (X: number, Y: number): { lat: number; lon: number } | null => {
    let E: number, N: number
    if (grid) {
      const p = pick(cam, grid, man.zRange.zMin, man.zRange.zMax, X, Y)
      if (!p) return null // no pick: keep the last valid position, never fall back to the plane
      ;[E, N] = [p.E, p.N]
    } else [E, N] = inverseAtHeight(cam, X, Y, 0) // manifest without a height grid: approximate
    const g = worldToGeo(man.geoToWorld.matrix, E, N)
    return { lat: g.lat, lon: g.lon }
  }
  const imageOf = (lat: number, lon: number): [number, number] | null => {
    const [E, N] = geoToWorld(man.geoToWorld.matrix, lon, lat)
    let h = cam.H0
    if (grid) {
      if (!inGrid(grid, E, N)) return null
      h = terrain(grid, E, N)
    }
    const [X, Y] = forward(cam as Camera, E, N, h)
    return X >= 0 && X <= W && Y >= 0 && Y <= H ? [X, Y] : null
  }

  // ---- URL state ---------------------------------------------------------------------------
  let applied: { X: number; Y: number; z: number } | null = null // view set from a URL: do not rewrite it
  let timer = 0
  const writeUrl = () => {
    const [X, Y] = centre(),
      z = cssZoom()
    if (applied && Math.hypot(X - applied.X, Y - applied.Y) < 0.05 && Math.abs(Math.log2(z / applied.z)) < 0.005) return
    applied = null
    const p = pickAt(X, Y)
    if (!p) return
    history.replaceState(null, '', formatHash({ zoom: Math.log2(z), ...p }))
  }
  const scheduleUrl = () => {
    clearTimeout(timer)
    timer = window.setTimeout(writeUrl, 250)
  }
  const applyHash = (): boolean => {
    const h = parseHash(location.hash)
    const xy = h && imageOf(h.lat, h.lon)
    if (!h || !xy) return false
    const z = 2 ** h.zoom
    setCssZoom(z, true)
    vp.panTo(toVp(...xy), true)
    applied = { X: xy[0], Y: xy[1], z }
    return true
  }
  const goHome = (now = reduced) => {
    vp.goHome(now)
    applied = null
  }

  // ---- markers and search ------------------------------------------------------------------
  let marker: HTMLElement | null = null
  const showMarker = (p: Poi) => {
    if (marker) viewer.removeOverlay(marker)
    marker = el('div', { class: 'marker', 'data-testid': 'marker' }, el('span', { class: 'marker-label' }, p.name))
    viewer.addOverlay({ element: marker, location: toVp(p.X, p.Y), placement: OpenSeadragon.Placement.CENTER })
  }
  const flyTo = (p: Poi) => {
    showMarker(p)
    if (p.imageBounds) {
      const [x0, y0, x1, y1] = p.imageBounds
      const pad = 0.25,
        w = (x1 - x0) * (1 + pad),
        h = (y1 - y0) * (1 + pad)
      vp.fitBounds(
        new OpenSeadragon.Rect((x0 + x1) / 2 / W - w / 2 / W, (y0 + y1) / 2 / W - h / 2 / W, w / W, h / W),
        reduced,
      )
    } else {
      setCssZoom(3, reduced)
      vp.panTo(toVp(p.X, p.Y), reduced)
    }
    clearTimeout(timer)
    // the URL describes the viewport centre once the move is over
    timer = window.setTimeout(writeUrl, reduced ? 50 : 1400)
  }

  // ---- UI ----------------------------------------------------------------------------------
  const btn = (cls: string, label: string, glyph: string, onclick: () => void) => {
    const b = el(
      'button',
      { type: 'button', class: `btn ${cls}`, 'aria-label': label, title: label },
      el('span', { 'aria-hidden': 'true' }, glyph),
    )
    b.addEventListener('click', onclick)
    return b
  }
  const tools = el('div', { class: 'tools', role: 'group', 'aria-label': 'Controles del mapa' })
  tools.append(
    btn('zoom-in', t.zoomIn, '+', () => vp.zoomBy(1.6)),
    btn('zoom-out', t.zoomOut, '−', () => vp.zoomBy(1 / 1.6)),
    btn('home', t.home, '⌂', () => goHome()),
  )
  const fsTarget = app
  if (document.fullscreenEnabled) {
    const fs = btn('fullscreen', t.fullscreen, '⛶', toggleFullscreen)
    document.addEventListener('fullscreenchange', () => {
      const on = !!document.fullscreenElement
      fs.setAttribute('aria-label', on ? t.exitFullscreen : t.fullscreen)
      fs.title = fs.getAttribute('aria-label')!
    })
    tools.append(fs)
  }
  function toggleFullscreen() {
    if (!document.fullscreenEnabled) return
    if (document.fullscreenElement) void document.exitFullscreen()
    else void fsTarget.requestFullscreen()
  }

  const dialog = el('dialog', { class: 'about', 'aria-labelledby': 'about-title' })
  const closeBtn = el('button', { type: 'button', class: 'btn close', 'aria-label': t.close }, '×')
  closeBtn.addEventListener('click', () => dialog.close())
  dialog.append(
    closeBtn,
    el('h2', { id: 'about-title' }, t.aboutTitle),
    el('p', {}, t.aboutIntro),
    el('p', {}, t.aboutData),
    el('p', { class: 'caveat' }, t.aboutCaveat),
    el('p', {}, t.aboutPick),
    el('p', {}, t.aboutLicence),
  )
  if (REPO_URL) dialog.append(el('p', {}, el('a', { href: REPO_URL, rel: 'noopener' }, t.repo)))
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) dialog.close()
  })
  tools.append(btn('about', t.about, 'i', () => dialog.showModal()))

  // search combobox (WAI-ARIA 1.2 pattern)
  const input = el('input', {
    type: 'search',
    id: 'search',
    role: 'combobox',
    'aria-label': t.searchLabel,
    placeholder: t.searchPlaceholder,
    'aria-autocomplete': 'list',
    'aria-expanded': 'false',
    'aria-controls': 'results',
    autocomplete: 'off',
    spellcheck: 'false',
  })
  const list = el('ul', { id: 'results', role: 'listbox', 'aria-label': t.searchLabel, hidden: '' })
  const live = el('p', { class: 'sr-only', role: 'status' })
  const box = el('div', { class: 'search' }, input, list, live)
  let hits: Poi[] = [],
    active = -1
  const setActive = (i: number) => {
    active = i
    list.querySelectorAll('li').forEach((li, k) => li.setAttribute('aria-selected', String(k === i)))
    if (i >= 0) input.setAttribute('aria-activedescendant', `opt-${i}`)
    else input.removeAttribute('aria-activedescendant')
    list.children[i]?.scrollIntoView({ block: 'nearest' })
  }
  const closeList = () => {
    list.hidden = true
    input.setAttribute('aria-expanded', 'false')
    setActive(-1)
  }
  const choose = (p: Poi) => {
    input.value = p.name
    closeList()
    flyTo(p)
    mapEl.focus()
  }
  const refresh = () => {
    hits = search(pois, input.value)
    list.replaceChildren(
      ...hits.map((p, i) => {
        const li = el('li', { id: `opt-${i}`, role: 'option', 'aria-selected': 'false' }, p.name)
        li.addEventListener('mousedown', (e) => {
          e.preventDefault()
          choose(p)
        })
        return li
      }),
    )
    const q = input.value.trim()
    if (!q) {
      live.textContent = ''
      closeList()
      return
    }
    if (!hits.length) list.replaceChildren(el('li', { class: 'none', role: 'presentation' }, t.noResults))
    list.hidden = false
    input.setAttribute('aria-expanded', 'true')
    setActive(-1)
    live.textContent = hits.length ? t.resultsCount(hits.length) : t.noResults
  }
  input.addEventListener('input', refresh)
  input.addEventListener('blur', closeList)
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!hits.length) return
      e.preventDefault()
      setActive(((active + (e.key === 'ArrowDown' ? 1 : -1) + 1 + hits.length + 1) % (hits.length + 1)) - 1)
    } else if (e.key === 'Enter') {
      const p = hits[active >= 0 ? active : 0]
      if (p && !list.hidden) {
        e.preventDefault()
        choose(p)
      }
    } else if (e.key === 'Escape') {
      if (!list.hidden) {
        e.preventDefault()
        closeList()
      } else if (input.value) {
        input.value = ''
        refresh()
      }
    }
  })

  const controls = el('div', { class: 'overlay' }, box, tools)
  if (man.styles.length > 1) {
    const sel = el(
      'select',
      { class: 'styles', 'aria-label': t.style },
      ...man.styles.map((s) => el('option', { value: s.id }, s.label)),
    )
    sel.addEventListener('change', () => {
      const next = man.styles.find((s) => s.id === sel.value)!
      const [c, z] = [vp.getCenter(true), vp.getZoom(true)]
      style = next
      viewer.addOnceHandler('open', () => {
        vp.zoomTo(z, undefined, true)
        vp.panTo(c, true)
      })
      viewer.open(tileSource(next) as never) // typings of open() omit option-object sources
    })
    tools.append(sel)
  }
  app.prepend(controls)
  app.append(dialog)

  // ---- keyboard ----------------------------------------------------------------------------
  const PAN = 0.12
  mapEl.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return
    const c = vp.getCenter(true),
      step = PAN / vp.getZoom(true)
    const pan = (dx: number, dy: number) => {
      vp.panTo(new OpenSeadragon.Point(c.x + dx, c.y + dy))
      vp.applyConstraints()
    }
    const handled = (
      {
        ArrowLeft: () => pan(-step, 0),
        ArrowRight: () => pan(step, 0),
        ArrowUp: () => pan(0, -step),
        ArrowDown: () => pan(0, step),
        '+': () => vp.zoomBy(1.4),
        '=': () => vp.zoomBy(1.4),
        '-': () => vp.zoomBy(1 / 1.4),
        _: () => vp.zoomBy(1 / 1.4),
        '0': () => goHome(),
        f: toggleFullscreen,
        F: toggleFullscreen,
      } as Record<string, () => void>
    )[e.key]
    if (handled) {
      e.preventDefault()
      handled()
    }
  })
  viewer.addHandler('canvas-click', () => mapEl.focus())
  for (const ev of ['pan', 'zoom'] as const) viewer.addHandler(ev, scheduleUrl)
  viewer.addHandler('canvas-drag-end', scheduleUrl)
  window.addEventListener('hashchange', () => {
    if (!applyHash()) goHome(true)
  })
  viewer.addOnceHandler('open', () => {
    if (!applyHash()) goHome(true)
  })
}

boot().catch(fail)
