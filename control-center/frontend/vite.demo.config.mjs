import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'


function requireTarget(name) {
  const value = process.env[name]
  if (!value) {
    throw new Error(`${name} is required`)
  }
  const parsed = new URL(value)
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error(`${name} must be an HTTP(S) URL`)
  }
  return parsed.origin
}


export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '^/api/v1/incidents/[^/]+/lifecycle(?:\\?.*)?$': {
        target: requireTarget('TITAN_VITE_LIFECYCLE_API_TARGET'),
        changeOrigin: false,
      },
      '^/api/v1/splunk/cluster/evidence(?:\\?.*)?$': {
        target: requireTarget('TITAN_VITE_SPLUNK_API_TARGET'),
        changeOrigin: false,
      },
      '/api': {
        target: requireTarget('TITAN_VITE_GENERAL_API_TARGET'),
        changeOrigin: false,
      },
    },
  },
})
