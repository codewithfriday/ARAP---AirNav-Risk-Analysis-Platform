import { useEffect, useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, MarkerType } from '@xyflow/react'
import type { Edge, Node, NodeProps } from '@xyflow/react'
import ELK from 'elkjs/lib/elk.bundled.js'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Alert, Button, Card, Checkbox, Col, Empty, Input, Popconfirm, Row, Select, Space, Tag } from 'antd'
import { DeleteOutlined, LinkOutlined } from '@ant-design/icons'
import { api } from '../api'
import type { EditorProps } from './types'

const elk = new ELK()
const TYPES = ['goal', 'strategy', 'solution', 'context', 'assumption', 'justification'] as const
const PREFIX: Record<string, string> = { goal: 'G', strategy: 'S', solution: 'Sn', context: 'C', assumption: 'A', justification: 'J' }
const CONTEXTUAL = new Set(['context', 'assumption', 'justification'])
const SIZE: Record<string, [number, number]> = { goal: [220, 86], strategy: [230, 76], solution: [118, 118], context: [200, 70], assumption: [190, 76], justification: [190, 76] }
const COLOR: Record<string, string> = { goal: '#1F3A5F', strategy: '#2A7F8E', solution: '#3C8D5A', context: '#6B7280', assumption: '#A16207', justification: '#7C3AED' }

/** GSN Community Standard v3 node shapes. */
function GsnNode({ data }: NodeProps) {
  const d = data as any
  const n = d.node
  const [w, h] = SIZE[n.type] ?? [200, 80]
  const c = COLOR[n.type]
  const ring = d.selected ? '0 0 0 3px #7FC3CF' : d.issue ? '0 0 0 2px #D98E04' : 'none'
  const base: React.CSSProperties = { width: w, height: h, border: `2px solid ${c}`, background: '#fff', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '6px 10px', fontSize: 11, lineHeight: 1.25, boxShadow: ring, boxSizing: 'border-box' }
  let shape: React.CSSProperties = {}
  if (n.type === 'strategy') shape = { transform: 'skewX(-14deg)' }
  if (n.type === 'solution') shape = { borderRadius: '50%', padding: 12 }
  if (n.type === 'context') shape = { borderRadius: 36 }
  if (n.type === 'assumption' || n.type === 'justification') shape = { borderRadius: '50%' }
  const inner: React.CSSProperties = n.type === 'strategy' ? { transform: 'skewX(14deg)' } : {}
  const ev = d.evidence
  return (
    <div style={{ position: 'relative' }}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div style={{ ...base, ...shape }}>
        <div style={inner}>
          <div style={{ fontWeight: 700, color: c, fontSize: 11.5 }}>{n.id}</div>
          <div style={{ overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: n.type === 'solution' ? 4 : 3, WebkitBoxOrient: 'vertical' as any }}>{n.text}</div>
          {ev && <div style={{ fontSize: 9.5, color: ev.ok ? '#3C8D5A' : '#B23A3A', marginTop: 2 }}>{ev.label}</div>}
        </div>
      </div>
      {(n.type === 'assumption' || n.type === 'justification') && <div style={{ position: 'absolute', right: 8, bottom: -2, fontWeight: 700, color: c }}>{n.type === 'assumption' ? 'A' : 'J'}</div>}
      {n.undeveloped && <div style={{ position: 'absolute', left: w / 2 - 9, bottom: -22, width: 18, height: 18, border: `2px solid ${c}`, background: '#fff', transform: 'rotate(45deg)' }} title="Undeveloped" />}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  )
}
const nodeTypes = { gsn: GsnNode }

