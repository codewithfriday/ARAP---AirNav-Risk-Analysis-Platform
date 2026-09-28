import { useState } from 'react'
import { Alert, App, Button, Card, Col, Descriptions, Empty, Input, InputNumber, Popconfirm, Row, Segmented, Select, Space, Table, Tabs } from 'antd'
import { CalculatorOutlined, DeleteOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import { fmtSci } from '../risk'
import EditableTable from '../components/EditableTable'
import type { EditorProps } from './types'

type RNode = { type: 'series' | 'parallel' | 'koon' | 'block'; label: string; children?: RNode[]; k?: number; mtbf?: number; mttr?: number }
const HPY = 8760
const avail = (b: RNode) => (b.mtbf ?? 0) / ((b.mtbf ?? 0) + (b.mttr ?? 0))
const getAt = (n: RNode, p: number[]): RNode => (p.length ? getAt(n.children![p[0]], p.slice(1)) : n)
const setAt = (n: RNode, p: number[], f: (x: RNode) => RNode | null): RNode | null => {
  if (!p.length) return f(n)
  const ch = (n.children ?? []).map((c, i) => (i === p[0] ? setAt(c, p.slice(1), f) : c)).filter(Boolean) as RNode[]
  return { ...n, children: ch }
}
const same = (a: number[] | null, b: number[]) => !!a && a.length === b.length && a.every((x, i) => x === b[i])

/** Nested drawing: series left→right, parallel/k-out-of-n stacked with rails. */
function Draw({ n, path, sel, onSel, depth = 0 }: { n: RNode; path: number[]; sel: number[] | null; onSel: (p: number[]) => void; depth?: number }) {
  const on = same(sel, path)
  const outline = on ? '2px solid #2A7F8E' : '1px dashed #cbd5e1'
  if (n.type === 'block') {
    const a = avail(n)
    return (
      <div onClick={(e) => { e.stopPropagation(); onSel(path) }} style={{ minWidth: 118, border: `2px solid ${on ? '#2A7F8E' : '#1F3A5F'}`, background: on ? '#E3F1F3' : '#fff', borderRadius: 4, padding: '6px 8px', cursor: 'pointer', textAlign: 'center', fontSize: 11 }}>
        <b>{n.label}</b>
        <div className="muted" style={{ fontSize: 10 }}>MTBF {n.mtbf} h · MTTR {n.mttr} h</div>
        <div style={{ fontSize: 10, color: a < 0.999 ? '#B23A3A' : '#3C8D5A' }}>A = {a.toFixed(6)}</div>
      </div>)
  }
  const kids = n.children ?? []
  const head = <div style={{ fontSize: 10, color: '#6B7280', marginBottom: 4 }}>{n.type === 'koon' ? `${n.k ?? 1}-out-of-${kids.length}` : n.type}: <b>{n.label}</b></div>
  if (n.type === 'series') return (
    <div onClick={(e) => { e.stopPropagation(); onSel(path) }} style={{ outline, padding: 8, borderRadius: 6, cursor: 'pointer', background: depth ? 'transparent' : '#fbfcfd' }}>
      {head}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        {kids.map((c, i) => <div key={i} style={{ display: 'flex', alignItems: 'center' }}>{i > 0 && <div style={{ width: 18, height: 2, background: '#4B5563' }} />}<Draw n={c} path={[...path, i]} sel={sel} onSel={onSel} depth={depth + 1} /></div>)}
        {!kids.length && <span className="muted small">empty</span>}
      </div>
    </div>)
  return (
    <div onClick={(e) => { e.stopPropagation(); onSel(path) }} style={{ outline, padding: 8, borderRadius: 6, cursor: 'pointer' }}>
      {head}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, borderLeft: '2px solid #4B5563', borderRight: '2px solid #4B5563', padding: '0 12px' }}>
        {kids.map((c, i) => <div key={i} style={{ display: 'flex', alignItems: 'center' }}><div style={{ width: 10, height: 2, background: '#4B5563', marginLeft: -12 }} /><Draw n={c} path={[...path, i]} sel={sel} onSel={onSel} depth={depth + 1} /><div style={{ flex: 1, minWidth: 10, height: 2, background: '#4B5563', marginRight: -12 }} /></div>)}
        {!kids.length && <span className="muted small">empty</span>}
      </div>
    </div>)
}

