import { expect, test } from 'bun:test'
import { assertMajor1 } from './schema'

test('accepts 1.x, rejects other majors and missing', () => {
  expect(() => assertMajor1({ schemaVersion: '1.0' }, 'm')).not.toThrow()
  expect(() => assertMajor1({ schemaVersion: '1.7' }, 'm')).not.toThrow()
  for (const v of ['2.0', '0.9', '10.0', undefined, 1])
    expect(() => assertMajor1({ schemaVersion: v }, 'm')).toThrow('unsupported schemaVersion')
})
