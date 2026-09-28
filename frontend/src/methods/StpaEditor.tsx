import { useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, MarkerType } from '@xyflow/react'
import type { Connection, NodeChange, NodeProps } from '@xyflow/react'
import { Alert, Button, Card, Col, Empty, Input, Row, Segmented, Select, Space, Table, Tabs, Tag, Tree } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import type { EditorProps } from './types'

function SNode({ data }: NodeProps) {
  const d = data as any
  return (
    <div className={`stpa-node ${d.kind}`} style={{ outline: d.selected ? '3px solid #7FC3CF' : 'none' }}>
      <Handle type="target" position={Position.Top} /><Handle type="target" position={Position.Left} id="l" />
      <b>{d.label}</b>{d.process_model && <div className="muted" style={{ fontSize: 10, marginTop: 3 }}>PM: {d.process_model}</div>}
      <Handle type="source" position={Position.Bottom} /><Handle type="source" position={Position.Right} id="r" />
    </div>
  )
}
const nodeTypes = { s: SNode }

function ListEditor({ items, onChange, readOnly, prefix, linkLabel, linkOptions, linkKey }: any) {
  return (
    <Table rowKey="id" size="small" pagination={false} dataSource={items}
      footer={() => !readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => onChange([...items, { id: `${prefix}-${items.length + 1}`, text: '', ...(linkKey ? { [linkKey]: [] } : {}) }])}>Add</Button>}
      columns={[
        { title: 'ID', dataIndex: 'id', width: 70 },
        { title: 'Statement', dataIndex: 'text', render: (v, _r, i) => <Input size="small" value={v} disabled={readOnly} onChange={(e) => onChange(items.map((x: any, j: number) => (j === i ? { ...x, text: e.target.value } : x)))} /> },
        ...(linkKey ? [{ title: linkLabel, dataIndex: linkKey, width: 220, render: (v: string[] = [], _r: any, i: number) => <Select size="small" mode="multiple" style={{ width: '100%' }} value={v} disabled={readOnly}
          options={linkOptions.map((o: any) => ({ value: o.id, label: o.id }))} onChange={(x) => onChange(items.map((y: any, j: number) => (j === i ? { ...y, [linkKey]: x } : y)))} /> }] : []),
        { title: '', width: 40, render: (_, _r, i) => !readOnly && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange(items.filter((_x: any, j: number) => j !== i))} /> },
      ]} />
  )
}

