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

  // ─── PDF.js Worker Configuration ───────────────────────────────────────────
  // Required for react-pdf to work properly
  worker: {
    format: 'es',
  },
  optimizeDeps: {
    include: ['pdfjs-dist'],
  },

  // ─── Production Build ───────────────────────────────────────────────────────
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/swiper')) return 'vendor-swiper';
          if (
            id.includes('node_modules/react/') ||
            id.includes('node_modules/react-dom/') ||
            id.includes('node_modules/react-router-dom/')
          ) return 'vendor-react';
          if (id.includes('node_modules/pdfjs-dist')) return 'vendor-pdf';
        },
      },
    },
  },
})
