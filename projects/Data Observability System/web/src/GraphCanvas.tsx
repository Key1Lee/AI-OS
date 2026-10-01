import type {Edge,MapNode,Stage} from './types';

type DisplayNode={id:string;name:string;subtitle:string;status:string;grain?:string|null;inferred?:boolean};

function positions(nodes:DisplayNode[],edges:{from:string;to:string}[],overview:boolean){
 const rank=new Map<string,number>();const pending=new Set(nodes.map(n=>n.id));
 if(overview)nodes.forEach((n,i)=>{rank.set(n.id,i);pending.delete(n.id);});
 for(let round=0;round<nodes.length&&pending.size;round++){
  let changed=false;
  for(const id of [...pending].sort()){
   const parents=edges.filter(e=>e.to===id&&nodes.some(n=>n.id===e.from)).map(e=>e.from);
   if(parents.every(p=>rank.has(p))){rank.set(id,parents.length?Math.max(...parents.map(p=>rank.get(p)!))+1:0);pending.delete(id);changed=true;}
  }
  if(!changed)break;
 }
 for(const id of pending)rank.set(id,0);
 const counts=new Map<number,number>();
 const result=new Map<string,{x:number;y:number}>();
 nodes.forEach(n=>{const col=rank.get(n.id)||0,row=counts.get(col)||0;counts.set(col,row+1);result.set(n.id,{x:18+col*225,y:22+row*122});});
 return {result,width:Math.max(460,...[...result.values()].map(p=>p.x+205)),height:Math.max(180,...[...result.values()].map(p=>p.y+116))};
}

export function GraphCanvas({nodes=[],edges=[],stages,stageEdges=[],selected,onNode,onStage}:{nodes?:MapNode[];edges?:Edge[];stages?:Stage[];stageEdges?:{from:string;to:string}[];selected?:string;onNode:(id:string)=>void;onStage:(id:string)=>void}){
 const overview=Boolean(stages);
 const display:DisplayNode[]=stages?stages.map(s=>({id:s.id,name:s.name,subtitle:`${s.count} ${s.count===1?'resource':'resources'}`,status:s.failed?'FAILED':'STAGE',inferred:s.classification==='INFERENCE'})):nodes.map(n=>({id:n.id,name:n.name,subtitle:n.node_type.replaceAll('_',' '),status:n.status,grain:n.grain,inferred:n.layer_classification==='INFERENCE'}));
 const connections=stages?stageEdges:edges.map(e=>({from:e.from_node,to:e.to_node}));
 const {result:coords,width,height}=positions(display,connections,overview);
 return <div className="dm-graph-scroll" role="region" aria-label={overview?'System stage overview':'Focused model lineage'} tabIndex={0}><div className="dm-graph" style={{width,height}}>
 <svg width={width} height={height} aria-label="Declared dependency arrows" className="dm-edges"><defs><marker id="dm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/></marker></defs>{connections.map((e,i)=>{const from=coords.get(e.from),to=coords.get(e.to);if(!from||!to)return null;const x=from.x+185,y=from.y+44,tx=to.x,ty=to.y+44;return <path key={i} d={`M ${x} ${y} C ${x+30} ${y}, ${tx-30} ${ty}, ${tx} ${ty}`} fill="none" stroke="currentColor" strokeWidth="1.4" markerEnd="url(#dm-arrow)"><title>Declared dependency</title></path>;})}</svg>
 {display.map(n=>{const p=coords.get(n.id)!;return <button key={n.id} style={{left:p.x,top:p.y}} className={'dm-node '+n.status.toLowerCase()+(selected===n.id?' selected':'')} onClick={()=>overview?onStage(n.id):onNode(n.id)} aria-label={overview?'Expand '+n.name:'Open node '+n.name} aria-pressed={selected===n.id}><span className="dm-node-top"><span>{overview?'STAGE':n.subtitle.toUpperCase()}</span><span className={'dm-status-dot '+n.status.toLowerCase()}/></span><strong>{n.name}</strong><span className="dm-node-subtitle">{overview?n.subtitle:n.status.toLowerCase().replaceAll('_',' ')}</span>{n.grain&&<span className="dm-node-grain">Declared: {n.grain}</span>}{n.inferred&&<span className="dm-inferred">Layer inferred</span>}</button>;})}
 </div></div>;
}
