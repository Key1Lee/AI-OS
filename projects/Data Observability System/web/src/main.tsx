import React from 'react';
import {createRoot} from 'react-dom/client';
import {DataMap,createClient} from './index';
import './foundation.css';
const client=createClient();
createRoot(document.getElementById('root')!).render(<React.StrictMode><DataMap client={client} standalone/></React.StrictMode>);
