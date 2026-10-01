import { useState } from 'react'
import { Alert, App, Button, Card, Col, Collapse, Input, InputNumber, Row, Space, Table, Tabs, Tag, TimePicker } from 'antd'
import { CalculatorOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import type { EditorProps } from './types'
import SamnPerelli from './SamnPerelli'

const COLORS = ['#B23A3A', '#2A7F8E', '#7C3AED', '#D98E04']
const toDayTime = (h: number) => ({ day: Math.floor(h / 24) + 1, time: dayjs().startOf('day').add(((h % 24) + 24) % 24 * 60, 'minute') })
const fromDayTime = (day: number, t: dayjs.Dayjs) => (day - 1) * 24 + t.hour() + t.minute() / 60
const clock = (h: number) => { const x = ((h % 24) + 24) % 24; return `${String(Math.floor(x)).padStart(2, '0')}:${String(Math.round((x % 1) * 60)).padStart(2, '0')}` }

function Periods({ list, onChange, readOnly, label }: { list: number[][]; onChange: (l: number[][]) => void; readOnly: boolean; label: string }) {
  const upd = (i: number, which: 0 | 1, day: number, t: dayjs.Dayjs) => onChange(list.map((p, j) => (j === i ? (which === 0 ? [fromDayTime(day, t), p[1]] : [p[0], fromDayTime(day, t)]) : p)))
  return (
    <Table rowKey="_k" size="small" pagination={false} dataSource={list.map((p, i) => ({ p, _k: i }))} title={() => <b>{label}</b>}
      footer={() => !readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => onChange([...list, list.length ? [list[list.length - 1][1] + 8, list[list.length - 1][1] + 16] : [23, 31]])}>Add</Button>}
      columns={[0, 1].map((w) => ({ title: w === 0 ? 'Start (day, time)' : 'End (day, time)', render: (_: any, r: any) => {
        const p: number[] = r.p; const i: number = r._k
        const { day, time } = toDayTime(p[w])
        return <Space.Compact><InputNumber size="small" min={0} max={30} value={day} disabled={readOnly} style={{ width: 58 }} onChange={(d) => upd(i, w as 0 | 1, d ?? 1, time)} />
          <TimePicker size="small" format="HH:mm" minuteStep={5} value={time} allowClear={false} disabled={readOnly} onChange={(t) => t && upd(i, w as 0 | 1, day, t)} /></Space.Compact>
      } })).concat([{ title: 'Hours', render: (_: any, r: any) => (r.p[1] - r.p[0]).toFixed(1) } as any,
        { title: '', render: (_: any, r: any) => !readOnly && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange(list.filter((_x, j) => j !== r._k))} /> } as any])} />
  )
}