export default function StpaEditor({ model, setModel, readOnly, template, promote }: EditorProps) {
  const m = { losses: [], hazards: [], constraints: [], structure: { nodes: [], edges: [] }, ucas: [], scenarios: [], ...model }
  const set = (k: string, v: any) => setModel({ ...m, [k]: v })
  const [sel, setSel] = useState<string | null>(null)
  const [edgeKind, setEdgeKind] = useState<'control' | 'feedback'>('control')
  const st = m.structure

  const rfNodes = st.nodes.map((n: any) => ({ id: n.id, type: 's', position: { x: n.x ?? 0, y: n.y ?? 0 }, data: { ...n, selected: sel === n.id }, draggable: !readOnly }))
  const rfEdges = st.edges.map((e: any) => ({ id: e.id, source: e.source, target: e.target, label: e.label, labelStyle: { fontSize: 10, fill: e.kind === 'control' ? '#1F3A5F' : '#3C8D5A' },
    style: { stroke: e.kind === 'control' ? '#1F3A5F' : '#3C8D5A', strokeDasharray: e.kind === 'feedback' ? '6 4' : undefined, strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: e.kind === 'control' ? '#1F3A5F' : '#3C8D5A' }, sourceHandle: e.kind === 'feedback' ? 'r' : undefined, targetHandle: e.kind === 'feedback' ? 'l' : undefined }))
  const onNodesChange = (ch: NodeChange[]) => {
    let moved = false
    const nodes = st.nodes.map((n: any) => { const c = ch.find((x) => x.type === 'position' && (x as any).id === n.id && (x as any).position) as any; if (c) { moved = true; return { ...n, x: c.position.x, y: c.position.y } } return n })
    if (moved) set('structure', { ...st, nodes })
  }
  const onConnect = (c: Connection) => set('structure', { ...st, edges: [...st.edges, { id: `e${Date.now()}`, source: c.source, target: c.target, kind: edgeKind, label: edgeKind === 'control' ? 'Control action' : 'Feedback' }] })
  const selNode = st.nodes.find((n: any) => n.id === sel)
  const selEdge = st.edges.find((e: any) => e.id === sel)
  const updNode = (k: string, v: any) => set('structure', { ...st, nodes: st.nodes.map((n: any) => (n.id === sel ? { ...n, [k]: v } : n)) })
  const updEdge = (k: string, v: any) => set('structure', { ...st, edges: st.edges.map((e: any) => (e.id === sel ? { ...e, [k]: v } : e)) })

  const controlActions = useMemo(() => [...new Set<string>(st.edges.filter((e: any) => e.kind === 'control').map((e: any) => e.label as string))], [st])
  const ucaIssues = m.ucas.filter((u: any) => !u.context?.trim() || !(u.hazards ?? []).length).map((u: any) => u.id)
  const addUca = (ca: string, type: string) => set('ucas', [...m.ucas, { id: `UCA-${m.ucas.length + 1}`, control_action: ca, type, text: '', context: '', hazards: [] }])
  const updUca = (id: string, k: string, v: any) => set('ucas', m.ucas.map((u: any) => (u.id === id ? { ...u, [k]: v } : u)))

  const trace = m.losses.map((l: any) => ({ key: l.id, title: <span><Tag color="red">{l.id}</Tag>{l.text}</span>,
    children: m.hazards.filter((h: any) => (h.losses ?? []).includes(l.id)).map((h: any) => ({ key: `${l.id}/${h.id}`, title: <span><Tag color="orange">{h.id}</Tag>{h.text}</span>,
      children: [
        ...m.constraints.filter((c: any) => (c.hazards ?? []).includes(h.id)).map((c: any) => ({ key: `${l.id}/${h.id}/${c.id}`, title: <span><Tag color="blue">{c.id}</Tag>{c.text}</span> })),
        ...m.ucas.filter((u: any) => (u.hazards ?? []).includes(h.id)).map((u: any) => ({ key: `${l.id}/${h.id}/${u.id}`, title: <span><Tag color="purple">{u.id}</Tag>{u.text} <i className="muted">{u.context}</i></span>,
          children: m.scenarios.filter((s: any) => s.uca === u.id).map((s: any) => ({ key: `${l.id}/${h.id}/${u.id}/${s.id}`, title: <span><Tag>{s.id}</Tag>{s.text} → <b>{s.requirement}</b></span> })) })),
      ] })) }))
  const broken = m.hazards.filter((h: any) => !m.ucas.some((u: any) => (u.hazards ?? []).includes(h.id))).map((h: any) => `${h.id} has no UCA`)
    .concat(m.ucas.filter((u: any) => !m.scenarios.some((s: any) => s.uca === u.id)).map((u: any) => `${u.id} has no loss scenario`))

  return (
    <Tabs items={[
      { key: '1', label: '1 · Purpose', children: (
        <Row gutter={16}>
          <Col xs={24} xl={8}><Card size="small" title="Losses"><ListEditor items={m.losses} onChange={(v: any) => set('losses', v)} readOnly={readOnly} prefix="L" /></Card></Col>
          <Col xs={24} xl={8}><Card size="small" title="System-level hazards"><ListEditor items={m.hazards} onChange={(v: any) => set('hazards', v)} readOnly={readOnly} prefix="H" linkKey="losses" linkLabel="Losses" linkOptions={m.losses} /></Card></Col>
          <Col xs={24} xl={8}><Card size="small" title="System-level constraints"><ListEditor items={m.constraints} onChange={(v: any) => set('constraints', v)} readOnly={readOnly} prefix="SC" linkKey="hazards" linkLabel="Hazards" linkOptions={m.hazards} /></Card></Col>
        </Row>) },
      { key: '2', label: '2 · Control structure', children: (
        <Row gutter={12}>
          <Col xs={24} xxl={17}>
            <Space style={{ marginBottom: 8 }} wrap>
              {!readOnly && ['controller', 'automation', 'process'].map((k) => <Button key={k} size="small" icon={<PlusOutlined />}
                onClick={() => { const id = `N${Date.now() % 100000}`; set('structure', { ...st, nodes: [...st.nodes, { id, label: `New ${k}`, kind: k, x: 40, y: 40 }] }); setSel(id) }}>{k}</Button>)}
              {!readOnly && <><span className="muted small">New connections are</span><Segmented size="small" value={edgeKind} onChange={(v) => setEdgeKind(v as any)} options={['control', 'feedback']} /></>}
            </Space>
            <div className="flow-wrap"><ReactFlowProvider>
              <ReactFlow nodes={rfNodes} edges={rfEdges} nodeTypes={nodeTypes} fitView onNodesChange={onNodesChange} onConnect={readOnly ? undefined : onConnect}
                onNodeClick={(_, n) => setSel(n.id)} onEdgeClick={(_, e) => setSel(e.id)} onPaneClick={() => setSel(null)}>
                <Background gap={24} color="#e5e7eb" /><Controls showInteractive={false} />
              </ReactFlow></ReactFlowProvider></div>
            <div className="small muted" style={{ marginTop: 6 }}>Solid = control action (downward), dashed = feedback. Control-action labels become rows in the UCA table.</div>
          </Col>
          <Col xs={24} xxl={7}><Card size="small" title="Properties">
            {selNode ? <Space orientation="vertical" style={{ width: '100%' }}>
              <Input prefix="Label" value={selNode.label} disabled={readOnly} onChange={(e) => updNode('label', e.target.value)} />
              <Select value={selNode.kind} disabled={readOnly} onChange={(v) => updNode('kind', v)} options={['controller', 'automation', 'process'].map((v) => ({ value: v, label: v }))} />
              <Input.TextArea rows={2} placeholder="Process model (what the controller believes)" value={selNode.process_model} disabled={readOnly} onChange={(e) => updNode('process_model', e.target.value)} />
              {!readOnly && <Button danger size="small" onClick={() => { set('structure', { nodes: st.nodes.filter((n: any) => n.id !== sel), edges: st.edges.filter((e: any) => e.source !== sel && e.target !== sel) }); setSel(null) }}>Delete</Button>}
            </Space> : selEdge ? <Space orientation="vertical" style={{ width: '100%' }}>
              <Input prefix="Label" value={selEdge.label} disabled={readOnly} onChange={(e) => updEdge('label', e.target.value)} />
              <Segmented value={selEdge.kind} disabled={readOnly} onChange={(v) => updEdge('kind', v)} options={['control', 'feedback']} />
              {!readOnly && <Button danger size="small" onClick={() => { set('structure', { ...st, edges: st.edges.filter((e: any) => e.id !== sel) }); setSel(null) }}>Delete</Button>}
            </Space> : <Empty description="Select a box or arrow" />}
          </Card></Col>
        </Row>) },
      { key: '3', label: `3 · Unsafe control actions (${m.ucas.length})`, children: (
        <div>
          {ucaIssues.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} title={`UCAs without a context or a linked hazard: ${ucaIssues.join(', ')} (STP-04)`} />}
          {controlActions.map((ca) => (
            <Card key={ca} size="small" title={<>Control action: <b>{ca}</b></>} style={{ marginBottom: 12 }}>
              <Row gutter={8}>
                {template.uca_types.map((t: string) => (
                  <Col key={t} xs={24} md={12} xl={6}>
                    <div style={{ background: '#F6F8FA', borderRadius: 6, padding: 8, height: '100%' }}>
                      <div className="small" style={{ fontWeight: 600, marginBottom: 6 }}>{t}</div>
                      {m.ucas.filter((u: any) => u.control_action === ca && u.type === t).map((u: any) => (
                        <Card key={u.id} size="small" style={{ marginBottom: 6 }} styles={{ body: { padding: 6 } }}>
                          <Tag>{u.id}</Tag>
                          <Input.TextArea size="small" autoSize placeholder="Unsafe control action" value={u.text} disabled={readOnly} onChange={(e) => updUca(u.id, 'text', e.target.value)} style={{ marginTop: 4 }} />
                          <Input.TextArea size="small" autoSize placeholder="Context: when …" value={u.context} disabled={readOnly} onChange={(e) => updUca(u.id, 'context', e.target.value)} style={{ marginTop: 4 }} />
                          <Select size="small" mode="multiple" placeholder="Hazards" style={{ width: '100%', marginTop: 4 }} value={u.hazards} disabled={readOnly} onChange={(v) => updUca(u.id, 'hazards', v)} options={m.hazards.map((h: any) => ({ value: h.id, label: h.id }))} />
                          {!readOnly && <Button size="small" type="link" danger onClick={() => set('ucas', m.ucas.filter((x: any) => x.id !== u.id))}>remove</Button>}
                        </Card>))}
                      {!readOnly && <Button size="small" type="dashed" block icon={<PlusOutlined />} onClick={() => addUca(ca, t)}>UCA</Button>}
                    </div>
                  </Col>))}
              </Row>
            </Card>))}
          {!controlActions.length && <Empty description="Add control-action arrows in the control structure first" />}
        </div>) },
      { key: '4', label: `4 · Loss scenarios (${m.scenarios.length})`, children: (
        <div>
          <Space style={{ marginBottom: 8 }}>
            {!readOnly && <Button icon={<PlusOutlined />} onClick={() => set('scenarios', [...m.scenarios, { id: `S-${m.scenarios.length + 1}`, uca: m.ucas[0]?.id, type: template.scenario_types[0], text: '', requirement: '' }])}>Scenario</Button>}
            {!readOnly && <Button onClick={() => promote(m.hazards.map((h: any) => ({ row_id: h.id, title: h.text, causes: m.ucas.filter((u: any) => (u.hazards ?? []).includes(h.id)).map((u: any) => `${u.id} ${u.text}`).join('; '),
              controls: m.scenarios.filter((s: any) => m.ucas.some((u: any) => u.id === s.uca && (u.hazards ?? []).includes(h.id))).map((s: any) => s.requirement).filter(Boolean) })))}>Send hazards to hazard log</Button>}
          </Space>
          <Table rowKey="id" size="small" pagination={false} dataSource={m.scenarios} columns={[
            { title: 'ID', dataIndex: 'id', width: 60 },
            { title: 'UCA', dataIndex: 'uca', width: 120, render: (v, r: any) => <Select size="small" value={v} disabled={readOnly} style={{ width: 110 }} options={m.ucas.map((u: any) => ({ value: u.id, label: u.id }))} onChange={(x) => set('scenarios', m.scenarios.map((s: any) => (s.id === r.id ? { ...s, uca: x } : s)))} /> },
            { title: 'Type', dataIndex: 'type', width: 230, render: (v, r: any) => <Select size="small" value={v} disabled={readOnly} style={{ width: 220 }} options={template.scenario_types.map((t: string) => ({ value: t, label: t }))} onChange={(x) => set('scenarios', m.scenarios.map((s: any) => (s.id === r.id ? { ...s, type: x } : s)))} /> },
            { title: 'Scenario', dataIndex: 'text', render: (v, r: any) => <Input.TextArea size="small" autoSize value={v} disabled={readOnly} onChange={(e) => set('scenarios', m.scenarios.map((s: any) => (s.id === r.id ? { ...s, text: e.target.value } : s)))} /> },
            { title: 'Requirement / constraint', dataIndex: 'requirement', render: (v, r: any) => <Input.TextArea size="small" autoSize value={v} disabled={readOnly} onChange={(e) => set('scenarios', m.scenarios.map((s: any) => (s.id === r.id ? { ...s, requirement: e.target.value } : s)))} /> },
            { title: '', width: 40, render: (_, r: any) => !readOnly && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => set('scenarios', m.scenarios.filter((s: any) => s.id !== r.id))} /> },
          ]} />
        </div>) },
      { key: '5', label: 'Traceability', children: (
        <div>
          {broken.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} title="Broken chains (STP-06)" description={broken.join(' · ')} />}
          <Tree defaultExpandAll treeData={trace} selectable={false} />
        </div>) },
    ]} />
  )
}
