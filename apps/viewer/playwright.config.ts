import { defineConfig, devices } from '@playwright/test'

const PORT = 4173
const env = { VITE_BASE: '/villena-isometrica/', VITE_MANIFEST: 'tiles/planeville/manifest.json' }

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: true,
  retries: 0,
  reporter: [['list']],
  use: { baseURL: `http://localhost:${PORT}/villena-isometrica/`, reducedMotion: 'reduce', trace: 'off' },
  webServer: {
    // Separate outDir so the e2e build (fixture manifest) never replaces dist/.
    command: `bunx --bun vite build --outDir dist-e2e --emptyOutDir && bunx --bun vite preview --outDir dist-e2e --port ${PORT} --strictPort`,
    env,
    url: `http://localhost:${PORT}/villena-isometrica/`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 5'] } },
  ],
})