/** Structural checks from the GSN standard (SRS GSN-03). */
export function validateGsn(nodes: any[]) {
  const issues: { id: string; msg: string; level: 'error' | 'warning' }[] = []
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]))
  const kids = (id: string) => nodes.filter((n) => n.parent === id)
  const roots = nodes.filter((n) => !n.parent)
  if (roots.length !== 1) issues.push({ id: roots[1]?.id ?? '-', msg: `The argument must have exactly one top-level goal (found ${roots.length}).`, level: 'error' })
  for (const r of roots) if (r.type !== 'goal') issues.push({ id: r.id, msg: 'The top-level element must be a goal.', level: 'error' })
  for (const n of nodes) {
    const p = n.parent ? byId[n.parent] : null
    if (n.parent && !p) issues.push({ id: n.id, msg: `Parent ${n.parent} does not exist.`, level: 'error' })
    const supp = kids(n.id).filter((k) => !CONTEXTUAL.has(k.type))
    if (n.type === 'goal' && !n.undeveloped && !supp.length) issues.push({ id: n.id, msg: 'Goal is not supported by a strategy, sub-goal or solution — develop it or mark it undeveloped.', level: 'warning' })
    if (n.type === 'goal' && n.undeveloped && supp.length) issues.push({ id: n.id, msg: 'Goal is marked undeveloped but has supporting elements.', level: 'warning' })
    if (n.type === 'strategy' && !supp.length) issues.push({ id: n.id, msg: 'Strategy has no sub-goals.', level: 'warning' })
    if (n.type === 'strategy' && supp.some((k) => k.type !== 'goal')) issues.push({ id: n.id, msg: 'A strategy may only be supported by goals.', level: 'error' })
    if (n.type === 'solution' && kids(n.id).length) issues.push({ id: n.id, msg: 'A solution must be a leaf.', level: 'error' })
    if (n.type === 'solution' && p && p.type !== 'goal') issues.push({ id: n.id, msg: 'A solution must support a goal.', level: 'error' })
    if (n.type === 'solution' && !n.evidence?.ref) issues.push({ id: n.id, msg: 'Solution has no evidence linked.', level: 'warning' })
    if (CONTEXTUAL.has(n.type) && kids(n.id).length) issues.push({ id: n.id, msg: `A ${n.type} must be a leaf.`, level: 'error' })
    if (CONTEXTUAL.has(n.type) && p && !['goal', 'strategy'].includes(p.type)) issues.push({ id: n.id, msg: `A ${n.type} may only be attached to a goal or strategy.`, level: 'error' })
  }
  // cycles
  for (const n of nodes) {
    const seen = new Set<string>()
    let c = n
    while (c?.parent) { if (seen.has(c.id)) { issues.push({ id: n.id, msg: 'Cycle in the argument structure.', level: 'error' }); break } seen.add(c.id); c = byId[c.parent] }
  }
  return issues
}

async function layout(nodes: any[], sel: string | null, evid: (n: any) => any, issueIds: Set<string>) {
  const valid = nodes.filter((n) => !n.parent || nodes.some((m) => m.id === n.parent))
  const g = await elk.layout({
    id: 'root', layoutOptions: { 'elk.algorithm': 'mrtree', 'elk.direction': 'DOWN', 'elk.spacing.nodeNode': '34', 'elk.mrtree.spacing.nodeNode': '34' } as any,
    children: valid.map((n) => ({ id: n.id, width: SIZE[n.type]?.[0] ?? 200, height: (SIZE[n.type]?.[1] ?? 80) + (n.undeveloped ? 26 : 0) })),
    edges: valid.filter((n) => n.parent).map((n) => ({ id: `e-${n.id}`, sources: [n.parent], targets: [n.id] })),
  })
  const pos = Object.fromEntries((g.children ?? []).map((c) => [c.id, { x: c.x ?? 0, y: c.y ?? 0 }]))
  const rn: Node[] = valid.map((n) => ({ id: n.id, type: 'gsn', position: pos[n.id] ?? { x: 0, y: 0 }, draggable: false,
    data: { node: n, selected: sel === n.id, evidence: n.type === 'solution' ? evid(n) : null, issue: issueIds.has(n.id) } }))
  const re: Edge[] = valid.filter((n) => n.parent).map((n) => {
    const ctx = CONTEXTUAL.has(n.type)
    return { id: `e-${n.id}`, source: n.parent, target: n.id, type: 'smoothstep', style: { stroke: '#4B5563', strokeDasharray: ctx ? '5 4' : undefined },
      markerEnd: ctx ? { type: MarkerType.Arrow, color: '#4B5563', width: 18, height: 18 } : { type: MarkerType.ArrowClosed, color: '#4B5563', width: 18, height: 18 } }
  })
  return { nodes: rn, edges: re }
}

