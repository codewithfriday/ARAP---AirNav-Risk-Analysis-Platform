import { Alert, Button, Card, Checkbox, Col, Descriptions, Input, InputNumber, Row, Space, Table, Tag, Tooltip, App } from 'antd'
import { PlusOutlined, DeleteOutlined, CalculatorOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import { fmtSci } from '../risk'
import type { EditorProps } from './types'

const CRIT = ['independent', 'effective', 'dependable', 'auditable'] as const

export default function LopaEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const m = { scenario: '', initiating: { label: 'Initiating event', frequency: 0.1, source: '' }, unit: 'per year', target: 1e-5, modifiers: [], safeguards: [], ...model }
  const set = (k: string, v: any) => setModel({ ...m, [k]: v })
  const upd = (list: 'modifiers' | 'safeguards', i: number, k: string, v: any) => set(list, m[list].map((x: any, j: number) => (j === i ? { ...x, [k]: v } : x)))

  const run = async () => {
    try {
      const r = await api.post('/calc/lopa', { initiating_frequency: m.initiating.frequency, conditional_modifiers: m.modifiers, safeguards: m.safeguards,
        target_frequency: m.target, unit: m.unit })
      setResults(r)
    } catch (e: any) {
      message.error(e.message)
    }
  }

  const chart = results?.steps && {
    grid: { left: 70, right: 30, top: 20, bottom: 70 },
    xAxis: { type: 'category', data: results.steps.map((s: any) => s.label), axisLabel: { interval: 0, rotate: 20, fontSize: 10, width: 110, overflow: 'break' } },
    yAxis: { type: 'log', name: `frequency (${results.unit})`, nameTextStyle: { fontSize: 10 }, axisLabel: { formatter: (v: number) => v.toExponential(0) } },
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => v.toExponential(2) },
    series: [{ type: 'bar', barWidth: 34, data: results.steps.map((s: any, i: number) => ({ value: s.frequency,
      itemStyle: { color: i === 0 ? '#B23A3A' : s.frequency <= results.target_frequency ? '#3C8D5A' : '#2A7F8E' } })),
      label: { show: true, position: 'top', formatter: (p: any) => p.value.toExponential(1), fontSize: 10 },
      markLine: { symbol: 'none', data: [{ yAxis: results.target_frequency, label: { formatter: `target ${fmtSci(results.target_frequency, 0)}` }, lineStyle: { color: '#B23A3A', type: 'dashed' } }] } }],
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={14}>
        <Card size="small" title="Scenario">
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Input prefix="Scenario" value={m.scenario} disabled={readOnly} onChange={(e) => set('scenario', e.target.value)} />
            <Space wrap>
              <Input prefix="Initiating event" style={{ width: 360 }} value={m.initiating.label} disabled={readOnly} onChange={(e) => set('initiating', { ...m.initiating, label: e.target.value })} />
              <InputNumber prefix="f(IE)" style={{ width: 170 }} value={m.initiating.frequency} disabled={readOnly} min={0} step={0.1} onChange={(v) => set('initiating', { ...m.initiating, frequency: v ?? 0 })} />
              <Input prefix="Unit" style={{ width: 170 }} value={m.unit} disabled={readOnly} onChange={(e) => set('unit', e.target.value)} />
            </Space>
            <Space wrap>
              <Input prefix="Data source" style={{ width: 360 }} value={m.initiating.source} disabled={readOnly} onChange={(e) => set('initiating', { ...m.initiating, source: e.target.value })} />
              <InputNumber prefix="Tolerable target" style={{ width: 240 }} value={m.target} disabled={readOnly} min={0} onChange={(v) => set('target', v ?? 1e-5)} />
            </Space>
          </Space>
        </Card>
        <Card size="small" title="Enabling conditions / conditional modifiers" style={{ marginTop: 12 }}
          extra={!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => set('modifiers', [...m.modifiers, { label: 'Condition', probability: 1 }])}>Add</Button>}>
          <Table rowKey="_k" size="small" pagination={false} dataSource={m.modifiers.map((x: any, i: number) => ({ ...x, _k: i }))} columns={[
            { title: 'Condition', dataIndex: 'label', render: (v, r: any) => <Input size="small" value={v} disabled={readOnly} onChange={(e) => upd('modifiers', r._k, 'label', e.target.value)} /> },
            { title: 'Probability', dataIndex: 'probability', width: 130, render: (v, r: any) => <InputNumber size="small" value={v} min={0} max={1} step={0.01} disabled={readOnly} onChange={(x) => upd('modifiers', r._k, 'probability', x)} /> },
            { title: '', width: 40, render: (_: any, r: any) => !readOnly && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => set('modifiers', m.modifiers.filter((_: any, j: number) => j !== r._k))} /> },
          ]} />
        </Card>
        <Card size="small" title="Safeguards — credited only if all four IPL criteria are met" style={{ marginTop: 12 }}
          extra={!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => set('safeguards', [...m.safeguards, { label: 'Safeguard', pfd: 0.1, independent: false, effective: false, dependable: false, auditable: false, dependencies: [] }])}>Add</Button>}>
          <Table rowKey="_k" size="small" pagination={false} dataSource={m.safeguards.map((x: any, i: number) => ({ ...x, _k: i }))} scroll={{ x: 900 }} columns={[
            { title: 'Safeguard', dataIndex: 'label', width: 220, render: (v, r: any) => <Input.TextArea size="small" autoSize value={v} disabled={readOnly} onChange={(e) => upd('safeguards', r._k, 'label', e.target.value)} /> },
            { title: 'PFD', dataIndex: 'pfd', width: 100, render: (v, r: any) => <InputNumber size="small" value={v} min={0} max={1} step={0.01} disabled={readOnly} onChange={(x) => upd('safeguards', r._k, 'pfd', x)} /> },
            ...CRIT.map((c) => ({ title: <Tooltip title={c}>{c.slice(0, 5)}.</Tooltip>, dataIndex: c, width: 58,
              render: (v: boolean, r: any) => <Checkbox checked={!!v} disabled={readOnly} onChange={(e) => upd('safeguards', r._k, c, e.target.checked)} /> })),
            { title: 'Shared dependencies', dataIndex: 'dependencies', width: 170, render: (v: string[] = [], r: any) => <Input size="small" placeholder="e.g. surveillance" value={v.join(', ')} disabled={readOnly}
              onChange={(e) => upd('safeguards', r._k, 'dependencies', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))} /> },
            { title: 'Justification', dataIndex: 'justification', width: 260, render: (v, r: any) => <Input.TextArea size="small" autoSize value={v} disabled={readOnly} onChange={(e) => upd('safeguards', r._k, 'justification', e.target.value)} /> },
            { title: '', width: 40, render: (_: any, r: any) => !readOnly && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => set('safeguards', m.safeguards.filter((_: any, j: number) => j !== r._k))} /> },
          ]} />
        </Card>
        <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 12 }} onClick={run}>Calculate</Button>
      </Col>
      <Col xs={24} xl={10}>
        <Card size="small" title="Result">
          {results?.steps ? <>
            <Descriptions size="small" column={1} bordered>
              <Descriptions.Item label="Mitigated frequency"><b>{fmtSci(results.mitigated_frequency)}</b> {results.unit}</Descriptions.Item>
              <Descriptions.Item label="Target">{fmtSci(results.target_frequency)} {results.unit}</Descriptions.Item>
              <Descriptions.Item label="Verdict">{results.target_met ? <Tag color="green">Target met</Tag> : <Tag color="red">Gap ×{results.ratio_to_target.toFixed(1)}</Tag>}</Descriptions.Item>
              {!results.target_met && <Descriptions.Item label="Further reduction needed">×{results.additional_risk_reduction_required.toFixed(1)} ({results.additional_orders_of_magnitude.toFixed(2)} orders of magnitude)</Descriptions.Item>}
              <Descriptions.Item label="Credited IPLs">{results.credited_ipls.join('; ') || '—'}</Descriptions.Item>
            </Descriptions>
            {results.rejected_safeguards.map((r: any) => <Alert key={r.label} style={{ marginTop: 8 }} type="info" showIcon title={`Not credited: ${r.label}`} description={`Missing: ${r.missing_criteria.join(', ')}`} />)}
            {results.warnings.map((w: string) => <Alert key={w} style={{ marginTop: 8 }} type="warning" showIcon title={w} />)}
            <ReactECharts option={chart} style={{ height: 320, marginTop: 12 }} />
            <div className="muted small">Engine {results.engine_version}. LOPA is an order-of-magnitude screening tool (Manual §11.4).</div>
          </> : <span className="muted">Press Calculate.</span>}
        </Card>
      </Col>
    </Row>
  )
}
