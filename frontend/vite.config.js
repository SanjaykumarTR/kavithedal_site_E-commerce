import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // ─── Dev Server ─────────────────────────────────────────────────────────────
  server: {
    proxy: {
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  // ─── Path Aliases ───────────────────────────────────────────────────────────
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Note: directory is named 'assects' (typo), kept as-is to avoid breaking imports
      '@assects': path.resolve(__dirname, './src/assects'),
      '@assets': path.resolve(__dirname, './src/assects'),
    },
  },

  // ─── Production Build ───────────────────────────────────────────────────────
  build: {
    outDir: 'dist',
    // Generate source maps for error tracking (can disable in prod for smaller bundle)
    sourcemap: false,
    // Chunk size warning threshold (kB)
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Split vendor libraries into separate chunks for better caching
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          swiper: ['swiper'],
          axios: ['axios'],
        },
      },
    },
  },
})
