import {useCallback,useEffect,useRef,useState} from 'react';
import {ApiError,request} from './api';
import type {Attempt} from './types';

export type Draft = {code:string;explanation:string;external_assistance:boolean};
const fromAttempt=(a:Attempt):Draft=>({code:a.code,explanation:a.explanation,external_assistance:a.external_assistance});

export function useDraft(attempt:Attempt,busy:boolean) {
  const key='ae-draft:'+attempt.id;
  const [recovery,setRecovery]=useState<Draft|null>(null);
  const [draft,setDraft]=useState<Draft>(()=>{
    try {
      const local=JSON.parse(localStorage.getItem(key)||'null');
      if(local&&!local.conflict&&attempt.status==='active'&&local.server_revision===attempt.draft_revision)return local.draft;
    } catch { /* Server draft remains authoritative when local storage is invalid. */ }
    return fromAttempt(attempt);
  });
  const [state,setState]=useState('Saved');
  const [saveError,setSaveError]=useState('');
  const latest=useRef(draft),revision=useRef(attempt.draft_revision),status=useRef(attempt.status);
  const chain=useRef<Promise<void>>(Promise.resolve());
  const conflicted=useRef(false);
  const saved=useRef(JSON.stringify(fromAttempt(attempt)));
  latest.current=draft;status.current=attempt.status;
  const remember=useCallback(()=>{
    try {localStorage.setItem(key,JSON.stringify({server_revision:revision.current,draft:latest.current,conflict:conflicted.current}));}
    catch { /* Server autosave can still work when browser storage is full. */ }
  },[key]);
  useEffect(()=>{
    try {
      const local=JSON.parse(localStorage.getItem(key)||'null');
      const backup=JSON.parse(localStorage.getItem('ae-recovery:'+attempt.id)||'null');
      if(local&&(local.conflict||local.server_revision!==attempt.draft_revision)&&JSON.stringify(local.draft)!==saved.current&&attempt.status==='active')setRecovery(local.draft);
      else if(backup&&JSON.stringify(backup)!==saved.current&&attempt.status==='active')setRecovery(backup);
    } catch { /* Keep server version. */ }
  },[]);
  const save=useCallback(()=>{
    const snapshot={...latest.current};
    const task=chain.current.catch(()=>{}).then(async()=>{
      if(conflicted.current)throw new Error('Resolve this draft conflict by loading the server version. Your browser copy is retained.');
      if(status.current!=='active'||JSON.stringify(snapshot)===saved.current)return;
      setState('Saving…');setSaveError('');
      try {
        const result=await request<{revision:number}>('/attempts/'+attempt.id+'/draft','PUT',{...snapshot,revision:revision.current});
        revision.current=result.revision;saved.current=JSON.stringify(snapshot);
        remember();setState(JSON.stringify(latest.current)===saved.current?'Saved':'Unsaved');
      }catch(error){
        if(error instanceof ApiError&&error.status===409){conflicted.current=true;try{localStorage.setItem('ae-recovery:'+attempt.id,JSON.stringify(latest.current));}catch{/* Retain in component. */}}
        remember();setState('Saved locally');setSaveError((error as Error).message);throw error;
      }
    });
    chain.current=task;return task;
  },[attempt.id,remember]);
  useEffect(()=>{
    if(attempt.status!=='active')return;
    remember();
    if(JSON.stringify(draft)!==saved.current)setState('Unsaved');
    if(busy||conflicted.current)return;
    const timer=window.setTimeout(()=>{void save().catch(()=>{});},700);
    return ()=>window.clearTimeout(timer);
  },[draft,busy,attempt.status,remember,save]);
  function sync(value:Attempt){revision.current=value.draft_revision;status.current=value.status;saved.current=JSON.stringify(fromAttempt(value));remember();setState(conflicted.current?'Draft conflict':'Saved');}
  function acceptServer(value:Attempt){
    const backup={...latest.current};setRecovery(backup);
    try{localStorage.setItem('ae-recovery:'+attempt.id,JSON.stringify(backup));}catch{/* Retain in memory. */}
    conflicted.current=false;latest.current=fromAttempt(value);setDraft(latest.current);sync(value);setSaveError('');
  }
  function restore(){if(recovery){setDraft(recovery);setRecovery(null);}}
  return {draft,setDraft,save,state,saveError,sync,recovery,restore,acceptServer};
}
