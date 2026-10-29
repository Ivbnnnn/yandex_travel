import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Бэк проверяет заголовок Origin по ALLOWED_ORIGINS (по умолчанию только :8000).
// Подменяем Origin в прокси, чтобы не менять настройки бэка.
const BACKEND = 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: BACKEND,
        changeOrigin: true,
        headers: { origin: BACKEND },
      },
    },
  },
})
