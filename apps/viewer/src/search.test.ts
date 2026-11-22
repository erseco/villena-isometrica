import { expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { norm, search } from './search'
import type { Poi } from './types'

const pois: Poi[] = JSON.parse(
  readFileSync(new URL('../../../tests/fixtures/tiles-synthetic/pois.json', import.meta.url), 'utf8'),
).pois
const mk = (id: string, name: string, kind = 'other'): Poi => ({ id, name, kind, lat: 0, lon: 0, X: 0, Y: 0 })

test('accent and case insensitive, finds alt names', () => {
  expect(search(pois, 'JARDIN').map((p) => p.id)).toEqual(['garden'])
  expect(search(pois, 'castillo').map((p) => p.id)).toEqual(['keep'])
  expect(search(pois, 'sintetico').map((p) => p.id)).toEqual(['church'])
})
test('empty query and no match give nothing', () => {
  expect(search(pois, '  ')).toEqual([])
  expect(search(pois, 'zzzz')).toEqual([])
})
test('prefix first, then kind, then alphabetical', () => {
  const l = [
    mk('a', 'Plaza Mayor', 'square'),
    mk('b', 'Calle Mayor', 'street'),
    mk('c', 'Mayoral', 'other'),
    mk('d', 'Mayor Zeta', 'church'),
    mk('e', 'Mayor Alfa', 'church'),
  ]
  expect(search(l, 'mayor').map((p) => p.id)).toEqual(['e', 'd', 'c', 'a', 'b'])
})
test('limit and 500 POIs', () => {
  const big = Array.from({ length: 500 }, (_, i) => mk(`p${i}`, `Calle ${i}`))
  expect(search(big, 'calle', 10)).toHaveLength(10)
  expect(norm('Ñandú')).toBe('nandu')
})
