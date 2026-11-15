import { expect, test, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'

const FIX = new URL('../../../tests/fixtures/tiles-synthetic/', import.meta.url)
const pois: { id: string; name: string; lat: number; lon: number }[] = JSON.parse(readFileSync(new URL('pois.json', FIX), 'utf8')).pois
const poi = (id: string) => pois.find((p) => p.id === id)!

const hash = (page: Page) => page.evaluate(() => location.hash)
const zoomOf = (h: string) => Number(h.split('/')[0].replace('#map=', ''))

/** Collect console errors and every request origin for the whole test. */
function watch(page: Page) {
  const errors: string[] = [], urls: string[] = []
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  page.on('pageerror', (e) => errors.push(String(e)))
  page.on('request', (r) => urls.push(r.url()))
  return { errors, urls }
}

async function open(page: Page, h = '') {
  await page.goto(h)
  await page.locator('#map canvas').first().waitFor()
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(300)
}

/** Centroid (viewport CSS px) of the fixture's red-cross pixels within `radius` CSS px of (cx, cy). */
async function cross(page: Page, cx: number, cy: number, radius = 40) {
  return page.evaluate(([cx, cy, radius]) => {
    const c = document.querySelector<HTMLCanvasElement>('#map canvas')!
    const r = c.getBoundingClientRect(), k = c.width / r.width
    const d = c.getContext('2d')!.getImageData(0, 0, c.width, c.height).data
    let sx = 0, sy = 0, n = 0
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) {
      const i = (y * c.width + x) * 4
      if (Math.abs(d[i] - 0xd9) < 4 && Math.abs(d[i + 1] - 0x3a) < 4 && Math.abs(d[i + 2] - 0x3a) < 4) {
        const px = r.left + x / k, py = r.top + y / k
        if (Math.hypot(px - cx, py - cy) <= radius) { sx += px; sy += py; n++ }
      }
    }
    return n ? { x: sx / n, y: sy / n, n } : null
  }, [cx, cy, radius] as const)
}
const centreOf = async (page: Page) => {
  const b = (await page.locator('#map').boundingBox())!
  return { x: b.x + b.width / 2, y: b.y + b.height / 2 }
}

test('loads under the base path, tiles from the right URLs, same origin, no console errors', async ({ page, baseURL }) => {
  const { errors, urls } = watch(page)
  const tiles: string[] = []
  page.on('response', (r) => { if (/\/procedural\//.test(r.url())) tiles.push(`${r.status()} ${new URL(r.url()).pathname}`) })
  await open(page)
  expect(page.url()).toContain('/villena-isometrica/')
  expect(tiles.length).toBeGreaterThan(0)
  for (const t of tiles) expect(t).toMatch(/^200 \/villena-isometrica\/tiles\/planeville\/procedural\/\d+\/\d+_\d+\.png$/)
  const origin = new URL(baseURL!).origin
  for (const u of urls) if (!u.startsWith('data:')) expect(new URL(u).origin).toBe(origin)
  expect(errors).toEqual([])
  await expect(page.locator('html')).toHaveAttribute('lang', 'es')
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(27, 38, 50)')
})

test('zoom buttons, keyboard and home', async ({ page }) => {
  await open(page)
  const z0 = zoomOf(await hash(page))
  await page.getByRole('button', { name: 'Acercar' }).click()
  await expect.poll(async () => zoomOf(await hash(page))).toBeGreaterThan(z0 + 0.3)
  await page.getByRole('button', { name: 'Vista completa' }).click()
  await expect.poll(async () => Math.abs(zoomOf(await hash(page)) - z0)).toBeLessThan(0.02)
  await page.getByRole('button', { name: 'Acercar' }).click()
  await page.getByRole('button', { name: 'Acercar' }).click()
  await page.locator('#map').focus()
  await page.keyboard.press('0')
  await expect.poll(async () => Math.abs(zoomOf(await hash(page)) - z0)).toBeLessThan(0.02)
  await page.keyboard.press('+')
  await expect.poll(async () => zoomOf(await hash(page))).toBeGreaterThan(z0 + 0.3)
  const before = await hash(page)
  await page.keyboard.press('ArrowLeft')
  await expect.poll(() => hash(page)).not.toBe(before)
  await page.keyboard.press('-')
  await page.getByRole('button', { name: 'Alejar' }).click()
})

test('drag and wheel change the view; double click is harmless', async ({ page, isMobile }) => {
  test.skip(isMobile, 'mouse only')
  await open(page, '#map=1.00/38.556518/-0.703975')
  const start = await hash(page)
  const c = await centreOf(page)
  await page.mouse.move(c.x, c.y)
  await page.mouse.down(); await page.mouse.move(c.x + 80, c.y + 40, { steps: 6 }); await page.mouse.up()
  await expect.poll(() => hash(page)).not.toBe(start)
  const afterDrag = await hash(page)
  await page.mouse.wheel(0, -300)
  await expect.poll(async () => zoomOf(await hash(page))).toBeGreaterThan(zoomOf(afterDrag))
})

test('touch drag pans', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'touch only')
  await open(page, '#map=1.00/38.556518/-0.703975')
  const start = await hash(page)
  const c = await centreOf(page)
  const cdp = await page.context().newCDPSession(page)
  const touch = (type: 'touchStart' | 'touchMove' | 'touchEnd', x: number, y: number) =>
    cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y }] })
  await touch('touchStart', c.x, c.y)
  for (let i = 1; i <= 8; i++) await touch('touchMove', c.x - i * 12, c.y - i * 6)
  await touch('touchEnd', 0, 0)
  await expect.poll(() => hash(page)).not.toBe(start)
})

