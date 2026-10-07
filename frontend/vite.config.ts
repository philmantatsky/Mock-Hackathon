/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      manifest: {
        name: 'Pantry Sign-In',
        short_name: 'Pantry Sign-In',
        description: 'Sign in food pantry visitors, even without wifi.',
        start_url: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#2f6b3a',
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'maskable-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Precache the app shell so it opens offline.
        globPatterns: ['**/*.{js,css,html,svg,png,ico,webmanifest}'],
        globIgnores: ['mockServiceWorker.js'],
        navigateFallback: '/index.html',
        // API calls (especially /api/sync) must always hit the network:
        // no SPA fallback for them and no runtimeCaching rule.
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
      },
      devOptions: {
        enabled: false,
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    env: {
      VITE_API_URL: 'http://localhost:8000',
    },
  },
})
