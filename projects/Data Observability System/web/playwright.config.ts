import {defineConfig} from '@playwright/test';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(root,'.cache/playwright');
const quote=(value:string)=>"'"+value.replaceAll("'","'\\''")+"'";
export default defineConfig({testDir:'./e2e',workers:1,retries:0,timeout:30000,
 use:{baseURL:'http://127.0.0.1:8124',headless:true,viewport:{width:1440,height:1050},trace:'retain-on-failure'},
 webServer:{command:quote(root+'/.venv/bin/python')+' '+quote(root+'/scripts/e2e_server.py'),url:'http://127.0.0.1:8124/api/health',reuseExistingServer:false,timeout:30000,cwd:root}});
