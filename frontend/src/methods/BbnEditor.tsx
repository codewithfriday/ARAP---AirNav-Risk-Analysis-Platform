import { useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, MarkerType } from '@xyflow/react'
import type { Connection, Node, NodeProps, NodeChange } from '@xyflow/react'
import { Alert, App, Button, Card, Col, Empty, Input, InputNumber, Row, Select, Space, Table, Tabs, Typography } from 'antd'
import { CalculatorOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import type { EditorProps } from './types'

type BNode = { id: string; label: string; states: string[]; parents: string[]; cpt: any }

function uniformCpt(n: BNode, nodes: Record<string, BNode>): any {
  const build = (ps: string[]): any => (ps.length ? nodes[ps[0]].states.map(() => build(ps.slice(1))) : n.states.map(() => 1 / n.states.length))
  return build(n.parents)
}
function combos(ps: string[], nodes: Record<string, BNode>): string[][] {
  if (!ps.length) return [[]]
  const rest = combos(ps.slice(1), nodes)
  return nodes[ps[0]].states.flatMap((s) => rest.map((r) => [s, ...r]))
}
const getAt = (cpt: any, idx: number[]) => idx.reduce((a, i) => a[i], cpt)

function BNodeView({ data }: NodeProps) {
  const d = data as any
  const marg = d.marginals as Record<string, number> | undefined
  return (
    <div className={`bbn-node ${d.evidence ? 'ev' : ''}`} style={{ outline: d.selected ? '3px solid #7FC3CF' : 'none' }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 700, marginBottom: 4 }}>{d.node.label} <span className="muted mono" style={{ fontSize: 9 }}>{d.node.id}</span></div>
      {d.node.states.map((s: string) => (
        <div key={s} style={{ display: 'grid', gridTemplateColumns: '58px 1fr 52px', alignItems: 'center', gap: 4 }}>
          <span style={{ fontWeight: d.evidence === s ? 700 : 400 }}>{s}</span>
          <div style={{ background: '#fff', borderRadius: 3 }}><div className="bbn-bar" style={{ width: `${Math.max(1, (marg?.[s] ?? 0) * 100)}%`, background: d.evidence === s ? '#D98E04' : undefined }} /></div>
          <span className="mono" style={{ fontSize: 10, textAlign: 'right' }}>{marg ? (marg[s] < 0.001 && marg[s] > 0 ? marg[s].toExponential(2) : (marg[s] * 100).toFixed(2) + '%') : ''}</span>
        </div>))}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}
const nodeTypes = { b: BNodeView }

export default function BbnEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const net: { nodes: BNode[] } = model.network ?? { nodes: [] }
  const positions: Record<string, number[]> = model.positions ?? {}
  const evidence: Record<string, string> = model.evidence ?? {}
  const [sel, setSel] = useState<string | null>(null)
  const [sens, setSens] = useState<any[] | null>(null)
  const byId = useMemo(() => Object.fromEntries(net.nodes.map((n) => [n.id, n])), [net])
  const marg = results?.marginals ?? {}
  const setNet = (nodes: BNode[], extra: any = {}) => setModel({ ...model, network: { nodes }, ...extra })

  const rfNodes: Node[] = net.nodes.map((n) => ({ id: n.id, type: 'b', position: { x: positions[n.id]?.[0] ?? 0, y: positions[n.id]?.[1] ?? 0 },
    data: { node: n, marginals: evidence[n.id] ? Object.fromEntries(n.states.map((s) => [s, s === evidence[n.id] ? 1 : 0])) : marg[n.id], evidence: evidence[n.id], selected: sel === n.id }, draggable: !readOnly }))
  const rfEdges = net.nodes.flatMap((n) => n.parents.map((p) => ({ id: `${p}-${n.id}`, source: p, target: n.id, markerEnd: { type: MarkerType.ArrowClosed, color: '#1F3A5F' }, style: { stroke: '#1F3A5F' } })))

  const onNodesChange = (ch: NodeChange[]) => {
    const pos = { ...positions }
    let moved = false
    for (const c of ch) if (c.type === 'position' && c.position) { pos[c.id] = [c.position.x, c.position.y]; moved = true }
    if (moved) setModel({ ...model, positions: pos })
  }
  const onConnect = (c: Connection) => {
    if (!c.source || !c.target || c.source === c.target) return
    const nodes = net.nodes.map((n) => (n.id === c.target && !n.parents.includes(c.source!) ? { ...n, parents: [...n.parents, c.source!] } : n))
    const idx = Object.fromEntries(nodes.map((n) => [n.id, n]))
    setNet(nodes.map((n) => (n.id === c.target ? { ...n, cpt: uniformCpt(n, idx) } : n)))
  }
  const addNode = () => {
    let i = 1
    while (byId[`N${i}`]) i++
    const n: BNode = { id: `N${i}`, label: 'New node', states: ['yes', 'no'], parents: [], cpt: [0.5, 0.5] }
    setModel({ ...model, network: { nodes: [...net.nodes, n] }, positions: { ...positions, [n.id]: [40 * i, 40 * i] } })
    setSel(n.id)
  }
  const n = sel ? byId[sel] : null
  const updNode = (patch: Partial<BNode>, resetCpt = false) => {
    const nodes = net.nodes.map((x) => (x.id === sel ? { ...x, ...patch } : x))
    const idx = Object.fromEntries(nodes.map((x) => [x.id, x]))
    setNet(nodes.map((x) => (resetCpt && (x.id === sel || x.parents.includes(sel!)) ? { ...x, cpt: uniformCpt(x, idx) } : x)))
  }
  const delNode = () => {
    const nodes = net.nodes.filter((x) => x.id !== sel).map((x) => (x.parents.includes(sel!) ? { ...x, parents: x.parents.filter((p) => p !== sel) } : x))
    const idx = Object.fromEntries(nodes.map((x) => [x.id, x]))
    const ev = { ...evidence }; delete ev[sel!]
    setNet(nodes.map((x) => ({ ...x, cpt: x.parents.length === byId[x.id].parents.length ? x.cpt : uniformCpt(x, idx) })), { evidence: ev })
    setSel(null)
  }
  const setCell = (rowIdx: number[], state: number, v: number) => {
    const cpt = structuredClone(n!.cpt)
    const dist = rowIdx.length ? getAt(cpt, rowIdx) : cpt
    dist[state] = v
    if (n!.states.length === 2) dist[1 - state] = +(1 - v).toFixed(12)
    updNode({ cpt })
  }
  const run = async (ev = evidence) => {
    try {
      setResults(await api.post('/calc/bbn', { network: net, evidence: ev }))
    } catch (e: any) {
      message.error(e.message)
    }
  }
  const setEv = (id: string, s: string | undefined) => {
    const ev = { ...evidence }
    if (s) ev[id] = s; else delete ev[id]
    setModel({ ...model, evidence: ev })
    run(ev)
  }
  const runSens = async (target: string, state: string) => {
    try {
      setSens(await api.post('/calc/bbn/sensitivity', { network: net, target, state, evidence }))
    } catch (e: any) {
      message.error(e.message)
    }
  }

  const cptRows = n ? combos(n.parents, byId).map((c) => {
    const idx = c.map((s, i) => byId[n.parents[i]].states.indexOf(s))
    const dist = idx.length ? getAt(n.cpt, idx) : n.cpt
    return { key: c.join('|') || 'prior', combo: c, idx, dist, sum: dist.reduce((a: number, b: number) => a + b, 0) }
  }) : []

  return (
    <Tabs items={[
      { key: 'g', label: 'Network', children: (
        <Row gutter={12}>
          <Col xs={24} xxl={15}>
            <Space style={{ marginBottom: 8 }} wrap>
              {!readOnly && <Button icon={<PlusOutlined />} onClick={addNode}>Node</Button>}
              <Button type="primary" icon={<CalculatorOutlined />} onClick={() => run()}>Update beliefs</Button>
              <span className="muted small">Drag from a node’s bottom handle to another node to add a causal arc. Set evidence in the panel.</span>
            </Space>
            <div className="flow-wrap">
              <ReactFlowProvider>
                <ReactFlow nodes={rfNodes} edges={rfEdges} nodeTypes={nodeTypes} fitView onNodesChange={onNodesChange} onConnect={readOnly ? undefined : onConnect}
                  onNodeClick={(_, x) => setSel(x.id)} onPaneClick={() => setSel(null)} nodesConnectable={!readOnly}
                  onEdgeDoubleClick={(_, e) => !readOnly && setNet(net.nodes.map((x) => (x.id === e.target ? { ...x, parents: x.parents.filter((p) => p !== e.source), cpt: uniformCpt({ ...x, parents: x.parents.filter((p) => p !== e.source) }, byId) } : x)))}>
                  <Background gap={24} color="#e5e7eb" /><Controls showInteractive={false} />
                </ReactFlow>
              </ReactFlowProvider>
            </div>
            {results?.probability_of_evidence !== undefined && Object.keys(evidence).length > 0 && <div className="small muted" style={{ marginTop: 6 }}>P(evidence) = {results.probability_of_evidence.toExponential(3)} · engine {results.engine_version}</div>}
          </Col>
          <Col xs={24} xxl={9}>
            <Card size="small" title={n ? `Node ${n.id}` : 'Node'}>
              {!n ? <Empty description="Select a node" /> : (
                <Space orientation="vertical" style={{ width: '100%' }}>
                  <Input prefix="Label" value={n.label} disabled={readOnly} onChange={(e) => updNode({ label: e.target.value })} />
                  <Input prefix="States" value={n.states.join(', ')} disabled={readOnly}
                    onChange={(e) => { const st = e.target.value.split(',').map((s) => s.trim()).filter(Boolean); if (st.length >= 2) updNode({ states: st }, true) }} />
                  <Space>Evidence <Select size="small" allowClear style={{ width: 160 }} placeholder="none" value={evidence[n.id]} onChange={(v) => setEv(n.id, v)} options={n.states.map((s) => ({ value: s, label: s }))} /></Space>
                  <Typography.Text strong>Conditional probability table</Typography.Text>
                  <Table size="small" pagination={false} dataSource={cptRows} scroll={{ x: true }} columns={[
                    ...n.parents.map((p, i) => ({ title: byId[p].label, render: (_: any, r: any) => r.combo[i] })),
                    ...n.states.map((s, si) => ({ title: `P(${s})`, render: (_: any, r: any) => <InputNumber size="small" min={0} max={1} step={0.001} value={r.dist[si]} disabled={readOnly} style={{ width: 92 }} onChange={(v) => setCell(r.idx, si, v ?? 0)} /> })),
                    { title: 'Σ', render: (_: any, r: any) => <span style={{ color: Math.abs(r.sum - 1) > 1e-9 ? '#B23A3A' : '#3C8D5A' }}>{r.sum.toFixed(3)}</span> },
                  ]} />
                  <Space wrap>
                    <Button size="small" onClick={() => runSens(n.id, n.states[0])}>Sensitivity of P({n.states[0]})</Button>
                    {!readOnly && <Button size="small" danger icon={<DeleteOutlined />} onClick={delNode}>Delete node</Button>}
                  </Space>
                </Space>)}
            </Card>
            {sens && <Card size="small" title="Sensitivity (tornado)" style={{ marginTop: 12 }}>
              {sens.length ? <ReactECharts style={{ height: 40 + sens.length * 34 }} option={{
                grid: { left: 130, right: 30, top: 10, bottom: 20 }, tooltip: {},
                xAxis: { type: 'value', axisLabel: { formatter: (v: number) => v.toExponential(1) } }, yAxis: { type: 'category', data: sens.map((s) => s.label), inverse: true },
                series: [{ type: 'bar', stack: 't', itemStyle: { color: 'transparent' }, data: sens.map((s) => s.min) }, { type: 'bar', stack: 't', itemStyle: { color: '#2A7F8E' }, data: sens.map((s) => s.max - s.min) }],
              }} /> : <Alert type="info" title="No other nodes influence the target." />}
            </Card>}
          </Col>
        </Row>) },
    ]} />
  )
}
