import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 45000,
  reporter: [['list']], use: { baseURL: 'http://127.0.0.1:8079', viewport: { width: 1440, height: 1000 }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: { command: 'node scripts/serve.mjs --port 8079', url: 'http://127.0.0.1:8079', reuseExistingServer: false, timeout: 15000 },
});
