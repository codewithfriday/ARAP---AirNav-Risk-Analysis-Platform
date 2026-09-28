import { useState } from 'react'
import { Alert, App, Button, Card, Checkbox, Col, Input, InputNumber, Row, Select, Space, Table, Tabs, Tag } from 'antd'
import { CalculatorOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import { fmtSci } from '../risk'
import { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

const g = (v: any) => (v === undefined || v === null ? '—' : Math.abs(v) < 0.01 && v !== 0 ? fmtSci(v, 2) : Number(v).toPrecision(3))

function Classical({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const experts: string[] = model.experts ?? []
  const items: any[] = model.items ?? []
  const [newExp, setNewExp] = useState('')
  const set = (patch: any) => setModel({ ...model, ...patch })
  const setItem = (i: number, patch: any) => set({ items: items.map((x, j) => (j === i ? { ...x, ...patch } : x)) })
  const setAns = (i: number, e: string, q: number, v: number | null) => {
    const a = [...(items[i].answers?.[e] ?? [null, null, null])]; a[q] = v
    setItem(i, { answers: { ...items[i].answers, [e]: a } })
  }
  const addExpert = () => { const n = newExp.trim(); if (!n || experts.includes(n)) return; set({ experts: [...experts, n] }); setNewExp('') }
  const delExpert = (e: string) => set({ experts: experts.filter((x) => x !== e), items: items.map((it) => { const a = { ...it.answers }; delete a[e]; return { ...it, answers: a } }) })
  const run = async () => {
    try { setResults({ ...results, classical: await api.post('/calc/sej', { experts, items, alpha: model.alpha ?? 0 }) }) } catch (e: any) { message.error(e.message) }
  }
  const r = results?.classical
  const bad = items.filter((it) => experts.some((e) => { const a = it.answers?.[e]; return !a || a.some((x: any) => x === null || x === undefined) || !(a[0] < a[1] && a[1] < a[2]) }))

  const cols: any[] = [
    { title: 'ID', width: 60, fixed: 'left', render: (_: any, it: any, i: number) => readOnly ? it.id : <Input size="small" value={it.id} onChange={(e) => setItem(i, { id: e.target.value })} /> },
    { title: 'Question', width: 240, fixed: 'left', render: (_: any, it: any, i: number) => readOnly ? it.label : <Input.TextArea size="small" autoSize value={it.label} onChange={(e) => setItem(i, { label: e.target.value })} /> },
    { title: 'Seed?', width: 60, render: (_: any, it: any, i: number) => <Checkbox checked={!!it.seed} disabled={readOnly} onChange={(e) => setItem(i, { seed: e.target.checked })} /> },
    { title: 'Realisation', width: 100, render: (_: any, it: any, i: number) => it.seed ? <InputNumber size="small" value={it.realisation} disabled={readOnly} onChange={(v) => setItem(i, { realisation: v })} style={{ width: '100%' }} /> : <span className="muted">target</span> },
    { title: 'Scale', width: 80, render: (_: any, it: any, i: number) => <Select size="small" value={it.scale ?? 'uni'} disabled={readOnly} onChange={(v) => setItem(i, { scale: v })} options={[{ value: 'uni', label: 'linear' }, { value: 'log', label: 'log' }]} /> },
    ...experts.map((e) => ({ title: <span>{e}{!readOnly && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => delExpert(e)} />}</span>, children: [0, 1, 2].map((q) => ({
      title: ['5%', '50%', '95%'][q], width: 78,
      render: (_: any, it: any, i: number) => <InputNumber size="small" controls={false} style={{ width: '100%' }} value={it.answers?.[e]?.[q]} disabled={readOnly} onChange={(v) => setAns(i, e, q, v)} />,
    })) })),
    ...(!readOnly ? [{ title: '', width: 40, render: (_: any, _it: any, i: number) => <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => set({ items: items.filter((_x, j) => j !== i) })} /> }] : []),
  ]
  return (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 10 }} title="Cooke's classical model: each expert gives 5/50/95% quantiles for seed questions (true value known to the facilitator) and target questions. Weights = calibration × information; experts below the significance level α get zero weight." />
      <Space style={{ marginBottom: 8 }} wrap>
        {!readOnly && <><Input size="small" placeholder="Expert name" value={newExp} onChange={(e) => setNewExp(e.target.value)} onPressEnter={addExpert} style={{ width: 160 }} />
          <Button size="small" icon={<PlusOutlined />} onClick={addExpert}>Expert</Button>
          <Button size="small" icon={<PlusOutlined />} onClick={() => set({ items: [...items, { id: nextId(items, 'Q', 1), label: '', seed: false, scale: 'uni', answers: {} }] })}>Question</Button></>}
        <InputNumber size="small" prefix="α" min={0} max={0.5} step={0.01} value={model.alpha ?? 0} disabled={readOnly} onChange={(v) => set({ alpha: v ?? 0 })} style={{ width: 110 }} />
        <Tag>{items.filter((x) => x.seed).length} seed · {items.filter((x) => !x.seed).length} target</Tag>
        {bad.length > 0 && <Tag color="orange">Incomplete or non-increasing quantiles: {bad.map((x) => x.id).join(', ')}</Tag>}
        <Button type="primary" icon={<CalculatorOutlined />} onClick={run}>Calculate weights</Button>
      </Space>
      <Table size="small" rowKey={(_, i) => String(i)} pagination={false} dataSource={items} columns={cols} bordered scroll={{ x: 640 + experts.length * 234 }} />
      {r && <Row gutter={12} style={{ marginTop: 12 }}>
        <Col xs={24} xl={10}><Card size="small" title="Expert scores">
          <Table size="small" rowKey="e" pagination={false} dataSource={Object.entries<any>(r.experts).map(([e, v]) => ({ e, ...v }))} columns={[
            { title: 'Expert', dataIndex: 'e' }, { title: 'Calibration', dataIndex: 'calibration', render: g }, { title: 'Information', dataIndex: 'information', render: (v) => v.toFixed(3) },
            { title: 'Bins', dataIndex: 'bins', render: (v) => v.join('/') }, { title: 'Weight', dataIndex: 'weight', render: (v) => <b>{v.toFixed(3)}</b> }]} />
          <ReactECharts style={{ height: 160 }} notMerge option={{ grid: { left: 80, right: 20, top: 10, bottom: 20 }, xAxis: { type: 'value', max: 1 }, yAxis: { type: 'category', data: Object.keys(r.experts) },
            series: [{ type: 'bar', data: Object.values<any>(r.experts).map((v) => +v.weight.toFixed(3)), itemStyle: { color: '#2A7F8E' }, label: { show: true, position: 'right' } }] }} />
        </Card></Col>
        <Col xs={24} xl={14}><Card size="small" title="Decision maker (combined distribution)">
          <Table size="small" rowKey="id" pagination={false} dataSource={r.decision_maker} columns={[
            { title: 'Item', render: (_, d: any) => <><b>{d.id}</b> {d.seed ? <Tag>seed</Tag> : <Tag color="blue">target</Tag>}<div className="small muted">{d.label}</div></> },
            { title: 'Performance-weighted 5 / 50 / 95%', render: (_, d: any) => <b>{d.performance.map(g).join(' / ')}</b> },
            { title: 'Equal-weight 5 / 50 / 95%', render: (_, d: any) => d.equal.map(g).join(' / ') }]} />
        </Card></Col>
      </Row>}
    </div>
  )
}

