import { useCallback, useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, getNodesBounds, getViewportForBounds, ReactFlowProvider, useReactFlow } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import { toPng, toSvg } from 'html-to-image'
import { Alert, Button, Card, Col, Divider, Empty, Input, Row, Segmented, Select, Space, Switch, Table, Tabs, Tag, Tooltip, Typography } from 'antd'
import { PlusOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined, PictureOutlined, WarningOutlined } from '@ant-design/icons'
import { uid } from '../hooks'
import type { BowtieModel, Barrier, Path } from './bowtieLayout'
import { layoutBowtie, bowtieChecks, EFFECTIVENESS_COLORS, emptyBowtie } from './bowtieLayout'
import type { EditorProps } from './types'

const H = (p: { id?: string; type: 'source' | 'target'; pos: Position }) => <Handle id={p.id} type={p.type} position={p.pos} style={{ opacity: 0, width: 4, height: 4 }} />

function HazardNode({ data }: NodeProps) {
  const d = data as any
  return <div className={`bt-node bt-hazard ${d.selected ? 'bt-selected' : ''}`}><div className="small muted" style={{ fontWeight: 500 }}>HAZARD</div>{d.text}<H type="source" pos={Position.Bottom} /></div>
}
function TopNode({ data }: NodeProps) {
  const d = data as any
  return <div className={`bt-top ${d.selected ? 'bt-selected' : ''}`}><div><div style={{ fontSize: 10, opacity: 0.85 }}>TOP EVENT</div>{d.text}</div>
    <H id="left" type="target" pos={Position.Left} /><H id="right" type="source" pos={Position.Right} /><H id="topin" type="target" pos={Position.Top} /></div>
}
function ThreatNode({ data }: NodeProps) {
  const d = data as any
  return <div className={`bt-node bt-threat ${d.selected ? 'bt-selected' : ''}`}>{d.path.text}<H type="source" pos={Position.Right} /></div>
}
function ConsNode({ data }: NodeProps) {
  const d = data as any
  return <div className={`bt-node bt-cons ${d.selected ? 'bt-selected' : ''}`}>{d.path.text}{d.path.severity && <span className="badge" style={{ background: '#B23A3A' }}>{d.path.severity}</span>}<H type="target" pos={Position.Left} /></div>
}
function BarrierNode({ data }: NodeProps) {
  const d = data as any
  const b: Barrier = d.barrier
  return (
    <div className={`bt-node bt-barrier ${d.selected ? 'bt-selected' : ''}`}>
      <div className="bar" style={{ background: d.color }} />
      <div>{b.text}{b.critical && <span className="badge" title="Safety-critical">C</span>}{d.shared ? <span className="badge" style={{ background: '#2A7F8E' }} title="Shared across paths">×{d.shared}</span> : null}</div>
      <div className="meta">{b.owner || 'no owner'} · {b.effectiveness}</div>
      <H type="target" pos={Position.Left} /><H type="source" pos={Position.Right} /><H id="bottom" type="target" pos={Position.Bottom} />
    </div>
  )
}
function EfNode({ data }: NodeProps) {
  const d = data as any
  return <div className={`bt-node bt-ef ${d.selected ? 'bt-selected' : ''}`}><b>EF:</b> {d.ef.text}{d.ef.ef_barriers.length > 0 && <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>↳ {d.ef.ef_barriers.join('; ')}</div>}<H id="top" type="source" pos={Position.Top} /></div>
}
const nodeTypes = { hazard: HazardNode, top: TopNode, threat: ThreatNode, cons: ConsNode, barrier: BarrierNode, ef: EfNode }

function Canvas({ m, colorBy, selected, onSelect }: { m: BowtieModel; colorBy: string; selected: string | null; onSelect: (id: string | null) => void }) {
  const { nodes, edges } = useMemo(() => layoutBowtie(m, colorBy, selected), [m, colorBy, selected])
  const rf = useReactFlow()
  const exportImage = async (kind: 'png' | 'svg') => {
    const b = getNodesBounds(rf.getNodes())
    const w = Math.max(1200, b.width + 120), h = Math.max(700, b.height + 120)
    const vp = getViewportForBounds(b, w, h, 0.2, 2, 0.05)
    const el = document.querySelector('.bowtie-flow .react-flow__viewport') as HTMLElement
    const opts = { backgroundColor: '#ffffff', width: w, height: h, style: { width: `${w}px`, height: `${h}px`, transform: `translate(${vp.x}px, ${vp.y}px) scale(${vp.zoom})` } }
    const url = kind === 'png' ? await toPng(el, { ...opts, pixelRatio: 2 }) : await toSvg(el, opts)
    const a = document.createElement('a'); a.href = url; a.download = `bowtie.${kind}`; a.click()
  }
  return (
    <div className="flow-wrap tall bowtie-flow" style={{ position: 'relative' }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.15} nodesConnectable={false}
        onNodeClick={(_, n) => onSelect(n.type === 'barrier' ? (n.data as any).barrier.id : n.type === 'ef' ? (n.data as any).ef.id : n.id)}
        onPaneClick={() => onSelect(null)}>
        <Background gap={24} color="#e5e7eb" />
        <Controls showInteractive={false} />
      </ReactFlow>
      <Space style={{ position: 'absolute', right: 12, top: 12, zIndex: 5 }}>
        <Button size="small" icon={<PictureOutlined />} onClick={() => exportImage('png')}>PNG</Button>
        <Button size="small" icon={<PictureOutlined />} onClick={() => exportImage('svg')}>SVG</Button>
      </Space>
    </div>
  )
}