export default function GsnEditor({ model, setModel, readOnly }: EditorProps) {
  const nodes: any[] = model.nodes ?? [{ id: 'G1', type: 'goal', text: 'The change is acceptably safe' }]
  const [sel, setSel] = useState<string | null>(null)
  const [graph, setGraph] = useState<{ nodes: Node[]; edges: Edge[] }>({ nodes: [], edges: [] })
  const { data: studies = [] } = useQuery({ queryKey: ['studies-index'], queryFn: () => api.get('/studies') })
  const { data: hazards = [] } = useQuery({ queryKey: ['hazards'], queryFn: () => api.get('/hazards') })
  const setNodes = (n: any[]) => setModel({ ...model, nodes: n })
  const issues = useMemo(() => validateGsn(nodes), [nodes])
  const issueIds = useMemo(() => new Set(issues.map((i) => i.id)), [issues])

  const evid = (n: any) => {
    const e = n.evidence
    if (!e?.ref) return { ok: false, label: 'no evidence' }
    if (e.kind === 'study') {
      const s = studies.find((x: any) => x.id === Number(e.ref))
      return s ? { ok: ['complete', 'closed'].includes(s.status) || ['endorsed', 'accepted', 'closed'].includes(s.assessment.status), label: `${s.method.toUpperCase()} #${s.id} · ${s.status}`, study: s } : { ok: false, label: `study ${e.ref} not found` }
    }
    if (e.kind === 'hazard') {
      const h = hazards.find((x: any) => x.ref === e.ref)
      return h ? { ok: ['closed', 'accepted', 'monitoring'].includes(h.status), label: `${h.ref} · ${h.status}`, hazard: h } : { ok: false, label: `${e.ref} not found` }
    }
    return { ok: true, label: e.kind }
  }
  useEffect(() => { layout(nodes, sel, evid, issueIds).then(setGraph) }, [model, sel, studies, hazards]) // eslint-disable-line react-hooks/exhaustive-deps

  const n = nodes.find((x) => x.id === sel)
  const upd = (patch: any) => setNodes(nodes.map((x) => (x.id === sel ? { ...x, ...patch } : x)))
  const add = (type: string) => {
    const p = PREFIX[type]
    let i = 1
    while (nodes.some((x) => x.id === `${p}${i}`)) i++
    setNodes([...nodes, { id: `${p}${i}`, type, parent: sel, text: '' }])
    setSel(`${p}${i}`)
  }
  const descendants = (id: string): string[] => nodes.filter((x) => x.parent === id).flatMap((x) => [x.id, ...descendants(x.id)])
  const del = () => { const gone = new Set([sel!, ...descendants(sel!)]); setNodes(nodes.filter((x) => !gone.has(x.id))); setSel(null) }
  const allowed: Record<string, string[]> = { goal: ['goal', 'strategy', 'solution', 'context', 'assumption', 'justification'], strategy: ['goal', 'context', 'assumption', 'justification'] }
  const e = n ? evid(n) : null
  const solutions = nodes.filter((x) => x.type === 'solution')
  const linked = solutions.filter((x) => x.evidence?.ref).length

  return (
    <Row gutter={12}>
      <Col xs={24} xxl={16}>
        <Space style={{ marginBottom: 8 }} wrap>
          <Tag color={issues.some((i) => i.level === 'error') ? 'red' : issues.length ? 'orange' : 'green'}>{issues.length ? `${issues.length} issue(s)` : 'Structure valid'}</Tag>
          <Tag>{nodes.filter((x) => x.type === 'goal').length} goals</Tag>
          <Tag>{linked}/{solutions.length} solutions linked to evidence</Tag>
          <Tag>{nodes.filter((x) => x.undeveloped).length} undeveloped</Tag>
          <span className="muted small">Solid arrow = SupportedBy · open arrow, dashed = InContextOf · ◇ = undeveloped. Click an element to edit.</span>
        </Space>
        <div className="flow-wrap tall"><ReactFlowProvider>
          <ReactFlow nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} fitView nodesConnectable={false} onNodeClick={(_, x) => setSel(x.id)} onPaneClick={() => setSel(null)} minZoom={0.15}>
            <Background gap={24} color="#e5e7eb" /><Controls showInteractive={false} />
          </ReactFlow>
        </ReactFlowProvider></div>
      </Col>
      <Col xs={24} xxl={8}>
        <Card size="small" title={n ? `${n.id} — ${n.type}` : 'Element'} extra={n && !readOnly && n.parent && <Popconfirm title="Delete this element and everything below it?" onConfirm={del}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>}>
          {!n ? <Empty description="Select an element in the diagram" /> : (
            <Space orientation="vertical" style={{ width: '100%' }}>
              <Input.TextArea autoSize={{ minRows: 2 }} value={n.text} disabled={readOnly} onChange={(ev) => upd({ text: ev.target.value })} placeholder={n.type === 'goal' ? 'Claim, stated as a proposition' : n.type === 'strategy' ? 'Argue over …' : ''} />
              {n.type === 'goal' && <Checkbox checked={!!n.undeveloped} disabled={readOnly} onChange={(ev) => upd({ undeveloped: ev.target.checked })}>Undeveloped (to be supported later)</Checkbox>}
              {n.parent !== undefined && n.parent !== null && <Space><span className="small">Parent</span>
                <Select size="small" style={{ width: 140 }} value={n.parent} disabled={readOnly} onChange={(v) => upd({ parent: v })}
                  options={nodes.filter((x) => ['goal', 'strategy'].includes(x.type) && x.id !== n.id && !descendants(n.id).includes(x.id)).map((x) => ({ value: x.id, label: x.id }))} /></Space>}
              {n.type === 'solution' && (
                <Card size="small" type="inner" title={<><LinkOutlined /> Evidence</>}>
                  <Space orientation="vertical" style={{ width: '100%' }}>
                    <Select size="small" value={n.evidence?.kind ?? 'study'} disabled={readOnly} style={{ width: 200 }} onChange={(k) => upd({ evidence: { kind: k, ref: null } })}
                      options={[{ value: 'study', label: 'ARAP study' }, { value: 'hazard', label: 'Hazard log entry' }, { value: 'document', label: 'External document' }]} />
                    {(n.evidence?.kind ?? 'study') === 'study' && <Select size="small" showSearch optionFilterProp="label" allowClear value={n.evidence?.ref ?? null} disabled={readOnly} style={{ width: '100%' }}
                      onChange={(v) => upd({ evidence: { kind: 'study', ref: v } })} options={studies.map((s: any) => ({ value: s.id, label: `#${s.id} ${s.method.toUpperCase()} — ${s.title}` }))} />}
                    {n.evidence?.kind === 'hazard' && <Select size="small" showSearch optionFilterProp="label" allowClear value={n.evidence?.ref ?? null} disabled={readOnly} style={{ width: '100%' }}
                      onChange={(v) => upd({ evidence: { kind: 'hazard', ref: v } })} options={hazards.map((h: any) => ({ value: h.ref, label: `${h.ref} — ${h.title}` }))} />}
                    {n.evidence?.kind === 'document' && <Input size="small" placeholder="Document reference / URL" value={n.evidence?.ref ?? ''} disabled={readOnly} onChange={(ev) => upd({ evidence: { kind: 'document', ref: ev.target.value } })} />}
                    {e && <div className="small">Status: <b style={{ color: e.ok ? '#3C8D5A' : '#B23A3A' }}>{e.label}</b>
                      {e.study && <> · <Link to={`/studies/${e.study.id}`}>open study</Link></>}
                      {!e.ok && n.evidence?.ref && <div className="muted">Evidence is not yet complete / accepted — the argument is provisional.</div>}</div>}
                  </Space>
                </Card>)}
              {!readOnly && allowed[n.type] && <div>
                <div className="small muted" style={{ marginBottom: 4 }}>Add below {n.id}</div>
                <Space wrap>{allowed[n.type].map((t) => <Button key={t} size="small" style={{ borderColor: COLOR[t], color: COLOR[t] }} onClick={() => add(t)}>+ {t}</Button>)}</Space>
              </div>}
            </Space>)}
        </Card>
        <Card size="small" title="Argument checks" style={{ marginTop: 12 }}>
          {!issues.length ? <Alert type="success" showIcon title="No structural issues found." /> :
            <Space orientation="vertical" style={{ width: '100%' }}>{issues.map((i, k) => (
              <div key={k} className="small" style={{ cursor: 'pointer' }} onClick={() => setSel(i.id)}>
                <Tag color={i.level === 'error' ? 'red' : 'orange'}>{i.id}</Tag>{i.msg}</div>))}</Space>}
        </Card>
      </Col>
    </Row>
  )
}

export const GSN_TYPES = TYPES
