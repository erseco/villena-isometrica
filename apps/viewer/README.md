# Villena Isométrica — viewer (WP05)

Static Vite + TypeScript site that shows one pre-rendered isometric image pyramid with
OpenSeadragon. No backend, no analytics, no third-party requests. UI language: Spanish
(all strings in `src/strings.ts`).

## Commands

```sh
bun ci                 # install (committed bun.lock)
bun run fixture        # copy tests/fixtures/tiles-synthetic/ to public/tiles/planeville/ (git-ignored)
bun run dev            # dev server on the fixture
bun run build          # production build to dist/
bun run lint           # tsc --noEmit (strict)
bun run test           # unit tests (bun test)
bun run e2e            # fixture + Playwright (Chromium desktop + Pixel 5 emulation) against a built vite preview
npx playwright install chromium   # first time only
```

## Environment variables (build time)

| Variable | Default | Meaning |
|---|---|---|
| `VITE_BASE` | `/villena-isometrica/` | Public base path. Every URL is built from it. |
| `VITE_MANIFEST` | `tiles/villena/manifest.json` | Manifest path, relative to the base. `dev` and `e2e` use `tiles/planeville/manifest.json`. |
| `VITE_REPO_URL` | unset | Repository link in the About dialog; hidden when unset. |

Tiles, `pois.json` and the height grid are resolved relative to the manifest URL; `tilesBase`
may also be an absolute https URL. Swapping `public/tiles/<city>/` is all it takes to change the map.

## Keyboard

Tab reaches: search, zoom in, zoom out, home, fullscreen (when the browser allows it), About,
then the map. In the search box: Down/Up choose a result, Enter flies to it, Escape closes the
list (again: clears it). On the focused map: arrows pan, `+` / `-` zoom, `0` home, `f` fullscreen.
In the About dialog Escape closes it.

## Share URL

`#map=<zoom>/<lat>/<lon>` as in `docs/contracts/projection.md` section 6: zoom is
`log2(CSS px per image px)`, lat/lon is the terrain-aware pick at the viewport centre. When
the centre is background (no pick) the URL keeps its last value. A view that was just
opened from a URL is not rewritten, so load, view, URL is stable. Invalid or out-of-bounds
fragments open the home view.

## Seam findings

OpenSeadragon canvas drawer with `imageSmoothingEnabled: false`, `smoothTileEdgesMinZoom:
Infinity` and the pyramid's 1 px overlap. Inspected screenshots of the fixture at zoom 0.63,
1.37 and 2.71 (CSS px per image px): pixels stay hard-edged and no seams are visible. Caveat:
the fixture is a low-contrast checkerboard; re-check on the real Villena tiles. Maximum zoom
is 8 CSS px per image pixel.

## Bundle size

JS + CSS gzip (`gzip -9`): 92 382 B + 1 302 B, about 93.7 kB (budget 200 kB). Mostly OpenSeadragon.

## Known limits

- Clicking a roof gives the ground behind it (documented in the About dialog).
- No pinch test in e2e (OpenSeadragon's own gesture code); a touch drag is tested.
- The attribution bar always shows every entry and wraps; it does not collapse on narrow screens.
