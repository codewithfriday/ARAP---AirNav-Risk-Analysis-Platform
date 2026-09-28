import { Alert, App, Button, Card, Col, Input, Row, Select, Space, Table, Tag } from 'antd'
import { CalculatorOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import EditableTable, { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

const parse = (s: string) => String(s ?? '').split(/[\s,;]+/).filter(Boolean).map(Number).filter((x) => !Number.isNaN(x))
const f = (v: any, d = 2) => (v === undefined || v === null ? '—' : Number(v).toFixed(d))

/** Real-time / fast-time simulation plan, measures and statistical comparison (baseline vs solution). */
export default function SimEditor({ model, setModel, results, setResults, readOnly, promote }: EditorProps) {
  const { message } = App.useApp()
  const ex = model.exercise ?? {}
  const measures: any[] = model.measures ?? []
  const setEx = (k: string, v: any) => setModel({ ...model, exercise: { ...ex, [k]: v } })
  const setM = (m: any[]) => setModel({ ...model, measures: m })
  const run = async () => { try { setResults({ measures: await api.post('/calc/sim', measures) }) } catch (e: any) { message.error(e.message) } }
  const res: any[] = results?.measures ?? []
  const failed = res.filter((r) => r.criterion_met === false)

  const rows = measures.map((m) => ({ ...m, ctype: m.criterion?.type, cvalue: m.criterion?.value, base_txt: m.baseline_text ?? (m.baseline ?? []).join(', '), sol_txt: m.solution_text ?? (m.solution ?? []).join(', ') }))
  const fromRows = (rs: any[]) => setM(rs.map(({ ctype, cvalue, base_txt, sol_txt, ...m }) => ({ ...m, criterion: { type: ctype ?? 'threshold', value: cvalue === '' || cvalue === undefined ? 0 : Number(cvalue) },
    baseline: parse(base_txt), solution: parse(sol_txt), baseline_text: base_txt, solution_text: sol_txt })))

  const chart = res.length > 0 && {
    tooltip: { trigger: 'axis' }, legend: { top: 0 }, grid: { left: 50, right: 20, top: 30, bottom: 60 },
    xAxis: { type: 'category', data: res.map((r) => r.id), axisLabel: { interval: 0 } },
    yAxis: { type: 'value', name: '% of baseline mean' },
    series: [
      { name: 'Baseline', type: 'bar', data: res.map(() => 100), itemStyle: { color: '#9CA3AF' } },
      { name: 'Solution', type: 'bar', data: res.map((r) => (r.baseline?.mean ? +(100 * r.solution.mean / r.baseline.mean).toFixed(1) : null)), itemStyle: { color: '#2A7F8E' } },
      { name: 'Solution 95% CI', type: 'custom', renderItem: (_p: any, api2: any) => {
        const r = res[api2.value(0)]; if (!r?.solution?.ci95 || !r.baseline?.mean) return null
        const lo = api2.coord([api2.value(0), 100 * r.solution.ci95[0] / r.baseline.mean]), hi = api2.coord([api2.value(0), 100 * r.solution.ci95[1] / r.baseline.mean])
        const x = lo[0] + api2.size([1, 0])[0] * 0.18
        return { type: 'group', children: [{ type: 'line', shape: { x1: x, y1: lo[1], x2: x, y2: hi[1] }, style: { stroke: '#1F3A5F', lineWidth: 1.5 } },
          { type: 'line', shape: { x1: x - 5, y1: lo[1], x2: x + 5, y2: lo[1] }, style: { stroke: '#1F3A5F' } }, { type: 'line', shape: { x1: x - 5, y1: hi[1], x2: x + 5, y2: hi[1] }, style: { stroke: '#1F3A5F' } }] }
      }, data: res.map((_, i) => [i]), z: 10 },
    ],
  }

  return (
    <Row gutter={16}>
      <Col xs={24} xl={9}>
        <Card size="small" title="Exercise plan">
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Input prefix="Title" value={ex.title} disabled={readOnly} onChange={(e) => setEx('title', e.target.value)} />
            <Select style={{ width: '100%' }} value={ex.type} disabled={readOnly} onChange={(v) => setEx('type', v)} placeholder="Type"
              options={['Real-time simulation', 'Fast-time simulation', 'Shadow-mode trial', 'Live trial'].map((v) => ({ value: v, label: v }))} />
            {[['objectives', 'Safety objectives / hypotheses'], ['scenarios', 'Scenarios, traffic samples, runs and design'], ['participants', 'Participants (ATCOs, pseudo-pilots)'], ['limitations', 'Limitations and validity (realism, learning effects)']].map(([k, l]) => (
              <div key={k}><div className="small muted">{l}</div><Input.TextArea autoSize={{ minRows: 2 }} value={ex[k]} disabled={readOnly} onChange={(e) => setEx(k, e.target.value)} /></div>))}
          </Space>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card size="small" title="Measures and run data" extra={<span className="small muted">one value per run, comma-separated</span>}>
          <EditableTable readOnly={readOnly} rows={rows} onChange={fromRows} scrollX={1100}
            newRow={() => ({ id: nextId(measures, 'M', 1), label: '', unit: '', better: 'lower', ctype: 'threshold', cvalue: 0, base_txt: '', sol_txt: '' })}
            columns={[{ key: 'id', title: 'ID', width: 55 }, { key: 'label', title: 'Measure', width: 200 }, { key: 'unit', title: 'Unit', width: 60 },
              { key: 'better', title: 'Better', type: 'select', options: ['lower', 'higher'], width: 90 },
              { key: 'ctype', title: 'Criterion', type: 'select', options: [{ value: 'threshold', label: 'threshold' }, { value: 'no_worse', label: 'no worse than baseline (+margin)' }], width: 150 },
              { key: 'cvalue', title: 'Value', type: 'number', width: 80 },
              { key: 'base_txt', title: 'Baseline runs', width: 220 }, { key: 'sol_txt', title: 'Solution runs', width: 220 }]} />
          <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 10 }} onClick={run}>Analyse</Button>
        </Card>
        {res.length > 0 && <Card size="small" title="Results" style={{ marginTop: 12 }}>
          {failed.length > 0 ? <Alert type="error" showIcon style={{ marginBottom: 8 }} title={`Success criteria not met: ${failed.map((r) => r.id).join(', ')}`}
            action={!readOnly && <Button size="small" onClick={() => promote(failed.map((r) => ({ row_id: r.id, title: `Simulation criterion not met: ${r.label}`, causes: `Solution mean ${f(r.solution.mean)} ${r.unit} vs baseline ${f(r.baseline.mean)} ${r.unit}` })))}>Send to hazard log</Button>} />
            : <Alert type="success" showIcon style={{ marginBottom: 8 }} title="All success criteria met." />}
          <Table size="small" rowKey="id" pagination={false} dataSource={res} scroll={{ x: 900 }} columns={[
            { title: 'Measure', render: (_, r: any) => <><b>{r.id}</b> {r.label}</> },
            { title: 'Baseline mean ± sd (n)', width: 160, render: (_, r: any) => `${f(r.baseline.mean)} ± ${f(r.baseline.sd)} (${r.baseline.n})` },
            { title: 'Solution mean ± sd (n)', width: 160, render: (_, r: any) => `${f(r.solution.mean)} ± ${f(r.solution.sd)} (${r.solution.n})` },
            { title: 'Solution 95% CI', width: 130, render: (_, r: any) => (r.solution.ci95 ? `${f(r.solution.ci95[0])} – ${f(r.solution.ci95[1])}` : '—') },
            { title: 'Δ', width: 70, render: (_, r: any) => f(r.difference) },
            { title: 'Welch p', width: 80, render: (_, r: any) => (r.p_value === undefined ? '—' : r.p_value < 0.001 ? '<0.001' : r.p_value.toFixed(3)) },
            { title: 'Criterion', width: 90, render: (_, r: any) => (r.criterion_met === undefined ? '—' : r.criterion_met ? <Tag color="green">met</Tag> : <Tag color="red">not met</Tag>) },
          ]} />
          {chart && <ReactECharts option={chart} style={{ height: 280, marginTop: 10 }} notMerge />}
          <div className="small muted">A statistically significant difference is not the same as an operationally significant one; judge both against the objectives and consider sample size and learning effects.</div>
        </Card>}
      </Col>
    </Row>
  )
}
