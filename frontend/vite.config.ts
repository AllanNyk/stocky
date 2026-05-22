import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// `base` controls the public path the built assets are served from.
// Local dev leaves it at "/"; the GitHub Pages build sets VITE_BASE="/stocky/"
// (the repo name) so asset URLs resolve under https://<user>.github.io/stocky/.
// For a custom apex domain, set VITE_BASE="/" in the workflow instead.
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
})