function Delphi({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const d = model.delphi ?? { question: '', rounds: [] }
  const rounds: any[] = d.rounds ?? []
  const panel = Array.from(new Set(rounds.flatMap((r) => Object.keys(r.estimates ?? {}))))
  const [np, setNp] = useState('')
  const setD = (patch: any) => setModel({ ...model, delphi: { ...d, ...patch } })
  const setEst = (i: number, p: string, v: number | null) => setD({ rounds: rounds.map((r, j) => (j === i ? { ...r, estimates: { ...r.estimates, [p]: v } } : r)) })
  const run = async () => { try { setResults({ ...results, delphi: await api.post('/calc/delphi', rounds) }) } catch (e: any) { message.error(e.message) } }
  const out: any[] = results?.delphi ?? []
  return (
    <Row gutter={12}>
      <Col xs={24} xl={13}>
        <Input.TextArea autoSize value={d.question} disabled={readOnly} onChange={(e) => setD({ question: e.target.value })} placeholder="Question put to the panel" style={{ marginBottom: 8 }} />
        <Space style={{ marginBottom: 8 }} wrap>
          {!readOnly && <>
            <Input size="small" placeholder="Panellist" value={np} onChange={(e) => setNp(e.target.value)} style={{ width: 120 }} />
            <Button size="small" icon={<PlusOutlined />} onClick={() => { if (!np.trim()) return; setD({ rounds: (rounds.length ? rounds : [{ round: 1, estimates: {} }]).map((r) => ({ ...r, estimates: { ...r.estimates, [np.trim()]: null } })) }); setNp('') }}>Panellist</Button>
            <Button size="small" icon={<PlusOutlined />} onClick={() => setD({ rounds: [...rounds, { round: rounds.length + 1, estimates: Object.fromEntries(panel.map((p) => [p, rounds.at(-1)?.estimates?.[p] ?? null])) }] })}>Round</Button></>}
          <Button type="primary" icon={<CalculatorOutlined />} onClick={run}>Summarise rounds</Button>
        </Space>
        <Table size="small" bordered rowKey="round" pagination={false} dataSource={rounds} columns={[
          { title: 'Round', dataIndex: 'round', width: 60 },
          ...panel.map((p) => ({ title: p, render: (_: any, _r: any, i: number) => <InputNumber size="small" controls={false} style={{ width: '100%' }} value={rounds[i].estimates?.[p]} disabled={readOnly} onChange={(v) => setEst(i, p, v)} /> })),
        ]} />
        <div className="small muted" style={{ marginTop: 6 }}>Between rounds, feed back the anonymous median, interquartile range and reasons given by outliers. Stop when the IQR stops shrinking or after three rounds.</div>
      </Col>
      <Col xs={24} xl={11}>
        {out.length > 0 && <>
          <Table size="small" rowKey="round" pagination={false} dataSource={out} columns={[
            { title: 'Round', dataIndex: 'round', width: 60 }, { title: 'n', dataIndex: 'n', width: 40 }, { title: 'Median', dataIndex: 'median', render: g },
            { title: 'Q1 – Q3', render: (_, o: any) => `${g(o.q1)} – ${g(o.q3)}` }, { title: 'IQR/median', dataIndex: 'relative_iqr', render: (v) => (v === null ? '—' : v.toFixed(2)) },
            { title: '', dataIndex: 'converging', width: 100, render: (v) => (v === undefined ? '' : v ? <Tag color="green">converging</Tag> : <Tag color="orange">not converging</Tag>) }]} />
          <ReactECharts style={{ height: 260, marginTop: 10 }} notMerge option={{
            tooltip: { trigger: 'axis' }, grid: { left: 60, right: 20, top: 20, bottom: 30 }, xAxis: { type: 'category', data: out.map((o) => `R${o.round}`) }, yAxis: { type: 'value', scale: true },
            series: [{ name: 'Q1', type: 'line', stack: 'iqr', data: out.map((o) => o.q1), lineStyle: { opacity: 0 }, symbol: 'none' },
              { name: 'IQR', type: 'line', stack: 'iqr', data: out.map((o) => o.q3 - o.q1), lineStyle: { opacity: 0 }, areaStyle: { color: '#7FC3CF', opacity: 0.5 }, symbol: 'none' },
              { name: 'Median', type: 'line', data: out.map((o) => o.median), lineStyle: { color: '#1F3A5F', width: 2 }, itemStyle: { color: '#1F3A5F' } },
              ...panel.map((p) => ({ name: p, type: 'line', data: rounds.map((r) => r.estimates?.[p]), lineStyle: { width: 1, type: 'dashed', color: '#9CA3AF' }, itemStyle: { color: '#9CA3AF' }, symbolSize: 4 }))] }} />
        </>}
      </Col>
    </Row>
  )
}

export default function SejEditor(props: EditorProps) {
  return <Tabs items={[{ key: 'c', label: 'Classical model (Cooke)', children: <Classical {...props} /> }, { key: 'd', label: 'Delphi', children: <Delphi {...props} /> }]} />
}
