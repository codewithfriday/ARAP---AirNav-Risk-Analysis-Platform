import { useMemo } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, MarkerType } from '@xyflow/react'
import type { Connection, Edge, Node, NodeChange, NodeProps } from '@xyflow/react'
import { Tag } from 'antd'

export const LAYERS = ['O', 'R', 'L', 'I', 'E'] as const
export const LAYER_NAME: Record<string, string> = { O: 'Organisational influences', R: 'Risk controls', L: 'Local conditions', I: 'Individual actions', E: 'Occurrence events' }
export const LAYER_COLOR: Record<string, string> = { O: '#F4B6D2', R: '#CDBAF0', L: '#FBE67A', I: '#FBC477', E: '#B7DBA3' }
const LANE_BG: Record<string, string> = { O: '#FDF0F6', R: '#F5F0FC', L: '#FFFBE3', I: '#FFF4E3', E: '#F1F8ED' }
export const SUPPORT_TERMS = ['SS', 'S', 'NE', 'O', 'SO']
export const SUPPORT_LABEL: Record<string, string> = { SO: 'Strongly oppose', O: 'Oppose', NE: 'No effect', S: 'Support', SS: 'Strongly support' }
export const PROB_TERMS = ['AC', 'VP', 'PR', 'ML', 'IM', 'HU']
export const PROB_LABEL: Record<string, string> = { HU: 'Highly unlikely', IM: 'Improbable', ML: 'More or less likely', PR: 'Probable', VP: 'Very probable', AC: 'Almost certain' }
export const PROB_COLOR: Record<string, string> = { HU: '#9CA3AF', IM: '#6B9BD1', ML: '#D9A441', PR: '#E0782F', VP: '#C2452D', AC: '#8B1E1E' }
export const SUPPORT_COLOR: Record<string, string> = { SO: '#1F6E43', O: '#4E9E6E', NE: '#9CA3AF', S: '#D0782F', SS: '#B23A3A' }

export type Block = { id: string; layer: string; kind: 'evidence' | 'hypothesis' | 'finding'; label: string; text?: string; factor?: string | null; quote?: string; quote_verified?: boolean; past?: any; x?: number; y?: number }
export type AEdge = { source: string; target: string; role?: 'input' | 'context' }
export type AModel = { blocks: Block[]; edges: AEdge[]; rules?: Record<string, any[]> }

const LANE_H = 190
const COL_W = 250
const LEFT = 150

/** Default positions: lanes top→bottom O R L I E; within a lane, columns by depth in the input graph. */
export function layout(m: AModel): Record<string, { x: number; y: number }> {
  const ins: Record<string, string[]> = {}
  m.blocks.forEach((b) => { ins[b.id] = [] })
  m.edges.forEach((e) => ins[e.target]?.push(e.source))
  const depth: Record<string, number> = {}
  const d = (id: string, seen = new Set<string>()): number => {
    if (depth[id] !== undefined) return depth[id]
    if (seen.has(id)) return 0
    seen.add(id)
    const v = ins[id].length ? 1 + Math.max(...ins[id].map((p) => d(p, seen))) : 0
    depth[id] = v
    return v
  }
  m.blocks.forEach((b) => d(b.id))
  const pos: Record<string, { x: number; y: number }> = {}
  const used: Record<string, number> = {}
  const sorted = [...m.blocks].sort((a, b) => depth[a.id] - depth[b.id])
  for (const b of sorted) {
    const li = Math.max(0, LAYERS.indexOf(b.layer as any))
    const k = used[b.layer] ?? 0
    const col = Math.max(k, depth[b.id])
    used[b.layer] = col + 1
    pos[b.id] = { x: b.x ?? LEFT + col * COL_W, y: b.y ?? li * LANE_H + 28 }
  }
  return pos
}

function Lane({ data }: NodeProps) {
  const d = data as any
  return (
    <div style={{ width: d.w, height: LANE_H - 6, background: LANE_BG[d.layer], borderTop: `3px solid ${LAYER_COLOR[d.layer]}`, borderRadius: 4 }}>
      <div style={{ width: 128, padding: '8px 10px', fontSize: 12, fontWeight: 700, color: '#374151' }}>
        {d.layer} · {LAYER_NAME[d.layer]}
      </div>
    </div>
  )
}

