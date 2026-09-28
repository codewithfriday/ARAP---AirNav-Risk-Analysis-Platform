import { App, Button, Card, Col, Input, InputNumber, Row, Select, Space, Switch, Table, Tag } from 'antd'
import { CalculatorOutlined } from '@ant-design/icons'
import { api } from '../api'
import { fmtSci } from '../risk'
import EditableTable, { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

const SEV_COLORS: Record<string, string> = { A: '#B23A3A', B: '#D98E04', C: '#E3B23C', D: '#3C8D5A', E: '#6B7280' }

/** Classic event-tree drawing: barriers as columns, branches up = success, down = failure. */
function TreeSvg({ model, res }: { model: any; res: any }) {
  const ev: any[] = model.events ?? []
  const seqs: any[] = res?.sequences ?? []
  const colW = 150, rowH = 34, left = 190, top = 50
  const W = left + colW * ev.length + 330
  const H = top + rowH * Math.max(seqs.length, 1) + 20
  const rowOf: Record<string, number> = {}
  seqs.forEach((s, i) => (rowOf[s.sequence] = i))
  const yOfPrefix = (prefix: string[]) => {
    const rows = seqs.filter((s) => s.path.slice(0, prefix.length).join('-') === prefix.join('-')).map((s) => rowOf[s.sequence])
    return rows.length ? top + rowH * (Math.min(...rows) + Math.max(...rows)) / 2 + rowH / 2 : top
  }
  const lines: React.ReactNode[] = []
  const walk = (prefix: string[], depth: number) => {
    const y0 = yOfPrefix(prefix)
    const x0 = left + depth * colW
    if (depth === ev.length || (prefix.length && prefix[prefix.length - 1] === 'S' && model.terminate_on_success !== false)) {
      lines.push(<line key={`end${prefix.join('')}`} x1={x0} y1={y0} x2={left + ev.length * colW} y2={y0} stroke="#9CA3AF" strokeDasharray="3 3" />)
      return
    }
    for (const b of ['S', 'F']) {
      const p = [...prefix, b]
      if (!seqs.some((s) => s.path.slice(0, p.length).join('-') === p.join('-'))) continue
      const y1 = yOfPrefix(p)
      lines.push(<path key={p.join('')} d={`M${x0},${y0} L${x0 + 18},${y0} L${x0 + 18},${y1} L${x0 + colW},${y1}`} fill="none" stroke={b === 'S' ? '#3C8D5A' : '#B23A3A'} strokeWidth={1.6} />)
      walk(p, depth + 1)
    }
  }
  if (seqs.length) walk([], 0)
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ background: '#fbfcfd', border: '1px solid #e5e7eb', borderRadius: 8 }}>
      <text x={10} y={24} fontSize={12} fontWeight={700} fill="#1F3A5F">Initiating event</text>
      <text x={10} y={40} fontSize={11} fill="#374151">{model.initiating?.label}</text>
      <text x={10} y={yOfPrefix([]) - 6} fontSize={11} fill="#6B7280">f = {fmtSci(model.initiating?.frequency)} {model.initiating?.unit}</text>
      <line x1={10} y1={yOfPrefix([])} x2={left} y2={yOfPrefix([])} stroke="#1F3A5F" strokeWidth={1.6} />
      {ev.map((e, i) => (
        <g key={e.id}>
          <text x={left + i * colW + 22} y={22} fontSize={11} fontWeight={700} fill="#1F3A5F">{e.id}</text>
          <text x={left + i * colW + 22} y={36} fontSize={10} fill="#374151">{String(e.label).slice(0, 24)}</text>
        </g>))}
      {lines}
      {seqs.map((s, i) => (
        <g key={s.sequence}>
          <rect x={left + ev.length * colW + 8} y={top + i * rowH + 7} width={22} height={18} rx={3} fill={SEV_COLORS[s.severity] ?? '#9CA3AF'} />
          <text x={left + ev.length * colW + 19} y={top + i * rowH + 20} fontSize={10} fill="#fff" textAnchor="middle" fontWeight={700}>{s.severity ?? '–'}</text>
          <text x={left + ev.length * colW + 38} y={top + i * rowH + 16} fontSize={10.5} fill="#111827">{String(s.label).slice(0, 38)}</text>
          <text x={left + ev.length * colW + 38} y={top + i * rowH + 29} fontSize={10} fill="#6B7280">{s.sequence} · {fmtSci(s.frequency)} {res.unit}</text>
        </g>))}
      <text x={left} y={H - 4} fontSize={10} fill="#6B7280">Up (green) = barrier succeeds · down (red) = barrier fails</text>
    </svg>
  )
}

