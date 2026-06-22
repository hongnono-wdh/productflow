import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Source lives at repo-root/web; build output ships inside the skill at
// productflow/assets/dist (served by scripts/server.py). base '/dist/' so the
// hashed asset URLs are absolute and resolve at both "/" and "/p/<id>/" routes.
export default defineConfig({
  base: '/dist/',
  plugins: [react()],
  build: {
    outDir: '../productflow/assets/dist',
    emptyOutDir: true,
    sourcemap: false,
  },
})
