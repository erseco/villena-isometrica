// Shapes of manifest.json and pois.json (the parts the viewer reads). Contracts: render.md §2.
export interface Attribution {
  text: string
  url?: string
}
export interface Style {
  id: string
  label: string
  format: string
  tilesBase: string
}
export interface HeightGridMeta {
  path: string
  width: number
  height: number
  cellSize: number
  westE: number
  northN: number
  offset: number
  scale: number
}
export interface Manifest {
  schemaVersion: string
  name: string
  background: string
  attribution: Attribution[]
  image: { width: number; height: number }
  tiles: { tileSize: number; tileOverlap: number; minLevel: number; maxLevel: number }
  styles: Style[]
  projection: {
    matrix: number[][]
    translation: number[]
    origin: { E0: number; N0: number; H0: number }
  }
  geoToWorld: { matrix: number[][]; maxResidualM: number }
  zRange: { zMin: number; zMax: number }
  heightGrid?: HeightGridMeta
  pois?: string
}
export interface Poi {
  id: string
  name: string
  altNames?: string[]
  kind: string
  lat: number
  lon: number
  X: number
  Y: number
  imageBounds?: [number, number, number, number]
}