export default function EtaEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const m = { initiating: { label: 'Initiating event', frequency: 0.1, unit: 'per year' }, events: [], overrides: {}, outcomes: {}, terminate_on_success: true, ...model }
  const set = (k: string, v: any) => setModel({ ...m, [k]: v })
  const run = async () => {
    try { setResults(await api.post('/calc/eta', m)) } catch (e: any) { message.error(e.message) }
  }
  const seqs = results?.sequences ?? []
  const ovRows = Object.entries(m.overrides ?? {}).flatMap(([path, o]: any) => Object.entries(o).map(([ev, v]: any) => ({ path, event: ev, p_success: v.p_success })))
  const setOv = (rows: any[]) => set('overrides', rows.reduce((acc: any, r) => { if (r.path !== undefined && r.event) (acc[r.path] ??= {})[r.event] = { p_success: r.p_success ?? 0 }; return acc }, {}))

  return (
    <Row gutter={16}>
      <Col xs={24} xl={9}>
        <Card size="small" title="Initiating event">
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Input value={m.initiating.label} disabled={readOnly} onChange={(e) => set('initiating', { ...m.initiating, label: e.target.value })} />
            <Space><InputNumber prefix="Frequency" style={{ width: 200 }} value={m.initiating.frequency} disabled={readOnly} onChange={(v) => set('initiating', { ...m.initiating, frequency: v ?? 0 })} />
              <Input style={{ width: 140 }} value={m.initiating.unit} disabled={readOnly} onChange={(e) => set('initiating', { ...m.initiating, unit: e.target.value })} /></Space>
            <Space><Switch size="small" checked={m.terminate_on_success} disabled={readOnly} onChange={(v) => set('terminate_on_success', v)} /><span className="small">A successful barrier ends the sequence (barrier event tree)</span></Space>
          </Space>
        </Card>
        <Card size="small" title="Barriers / functional events (in order)" style={{ marginTop: 12 }}>
          <EditableTable readOnly={readOnly} rows={m.events} onChange={(r) => set('events', r)} newRow={() => ({ id: nextId(m.events, 'B', 1), label: 'New barrier', p_success: 0.9 })}
            columns={[{ key: 'id', title: 'ID', width: 60 }, { key: 'label', title: 'Barrier' }, { key: 'p_success', title: 'P(success)', type: 'number', width: 100, min: 0, max: 1, step: 0.01 }]} />
        </Card>
        <Card size="small" title="Conditional probabilities (dependence)" style={{ marginTop: 12 }}
          extra={<span className="small muted">path prefix e.g. “F” or “F-F”</span>}>
          <EditableTable readOnly={readOnly} rows={ovRows} onChange={setOv} newRow={() => ({ path: 'F', event: m.events[1]?.id, p_success: 0.8 })}
            columns={[{ key: 'path', title: 'After path', width: 90 }, { key: 'event', title: 'Barrier', type: 'select', options: m.events.map((e: any) => e.id), width: 90 },
              { key: 'p_success', title: 'P(success)', type: 'number', min: 0, max: 1, step: 0.01, width: 100 }]} />
        </Card>
        <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 12 }} onClick={run}>Calculate</Button>
      </Col>
      <Col xs={24} xl={15}>
        {results?.sequences ? <TreeSvg model={m} res={results} /> : <Card size="small"><span className="muted">Press Calculate to draw the tree.</span></Card>}
        {seqs.length > 0 && <Card size="small" title="Outcomes" style={{ marginTop: 12 }}>
          <Table rowKey="sequence" size="small" pagination={false} dataSource={seqs} columns={[
            { title: 'Sequence', dataIndex: 'sequence', width: 90 },
            { title: 'Outcome', dataIndex: 'label', render: (v, r: any) => readOnly ? v : <Input size="small" value={m.outcomes?.[r.sequence]?.label ?? v}
              onChange={(e) => set('outcomes', { ...m.outcomes, [r.sequence]: { ...m.outcomes?.[r.sequence], label: e.target.value } })} /> },
            { title: 'Severity', dataIndex: 'severity', width: 90, render: (v, r: any) => readOnly ? <Tag color={SEV_COLORS[v]}>{v}</Tag> : <Select size="small" style={{ width: 70 }} value={m.outcomes?.[r.sequence]?.severity ?? v} allowClear
              options={['A', 'B', 'C', 'D', 'E'].map((x) => ({ value: x, label: x }))} onChange={(x) => set('outcomes', { ...m.outcomes, [r.sequence]: { ...m.outcomes?.[r.sequence], severity: x } })} /> },
            { title: 'Probability', dataIndex: 'probability', width: 100, render: (v) => fmtSci(v, 3) },
            { title: `Frequency (${results.unit})`, dataIndex: 'frequency', width: 140, render: (v) => <b>{fmtSci(v, 3)}</b> },
          ]} />
          <div className="small muted" style={{ marginTop: 6 }}>Σ probability = {results.probability_check.toFixed(6)} · by severity: {Object.entries(results.frequency_by_severity).map(([k, v]: any) => `${k} ${fmtSci(v)}`).join(' · ')} · edit outcomes then recalculate</div>
        </Card>}
      </Col>
    </Row>
  )
}
