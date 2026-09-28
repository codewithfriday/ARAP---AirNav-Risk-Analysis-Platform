import { useEffect, useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider } from '@xyflow/react'
import type { Edge, Node, NodeProps } from '@xyflow/react'
import ELK from 'elkjs/lib/elk.bundled.js'
import { App, Button, Card, Col, Descriptions, Empty, Input, InputNumber, Row, Select, Space, Table, Tabs, Tag, Typography } from 'antd'
import { CalculatorOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { api } from '../api'
import { fmtSci } from '../risk'
import { uid } from '../hooks'
import type { EditorProps } from './types'

const elk = new ELK()
const GATE_W = 180, GATE_H = 86, EV = 104

function GateSymbol({ type, k }: { type: string; k?: number }) {
  return (
    <svg width="44" height="30" viewBox="0 0 44 30" style={{ display: 'block', margin: '2px auto 0' }}>
      {type === 'and' ? <path d="M6 29 V13 A16 12 0 0 1 38 13 V29 Z" fill="#fff" stroke="#1F3A5F" strokeWidth="1.6" />
        : <path d="M6 29 Q22 20 38 29 Q36 10 22 1 Q8 10 6 29 Z" fill="#fff" stroke="#1F3A5F" strokeWidth="1.6" />}
      <text x="22" y="24" textAnchor="middle" fontSize="8.5" fontWeight="700" fill="#1F3A5F">{type === 'vote' ? `${k}/n` : type.toUpperCase()}</text>
    </svg>
  )
}

function GateNode({ data }: NodeProps) {
  const d = data as any
  return (
    <div style={{ width: GATE_W, textAlign: 'center' }}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className={`fta-event ${d.top ? 'fta-top' : ''}`} style={{ outline: d.selected ? '3px solid #7FC3CF' : 'none' }}>
        <div className="mono muted" style={{ fontSize: 9 }}>{d.id}{d.p !== undefined ? ` · ${fmtSci(d.p)}` : ''}</div>{d.label}
      </div>
      <GateSymbol type={d.type} k={d.k} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  )
}
function EventNode({ data }: NodeProps) {
  const d = data as any
  const shape = d.type === 'undeveloped' ? { transform: 'rotate(45deg)', borderRadius: 6, width: 70, height: 70 } : d.type === 'house' ? { borderRadius: 4, clipPath: 'polygon(50% 0, 100% 30%, 100% 100%, 0 100%, 0 30%)' } : {}
  const fv = d.fv
  return (
    <div style={{ width: EV, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="fta-event fta-basic" style={{ ...shape, outline: d.selected ? '3px solid #7FC3CF' : 'none', background: fv !== undefined ? `rgba(178,58,58,${Math.min(0.85, 0.08 + fv)})` : undefined, color: fv > 0.5 ? '#fff' : undefined }}>
        <div style={d.type === 'undeveloped' ? { transform: 'rotate(-45deg)' } : {}}><b>{d.id}</b><div style={{ fontSize: 9.5 }}>{fmtSci(d.p)}</div></div>
      </div>
      <div style={{ fontSize: 10, textAlign: 'center', marginTop: 3, lineHeight: 1.2 }}>{d.label}</div>
    </div>
  )
}
const nodeTypes = { gate: GateNode, event: EventNode }

async function layout(tree: any, sel: string | null, fv: Record<string, number>) {
  const nodes = tree.nodes as Record<string, any>
  const ids = Object.keys(nodes)
  const edgesRaw: [string, string][] = []
  for (const [id, n] of Object.entries(nodes)) for (const c of n.children ?? []) edgesRaw.push([id, c])
  const g = await elk.layout({ id: 'root', layoutOptions: { 'elk.algorithm': 'mrtree', 'elk.direction': 'DOWN', 'elk.spacing.nodeNode': '28', 'elk.mrtree.spacing.nodeNode': '28' } as any,
    children: ids.map((id) => ({ id, width: nodes[id].type in { and: 1, or: 1, vote: 1 } ? GATE_W : EV, height: nodes[id].type in { and: 1, or: 1, vote: 1 } ? GATE_H + 40 : EV + 30 })),
    edges: edgesRaw.map(([s, t], i) => ({ id: `e${i}`, sources: [s], targets: [t] })) })
  const pos = Object.fromEntries((g.children ?? []).map((c) => [c.id, { x: c.x ?? 0, y: c.y ?? 0 }]))
  const rn: Node[] = ids.map((id) => {
    const n = nodes[id]
    const isGate = ['and', 'or', 'vote'].includes(n.type)
    return { id, type: isGate ? 'gate' : 'event', position: pos[id], data: { ...n, id, top: id === tree.top, selected: sel === id, fv: fv[id] }, draggable: false }
  })
  const re: Edge[] = edgesRaw.map(([s, t], i) => ({ id: `e${i}`, source: s, target: t, type: 'smoothstep', style: { stroke: '#6B7280' } }))
  return { nodes: rn, edges: re }
}

export default function FtaEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const tree = model.tree ?? { top: 'TOP', nodes: { TOP: { type: 'or', label: 'Top event', children: [] } } }
  const ccf = tree.ccf_groups ?? []
  const [sel, setSel] = useState<string | null>(null)
  const [graph, setGraph] = useState<{ nodes: Node[]; edges: Edge[] }>({ nodes: [], edges: [] })
  const fv = useMemo(() => Object.fromEntries((results?.importance ?? []).map((x: any) => [x.event, x.fussell_vesely])), [results])
  useEffect(() => { layout(tree, sel, fv).then(setGraph) }, [model, sel, fv]) // eslint-disable-line react-hooks/exhaustive-deps

  const setTree = (t: any) => setModel({ ...model, tree: t })
  const n = sel ? tree.nodes[sel] : null
  const updNode = (k: string, v: any) => setTree({ ...tree, nodes: { ...tree.nodes, [sel!]: { ...n, [k]: v } } })
  const addChild = (type: string) => {
    const prefix = ['and', 'or', 'vote'].includes(type) ? 'G' : 'E'
    let i = 1
    while (tree.nodes[`${prefix}${i}`]) i++
    const id = `${prefix}${i}`
    const child = ['and', 'or', 'vote'].includes(type) ? { type, label: 'New gate', children: [], ...(type === 'vote' ? { k: 2 } : {}) } : { type, label: 'New event', p: 1e-3 }
    setTree({ ...tree, nodes: { ...tree.nodes, [id]: child, [sel!]: { ...n, children: [...(n.children ?? []), id] } } })
    setSel(id)
  }
  const del = () => {
    if (!sel || sel === tree.top) return
    const nodes = Object.fromEntries(Object.entries(tree.nodes).filter(([k]) => k !== sel).map(([k, v]: any) => [k, v.children ? { ...v, children: v.children.filter((c: string) => c !== sel) } : v]))
    setTree({ ...tree, nodes })
    setSel(null)
  }
  const run = async () => {
    try {
      setResults(await api.post('/calc/fta', { tree }))
    } catch (e: any) {
      message.error(e.message)
    }
  }
  const isGate = n && ['and', 'or', 'vote'].includes(n.type)
  const others = Object.keys(tree.nodes).filter((k) => k !== sel && k !== tree.top && !(n?.children ?? []).includes(k))

  return (
    <Tabs items={[
      { key: 't', label: 'Fault tree', children: (
        <Row gutter={12}>
          <Col xs={24} xxl={18}>
            <Space style={{ marginBottom: 8 }}>
              <Button type="primary" icon={<CalculatorOutlined />} onClick={run}>Calculate</Button>
              {results?.top_probability !== undefined && <Tag color="red">P(top) = {fmtSci(results.top_probability, 3)}</Tag>}
              {results && <span className="muted small">Basic events shaded by Fussell–Vesely importance.</span>}
            </Space>
            <div className="flow-wrap tall">
              <ReactFlowProvider>
                <ReactFlow nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} fitView minZoom={0.1} nodesConnectable={false}
                  onNodeClick={(_, x) => setSel(x.id)} onPaneClick={() => setSel(null)}>
                  <Background gap={24} color="#e5e7eb" /><Controls showInteractive={false} />
                </ReactFlow>
              </ReactFlowProvider>
            </div>
          </Col>
          <Col xs={24} xxl={6}>
            <Card size="small" title={n ? `Node ${sel}` : 'Properties'}>
              {!n ? <Empty description="Select a gate or event" /> : (
                <Space orientation="vertical" style={{ width: '100%' }}>
                  <Input.TextArea rows={2} value={n.label} disabled={readOnly} onChange={(e) => updNode('label', e.target.value)} />
                  <Select value={n.type} disabled={readOnly} style={{ width: '100%' }} onChange={(v) => updNode('type', v)}
                    options={(isGate ? ['or', 'and', 'vote'] : ['basic', 'undeveloped', 'house']).map((v) => ({ value: v, label: `Type: ${v}` }))} />
                  {n.type === 'vote' && <InputNumber prefix="k (of n)" min={1} value={n.k} disabled={readOnly} onChange={(v) => updNode('k', v)} />}
                  {!isGate && n.type !== 'house' && <>
                    <Typography.Text type="secondary" className="small">Give a probability, or a rate with time / MTTR / test interval.</Typography.Text>
                    <InputNumber prefix="p" style={{ width: '100%' }} value={n.p} disabled={readOnly} onChange={(v) => updNode('p', v ?? undefined)} />
                    <InputNumber prefix="λ (/h)" style={{ width: '100%' }} value={n.rate} disabled={readOnly} onChange={(v) => updNode('rate', v ?? undefined)} />
                    <Space.Compact style={{ width: '100%' }}>
                      <InputNumber placeholder="t (h)" value={n.time} disabled={readOnly} onChange={(v) => updNode('time', v ?? undefined)} />
                      <InputNumber placeholder="MTTR" value={n.mttr} disabled={readOnly} onChange={(v) => updNode('mttr', v ?? undefined)} />
                      <InputNumber placeholder="test T" value={n.test_interval} disabled={readOnly} onChange={(v) => updNode('test_interval', v ?? undefined)} />
                    </Space.Compact>
                  </>}
                  {n.type === 'house' && <Select value={n.state ? 'true' : 'false'} disabled={readOnly} onChange={(v) => updNode('state', v === 'true')} options={[{ value: 'true', label: 'State: TRUE' }, { value: 'false', label: 'State: FALSE' }]} />}
                  {isGate && !readOnly && <>
                    <Space wrap><Button size="small" icon={<PlusOutlined />} onClick={() => addChild('or')}>OR gate</Button>
                      <Button size="small" icon={<PlusOutlined />} onClick={() => addChild('and')}>AND gate</Button>
                      <Button size="small" icon={<PlusOutlined />} onClick={() => addChild('basic')}>Basic event</Button>
                      <Button size="small" icon={<PlusOutlined />} onClick={() => addChild('undeveloped')}>Undeveloped</Button></Space>
                    {others.length > 0 && <Select size="small" placeholder="Reuse an existing node as input" value={null as any} style={{ width: '100%' }}
                      onChange={(v) => updNode('children', [...(n.children ?? []), v])} options={others.map((k) => ({ value: k, label: `${k} · ${tree.nodes[k].label}` }))} />}
                  </>}
                  {!readOnly && sel !== tree.top && <Button size="small" danger icon={<DeleteOutlined />} onClick={del}>Delete node</Button>}
                </Space>)}
            </Card>
            <Card size="small" title="Common-cause groups (β-factor)" style={{ marginTop: 12 }}
              extra={!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => setTree({ ...tree, ccf_groups: [...ccf, { id: uid('CCF'), members: [], beta: 0.05 }] })} />}>
              {ccf.map((g: any, i: number) => (
                <Space key={g.id} direction="vertical" style={{ width: '100%', marginBottom: 8 }}>
                  <Select mode="multiple" size="small" placeholder="Members" value={g.members} disabled={readOnly} style={{ width: '100%' }}
                    onChange={(v) => setTree({ ...tree, ccf_groups: ccf.map((x: any, j: number) => (j === i ? { ...x, members: v } : x)) })}
                    options={Object.entries(tree.nodes).filter(([, v]: any) => v.type === 'basic').map(([k]) => ({ value: k, label: k }))} />
                  <Space><InputNumber size="small" prefix="β" min={0} max={1} step={0.01} value={g.beta} disabled={readOnly}
                    onChange={(v) => setTree({ ...tree, ccf_groups: ccf.map((x: any, j: number) => (j === i ? { ...x, beta: v } : x)) })} />
                    {!readOnly && <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={() => setTree({ ...tree, ccf_groups: ccf.filter((_: any, j: number) => j !== i) })} />}</Space>
                </Space>))}
              {!ccf.length && <span className="muted small">None defined</span>}
            </Card>
          </Col>
        </Row>) },
      { key: 'r', label: 'Results', children: results?.cut_sets ? (
        <Row gutter={16}>
          <Col xs={24} lg={10}>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Top-event probability (exact, BDD)"><b>{fmtSci(results.top_probability, 4)}</b></Descriptions.Item>
              <Descriptions.Item label="Rare-event approximation">{fmtSci(results.rare_event_approximation, 4)}</Descriptions.Item>
              <Descriptions.Item label="Min-cut upper bound">{fmtSci(results.min_cut_upper_bound, 4)}</Descriptions.Item>
              <Descriptions.Item label="Single points of failure">{results.single_points_of_failure.join(', ') || 'none'}</Descriptions.Item>
              <Descriptions.Item label="Engine">{results.engine_version} · {results.bdd_nodes} BDD nodes</Descriptions.Item>
            </Descriptions>
            <h4 style={{ marginTop: 16 }}>Minimal cut sets</h4>
            <Table rowKey={(r: any) => r.events.join(',')} size="small" pagination={false} dataSource={results.cut_sets} columns={[
              { title: 'Cut set', dataIndex: 'events', render: (e: string[]) => `{${e.join(', ')}}` }, { title: 'Order', dataIndex: 'order', width: 70 },
              { title: 'Probability', dataIndex: 'probability', width: 110, render: (v) => fmtSci(v) },
              { title: 'Share', dataIndex: 'contribution', width: 80, render: (v) => `${(v * 100).toFixed(1)}%` }]} />
          </Col>
          <Col xs={24} lg={14}>
            <h4>Importance measures</h4>
            <Table rowKey="event" size="small" pagination={false} dataSource={results.importance} columns={[
              { title: 'Event', dataIndex: 'event', width: 80 }, { title: 'Description', dataIndex: 'label' },
              { title: 'p', dataIndex: 'probability', width: 90, render: (v) => fmtSci(v) },
              { title: 'Birnbaum', dataIndex: 'birnbaum', width: 100, render: (v) => fmtSci(v) },
              { title: 'Fussell–Vesely', dataIndex: 'fussell_vesely', width: 120, render: (v) => fmtSci(v, 3) }]} />
          </Col>
        </Row>) : <span className="muted">Press Calculate on the Fault tree tab.</span> },
    ]} />
  )
}
