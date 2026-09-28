import { useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, MarkerType } from '@xyflow/react'
import type { NodeChange, NodeProps } from '@xyflow/react'
import { Alert, Button, Card, Col, Empty, Input, Row, Select, Space, Table, Tabs, Tag } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import type { EditorProps } from './types'

const ASPECTS = ['Input', 'Output', 'Precondition', 'Resource', 'Control', 'Time'] as const
const CODE: Record<string, string> = { Input: 'I', Output: 'O', Precondition: 'P', Resource: 'R', Control: 'C', Time: 'T' }
// hexagon with pointy left/right: aspect positions (percent of 200×174 box)
const POS: Record<string, [number, number]> = { I: [0, 50], O: [100, 50], T: [25, 0], C: [75, 0], P: [25, 100], R: [75, 100] }
const TYPE_COLOR: Record<string, string> = { Human: '#2A7F8E', Technological: '#1F3A5F', Organisational: '#D98E04' }
const VAR_COLOR = (v: any) => (v?.timing === 'Not at all' || v?.precision === 'Imprecise' ? '#B23A3A' : v?.timing === 'Too late' || v?.timing === 'Too early' ? '#D98E04' : '#3C8D5A')

function Hex({ data }: NodeProps) {
  const d = data as any
  const c = TYPE_COLOR[d.fn.type] ?? '#2A7F8E'
  return (
    <div className="fram-fn" style={{ filter: d.selected ? 'drop-shadow(0 0 5px #7FC3CF)' : undefined }}>
      <svg viewBox="0 0 200 174" width="200" height="174">
        <polygon points="0,87 50,0 150,0 200,87 150,174 50,174" fill="#fff" stroke={c} strokeWidth="3" />
        {Object.entries(POS).map(([k, [x, y]]) => (
          <g key={k}><circle cx={x * 2} cy={y * 1.74} r="11" fill="#EEF2F6" stroke={c} strokeWidth="1.5" /><text x={x * 2} y={y * 1.74 + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill="#1F3A5F">{k}</text></g>
        ))}
      </svg>
      <div className="label">{d.fn.name}</div>
      <div className="var"><span style={{ color: VAR_COLOR(d.fn.variability) }}>●</span> {d.fn.variability?.timing ?? '–'} / {d.fn.variability?.precision ?? '–'}</div>
      {Object.entries(POS).map(([k, [x, y]]) => (
        <Handle key={k} id={k} type={k === 'O' ? 'source' : 'target'} position={k === 'O' ? Position.Right : k === 'I' ? Position.Left : y === 0 ? Position.Top : Position.Bottom}
          style={{ left: `${x}%`, top: `${y}%`, opacity: 0 }} />
      ))}
    </div>
  )
}
const nodeTypes = { h: Hex }

export default function FramEditor({ model, setModel, readOnly, template }: EditorProps) {
  const fns: any[] = model.functions ?? []
  const [sel, setSel] = useState<string | null>(null)
  const setFns = (f: any[]) => setModel({ ...model, functions: f })
  const upd = (id: string, patch: any) => setFns(fns.map((f) => (f.id === id ? { ...f, ...patch } : f)))

  // couplings: an Output text of one function matching an aspect text of another function (FRM-02)
  const { edges, orphans } = useMemo(() => {
    const outs: Record<string, string> = {}
    fns.forEach((f) => (f.aspects?.Output ?? []).forEach((o: string) => (outs[o.trim().toLowerCase()] = f.id)))
    const es: any[] = []
    const orph: string[] = []
    fns.forEach((f) => ASPECTS.filter((a) => a !== 'Output').forEach((a) => (f.aspects?.[a] ?? []).forEach((t: string) => {
      const src = outs[t.trim().toLowerCase()]
      if (src && src !== f.id) es.push({ id: `${src}-${f.id}-${a}-${t}`, source: src, sourceHandle: 'O', target: f.id, targetHandle: CODE[a], label: t,
        labelStyle: { fontSize: 9.5 }, style: { stroke: '#6B7280' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#6B7280' }, type: 'default' })
      else orph.push(`${f.name}: ${a} “${t}”`)
    })))
    const used = new Set(es.map((e) => e.label.toLowerCase()))
    fns.forEach((f) => (f.aspects?.Output ?? []).forEach((o: string) => { if (!used.has(o.trim().toLowerCase())) orph.push(`${f.name}: Output “${o}” is not used`) }))
    return { edges: es, orphans: orph }
  }, [fns])

  const nodes = fns.map((f) => ({ id: f.id, type: 'h', position: { x: f.x ?? 0, y: f.y ?? 0 }, data: { fn: f, selected: sel === f.id }, draggable: !readOnly }))
  const onNodesChange = (ch: NodeChange[]) => {
    let moved = false
    const n = fns.map((f) => { const c = ch.find((x) => x.type === 'position' && (x as any).id === f.id && (x as any).position) as any; if (c) { moved = true; return { ...f, x: c.position.x, y: c.position.y } } return f })
    if (moved) setFns(n)
  }
  const f = fns.find((x) => x.id === sel)

  return (
    <Tabs items={[
      { key: 'm', label: 'Model', children: (
        <Row gutter={12}>
          <Col xs={24} xxl={16}>
            <Space style={{ marginBottom: 8 }}>
              {!readOnly && <Button icon={<PlusOutlined />} onClick={() => { let i = 1; while (fns.some((x) => x.id === `F${i}`)) i++; setFns([...fns, { id: `F${i}`, name: 'New function', type: 'Human', x: 60, y: 60, aspects: {}, variability: {} }]); setSel(`F${i}`) }}>Function</Button>}
              <span className="muted small">Couplings are drawn automatically when an Output of one function matches an aspect of another.</span>
            </Space>
            <div className="flow-wrap tall"><ReactFlowProvider>
              <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView onNodesChange={onNodesChange} nodesConnectable={false}
                onNodeClick={(_, n) => setSel(n.id)} onPaneClick={() => setSel(null)}>
                <Background gap={24} color="#e5e7eb" /><Controls showInteractive={false} />
              </ReactFlow></ReactFlowProvider></div>
            <Space className="small" style={{ marginTop: 6 }}>{Object.entries(TYPE_COLOR).map(([k, c]) => <span key={k}><span style={{ display: 'inline-block', width: 10, height: 10, border: `2px solid ${c}`, marginRight: 4 }} />{k}</span>)}
              <span className="muted">· dot colour = output variability (green stable, amber timing, red imprecise / not at all)</span></Space>
          </Col>
          <Col xs={24} xxl={8}>
            <Card size="small" title={f ? `Function ${f.id}` : 'Function'}>
              {!f ? <Empty description="Select a function" /> : (
                <Space orientation="vertical" style={{ width: '100%' }}>
                  <Input prefix="Name" value={f.name} disabled={readOnly} onChange={(e) => upd(f.id, { name: e.target.value })} />
                  <Select value={f.type} disabled={readOnly} onChange={(v) => upd(f.id, { type: v })} options={template.function_types.map((t: string) => ({ value: t, label: `Type: ${t}` }))} />
                  {ASPECTS.map((a) => (
                    <Select key={a} mode="tags" placeholder={`${a} (${CODE[a]})`} value={f.aspects?.[a] ?? []} disabled={readOnly} style={{ width: '100%' }}
                      onChange={(v) => upd(f.id, { aspects: { ...f.aspects, [a]: v } })} tokenSeparators={[';']}
                      options={[...new Set(fns.flatMap((x) => x.aspects?.Output ?? []))].map((o) => ({ value: o as string, label: o as string }))} prefix={<b style={{ width: 14, display: 'inline-block' }}>{CODE[a]}</b>} />
                  ))}
                  <Space>
                    <Select value={f.variability?.timing} placeholder="Timing" style={{ width: 130 }} disabled={readOnly} onChange={(v) => upd(f.id, { variability: { ...f.variability, timing: v } })} options={template.timing.map((t: string) => ({ value: t, label: t }))} />
                    <Select value={f.variability?.precision} placeholder="Precision" style={{ width: 130 }} disabled={readOnly} onChange={(v) => upd(f.id, { variability: { ...f.variability, precision: v } })} options={template.precision.map((t: string) => ({ value: t, label: t }))} />
                  </Space>
                  <Input.TextArea rows={2} placeholder="Notes on variability / how it is managed" value={f.notes} disabled={readOnly} onChange={(e) => upd(f.id, { notes: e.target.value })} />
                  {!readOnly && <Button danger size="small" icon={<DeleteOutlined />} onClick={() => { setFns(fns.filter((x) => x.id !== f.id)); setSel(null) }}>Delete function</Button>}
                </Space>)}
            </Card>
            {orphans.length > 0 && <Alert style={{ marginTop: 12 }} type="info" showIcon title={`Unmatched aspects (${orphans.length})`} description={<div className="small">{orphans.slice(0, 12).map((o) => <div key={o}>{o}</div>)}</div>} />}
          </Col>
        </Row>) },
      { key: 't', label: 'Function table', children: (
        <Table rowKey="id" size="small" pagination={false} dataSource={fns} columns={[
          { title: 'ID', dataIndex: 'id', width: 60 }, { title: 'Function', dataIndex: 'name' }, { title: 'Type', dataIndex: 'type', width: 130 },
          ...ASPECTS.map((a) => ({ title: CODE[a], render: (_: any, r: any) => (r.aspects?.[a] ?? []).join('; ') })),
          { title: 'Variability', render: (_: any, r: any) => <Tag color={VAR_COLOR(r.variability)}>{r.variability?.timing ?? '–'} / {r.variability?.precision ?? '–'}</Tag> },
          { title: 'Notes', dataIndex: 'notes' },
        ]} />) },
    ]} />
  )
}