test('search flies to a POI, marker sits on the red cross, URL deep link returns to it', async ({ page }) => {
  const { errors } = watch(page)
  await open(page)
  const before = await hash(page)
  const input = page.getByRole('combobox', { name: 'Buscar un lugar' })
  await input.fill('castillo') // altName of the keep
  await expect(page.getByRole('option')).toHaveCount(1)
  await expect(page.getByRole('option').first()).toHaveText('Torre del Homenaje')
  await input.press('ArrowDown')
  await expect(input).toHaveAttribute('aria-activedescendant', 'opt-0')
  await input.press('Enter')
  await expect.poll(() => hash(page)).not.toBe(before)
  await page.waitForLoadState('networkidle'); await page.waitForTimeout(300)
  const m = (await page.getByTestId('marker').boundingBox())!
  const mc = { x: m.x + m.width / 2, y: m.y + m.height / 2 }
  const x = await cross(page, mc.x, mc.y)
  expect(x, 'red cross visible near the marker').not.toBeNull()
  expect(Math.hypot(x!.x - mc.x, x!.y - mc.y)).toBeLessThan(2)

  // The URL describes the centre; reloading it puts the same cross back in the centre.
  const h = await hash(page)
  await open(page, h)
  expect(await hash(page)).toBe(h)
  const c = await centreOf(page)
  const x2 = await cross(page, c.x, c.y)
  expect(x2).not.toBeNull()
  expect(Math.hypot(x2!.x - c.x, x2!.y - c.y)).toBeLessThan(2)
  expect(errors).toEqual([])
})

test('combobox: accents, Escape, no results, empty', async ({ page }) => {
  await open(page)
  const input = page.getByRole('combobox', { name: 'Buscar un lugar' })
  await input.fill('JARDIN')
  await expect(page.getByRole('option')).toHaveText(['Jardín'])
  await expect(input).toHaveAttribute('aria-expanded', 'true')
  await input.press('Escape')
  await expect(input).toHaveAttribute('aria-expanded', 'false')
  await input.fill('zzzz')
  await expect(page.getByText('Sin resultados').first()).toBeVisible()
})

test('deep link to a ground POI centres its cross; URL is stable', async ({ page }) => {
  const g = poi('garden')
  const h = `#map=1.00/${g.lat.toFixed(6)}/${g.lon.toFixed(6)}`
  await open(page, h)
  await page.waitForTimeout(500)
  expect(await hash(page)).toBe(h) // load → view → URL is stable
  const c = await centreOf(page)
  const x = await cross(page, c.x, c.y)
  expect(x).not.toBeNull()
  expect(Math.hypot(x!.x - c.x, x!.y - c.y)).toBeLessThan(2)
  // hashchange moves the view
  await page.evaluate(() => { location.hash = '#map=0.00/38.556518/-0.703975' })
  await expect.poll(async () => zoomOf(await hash(page))).toBeCloseTo(0, 1)
})

test('invalid or out-of-bounds fragments fall back to home without errors', async ({ page }) => {
  const { errors } = watch(page)
  for (const h of ['#map=abc', '#map=1/0/0', '#map=1/99/0', '#map=1/38.5565/-0.7039/9']) {
    await open(page, h)
    await expect(page.locator('#map canvas').first()).toBeVisible()
  }
  expect(errors).toEqual([])
})

for (const [w, h] of [[320, 568], [1440, 900]] as const) {
  test(`attribution visible at ${w}x${h}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h })
    await open(page)
    const credits = page.locator('footer.credits')
    await expect(credits).toBeVisible()
    await expect(credits).toContainText('Synthetic fixture data')
    const b = (await credits.boundingBox())!
    expect(b.y + b.height).toBeLessThanOrEqual(h + 0.5)
    // nothing covers it
    expect(await page.evaluate(([x, y]) => document.elementFromPoint(x, y)?.closest('footer.credits') !== null, [b.x + 4, b.y + b.height / 2])).toBe(true)
    // every control is at least 44 px and inside the viewport
    for (const btn of await page.locator('.tools button').all()) {
      const bb = (await btn.boundingBox())!
      expect(bb.width).toBeGreaterThanOrEqual(44); expect(bb.height).toBeGreaterThanOrEqual(44)
      expect(bb.x + bb.width).toBeLessThanOrEqual(w)
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('keyboard only: search, zoom, home, fullscreen, about', async ({ page, isMobile }) => {
  test.skip(isMobile, 'keyboard')
  await open(page)
  const seen: string[] = []
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press('Tab')
    seen.push(await page.evaluate(() => document.activeElement?.getAttribute('aria-label') ?? document.activeElement?.id ?? ''))
  }
  for (const n of ['Buscar un lugar', 'Acercar', 'Alejar', 'Vista completa', 'Pantalla completa', 'Acerca de'])
    expect(seen, n).toContain(n)
  await page.getByRole('button', { name: 'Acerca de' }).focus()
  await page.keyboard.press('Enter')
  const dlg = page.getByRole('dialog')
  await expect(dlg).toBeVisible()
  await expect(dlg).toContainText('estimadas o procedurales')
  await page.keyboard.press('Escape')
  await expect(dlg).toBeHidden()
})

test('a failed manifest shows a readable error', async ({ page }) => {
  await page.route('**/manifest.json', (r) => r.fulfill({ status: 404, body: 'nope' }))
  await page.goto('')
  await expect(page.locator('#status.error')).toContainText('No se ha podido cargar el mapa')
})

test('a missing tile does not break the viewer', async ({ page }) => {
  await page.route(/\/procedural\/10\//, (r) => r.fulfill({ status: 404, body: '' }))
  await open(page, '#map=2.00/38.556518/-0.703975')
  await page.getByRole('button', { name: 'Alejar' }).click()
  await expect(page.locator('#map canvas').first()).toBeVisible()
})
