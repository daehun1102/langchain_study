import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/threads': {
        target: 'http://localhost:2024',
        changeOrigin: true,
      },
      '/assistants': {
        target: 'http://localhost:2024',
        changeOrigin: true,
      },
      '/ok': {
        target: 'http://localhost:2024',
        changeOrigin: true,
      },
    },
  },
})
