import { Background, Handle, MarkerType, Position, ReactFlow, type Node, type NodeProps } from '@xyflow/react';
import { Database, Layers3, Sigma, Table2 } from 'lucide-react';
import { StatusPill } from './components';
import type { Model } from './types';

type FlowData = { model: Model; selected: boolean; index: string; value?: string | null } & Record<string, unknown>;
type StoryNode = Node<FlowData, 'model'>;
function ModelNode({ data }: NodeProps<StoryNode>) {
  const model = data.model;
  const Icon = model.layer === 'source' ? Database : model.layer === 'staging' ? Layers3 : model.layer === 'metric' ? Sigma : Table2;
  return <div className={`model-node ${model.layer} ${data.selected ? 'selected' : ''} ${model.status === 'fail' ? 'broken' : ''}`}>
    <Handle id="in" type="target" position={Position.Left} />
    <div className="node-head"><span><Icon size={15}/>{model.layer.toUpperCase()}</span><small>{data.index}</small></div>
    <strong>{model.name}</strong>
    <div className="node-count">{model.layer === 'metric' ? data.value == null ? '—' : `$${data.value}` : model.row_count ?? '—'}{model.layer !== 'metric' && <span> rows</span>}</div>
    <StatusPill status={model.grain.status} label={model.grain.status === 'unknown' ? 'GRAIN UNKNOWN' : model.grain.label} />
    <Handle id="out" type="source" position={Position.Right} />
  </div>;
}
const nodeTypes = { model: ModelNode };

export function StoryFlow({ models, selected, value, choose, inspect }: { models: Model[]; selected: string; value?: string | null; choose: (id: string) => void; inspect: (source: string, target: string) => void }) {
  const mainIds = ['raw_orders', 'stg_orders', 'fct_orders', 'revenue'];
  const extra = models.filter(m => !mainIds.includes(m.id));
  const nodes: StoryNode[] = models.map(model => {
    const index = mainIds.indexOf(model.id);
    return { id: model.id, type: 'model', position: index >= 0 ? { x: index * 220, y: 36 } : { x: 220 + extra.indexOf(model) * 220, y: 247 },
      sourcePosition: Position.Right, targetPosition: Position.Left,
      data: { model, selected: selected === model.id, index: index >= 0 ? `0${index + 1}` : '+', value: model.id === 'revenue' ? value : null },
      ariaLabel: `${model.name}: ${model.row_count ?? 'not built'} rows, ${model.grain.label}` };
  });
  const ids = new Set(models.map(m => m.id));
  const edges = models.flatMap(model => model.parents.filter(parent => ids.has(parent)).map(parent => ({
    id: `${parent}→${model.id}`, source: parent, target: model.id, sourceHandle:'out', targetHandle:'in',
    label: model.id === 'stg_orders' ? 'CLEAN' : model.id === 'revenue' ? 'MEASURE' : 'MODEL',
    style: { stroke: model.status === 'fail' ? '#ce7d4a' : '#96afa3', strokeWidth: 1.6 },
    labelStyle: { fontSize: 10, fontWeight: 700, fill: '#60756b', letterSpacing: 1 }, labelBgPadding: [8, 5] as [number,number],
    labelBgStyle: { fill: '#f5f7f3' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#96afa3', width: 16, height: 16 },
  })));
  return <div className="flow-scroll"><div className={`flow-canvas ${extra.length ? 'has-extra' : ''}`}>
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: .04 }}
      nodesDraggable={false} nodesConnectable={false} edgesFocusable={false} panOnDrag={false} zoomOnScroll={false}
      zoomOnPinch={false} zoomOnDoubleClick={false} minZoom={.5} maxZoom={1} preventScrolling={false}
      onNodeClick={(_, node) => choose(node.id)} onEdgeClick={(_, edge) => inspect(edge.source, edge.target)}
      proOptions={{ hideAttribution: true }}>
      <Background color="#d5dfd5" gap={20} size={1} />
    </ReactFlow>
  </div></div>;
}
