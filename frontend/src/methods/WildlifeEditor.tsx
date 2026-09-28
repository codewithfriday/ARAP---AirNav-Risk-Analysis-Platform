import { useState } from 'react'
import { Alert, App, Button, Card, Col, Descriptions, Empty, Input, InputNumber, Row, Select, Space, Table, Tabs, Tag, Tooltip } from 'antd'
import { CalculatorOutlined, PlusOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import EditableTable, { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

const RISK_COLOR: Record<string, string> = { high: '#B23A3A', moderate: '#D98E04', low: '#3C8D5A' }
const CLS = ['', 'Very low', 'Low', 'Moderate', 'High', 'Very high']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const f1 = (v: any, d = 1) => (v === null || v === undefined ? '—' : Number(v).toFixed(d))

/** 5 × 5 likelihood × severity grid with species placed in their cells (Manual §31.2). */
function Matrix({ res, bands, sel, onSel }: { res: any[]; bands: any; sel: string | null; onSel: (id: string) => void }) {
  const lvl = (l: number, s: number) => (l * s >= bands.risk_high ? 'high' : l * s >= bands.risk_moderate ? 'moderate' : 'low')
  return (
    <table style={{ borderCollapse: 'separate', borderSpacing: 3, width: '100%' }}>
      <tbody>
        {[5, 4, 3, 2, 1].map((l) => (
          <tr key={l}>
            <td className="small" style={{ width: 88, textAlign: 'right', paddingRight: 6 }}>{CLS[l]}<div className="muted" style={{ fontSize: 10 }}>{['', '<0.3', '0.3–1', '1–3', '3–10', '>10'][l]} /yr</div></td>
            {[1, 2, 3, 4, 5].map((s) => {
              const here = res.filter((r) => r.likelihood === l && r.severity === s)
              return (
                <td key={s} style={{ background: RISK_COLOR[lvl(l, s)], opacity: here.length ? 1 : 0.35, borderRadius: 4, height: 64, verticalAlign: 'top', padding: 4 }}>
                  {here.map((r) => (
                    <Tooltip key={r.id} title={`${r.common} — ${f1(r.per_year)}/yr, ${r.damage_pct === null ? 'no strikes' : f1(r.damage_pct) + '% damaging'} (${r.severity_basis})`}>
                      <div onClick={() => onSel(r.id)} style={{ background: '#fff', borderRadius: 10, padding: '1px 6px', margin: '0 0 3px', fontSize: 10.5, cursor: 'pointer', fontStyle: 'italic', outline: sel === r.id ? '2px solid #1F3A5F' : 'none' }}>{r.scientific}</div>
                    </Tooltip>))}
                </td>)
            })}
          </tr>))}
        <tr><td />{[1, 2, 3, 4, 5].map((s) => <td key={s} className="small" style={{ textAlign: 'center' }}>{CLS[s]}<div className="muted" style={{ fontSize: 10 }}>{['', '<1%', '1–5%', '5–10%', '10–20%', '>20%'][s]}</div></td>)}</tr>
      </tbody>
    </table>
  )
}

export default function WildlifeEditor({ model, setModel, results, setResults, readOnly, template, promote }: EditorProps) {
  const { message } = App.useApp()
  const years: number[] = model.years ?? []
  const species: any[] = model.species ?? []
  const [sel, setSel] = useState<string | null>(species[0]?.id ?? null)
  const set = (k: string, v: any) => setModel({ ...model, [k]: v })
  const run = async () => { try { setResults(await api.post('/calc/wildlife', model)) } catch (e: any) { message.error(e.message) } }
  const res: any[] = results?.species ?? []
  const bands = results?.bands ?? { risk_high: 12, risk_moderate: 6 }

  // species table rows are flattened: s_<year> and d_<year> columns
  const rows = species.map((s) => ({ ...s, ...Object.fromEntries(years.flatMap((y) => [[`s_${y}`, s.strikes?.[y]], [`d_${y}`, s.damaging?.[y]]])) }))
  const fromRows = (rs: any[]) => set('species', rs.map((r) => {
    const { strikes: _s, damaging: _d, ...rest } = r
    const clean = Object.fromEntries(Object.entries(rest).filter(([k]) => !/^[sd]_\d+$/.test(k)))
    return { ...clean, strikes: Object.fromEntries(years.map((y) => [String(y), r[`s_${y}`] ?? 0])), damaging: Object.fromEntries(years.map((y) => [String(y), r[`d_${y}`] ?? 0])) }
  }))
  const sp = species.find((s) => s.id === sel)
  const r = res.find((x) => x.id === sel)
  const prof = model.profiles?.[sel ?? ''] ?? {}
  const setProf = (k: string, v: any) => set('profiles', { ...model.profiles, [sel!]: { ...prof, [k]: v } })
  const attractants: any[] = model.attractants ?? []
  const circle = template.circle_km ?? 13

  const doPromote = () => promote(res.filter((x) => x.risk !== 'low').map((x) => ({
    row_id: x.id, title: `Wildlife strike — ${x.common} (${x.scientific})`,
    causes: `${f1(x.per_year)} strikes/yr (${f1(x.rate_per_10k, 2)} per 10,000 movements); attractants: ${attractants.filter((a) => [].concat(a.species ?? []).map(String).some((v: string) => v.includes(x.id))).map((a) => a.site).join('; ') || '—'}`,
    consequences: `Engine ingestion / airframe damage; ${x.damage_pct === null ? 'severity from mass surrogate' : f1(x.damage_pct) + '% of strikes damaging'}`,
    controls: (model.profiles?.[x.id]?.mitigations ?? []).map((m: any) => m.text),
  })))

  const addYear = () => { const y = (years.at(-1) ?? new Date().getFullYear() - 1) + 1; set('years', [...years, y]) }
  const trendChart = sp && {
    tooltip: { trigger: 'axis' }, legend: { top: 0 }, grid: { left: 45, right: 50, top: 30, bottom: 25 },
    xAxis: { type: 'category', data: years.map(String) },
    yAxis: [{ type: 'value', name: 'strikes' }, { type: 'value', name: 'per 10k mvt', splitLine: { show: false } }],
    series: [{ name: 'Strikes', type: 'bar', data: years.map((y) => sp.strikes?.[y] ?? 0), itemStyle: { color: '#9CC9D1' } },
      { name: 'Damaging', type: 'bar', data: years.map((y) => sp.damaging?.[y] ?? 0), itemStyle: { color: '#B23A3A' } },
      { name: 'Rate per 10,000 movements', type: 'line', yAxisIndex: 1, data: years.map((y) => (model.movements?.[y] ? +((sp.strikes?.[y] ?? 0) / model.movements[y] * 1e4).toFixed(2) : null)), itemStyle: { color: '#1F3A5F' } }],
  }
  const seasonChart = prof.monthly_counts && {
    tooltip: { trigger: 'axis' }, legend: { top: 0 }, grid: { left: 45, right: 45, top: 30, bottom: 25 },
    xAxis: { type: 'category', data: MONTHS }, yAxis: [{ type: 'value', name: 'mean count' }, { type: 'value', name: 'strikes', splitLine: { show: false } }],
    series: [{ name: 'Survey count (mean)', type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, data: prof.monthly_counts, itemStyle: { color: '#2A7F8E' } },
      { name: 'Strikes (period total)', type: 'bar', yAxisIndex: 1, data: prof.monthly_strikes ?? [], itemStyle: { color: '#D98E04' } }],
  }

  return (
    <Tabs items={[
      { key: 'data', label: 'Species and strikes', children: (
        <div>
          <Alert type="info" showIcon style={{ marginBottom: 10 }} title="Rate each species separately. Likelihood = mean strikes per year over the review period; severity = share of strikes that caused damage or an effect on flight. With fewer than 5 strikes, severity comes from body mass (+1 class for flocking species). Bands are ARAP defaults — calibrate them for your aerodrome." />
          <Space style={{ marginBottom: 10 }} wrap>
            <Input prefix="Aerodrome" style={{ width: 420 }} value={model.aerodrome} disabled={readOnly} onChange={(e) => set('aerodrome', e.target.value)} />
            {!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={addYear}>Year</Button>}
            {!readOnly && years.length > 1 && <Button size="small" onClick={() => set('years', years.slice(1))}>Drop {years[0]}</Button>}
          </Space>
          <Card size="small" title="Aircraft movements per year" style={{ marginBottom: 10 }}>
            <Space wrap>{years.map((y) => <InputNumber key={y} prefix={String(y)} style={{ width: 170 }} value={model.movements?.[y]} disabled={readOnly} min={0}
              onChange={(v) => set('movements', { ...model.movements, [y]: v })} />)}</Space>
          </Card>
          <EditableTable readOnly={readOnly} rows={rows} onChange={fromRows} scrollX={560 + years.length * 130} addLabel="Species"
            newRow={() => ({ id: nextId(species, 'SP-', 2), common: '', scientific: '', mass_kg: 0.1, flocking: false })}
            columns={[
              { key: 'id', title: 'ID', width: 70 }, { key: 'common', title: 'Common / local name', width: 180 },
              { key: 'scientific', title: 'Scientific name', width: 150 }, { key: 'mass_kg', title: 'Mass (kg)', type: 'number', width: 90, min: 0, step: 0.01 },
              { key: 'flocking', title: 'Flocks', type: 'bool', width: 60 },
              ...years.flatMap((y) => [{ key: `s_${y}`, title: <span>{y}<div className="muted" style={{ fontSize: 10 }}>strikes</div></span>, type: 'number' as const, width: 70, min: 0 },
                { key: `d_${y}`, title: <span>{y}<div className="muted" style={{ fontSize: 10 }}>damaging</div></span>, type: 'number' as const, width: 70, min: 0 }]),
            ]} />
          <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 10 }} onClick={run}>Calculate risk</Button>
        </div>) },
      { key: 'matrix', label: 'Risk matrix', children: !res.length ? <Empty description="Press Calculate risk on the first tab" /> : (
        <Row gutter={16}>
          <Col xs={24} xl={11}>
            <Card size="small" title="Species risk matrix" extra={<span className="small muted">rows: likelihood · columns: severity</span>}>
              <Matrix res={res} bands={bands} sel={sel} onSel={setSel} />
            </Card>
            <Space style={{ marginTop: 10 }} wrap>
              <Tag color="red">{results.counts.high} high</Tag><Tag color="orange">{results.counts.moderate} moderate</Tag><Tag color="green">{results.counts.low} low</Tag>
              <span className="small">All species: {results.total_strikes} strikes, {f1(results.rate_per_10k, 2)} per 10,000 movements</span>
              {!readOnly && <Button size="small" type="primary" ghost onClick={doPromote}>Send high and moderate species to hazard log</Button>}
            </Space>
          </Col>
          <Col xs={24} xl={13}>
            <Table size="small" rowKey="id" pagination={false} dataSource={res} onRow={(x: any) => ({ onClick: () => setSel(x.id), style: { cursor: 'pointer', background: x.id === sel ? '#E3F1F3' : undefined } })}
              columns={[
                { title: '#', dataIndex: 'rank', width: 36 },
                { title: 'Species', render: (_, x: any) => <><b>{x.common}</b><div className="small muted"><i>{x.scientific}</i></div></> },
                { title: 'Strikes/yr', dataIndex: 'per_year', width: 80, render: (v) => f1(v) },
                { title: 'Per 10k mvt', dataIndex: 'rate_per_10k', width: 85, render: (v) => f1(v, 2) },
                { title: 'Damaging', dataIndex: 'damage_pct', width: 80, render: (v) => (v === null ? '—' : `${f1(v)}%`) },
                { title: 'L × S', width: 80, render: (_, x: any) => <Tooltip title={`Severity basis: ${x.severity_basis}`}><span>{x.likelihood} × {x.severity}{x.severity_basis.startsWith('surrogate') ? '*' : ''} = <b>{x.score}</b></span></Tooltip> },
                { title: 'Risk', dataIndex: 'risk', width: 90, render: (v) => <Tag color={RISK_COLOR[v]}>{v}</Tag> },
                { title: 'Trend', dataIndex: 'trend_per_year', width: 70, render: (v) => (v === null ? '—' : <Tooltip title="Change in strikes per 10,000 movements per year (least squares)"><span style={{ color: v > 0.05 ? '#B23A3A' : v < -0.05 ? '#3C8D5A' : undefined }}>{v > 0 ? '▲' : v < 0 ? '▼' : '■'} {f1(Math.abs(v), 2)}</span></Tooltip>) },
              ]} />
            <div className="small muted" style={{ marginTop: 6 }}>* severity from the body-mass surrogate (too few strikes for a stable percentage). Engine {results.engine_version}.</div>
          </Col>
        </Row>) },
      { key: 'profile', label: 'Species profile', children: (
        <Row gutter={16}>
          <Col xs={24} xl={10}>
            <Select style={{ width: '100%', marginBottom: 10 }} value={sel} onChange={setSel} options={species.map((s) => ({ value: s.id, label: `${s.common} — ${s.scientific}` }))} />
            {!sp ? <Empty /> : <>
              <Descriptions bordered size="small" column={1}>
                <Descriptions.Item label="Species"><b>{sp.common}</b> — <i>{sp.scientific}</i></Descriptions.Item>
                <Descriptions.Item label="Mass / behaviour">{sp.mass_kg} kg · {sp.flocking ? 'flocks' : 'solitary or small groups'}</Descriptions.Item>
                {r && <Descriptions.Item label="Risk"><Tag color={RISK_COLOR[r.risk]}>{r.risk}</Tag> L {r.likelihood} ({r.likelihood_label}) × S {r.severity} ({r.severity_label}) = {r.score}</Descriptions.Item>}
                {r && <Descriptions.Item label="Strikes">{r.strikes} in {years.length} years ({f1(r.per_year)}/yr); {r.damaging} damaging; {f1(r.share_pct)}% of all strikes</Descriptions.Item>}
                {sp.notes && <Descriptions.Item label="Notes">{sp.notes}</Descriptions.Item>}
              </Descriptions>
              <div className="small muted" style={{ margin: '10px 0 4px' }}>Ecology and behaviour relevant to the aerodrome</div>
              <Input.TextArea autoSize={{ minRows: 3 }} value={prof.ecology} disabled={readOnly} onChange={(e) => setProf('ecology', e.target.value)} />
              <div className="small muted" style={{ margin: '10px 0 4px' }}>Time of day / season of strikes</div>
              <Input.TextArea autoSize value={prof.diurnal} disabled={readOnly} onChange={(e) => setProf('diurnal', e.target.value)} />
            </>}
          </Col>
          <Col xs={24} xl={14}>
            {sp && <Card size="small" title="Strikes and strike rate by year"><ReactECharts option={trendChart} style={{ height: 220 }} notMerge /></Card>}
            {sp && <Card size="small" title="Seasonality — monthly survey counts and strikes" style={{ marginTop: 10 }}
              extra={!readOnly && <Button size="small" onClick={() => setProf('monthly_counts', prof.monthly_counts ?? Array(12).fill(0))}>Edit</Button>}>
              {seasonChart ? <ReactECharts option={seasonChart} style={{ height: 220 }} notMerge /> : <span className="muted small">No survey data yet.</span>}
              {prof.monthly_counts && !readOnly && <Space wrap size={4} style={{ marginTop: 6 }}>{MONTHS.map((m, i) => (
                <InputNumber key={m} size="small" prefix={m} style={{ width: 92 }} value={prof.monthly_counts[i]} min={0}
                  onChange={(v) => setProf('monthly_counts', prof.monthly_counts.map((x: number, j: number) => (j === i ? v ?? 0 : x)))} />))}</Space>}
            </Card>}
            {sp && <Card size="small" title="Species management measures" style={{ marginTop: 10 }}>
              <EditableTable readOnly={readOnly} rows={prof.mitigations ?? []} onChange={(v) => setProf('mitigations', v)} newRow={() => ({ text: '', type: 'Habitat', owner: '', status: 'planned' })}
                columns={[{ key: 'text', title: 'Measure', type: 'textarea' }, { key: 'type', title: 'Type', type: 'select', options: template.mitigation_types ?? [], width: 110 },
                  { key: 'owner', title: 'Owner', width: 150 }, { key: 'status', title: 'Status', type: 'select', options: ['existing', 'planned'], width: 100 }]} />
            </Card>}
          </Col>
        </Row>) },
      { key: 'attract', label: `Attractants within ${circle} km`, children: (
        <div>
          <Alert type="info" showIcon style={{ marginBottom: 10 }} title={`ICAO Annex 14 §9.4 and Doc 9137 Part 3: assess land uses that attract wildlife within about ${circle} km of the aerodrome reference point, and press the relevant authority to remove or control them.`} />
          <EditableTable readOnly={readOnly} rows={attractants} onChange={(v) => set('attractants', v)} scrollX={1100} addLabel="Attractant"
            newRow={() => ({ id: nextId(attractants, 'AT-', 2), site: '', land_use: undefined, distance_km: 1, species: '', action: '', owner: '' })}
            columns={[{ key: 'id', title: 'ID', width: 70 }, { key: 'site', title: 'Site', width: 200 },
              { key: 'land_use', title: 'Land use', type: 'select', options: template.land_uses ?? [], width: 180 },
              { key: 'distance_km', title: 'Distance (km)', type: 'number', min: 0, step: 0.1, width: 100 },
              { key: 'inside', title: `≤ ${circle} km`, type: 'readonly', width: 70, render: (a: any) => (Number(a.distance_km) <= circle ? <Tag color="orange">inside</Tag> : <Tag>outside</Tag>) },
              { key: 'species', title: 'Species attracted', type: 'tags', options: species.map((s) => ({ value: s.id, label: `${s.id} ${s.scientific}` })), width: 200 },
              { key: 'action', title: 'Action', type: 'textarea', width: 220 }, { key: 'owner', title: 'Owner', width: 160 }]} />
        </div>) },
    ]} />
  )
}
