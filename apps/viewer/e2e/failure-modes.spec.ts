// WP08 7.3 / frozen-contract note: failure modes of the viewer that viewer.spec.ts does not cover, and the
// "background pixels have no pick" rule (projection.md 5.2). Manifest 404 and unknown MAJOR version are already
// covered in viewer.spec.ts ("a failed manifest shows a readable error", "unknown MAJOR schemaVersion ...").
import { expect, test, type Page } from '@playwright/test'

const SHARE_URL = /^#map=-?\d+\.\d\d\/38\.\d{6}\/-0\.\d{6}$/
const hash = (page: Page) => page.evaluate(() => location.hash)
const zoomOf = (h: string) => Number(h.split('/')[0].replace('#map=', ''))

async function open(page: Page, h = '') {
  await page.goto(h)
  await page.locator('#map canvas').first().waitFor()
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(300)
}

function watch(page: Page) {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  return pageErrors
}

test('one tile that 404s: the other tiles load and the viewer keeps working', async ({ page }) => {
  const pageErrors = watch(page)
  const status = new Map<string, number>()
  page.on('response', (r) => {
    if (/\/procedural\//.test(r.url())) status.set(new URL(r.url()).pathname.split('/procedural/')[1], r.status())
  })
  await page.route(/\/procedural\/10\/1_0\.png$/, (r) => r.fulfill({ status: 404, body: '' }))
  await open(page, '#map=2.00/38.556518/-0.703975') // deep zoom at the centre: level-10 tiles are requested
  await page.getByRole('button', { name: 'Acercar' }).click()
  await page.getByRole('button', { name: 'Alejar' }).click()
  await page.waitForLoadState('networkidle')
  expect(status.get('10/1_0.png')).toBe(404)
  const ok = [...status].filter(([k]) => k !== '10/1_0.png')
  expect(ok.length).toBeGreaterThan(0)
  for (const [, s] of ok) expect(s).toBe(200)
  await expect(page.locator('#map canvas').first()).toBeVisible()
  await expect(page.locator('#status')).toHaveCount(0) // no error state: the page still has its map
  expect(pageErrors).toEqual([])
  // the URL still follows the view
  const before = await hash(page)
  await page.locator('#map').focus()
  await page.keyboard.press('ArrowLeft')
  await expect.poll(() => hash(page)).not.toBe(before)
})

test('height grid 404: falls back to reference-plane picking, flags it, and still produces a share URL', async ({
  page,
}) => {
  const pageErrors = watch(page)
  await page.route('**/height.u16', (r) => r.fulfill({ status: 404, body: '' }))
  await open(page)
  await expect(page.getByTestId('approx')).toBeVisible()
  await expect(page.locator('#map canvas').first()).toBeVisible()
  await expect.poll(() => hash(page)).toMatch(SHARE_URL) // the home view already writes one
  const home = await hash(page)
  await page.locator('#map').focus()
  await page.keyboard.press('+')
  await expect.poll(() => hash(page)).not.toBe(home)
  await page.waitForTimeout(600)
  // the shared URL can be opened again, and shows the view it describes (zoom survives the round trip)
  const h = await hash(page)
  expect(h).toMatch(SHARE_URL)
  await open(page, h)
  expect(await hash(page)).toBe(h)
  expect(pageErrors).toEqual([])
})

test('height grid with the wrong size: same fallback, no crash', async ({ page }) => {
  const pageErrors = watch(page)
  await page.route('**/height.u16', (r) => r.fulfill({ status: 200, body: Buffer.alloc(10) }))
  await open(page)
  await expect(page.getByTestId('approx')).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('pois.json 404: the map still works, search finds nothing', async ({ page }) => {
  const pageErrors = watch(page)
  await page.route('**/pois.json', (r) => r.fulfill({ status: 404, body: '' }))
  await open(page)
  await expect(page.locator('#map canvas').first()).toBeVisible()
  const input = page.getByRole('combobox', { name: 'Buscar un lugar' })
  await input.fill('castillo')
  await expect(page.getByText('Sin resultados').first()).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('a background pixel has no pick: the URL and the marker stay where they were', async ({ page }) => {
  // "No pick" = the pixel's ray never meets the height grid (projection.md 5.2). The strip of margin ground between the
  // drawn diamond and the grid edge is background too, but its rays do hit the grid: the test goes well beyond it.
  const pageErrors = watch(page)
  await open(page)
  const input = page.getByRole('combobox', { name: 'Buscar un lugar' })
  await input.fill('esquina') // south-west corner of the AOI: the lowest tip of the drawn diamond, at image (363, 470)
  await input.press('Enter')
  await expect(page.getByTestId('marker')).toHaveCount(1)
  await page.waitForTimeout(500)
  await page.waitForLoadState('networkidle')
  const TIP = { X: 363, Y: 470 }
  const centreIsBackground = () =>
    page.evaluate(() => {
      const c = document.querySelector<HTMLCanvasElement>('#map canvas')!
      const [r, g, b, a] = c
        .getContext('2d')!
        .getImageData(Math.floor(c.width / 2), Math.floor(c.height / 2), 1, 1).data
      return r === 0x1b && g === 0x26 && b === 0x32 && a === 255 // the manifest's background #1b2632, a loaded tile
    })
  // image X of the viewport centre, from the marker (anchored at TIP) and the zoom in the URL (CSS px per image px)
  const centreX = async () => {
    const z = 2 ** zoomOf(await hash(page))
    const m = (await page.getByTestId('marker').boundingBox())!,
      v = (await page.locator('#map').boundingBox())!
    return TIP.X + (v.x + v.width / 2 - (m.x + m.width / 2)) / z
  }
  await page.locator('#map').focus()
  let steps = 0
  while (!((await centreIsBackground()) && (await centreX()) < 200) && steps++ < 40) {
    await page.keyboard.press('ArrowLeft')
    await page.waitForTimeout(150)
  }
  expect(steps, 'the viewport centre reached the far background').toBeLessThan(40)
  await page.waitForTimeout(700) // > the 250 ms debounce of the URL writer
  const last = await hash(page)
  expect(last).toMatch(/^#map=/)
  const markerAt = async () => (await page.getByTestId('marker').boundingBox())!.x
  const m0 = await markerAt()

  await page.keyboard.press('ArrowLeft') // the centre moves on over background
  await page.waitForTimeout(150)
  expect(await centreIsBackground()).toBe(true)
  await page.waitForTimeout(700)
  expect(await markerAt(), 'the view really moved').not.toBe(m0) // the marker is anchored in the image, so it shifts on screen
  expect(await hash(page)).toBe(last) // ... but no pick: the URL is untouched
  await expect(page.getByTestId('marker')).toHaveCount(1)
  expect(pageErrors).toEqual([])
})