export default function BowtieEditor({ model, setModel, readOnly, promote }: EditorProps) {
  const m: BowtieModel = useMemo(() => ({ ...emptyBowtie(), ...(model as any) }), [model])
  const [colorBy, setColorBy] = useState('effectiveness')
  const [sel, setSel] = useState<string | null>(null)
  const set = useCallback((f: (x: BowtieModel) => BowtieModel) => setModel(f(structuredClone(m))), [m, setModel])
  const warnings = bowtieChecks(m)

  const findPath = (id: string) => m.threats.find((p) => p.id === id) ?? m.consequences.find((p) => p.id === id)
  const selPath = sel ? findPath(sel) : undefined
  const selBarrier = sel ? m.barriers[sel] : undefined
  const selEf = sel ? m.escalation.find((e) => e.id === sel) : undefined
  const isThreat = selPath && m.threats.some((p) => p.id === selPath.id)

  const addPath = (kind: 'threats' | 'consequences') => {
    const id = uid(kind === 'threats' ? 'T' : 'C')
    set((x) => { x[kind].push({ id, text: kind === 'threats' ? 'New threat' : 'New consequence', barriers: [] }); return x })
    setSel(id)
  }
  const updPath = (k: keyof Path, v: any) => set((x) => { const p = [...x.threats, ...x.consequences].find((q) => q.id === sel)!; (p as any)[k] = v; return x })
  const addBarrier = (existing?: string) => set((x) => {
    const p = [...x.threats, ...x.consequences].find((q) => q.id === sel)!
    const id = existing ?? uid('B')
    if (!existing) x.barriers[id] = { id, text: 'New barrier', kind: 'human', owner: '', effectiveness: 'unknown', critical: false, verification: 'planned' }
    if (!p.barriers.includes(id)) p.barriers.push(id)
    return x
  })
  const moveBarrier = (i: number, d: number) => set((x) => { const p = [...x.threats, ...x.consequences].find((q) => q.id === sel)!; const b = p.barriers; [b[i], b[i + d]] = [b[i + d], b[i]]; return x })
  const removeFromPath = (bid: string) => set((x) => { const p = [...x.threats, ...x.consequences].find((q) => q.id === sel)!; p.barriers = p.barriers.filter((b) => b !== bid); return x })
  const deleteSelected = () => {
    if (!sel) return
    set((x) => {
      x.threats = x.threats.filter((p) => p.id !== sel)
      x.consequences = x.consequences.filter((p) => p.id !== sel)
      if (x.barriers[sel]) {
        delete x.barriers[sel]
        for (const p of [...x.threats, ...x.consequences]) p.barriers = p.barriers.filter((b) => b !== sel)
        x.escalation = x.escalation.filter((e) => e.barrier !== sel)
      }
      x.escalation = x.escalation.filter((e) => e.id !== sel)
      return x
    })
    setSel(null)
  }
  const updBarrier = (k: keyof Barrier, v: any) => set((x) => { (x.barriers[sel!] as any)[k] = v; return x })
  const addEf = () => { const id = uid('EF'); set((x) => { x.escalation.push({ id, text: 'New escalation factor', barrier: sel!, ef_barriers: [] }); return x }); setSel(id) }
  const updEf = (k: string, v: any) => set((x) => { const e = x.escalation.find((q) => q.id === sel)!; (e as any)[k] = v; return x })

  const doPromote = () => promote([{ row_id: 'bowtie', title: m.top_event, causes: m.threats.map((t) => t.text).join('; '),
    consequences: m.consequences.map((c) => c.text).join('; '), controls: Object.values(m.barriers).map((b) => b.text) }])

  const panel = () => {
    if (!sel) return <Empty description="Select an element on the diagram to edit it" />
    if (sel === 'hazard' || sel === 'top') return (
      <div>
        <Typography.Text strong>{sel === 'hazard' ? 'Hazard' : 'Top event'}</Typography.Text>
        <Input.TextArea rows={3} value={sel === 'hazard' ? m.hazard : m.top_event} disabled={readOnly}
          onChange={(e) => set((x) => { if (sel === 'hazard') x.hazard = e.target.value; else x.top_event = e.target.value; return x })} />
        {sel === 'top' && <div className="small muted" style={{ marginTop: 6 }}>Phrase the top event as the moment control is lost, before any damage occurs.</div>}
      </div>)
    if (selPath) {
      const others = Object.values(m.barriers).filter((b) => !selPath.barriers.includes(b.id))
      return (
        <div>
          <Typography.Text strong>{isThreat ? 'Threat' : 'Consequence'}</Typography.Text>
          <Input.TextArea rows={2} value={selPath.text} disabled={readOnly} onChange={(e) => updPath('text', e.target.value)} />
          {!isThreat && <div style={{ marginTop: 8 }}>Severity <Select size="small" style={{ width: 90 }} value={selPath.severity} disabled={readOnly} allowClear
            onChange={(v) => updPath('severity', v)} options={['A', 'B', 'C', 'D', 'E'].map((v) => ({ value: v, label: v }))} /></div>}
          <Divider titlePlacement="left" plain style={{ margin: '12px 0 6px' }}>{isThreat ? 'Prevention' : 'Recovery'} barriers (in order)</Divider>
          <div>{selPath.barriers.map((bid, i) => (
            <div key={bid} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f0f0f0', padding: '4px 0' }}>
              <a onClick={() => setSel(bid)}>{i + 1}. {m.barriers[bid]?.text}</a>
              {!readOnly && <span>
                <Button size="small" type="text" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => moveBarrier(i, -1)} />
                <Button size="small" type="text" icon={<ArrowDownOutlined />} disabled={i === selPath.barriers.length - 1} onClick={() => moveBarrier(i, 1)} />
                <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => removeFromPath(bid)} /></span>}
            </div>))}</div>
          {!readOnly && <Space orientation="vertical" style={{ width: '100%', marginTop: 8 }}>
            <Button size="small" icon={<PlusOutlined />} onClick={() => addBarrier()}>New barrier on this path</Button>
            {others.length > 0 && <Select size="small" placeholder="Add an existing (shared) barrier" style={{ width: '100%' }} value={null as any}
              onChange={(v) => addBarrier(v)} options={others.map((b) => ({ value: b.id, label: b.text }))} />}
            <Button size="small" danger icon={<DeleteOutlined />} onClick={deleteSelected}>Delete {isThreat ? 'threat' : 'consequence'}</Button>
          </Space>}
        </div>)
    }
    if (selBarrier) {
      const on = [...m.threats, ...m.consequences].filter((p) => p.barriers.includes(selBarrier.id))
      return (
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Typography.Text strong>Barrier</Typography.Text>
          <Input.TextArea rows={2} value={selBarrier.text} disabled={readOnly} onChange={(e) => updBarrier('text', e.target.value)} />
          <Select value={selBarrier.kind} disabled={readOnly} onChange={(v) => updBarrier('kind', v)} style={{ width: '100%' }}
            options={['hardware', 'software', 'human', 'human-hardware', 'procedure', 'organisational'].map((v) => ({ value: v, label: `Type: ${v}` }))} />
          <Select value={selBarrier.effectiveness} disabled={readOnly} onChange={(v) => updBarrier('effectiveness', v)} style={{ width: '100%' }}
            options={Object.keys(EFFECTIVENESS_COLORS).map((v) => ({ value: v, label: <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: EFFECTIVENESS_COLORS[v], marginRight: 6 }} />Effectiveness: {v}</span> }))} />
          <Select value={selBarrier.verification} disabled={readOnly} onChange={(v) => updBarrier('verification', v)} style={{ width: '100%' }}
            options={['existing-verified', 'existing-unverified', 'planned'].map((v) => ({ value: v, label: `Status: ${v}` }))} />
          <Input prefix="Owner" value={selBarrier.owner} disabled={readOnly} onChange={(e) => updBarrier('owner', e.target.value)} />
          <Input prefix="SPI / audit" value={selBarrier.spi ?? ''} disabled={readOnly} onChange={(e) => updBarrier('spi', e.target.value)} />
          <Space><Switch checked={selBarrier.critical} disabled={readOnly} onChange={(v) => updBarrier('critical', v)} /> Safety-critical barrier</Space>
          <div className="small muted">On {on.length} path(s): {on.map((p) => p.text).join('; ')}</div>
          {!readOnly && <Space><Button size="small" icon={<WarningOutlined />} onClick={addEf}>Add escalation factor</Button>
            <Button size="small" danger icon={<DeleteOutlined />} onClick={deleteSelected}>Delete barrier</Button></Space>}
        </Space>)
    }
    if (selEf) return (
      <Space orientation="vertical" style={{ width: '100%' }}>
        <Typography.Text strong>Escalation factor on “{m.barriers[selEf.barrier]?.text}”</Typography.Text>
        <Input.TextArea rows={2} value={selEf.text} disabled={readOnly} onChange={(e) => updEf('text', e.target.value)} />
        <div className="small">Escalation-factor barriers (one per line)</div>
        <Input.TextArea rows={3} value={selEf.ef_barriers.join('\n')} disabled={readOnly} onChange={(e) => updEf('ef_barriers', e.target.value.split('\n').filter(Boolean))} />
        {!readOnly && <Button size="small" danger icon={<DeleteOutlined />} onClick={deleteSelected}>Delete escalation factor</Button>}
      </Space>)
    return null
  }

  const register = Object.values(m.barriers).map((b) => ({ ...b, paths: [...m.threats, ...m.consequences].filter((p) => p.barriers.includes(b.id)).map((p) => p.text).join('; '),
    side: m.threats.some((p) => p.barriers.includes(b.id)) ? (m.consequences.some((p) => p.barriers.includes(b.id)) ? 'both' : 'prevention') : 'recovery' }))

  return (
    <Tabs items={[
      { key: 'd', label: 'Diagram', children: (
        <Row gutter={12}>
          <Col xs={24} xxl={18}>
            <Space style={{ marginBottom: 8 }} wrap>
              {!readOnly && <><Button icon={<PlusOutlined />} onClick={() => addPath('threats')}>Threat</Button>
                <Button icon={<PlusOutlined />} onClick={() => addPath('consequences')}>Consequence</Button></>}
              <span className="muted small">Colour barriers by</span>
              <Segmented size="small" value={colorBy} onChange={(v) => setColorBy(String(v))} options={[{ label: 'Effectiveness', value: 'effectiveness' }, { label: 'Type', value: 'kind' }, { label: 'Owner', value: 'owner' }]} />
              {!readOnly && <Button onClick={doPromote}>Send to hazard log</Button>}
              {warnings.length > 0 && <Tooltip title={warnings.join('\n')}><Tag color="gold" icon={<WarningOutlined />}>{warnings.length} check(s)</Tag></Tooltip>}
            </Space>
            <ReactFlowProvider><Canvas m={m} colorBy={colorBy} selected={sel} onSelect={setSel} /></ReactFlowProvider>
            {colorBy === 'effectiveness' && <Space className="small" style={{ marginTop: 6 }}>{Object.entries(EFFECTIVENESS_COLORS).map(([k, c]) => <span key={k}><span style={{ display: 'inline-block', width: 10, height: 10, background: c, borderRadius: 2, marginRight: 4 }} />{k}</span>)}
              <span className="muted">· C = safety-critical · ×n = shared barrier · EF = escalation factor</span></Space>}
          </Col>
          <Col xs={24} xxl={6}><Card size="small" title="Properties" style={{ position: 'sticky', top: 8 }}>{panel()}</Card></Col>
        </Row>) },
      { key: 'r', label: `Barrier register (${register.length})`, children: (
        <Table rowKey="id" size="small" dataSource={register} pagination={false} columns={[
          { title: 'Barrier', dataIndex: 'text' }, { title: 'Side', dataIndex: 'side', width: 100 }, { title: 'Type', dataIndex: 'kind', width: 130 },
          { title: 'Owner', dataIndex: 'owner', width: 150 },
          { title: 'Effectiveness', dataIndex: 'effectiveness', width: 120, render: (v) => <Tag color={EFFECTIVENESS_COLORS[v]}>{v}</Tag> },
          { title: 'Critical', dataIndex: 'critical', width: 80, render: (v) => (v ? 'Yes' : '') }, { title: 'Status', dataIndex: 'verification', width: 150 },
          { title: 'Paths', dataIndex: 'paths' }, { title: 'SPI / audit', dataIndex: 'spi' },
        ]} />) },
      { key: 'c', label: `Checks (${warnings.length})`, children: warnings.length ? warnings.map((w, i) => <Alert key={i} type="warning" showIcon title={w} style={{ marginBottom: 8 }} />) : <Alert type="success" title="No issues found" /> },
    ]} />
  )
}
