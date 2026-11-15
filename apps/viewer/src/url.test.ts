import { expect, test } from 'bun:test'
import { formatHash, parseHash } from './url'

test('formats zoom with 2 and lat/lon with 6 decimals', () => {
  expect(formatHash({ zoom: 1.5, lat: 38.5565177, lon: -0.7039752 })).toBe('#map=1.50/38.556518/-0.703975')
})
test('parse round trip is stable', () => {
  const h = '#map=-0.25/38.556518/-0.703975'
  expect(formatHash(parseHash(h)!)).toBe(h)
})
test('invalid fragments give null', () => {
  for (const h of ['', '#', '#map=', '#map=1/2', '#map=a/b/c', '#map=1/95/0', '#map=1/0/190', '#x=1/2/3', '#map=1/2/3/4'])
    expect(parseHash(h)).toBeNull()
})
