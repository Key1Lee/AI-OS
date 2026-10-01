import {defineConfig} from '@playwright/test';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(root,'.cache/playwright');
export default defineConfig({
 testDir:'./e2e',timeout:45000,fullyParallel:false,workers:1,retries:0,
 use:{baseURL:'http://127.0.0.1:8123',headless:true,viewport:{width:1440,height:1050},trace:'retain-on-failure'},
 webServer:{command:`${root}/.venv/bin/python ${root}/scripts/e2e_server.py`,url:'http://127.0.0.1:8123/api/health',reuseExistingServer:false,timeout:30000,cwd:root},
});