export default function FatigueEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const m = { start: 0, end: 72, step_minutes: 5, kss_threshold: 7, params: {}, variants: [{ name: 'Roster A', sleeps: [[-1, 7]], duties: [[7, 14]] }], ...model }
  const [active, setActive] = useState('0')
  const [view, setView] = useState('model')
  const set = (k: string, v: any) => setModel({ ...m, [k]: v })
  const updVar = (i: number, k: string, v: any) => set('variants', m.variants.map((x: any, j: number) => (j === i ? { ...x, [k]: v } : x)))

  const run = async () => {
    try {
      const out = []
      for (const v of m.variants) {
        const r = await api.post('/calc/fatigue', { sleeps: v.sleeps, duties: v.duties, start: m.start, end: m.end, step_minutes: m.step_minutes, params: m.params, kss_threshold: m.kss_threshold })
        out.push({ name: v.name, duties: r.duties, series: r.series.filter((_: any, i: number) => i % 2 === 0).map((p: any) => [p.t, p.alertness === null ? null : +p.alertness.toFixed(3)]),
          notice: r.notice, engine_version: r.engine_version })
      }
      setResults({ ...(results ?? {}), variants: out })
    } catch (e: any) {
      message.error(e.message)
    }
  }

  const res = results?.variants
  const dutyAreas = m.variants[0]?.duties.map((d: number[]) => [{ xAxis: d[0], itemStyle: { color: 'rgba(31,58,95,0.07)' } }, { xAxis: d[1] }])
  const chart = res && {
    grid: { left: 55, right: 20, top: 40, bottom: 50 },
    legend: { top: 0 },
    tooltip: { trigger: 'axis', formatter: (ps: any[]) => `Day ${Math.floor(ps[0].value[0] / 24) + 1} ${clock(ps[0].value[0])}<br/>` + ps.map((p) => `${p.marker}${p.seriesName}: ${p.value[1] ?? 'asleep'} (KSS ${p.value[1] === null ? '–' : (10.6 - 0.6 * p.value[1]).toFixed(1)})`).join('<br/>') },
    xAxis: { type: 'value', min: m.start, max: m.end, interval: 6, axisLabel: { formatter: (v: number) => clock(v) }, name: 'clock time (shaded = duties of first roster; gaps = sleep)', nameLocation: 'middle', nameGap: 30 },
    yAxis: { type: 'value', name: 'alertness (S+C+W)', min: 3, max: 16 },
    series: res.map((v: any, i: number) => ({ name: v.name, type: 'line', showSymbol: false, connectNulls: false, data: v.series, lineStyle: { width: 2, color: COLORS[i % 4] }, itemStyle: { color: COLORS[i % 4] },
      ...(i === 0 ? { markArea: { silent: true, data: dutyAreas }, markLine: { symbol: 'none', silent: true, data: [{ yAxis: (10.6 - m.kss_threshold) / 0.6, lineStyle: { color: '#D98E04', type: 'dashed' }, label: { formatter: `KSS ${m.kss_threshold}`, position: 'insideEndTop' } }] } } : {}) })),
  }
  const rows = res ? res.flatMap((v: any) => v.duties.filter((d: any) => d.min_alertness !== undefined).map((d: any) => ({ key: `${v.name}${d.duty}`, variant: v.name, ...d }))) : []

  const sp = <SamnPerelli ratings={m.sp_ratings ?? []} onChange={(r) => set('sp_ratings', r)} readOnly={readOnly}
    result={results?.samn_perelli} setResult={(r) => setResults({ ...(results ?? {}), samn_perelli: r })} />
  const spRes = results?.samn_perelli
  const spBad = (spRes?.checks ?? []).filter((c: any) => c.severity !== 'info').length

  const modelView = (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Three-process model of alertness (Åkerstedt–Folkard; parameters from Ingre et al. 2014). Predictions are group averages for healthy adults, not a measure of an individual’s fatigue." />
      <Row gutter={16}>
        <Col xs={24} xl={10}>
          <Tabs activeKey={active} onChange={setActive} type={readOnly ? 'card' : 'editable-card'}
            onEdit={(k, a) => { if (a === 'add') { set('variants', [...m.variants, { name: `Roster ${String.fromCharCode(65 + m.variants.length)}`, sleeps: structuredClone(m.variants[0]?.sleeps ?? []), duties: structuredClone(m.variants[0]?.duties ?? []) }]); setActive(String(m.variants.length)) } else { set('variants', m.variants.filter((_: any, j: number) => String(j) !== k)); setActive('0') } }}
            items={m.variants.map((v: any, i: number) => ({ key: String(i), label: v.name, closable: m.variants.length > 1, children: (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Input prefix="Name" value={v.name} disabled={readOnly} onChange={(e) => updVar(i, 'name', e.target.value)} />
                <Periods label="Duties" list={v.duties} readOnly={readOnly} onChange={(l) => updVar(i, 'duties', l)} />
                <Periods label="Sleep periods (planned or measured)" list={v.sleeps} readOnly={readOnly} onChange={(l) => updVar(i, 'sleeps', l)} />
              </Space>) }))} />
          <Collapse size="small" style={{ marginTop: 12 }} items={[{ key: 'p', label: 'Simulation settings and parameters', children: (
            <Space wrap>
              <InputNumber prefix="Days" min={1} max={28} value={Math.round((m.end - m.start) / 24)} disabled={readOnly} onChange={(d) => set('end', m.start + (d ?? 3) * 24)} />
              <InputNumber prefix="Step (min)" min={1} max={60} value={m.step_minutes} disabled={readOnly} onChange={(v) => set('step_minutes', v ?? 5)} />
              <InputNumber prefix="KSS threshold" min={1} max={9} value={m.kss_threshold} disabled={readOnly} onChange={(v) => set('kss_threshold', v ?? 7)} />
              {['s0', 'la', 'ha', 'd', 'g', 'ca', 'p', 'wc', 'wd', 'kss_a', 'kss_b'].map((k) => (
                <InputNumber key={k} prefix={k} style={{ width: 150 }} value={(m.params as any)[k]} placeholder="default" disabled={readOnly} onChange={(v) => set('params', { ...m.params, [k]: v ?? undefined })} />))}
            </Space>) }]} />
          <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 12 }} onClick={run}>Run model</Button>
        </Col>
        <Col xs={24} xl={14}>
          <Card size="small" title="Predicted alertness">
            {res ? <ReactECharts option={chart} style={{ height: 380 }} notMerge /> : <span className="muted">Run the model to see the curves.</span>}
          </Card>
          {res && <Table size="small" style={{ marginTop: 12 }} pagination={false} dataSource={rows} columns={[
            { title: 'Roster', dataIndex: 'variant' },
            { title: 'Duty', dataIndex: 'duty', render: (d: number[]) => `day ${Math.floor(d[0] / 24) + 1} ${clock(d[0])}–${clock(d[1])}` },
            { title: 'Min alertness', dataIndex: 'min_alertness', render: (v, r: any) => `${v.toFixed(2)} at ${r.min_clock}` },
            { title: 'Max KSS', dataIndex: 'max_kss', render: (v) => <b style={{ color: v >= m.kss_threshold ? '#B23A3A' : undefined }}>{v.toFixed(2)}</b> },
            { title: `Time at KSS ≥ ${m.kss_threshold}`, dataIndex: 'share_at_or_above_threshold', render: (v, r: any) => `${(v * 100).toFixed(0)}% (${r.hours_at_or_above_threshold.toFixed(1)} h)` },
          ]} />}
        </Col>
      </Row>
    </div>
  )
  return <Tabs activeKey={view} onChange={setView} items={[
    { key: 'model', label: 'Three-process model (roster)', children: modelView },
    { key: 'sp', label: <span>Samn-Perelli fatigue check {(m.sp_ratings ?? []).length > 0 && <Tag>{(m.sp_ratings ?? []).length}</Tag>}{spBad > 0 && <Tag color="orange">{spBad} to act on</Tag>}</span>, children: sp },
  ]} />
}
