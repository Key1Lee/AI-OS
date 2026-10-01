import React,{lazy,Suspense} from 'react';
import {createRoot} from 'react-dom/client';
import {App} from './App';
import './styles.css';

const DataMap=lazy(()=>import('./data-map/DataMap').then(module=>({default:module.DataMap})));
const standalone=window.location.pathname==='/map';
createRoot(document.getElementById('root')!).render(<React.StrictMode>{standalone?<Suspense fallback={<main className="panel">Opening Data System Map…</main>}><DataMap standalone/></Suspense>:<App/>}</React.StrictMode>);