function BlockView({ data }: NodeProps) {
  const d = data as any
  const b: Block = d.block
  const border = d.selected ? '2px solid #1F3A5F' : `1px solid ${b.kind === 'evidence' ? '#9CA3AF' : '#1F3A5F'}`
  return (
    <div style={{ width: 210, background: '#fff', border, borderRadius: 6, boxShadow: '0 1px 3px rgba(0,0,0,.08)', fontSize: 11.5 }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ background: LAYER_COLOR[b.layer], padding: '3px 7px', borderRadius: '5px 5px 0 0', display: 'flex', justifyContent: 'space-between', gap: 4 }}>
        <span style={{ fontWeight: 700 }}>{b.kind === 'evidence' ? 'Evidence' : b.kind === 'hypothesis' ? 'Hypothesis' : 'Finding'}</span>
        <span className="mono" style={{ fontSize: 10, opacity: 0.7 }}>{b.id}</span>
      </div>
      <div style={{ padding: '5px 7px' }}>
        <div style={{ fontWeight: 600, lineHeight: 1.25 }}>{b.label || <i className="muted">untitled</i>}</div>
        {b.factor && <div className="mono muted" style={{ fontSize: 9.5, marginTop: 2 }}>{b.factor}</div>}
        {b.quote_verified === false && b.quote && <Tag color="red" style={{ fontSize: 10, marginTop: 3 }}>quote not found</Tag>}
        {d.extra}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

const nodeTypes = { lane: Lane, block: BlockView }

type Props = {
  model: AModel
  height?: number
  editable?: boolean
  selected?: string | null
  selectedEdge?: string | null
  onSelect?: (id: string | null) => void
  onSelectEdge?: (id: string | null) => void
  onChange?: (m: AModel) => void
  extra?: (b: Block) => React.ReactNode
}

export function edgeId(e: AEdge) { return `${e.source}->${e.target}` }

export default function AcciMap({ model, height = 620, editable = false, selected, selectedEdge, onSelect, onSelectEdge, onChange, extra }: Props) {
  const pos = useMemo(() => layout(model), [model])
  const maxX = Math.max(900, ...Object.values(pos).map((p) => p.x + 260))
  const lanes: Node[] = LAYERS.map((l, i) => ({ id: `lane-${l}`, type: 'lane', position: { x: 0, y: i * LANE_H }, data: { layer: l, w: maxX },
    draggable: false, selectable: false, connectable: false, zIndex: -1, style: { pointerEvents: 'none' as const } }))
  const nodes: Node[] = [...lanes, ...model.blocks.map((b) => ({ id: b.id, type: 'block', position: pos[b.id], draggable: editable,
    data: { block: b, selected: selected === b.id, extra: extra?.(b) } }))]
  const edges: Edge[] = model.edges.map((e) => {
    const ctx = e.role === 'context'
    const sel = selectedEdge === edgeId(e)
    const c = sel ? '#B23A3A' : ctx ? '#9CA3AF' : '#1F3A5F'
    return { id: edgeId(e), source: e.source, target: e.target, markerEnd: { type: MarkerType.ArrowClosed, color: c },
      style: { stroke: c, strokeWidth: sel ? 2.5 : 1.5, strokeDasharray: ctx ? '5 4' : undefined } }
  })
  const onNodesChange = (ch: NodeChange[]) => {
    if (!editable || !onChange) return
    let moved = false
    const blocks = model.blocks.map((b) => {
      const c = ch.find((x) => x.type === 'position' && x.id === b.id && (x as any).position) as any
      if (!c) return b
      moved = true
      return { ...b, x: Math.round(c.position.x), y: Math.round(c.position.y) }
    })
    if (moved) onChange({ ...model, blocks })
  }
  const onDragStop = (_: any, n: Node) => {
    if (!editable || !onChange) return
    const li = Math.min(4, Math.max(0, Math.floor((n.position.y + 40) / LANE_H)))
    const layer = LAYERS[li]
    onChange({ ...model, blocks: model.blocks.map((b) => (b.id === n.id ? { ...b, layer, x: Math.round(n.position.x), y: Math.round(n.position.y) } : b)) })
  }
  const onConnect = (c: Connection) => {
    if (!editable || !onChange || !c.source || !c.target || c.source === c.target) return
    if (model.edges.some((e) => e.source === c.source && e.target === c.target)) return
    onChange({ ...model, edges: [...model.edges, { source: c.source, target: c.target, role: 'input' }] })
  }
  return (
    <div style={{ height, border: '1px solid #e5e7eb', borderRadius: 6 }}>
      <ReactFlowProvider>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.2} onNodesChange={onNodesChange}
          onNodeDragStop={onDragStop} onConnect={editable ? onConnect : undefined} nodesConnectable={editable}
          onNodeClick={(_, n) => { if (n.type === 'block') { onSelect?.(n.id); onSelectEdge?.(null) } }}
          onEdgeClick={(_, e) => { onSelectEdge?.(e.id); onSelect?.(null) }}
          onPaneClick={() => { onSelect?.(null); onSelectEdge?.(null) }} proOptions={{ hideAttribution: true }}>
          <Background gap={24} color="#eef0f3" /><Controls showInteractive={false} />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  )
}
