import { useEffect, useRef } from 'react'
import { Alert, Card, Col, Row, Select, Space, Table, Tag, Tooltip } from 'antd'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import { useSamnPerelliMeta } from '../hooks'
import EditableTable, { nextId } from '../components/EditableTable'

const SEV: Record<string, string> = { error: 'error', warning: 'warning', info: 'info' }

/** Samn-Perelli 7-point fatigue checklist: pre-shift self-ratings, traffic-light actions and the supervisor's response. */
export default function SamnPerelli({ ratings, onChange, result, setResult, readOnly }: {
  ratings: any[]; onChange: (r: any[]) => void; result: any; setResult: (r: any) => void; readOnly: boolean
}) {
  const { data: meta } = useSamnPerelliMeta()
  const first = useRef(true)
  useEffect(() => {
    if (first.current) { first.current = false; if (result?.engine_version) return }
    const h = setTimeout(() => { api.post('/calc/samn-perelli', { ratings }).then(setResult).catch(() => { /* next edit retries */ }) }, 400)
    return () => clearTimeout(h)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ratings])
  if (!meta) return null
  const lightOf = (s?: number) => meta.lights.find((l: any) => l.scores.includes(s))
  const byId: Record<string, any> = Object.fromEntries((result?.rows ?? []).map((r: any) => [r.id, r]))
  const checksFor = (id: string) => (result?.checks ?? []).filter((c: any) => c.ref === id)
  const scoreOpts = meta.scale.map((s: any) => ({ value: s.score, label: <span><Tag color={lightOf(s.score).color} style={{ marginRight: 6 }}>{s.score}</Tag>{s.description}</span> }))
  const counts = result?.counts ?? {}
  const dist = result?.distribution ?? {}

  return <div>
    <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Samn-Perelli fatigue checklist"
      description={<span className="small">A 7-point self-rating of mental exhaustion and cognitive slowing, taken before the controller takes over a position.
        The three-process model predicts group-average alertness for a roster; this rating records how the individual feels now. Record controller IDs, not names —
        ratings are personal data and are used to manage fatigue, not to judge performance.</span>} />
    <Row gutter={12}>
      <Col xs={24} xl={9}>
        <Card size="small" title="Scale and action thresholds" style={{ marginBottom: 12 }}>
          <Table size="small" pagination={false} rowKey="score" dataSource={meta.scale} showHeader={false}
            columns={[{ dataIndex: 'score', width: 44, render: (s: number) => <Tag color={lightOf(s).color} style={{ fontWeight: 700 }}>{s}</Tag> },
              { dataIndex: 'description' }]} />
          {meta.lights.map((l: any) => <div key={l.key} style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <div style={{ width: 14, height: 14, borderRadius: 7, background: l.color, flex: 'none', marginTop: 3 }} />
            <div className="small"><b>{l.scores.length > 1 ? `Scores ${l.scores[0]}–${l.scores[l.scores.length - 1]}` : `Score ${l.scores[0]}`}: {l.name}.</b> {l.action}</div>
          </div>)}
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card size="small" title="Summary" style={{ marginBottom: 12 }}>
          <Space wrap style={{ marginBottom: 6 }}>
            <span>{result?.n ?? 0} rating(s)</span>
            {meta.lights.map((l: any) => <Tag key={l.key} color={l.color}>{l.name}: {counts[l.key] ?? 0}</Tag>)}
            {result?.mean_score != null && <span className="small muted">mean {result.mean_score.toFixed(1)} · {(result.share_not_green * 100).toFixed(0)}% not green</span>}
          </Space>
          {(result?.n ?? 0) > 0 && <ReactECharts style={{ height: 170 }} notMerge option={{
            grid: { left: 36, right: 10, top: 10, bottom: 24 }, tooltip: { trigger: 'axis' },
            xAxis: { type: 'category', data: meta.scale.map((s: any) => String(s.score)), name: 'score' },
            yAxis: { type: 'value', minInterval: 1 },
            series: [{ type: 'bar', data: meta.scale.map((s: any) => ({ value: dist[s.score] ?? 0, itemStyle: { color: lightOf(s.score).color } })) }],
          }} />}
          {(result?.checks ?? []).length > 0 && <Alert style={{ marginTop: 8 }} showIcon type={(result.checks.some((c: any) => c.severity === 'error') ? 'error' : 'warning')}
            title={`${result.checks.length} response check(s)`}
            description={<ul style={{ margin: 0, paddingLeft: 16 }}>{result.checks.map((c: any, i: number) => <li key={i} className="small">{c.message}</li>)}</ul>} />}
        </Card>
      </Col>
    </Row>
    <Card size="small" title="Pre-shift ratings">
      <EditableTable readOnly={readOnly} rows={ratings} onChange={onChange} addLabel="Rating" scrollX={1850}
        newRow={() => ({ id: nextId(ratings, 'SP', 1), date: new Date().toISOString().slice(0, 10), time: '', shift: '', controller: '', position: '', score: null, outcome: '', mitigations: [], notes: '' })}
        columns={[
          { key: 'date', title: 'Date', width: 130 }, { key: 'time', title: 'Time', width: 90 }, { key: 'shift', title: 'Shift', width: 100 },
          { key: 'controller', title: 'Controller ID', width: 110 }, { key: 'position', title: 'Planned position', width: 130 },
          { key: 'score', title: 'Score', width: 300, render: (r: any, i: number) => readOnly
            ? (r.score ? <span><Tag color={lightOf(r.score)?.color}>{r.score}</Tag>{meta.scale[r.score - 1].description}</span> : '')
            : <Select size="small" style={{ width: '100%' }} value={r.score ?? undefined} placeholder="1–7" options={scoreOpts}
                onChange={(v) => onChange(ratings.map((x, j) => (j === i ? { ...x, score: v } : x)))} /> },
          { key: 'light', title: 'Light / required action', width: 150, render: (r: any) => {
            const l = lightOf(r.score); if (!l) return null
            return <Tooltip title={l.action}><Tag color={l.color}>{l.name}</Tag></Tooltip> } },
          { key: 'outcome', title: "Supervisor's response", width: 230, type: 'select', options: meta.outcomes.map((o: any) => ({ value: o.key, label: o.name })) },
          { key: 'mitigations', title: 'Mitigations', width: 220, type: 'multiselect', options: meta.mitigations },
          { key: 'check', title: '', width: 50, render: (r: any) => {
            const cs = checksFor(r.id); const row = byId[r.id]
            if (cs.length) return <Tooltip title={cs.map((c: any) => c.message).join(' ')}><Tag color={SEV[cs[0].severity] === 'error' ? 'red' : cs[0].severity === 'warning' ? 'orange' : 'blue'}>!</Tag></Tooltip>
            return row?.response_ok ? <Tag color="green">✓</Tag> : null } },
          { key: 'notes', title: 'Notes', width: 230, type: 'textarea' },
        ]} />
    </Card>
  </div>
}