function MarkovSvg({ states, transitions, pi }: { states: any[]; transitions: any[]; pi?: Record<string, number> }) {
  const n = states.length
  if (!n) return null
  const W = 520, H = 300, R = 105, cx = W / 2, cy = H / 2
  const pos = Object.fromEntries(states.map((s, i) => [s.id, n === 1 ? [cx, cy] : [cx + R * 1.6 * Math.cos((2 * Math.PI * i) / n - Math.PI / 2), cy + R * Math.sin((2 * Math.PI * i) / n - Math.PI / 2)]]))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ background: '#fbfcfd', border: '1px solid #e5e7eb', borderRadius: 8 }}>
      <defs><marker id="mk" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#4B5563" /></marker></defs>
      {transitions.filter((t) => pos[t.from] && pos[t.to]).map((t, i) => {
        const [x1, y1] = pos[t.from], [x2, y2] = pos[t.to]
        const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1
        const nx = -dy / L, ny = dx / L, off = 14
        const sx = x1 + (dx / L) * 34 + nx * off, sy = y1 + (dy / L) * 34 + ny * off
        const ex = x2 - (dx / L) * 34 + nx * off, ey = y2 - (dy / L) * 34 + ny * off
        return <g key={i}><line x1={sx} y1={sy} x2={ex} y2={ey} stroke="#4B5563" markerEnd="url(#mk)" />
          <text x={(sx + ex) / 2 + nx * 10} y={(sy + ey) / 2 + ny * 10} fontSize={9.5} fill="#374151" textAnchor="middle">{fmtSci(Number(t.rate), 2)}/h</text></g>
      })}
      {states.map((s) => { const [x, y] = pos[s.id]; return (
        <g key={s.id}><circle cx={x} cy={y} r={32} fill={s.up ? '#E8F3EC' : '#F8E3E3'} stroke={s.up ? '#3C8D5A' : '#B23A3A'} strokeWidth={2} />
          <text x={x} y={y - 2} textAnchor="middle" fontSize={12} fontWeight={700} fill="#1F3A5F">{s.id}</text>
          {pi?.[s.id] !== undefined && <text x={x} y={y + 13} textAnchor="middle" fontSize={9} fill="#374151">π={fmtSci(pi[s.id], 3)}</text>}</g>) })}
    </svg>)
}

