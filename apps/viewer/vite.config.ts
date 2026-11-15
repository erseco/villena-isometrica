import { defineConfig } from 'vite'

export default defineConfig({
  base: process.env.VITE_BASE ?? '/villena-isometrica/',
  build: { target: 'es2022' },
})
