import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiTarget = process.env.TITAN_API_PROXY_TARGET;
const splunkTarget = process.env.TITAN_SPLUNK_PROXY_TARGET;

if (!apiTarget || !splunkTarget) {
  throw new Error(
    'TITAN_API_PROXY_TARGET and TITAN_SPLUNK_PROXY_TARGET are required'
  );
}

const host = process.env.TITAN_UI_BIND_HOST || '127.0.0.1';
const port = Number(process.env.TITAN_UI_PORT || '5173');

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('Invalid TITAN_UI_PORT');
}

export default defineConfig({
  plugins: [react()],
  server: {
    host,
    port,
    strictPort: true,
    proxy: {
      '/api/v1/splunk': {
        target: splunkTarget,
        changeOrigin: true,
      },
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
