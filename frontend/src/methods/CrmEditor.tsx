import { Alert, App, Button, Card, Col, Descriptions, InputNumber, Row, Select, Space, Tabs, Tag } from 'antd'
import { CalculatorOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import { fmtSci } from '../risk'
import type { EditorProps } from './types'

const FT = 6076.12
const V_FIELDS: [string, string, number?][] = [
  ['pz_sz', 'P_z(S_z) — vertical overlap at 1000 ft'], ['py0', 'P_y(0) — lateral overlap on same track'],
  ['ez_same', 'E_z(same) — same-direction vertical occupancy'], ['ez_opp', 'E_z(opp) — opposite-direction vertical occupancy'],
  ['sx', 'S_x — longitudinal window (NM)'], ['dv', '|Δv| same-direction relative speed (kt)'], ['v', '|v| aircraft speed (kt)'],
  ['ydot', '|ẏ| lateral relative speed (kt)'], ['zdot', '|ż| vertical relative speed (kt)'], ['tls', 'Target level of safety (per flight hour)'],
]
const L_FIELDS: [string, string][] = [
  ['pz0', 'P_z(0) — vertical overlap, same level'], ['ey_same', 'E_y(same) — same-direction lateral occupancy'],
  ['ey_opp', 'E_y(opp) — opposite-direction lateral occupancy'], ['sx', 'S_x — longitudinal window (NM)'],
  ['dv', '|Δv| (kt)'], ['v', '|v| (kt)'], ['zdot', '|ż| (kt)'], ['ydot_sy', '|ẏ(S_y)| lateral closing speed at loss of spacing (kt)'], ['tls', 'Target level of safety'],
]

function Dims({ m, set, readOnly }: { m: any; set: (k: string, v: number) => void; readOnly: boolean }) {
  return (
    <Space wrap>
      {[['lx', 'λx length'], ['ly', 'λy wingspan'], ['lz', 'λz height']].map(([k, l]) => (
        <InputNumber key={k} prefix={`${l} (ft)`} style={{ width: 200 }} disabled={readOnly} value={m[k] !== undefined ? Math.round(m[k] * FT) : undefined}
          onChange={(v) => set(k, (v ?? 0) / FT)} />))}
    </Space>
  )
}

export default function CrmEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const vm = model.vertical ?? {}
  const lm = model.lateral ?? {}
  const setV = (k: string, v: number) => setModel({ ...model, vertical: { ...vm, [k]: v } })
  const setL = (k: string, v: any) => setModel({ ...model, lateral: { ...lm, [k]: v } })

  const runV = async () => {
    try { setResults({ ...results, vertical: await api.post('/calc/crm', { dimension: 'vertical', params: vm }) }) } catch (e: any) { message.error(e.message) }
  }
  const runL = async () => {
    try {
      const ov = await api.post('/calc/crm/overlap', { spacing: lm.spacing, lam_y: lm.ly, model: lm.model, scale: lm.scale })
      const params = { py_sy: ov.py_sy, pz0: lm.pz0, lx: lm.lx, ly: lm.ly, lz: lm.lz, sx: lm.sx, ey_same: lm.ey_same, ey_opp: lm.ey_opp,
        dv: lm.dv, v: lm.v, zdot: lm.zdot, ydot_sy: lm.ydot_sy, tls: lm.tls }
      const r = await api.post('/calc/crm', { dimension: 'lateral', params, curve: { lam_y: lm.ly, model: lm.model, scale: lm.scale, spacings: lm.spacings ?? [5, 10, 15, 20, 25, 30] } })
      setResults({ ...results, lateral: { ...r, py_sy: ov.py_sy, spacing: lm.spacing } })
    } catch (e: any) { message.error(e.message) }
  }
  const verdict = (r: any) => r && (r.meets_tls ? <Tag color="green">Meets TLS</Tag> : <Tag color="red">Exceeds TLS ×{r.ratio_to_tls.toFixed(1)}</Tag>)
  const lr = results?.lateral
  const chart = lr?.curve && {
    grid: { left: 70, right: 20, top: 30, bottom: 45 }, tooltip: { trigger: 'axis', valueFormatter: (v: number) => v.toExponential(2) },
    xAxis: { type: 'value', name: 'route spacing (NM)', nameLocation: 'middle', nameGap: 28 },
    yAxis: { type: 'log', name: 'collision risk / fh', axisLabel: { formatter: (v: number) => v.toExponential(0) } },
    series: [{ type: 'line', data: lr.curve.map((p: any) => [p.spacing, p.risk]), smooth: true, lineStyle: { color: '#1F3A5F' }, itemStyle: { color: '#1F3A5F' },
      markLine: { symbol: 'none', data: [{ yAxis: lr.tls, label: { formatter: `TLS ${fmtSci(lr.tls, 0)}` }, lineStyle: { color: '#B23A3A', type: 'dashed' } },
        ...(lr.minimum_spacing?.minimum_spacing ? [{ xAxis: lr.minimum_spacing.minimum_spacing, label: { formatter: `min ${lr.minimum_spacing.minimum_spacing.toFixed(1)} NM` }, lineStyle: { color: '#3C8D5A' } }] : [])] } }],
  }

  return (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Reich collision risk model in occupancy form (ICAO Doc 9689 / Doc 9574). Overlap probabilities and occupancies should come from regional monitoring agency data (e.g. height-keeping and lateral deviation monitoring)." />
      <Tabs items={[
        { key: 'v', label: 'Vertical (RVSM)', children: (
          <Row gutter={16}>
            <Col xs={24} xl={13}>
              <Card size="small" title="Parameters">
                <Dims m={vm} set={setV} readOnly={readOnly} />
                <Row gutter={[8, 8]} style={{ marginTop: 10 }}>
                  {V_FIELDS.map(([k, l]) => <Col span={12} key={k}><div className="small muted">{l}</div><InputNumber style={{ width: '100%' }} disabled={readOnly} value={vm[k]} onChange={(v) => setV(k, v ?? 0)} /></Col>)}
                </Row>
                <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 12 }} onClick={runV}>Calculate</Button>
              </Card>
            </Col>
            <Col xs={24} xl={11}>
              <Card size="small" title="Result">
                {results?.vertical ? <Descriptions bordered size="small" column={1}>
                  <Descriptions.Item label="Same-direction risk">{fmtSci(results.vertical.same_direction)}</Descriptions.Item>
                  <Descriptions.Item label="Opposite-direction risk">{fmtSci(results.vertical.opposite_direction)}</Descriptions.Item>
                  <Descriptions.Item label="Total (fatal accidents / fh)"><b>{fmtSci(results.vertical.total, 3)}</b></Descriptions.Item>
                  <Descriptions.Item label="TLS">{fmtSci(results.vertical.tls, 1)} {verdict(results.vertical)}</Descriptions.Item>
                </Descriptions> : <span className="muted">Press Calculate.</span>}
              </Card>
            </Col>
          </Row>) },
        { key: 'l', label: 'Lateral (route spacing)', children: (
          <Row gutter={16}>
            <Col xs={24} xl={12}>
              <Card size="small" title="Parameters">
                <Dims m={lm} set={setL} readOnly={readOnly} />
                <Space wrap style={{ marginTop: 10 }}>
                  <span className="small">Lateral deviation model</span>
                  <Select value={lm.model} disabled={readOnly} style={{ width: 170 }} onChange={(v) => setL('model', v)} options={[{ value: 'laplace', label: 'Double exponential' }, { value: 'gaussian', label: 'Gaussian' }]} />
                  <InputNumber prefix="scale (NM)" style={{ width: 170 }} disabled={readOnly} value={lm.scale} min={0.01} step={0.1} onChange={(v) => setL('scale', v)} />
                  <InputNumber prefix="Route spacing S_y (NM)" style={{ width: 240 }} disabled={readOnly} value={lm.spacing} onChange={(v) => setL('spacing', v)} />
                </Space>
                <Row gutter={[8, 8]} style={{ marginTop: 10 }}>
                  {L_FIELDS.map(([k, l]) => <Col span={12} key={k}><div className="small muted">{l}</div><InputNumber style={{ width: '100%' }} disabled={readOnly} value={lm[k]} onChange={(v) => setL(k, v ?? 0)} /></Col>)}
                </Row>
                <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 12 }} onClick={runL}>Calculate</Button>
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card size="small" title="Result">
                {lr ? <>
                  <Descriptions bordered size="small" column={1}>
                    <Descriptions.Item label={`P_y(S_y) at ${lr.spacing} NM`}>{fmtSci(lr.py_sy)}</Descriptions.Item>
                    <Descriptions.Item label="Lateral risk (fatal accidents / fh)"><b>{fmtSci(lr.total, 3)}</b> {verdict(lr)}</Descriptions.Item>
                    <Descriptions.Item label="Minimum spacing meeting TLS">{lr.minimum_spacing?.minimum_spacing ? `${lr.minimum_spacing.minimum_spacing.toFixed(2)} NM` : lr.minimum_spacing?.note}</Descriptions.Item>
                  </Descriptions>
                  <ReactECharts option={chart} style={{ height: 300, marginTop: 10 }} notMerge />
                </> : <span className="muted">Press Calculate.</span>}
              </Card>
            </Col>
          </Row>) },
      ]} />
    </div>
  )
}
