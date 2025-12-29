import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    base: './', // Support subdirectory deployment
    server: {
        proxy: {
            // HTTP API requests
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                // Enable WebSocket proxying
                ws: true,
            }
        }
    }
})
