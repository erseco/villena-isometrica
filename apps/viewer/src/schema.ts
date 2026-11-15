/** Consumers reject an unknown MAJOR version (tile-manifest and poi schemas). */
export function assertMajor1(doc: { schemaVersion?: unknown }, what: string): void {
  const v = doc.schemaVersion
  if (typeof v !== 'string' || !/^1\./.test(v)) throw new Error(`${what}: unsupported schemaVersion ${JSON.stringify(v)}`)
}
