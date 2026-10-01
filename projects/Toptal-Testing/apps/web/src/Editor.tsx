import {useEffect,useRef} from 'react';
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api.js';
import 'monaco-editor/esm/vs/basic-languages/sql/sql.contribution.js';
import 'monaco-editor/esm/vs/editor/contrib/find/browser/findController.js';
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';

(globalThis as unknown as {MonacoEnvironment:unknown}).MonacoEnvironment = {getWorker:()=>new EditorWorker()};
monaco.editor.defineTheme('workbench',{base:'vs-dark',inherit:true,rules:[],colors:{'editor.background':'#111815','editorLineNumber.foreground':'#5c7065','editorLineNumber.activeForeground':'#b9ccbe','editor.selectionBackground':'#2b4b3a','editor.lineHighlightBackground':'#19231d','editorCursor.foreground':'#b4e9bf'}});

export function Editor({value,onChange,readOnly=false,onRun,theme='dark'}:{value:string;onChange:(v:string)=>void;readOnly?:boolean;onRun:()=>void;theme?:string}) {
  const element=useRef<HTMLDivElement>(null);
  const editor=useRef<monaco.editor.IStandaloneCodeEditor|null>(null);
  const change=useRef(onChange),run=useRef(onRun);
  change.current=onChange;run.current=onRun;
  useEffect(()=>{
    const instance=monaco.editor.create(element.current!,{value,language:'sql',theme:theme==='dark'?'workbench':'vs',automaticLayout:true,editContext:false,minimap:{enabled:false},fontSize:14,lineHeight:24,tabSize:2,scrollBeyondLastLine:false,wordWrap:'on',padding:{top:20,bottom:20},ariaLabel:'SQL query editor',readOnly,renderLineHighlight:'gutter',overviewRulerLanes:0,hideCursorInOverviewRuler:true});
    editor.current=instance;
    const listener=instance.onDidChangeModelContent(()=>change.current(instance.getValue()));
    instance.addCommand(monaco.KeyMod.CtrlCmd|monaco.KeyCode.Enter,()=>run.current());
    return ()=>{listener.dispose();instance.getModel()?.dispose();instance.dispose();editor.current=null;};
  },[]);
  useEffect(()=>{const instance=editor.current;if(instance && instance.getValue()!==value){instance.pushUndoStop();instance.executeEdits('external',[{range:instance.getModel()!.getFullModelRange(),text:value}]);instance.pushUndoStop();}},[value]);
  useEffect(()=>editor.current?.updateOptions({readOnly}),[readOnly]);
  useEffect(()=>monaco.editor.setTheme(theme==='dark'?'workbench':'vs'),[theme]);
  return <div className="editor" ref={element}/>;
}