export default function RbdEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const root: RNode = model.rbd ?? { type: 'series', label: 'System', children: [] }
  const mk = model.markov ?? { states: [], transitions: [] }
  const [sel, setSel] = useState<number[] | null>([])
  const setRoot = (r: RNode) => setModel({ ...model, rbd: r })
  const setMk = (m: any) => setModel({ ...model, markov: m })
  const n = sel ? getAt(root, sel) : null
  const upd = (patch: Partial<RNode>) => setRoot(setAt(root, sel!, (x) => ({ ...x, ...patch }))!)
  const add = (type: RNode['type']) => {
    const child: RNode = type === 'block' ? { type, label: 'New block', mtbf: 10000, mttr: 4 } : { type, label: `New ${type}`, children: [], ...(type === 'koon' ? { k: 2 } : {}) }
    setRoot(setAt(root, sel!, (x) => ({ ...x, children: [...(x.children ?? []), child] }))!)
  }
  const del = () => { setRoot(setAt(root, sel!, () => null)!); setSel([]) }
  const move = (d: -1 | 1) => {
    const parent = sel!.slice(0, -1), i = sel![sel!.length - 1], j = i + d
    setRoot(setAt(root, parent, (x) => { const c = [...(x.children ?? [])]; if (j < 0 || j >= c.length) return x; [c[i], c[j]] = [c[j], c[i]]; return { ...x, children: c } })!)
    setSel([...parent, j])
  }
  const runRbd = async () => { try { setResults({ ...results, rbd: await api.post('/calc/rbd', root) }) } catch (e: any) { message.error(e.message) } }
  const runMk = async () => { try { setResults({ ...results, markov: await api.post('/calc/markov', mk) }) } catch (e: any) { message.error(e.message) } }
  const r = results?.rbd, m = results?.markov

  return (
    <Tabs items={[
      { key: 'rbd', label: 'Reliability block diagram', children: (
        <Row gutter={12}>
          <Col xs={24} xxl={16}>
            <div style={{ overflow: 'auto', padding: 12, border: '1px solid #e5e7eb', borderRadius: 8, background: '#fbfcfd' }} onClick={() => setSel([])}>
              <Draw n={root} path={[]} sel={sel} onSel={setSel} />
            </div>
            <Space style={{ marginTop: 10 }}><Button type="primary" icon={<CalculatorOutlined />} onClick={runRbd}>Calculate availability</Button>
              <span className="muted small">Blocks are assumed independent — check with common cause analysis.</span></Space>
            {r && <Row gutter={12} style={{ marginTop: 12 }}>
              <Col xs={24} lg={10}><Descriptions bordered size="small" column={1}>
                <Descriptions.Item label="Availability">{r.availability.toFixed(8)}</Descriptions.Item>
                <Descriptions.Item label="Unavailability">{fmtSci(r.unavailability, 3)}</Descriptions.Item>
                <Descriptions.Item label="Expected downtime"><b>{r.downtime_hours_per_year.toFixed(3)} h/yr</b> ({(r.downtime_hours_per_year * 60).toFixed(1)} min)</Descriptions.Item>
              </Descriptions></Col>
              <Col xs={24} lg={14}><ReactECharts style={{ height: 220 }} notMerge option={{
                grid: { left: 150, right: 30, top: 10, bottom: 30 }, tooltip: { valueFormatter: (v: number) => `${v.toFixed(2)} min/yr` },
                xAxis: { type: 'value', name: 'downtime saved if perfect (min/yr)', nameLocation: 'middle', nameGap: 22 },
                yAxis: { type: 'category', inverse: true, data: r.blocks.map((b: any) => b.block) },
                series: [{ type: 'bar', data: r.blocks.map((b: any) => +(b.improvement_if_perfect * HPY * 60).toFixed(3)), itemStyle: { color: '#2A7F8E' } }] }} /></Col>
            </Row>}
          </Col>
          <Col xs={24} xxl={8}>
            <Card size="small" title="Selected element" extra={n && sel!.length > 0 && !readOnly && <Space>
              <Button size="small" onClick={() => move(-1)}>↑</Button><Button size="small" onClick={() => move(1)}>↓</Button>
              <Popconfirm title="Delete this element?" onConfirm={del}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm></Space>}>
              {!n ? <Empty /> : <Space orientation="vertical" style={{ width: '100%' }}>
                <Input prefix="Label" value={n.label} disabled={readOnly} onChange={(e) => upd({ label: e.target.value })} />
                <Segmented value={n.type} disabled={readOnly} options={['series', 'parallel', 'koon', 'block']} onChange={(t) => upd(t === 'block' ? { type: 'block', mtbf: n.mtbf ?? 10000, mttr: n.mttr ?? 4, children: undefined } : { type: t as any, children: n.children ?? [] })} />
                {n.type === 'koon' && <InputNumber prefix="k (needed)" min={1} max={(n.children ?? []).length || 1} value={n.k} disabled={readOnly} onChange={(v) => upd({ k: v ?? 1 })} />}
                {n.type === 'block' && <Space>
                  <InputNumber prefix="MTBF (h)" min={1} value={n.mtbf} disabled={readOnly} onChange={(v) => upd({ mtbf: v ?? 1 })} style={{ width: 170 }} />
                  <InputNumber prefix="MTTR (h)" min={0} value={n.mttr} disabled={readOnly} onChange={(v) => upd({ mttr: v ?? 0 })} style={{ width: 150 }} /></Space>}
                {n.type === 'block' && <div className="small">Block availability A = MTBF / (MTBF + MTTR) = <b>{avail(n).toFixed(6)}</b></div>}
                {n.type !== 'block' && !readOnly && <Space wrap><span className="small muted">Add inside:</span>
                  {(['block', 'series', 'parallel', 'koon'] as const).map((t) => <Button key={t} size="small" onClick={() => add(t)}>+ {t}</Button>)}</Space>}
              </Space>}
            </Card>
          </Col>
        </Row>) },
      { key: 'mk', label: 'Markov model', children: (
        <Row gutter={12}>
          <Col xs={24} xl={13}>
            <Alert type="info" showIcon style={{ marginBottom: 10 }} title="Use a Markov model where blocks are not independent: shared repair crews, cold/warm standby, imperfect switchover (coverage). Rates are per hour (λ = 1/MTBF, μ = 1/MTTR)." />
            <Card size="small" title="States">
              <EditableTable readOnly={readOnly} rows={mk.states} onChange={(s) => setMk({ ...mk, states: s })} newRow={() => ({ id: `S${mk.states.length}`, label: '', up: true })}
                columns={[{ key: 'id', title: 'ID', width: 70 }, { key: 'label', title: 'Description' }, { key: 'up', title: 'Service up?', type: 'bool', width: 90 }]} />
            </Card>
            <Card size="small" title="Transitions" style={{ marginTop: 10 }}>
              <EditableTable readOnly={readOnly} rows={mk.transitions} onChange={(t) => setMk({ ...mk, transitions: t })} newRow={() => ({ from: mk.states[0]?.id, to: mk.states[1]?.id, rate: 1e-4, label: '' })}
                columns={[{ key: 'from', title: 'From', type: 'select', options: mk.states.map((s: any) => s.id), width: 80 }, { key: 'to', title: 'To', type: 'select', options: mk.states.map((s: any) => s.id), width: 80 },
                  { key: 'rate', title: 'Rate (/h)', type: 'number', width: 120, min: 0 }, { key: 'label', title: 'Meaning' }]} />
            </Card>
            <Space style={{ marginTop: 10 }}>
              <Select style={{ width: 220 }} placeholder="Initial state (for MTTFF)" allowClear value={mk.initial} onChange={(v) => setMk({ ...mk, initial: v })} options={mk.states.map((s: any) => ({ value: s.id, label: s.id }))} />
              <Button type="primary" icon={<CalculatorOutlined />} onClick={runMk}>Solve</Button></Space>
          </Col>
          <Col xs={24} xl={11}>
            <MarkovSvg states={mk.states} transitions={mk.transitions} pi={m?.steady_state} />
            {m && <Descriptions bordered size="small" column={1} style={{ marginTop: 10 }}>
              <Descriptions.Item label="Availability">{m.availability.toFixed(9)}</Descriptions.Item>
              <Descriptions.Item label="Unavailability"><b>{fmtSci(m.unavailability, 4)}</b> ({(m.unavailability * HPY * 60).toFixed(2)} min/yr)</Descriptions.Item>
              <Descriptions.Item label="Failure frequency">{fmtSci(m.failure_frequency_per_hour, 3)} /h</Descriptions.Item>
              <Descriptions.Item label="System MTBF">{m.mtbf_system_hours ? `${Math.round(m.mtbf_system_hours).toLocaleString()} h` : '—'}</Descriptions.Item>
              <Descriptions.Item label="Mean down time">{m.mean_down_time_hours?.toFixed(2) ?? '—'} h</Descriptions.Item>
              <Descriptions.Item label="MTTFF">{m.mttff_hours ? `${Math.round(m.mttff_hours).toLocaleString()} h (${(m.mttff_hours / HPY).toFixed(1)} yr)` : '—'}</Descriptions.Item>
            </Descriptions>}
            {m && <Table style={{ marginTop: 10 }} size="small" pagination={false} rowKey="id" dataSource={mk.states.map((s: any) => ({ ...s, pi: m.steady_state[s.id] }))}
              columns={[{ title: 'State', dataIndex: 'id', width: 60 }, { title: 'Description', dataIndex: 'label' }, { title: 'π (steady state)', dataIndex: 'pi', render: (v) => fmtSci(v, 4), width: 130 }]} />}
          </Col>
        </Row>) },
    ]} />
  )
}
