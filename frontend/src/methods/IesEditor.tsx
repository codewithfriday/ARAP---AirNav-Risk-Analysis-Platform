import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Empty, Input, Progress, Row, Select, Space, Table, Tabs, Tag, Tooltip, Typography } from 'antd'
import { ApartmentOutlined, ExperimentOutlined, SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import AcciMap, { LAYER_COLOR, LAYER_NAME, SUPPORT_LABEL, SUPPORT_TERMS } from '../components/AcciMap'
import type { Block } from '../components/AcciMap'
import { ResultBadge, inputsOf } from '../pages/CaseEditor'
import { useIesMeta } from '../pages/CaseLibrary'
import type { EditorProps } from './types'

const RATE_OPTS = [...SUPPORT_TERMS.map((t) => ({ value: t, label: SUPPORT_LABEL[t] })), { value: 'NP', label: 'Not provided' }]
const rkey = (caseId: number, b: Block) => (b.factor ? `f:${b.factor}` : `b:${caseId}:${b.id}`)

export default function IesEditor({ model, setModel, results, setResults, readOnly, assessmentId }: EditorProps & { assessmentId?: number }) {
  const { message } = App.useApp()
  const nav = useNavigate()
  const { data: meta } = useIesMeta()
  const [hits, setHits] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const category: string = model.category ?? 'ats-los'
  const selected: number[] = model.selected ?? []
  const ratings: Record<string, string> = model.ratings ?? {}
  const caseQs = useQueries({ queries: selected.map((id) => ({ queryKey: ['case', String(id)], queryFn: () => api.get(`/cases/${id}`) })) })
  const cases = caseQs.map((q) => q.data).filter(Boolean) as any[]
  const cat = meta?.categories?.[category]
  const mechs: any[] = cat?.mechanisms ?? []
  const factors: any[] = cat?.factors ?? []
  const mechLabel = (m: string) => mechs.find((x) => x.code === m)?.label ?? m
  const fz = results?.fuzzy
  const bn = results?.bn
  const bnClue = useMemo(() => Object.fromEntries((bn?.clues ?? []).map((c: any, i: number) => [c.factor, i + 1])), [bn])

  const set = (patch: any) => setModel({ ...model, category, ...patch })
  const rate = (key: string, v: string) => {
    const r = { ...ratings }
    if (v === 'NP') delete r[key]; else r[key] = v
    set({ ratings: r })
  }
  const search = async () => {
    if (!model.narrative?.trim()) { message.warning('Describe the occurrence first'); return }
    setBusy(true)
    try { setHits(await api.post('/ies/search', { category, text: model.narrative })) } catch (e: any) { message.error(e.message) } finally { setBusy(false) }
  }
  const run = async () => {
    setBusy(true)
    try { setResults(await api.post('/ies/analyse', { model: { ...model, category } })); message.success('Analysis updated') } catch (e: any) { message.error(e.message) } finally { setBusy(false) }
  }
  const exportBn = async () => {
    try {
      const s = await api.post('/ies/bn/export', { assessment_id: assessmentId, category, ratings })
      message.success('Bayesian-network study created')
      nav(`/studies/${s.id}`)
    } catch (e: any) { message.error(e.message) }
  }

  // factor rows for the ratings table: every catalogue factor, plus un-coded evidence blocks of the selected cases
  const inCases: Record<string, string[]> = {}
  cases.forEach((c) => c.model.blocks.forEach((b: Block) => { const k = rkey(c.id, b); (inCases[k] ??= []).push(c.ref) }))
  const rows = [
    ...factors.map((f) => ({ key: `f:${f.code}`, layer: f.layer, label: f.label, code: f.code })),
    ...cases.flatMap((c) => c.model.blocks.filter((b: Block) => b.kind === 'evidence' && !b.factor).map((b: Block) => ({ key: rkey(c.id, b), layer: b.layer, label: b.label, code: `${c.ref}/${b.id}` }))),
  ]
  const rated = Object.keys(ratings).length

  const leading = bn?.leading
  const summary = (fz || bn) && <Alert type="info" showIcon style={{ marginBottom: 12 }}
    title={<span>Bayesian network: <b>{leading} {mechLabel(leading)}</b> {(100 * (bn?.posterior?.[leading] ?? 0)).toFixed(0)}% (prior {(100 * (bn?.prior?.[leading] ?? 0)).toFixed(0)}%) from {bn?.n_cases} approved cases
      {fz?.cases?.filter((c: any) => c.findings[0]?.determined).map((c: any) => {
        const best = Object.entries(c.findings[0].outputs).sort((a: any, b: any) => b[1].crisp - a[1].crisp)[0] as any
        return <span key={c.id}> · {c.ref}: {best[0]} {best[1].term}</span>
      })}</span>}
    description={<span className="small">Advisory only: the system points to similar past occurrences and to evidence worth collecting. Investigators draw the conclusions; findings do not apportion blame or liability. {results?.at && `Analysed ${results.at.replace('T', ' ')}.`}</span>} />

  return (
    <div>
      <Space style={{ marginBottom: 10 }} wrap>
        <span>Occurrence category</span>
        <Select style={{ width: 260 }} value={category} disabled={readOnly} onChange={(v) => set({ category: v, selected: [], ratings: {} })}
          options={Object.entries(meta?.categories ?? {}).map(([k, v]: any) => ({ value: k, label: v.name }))} />
        <Tag>{selected.length} case(s) selected</Tag><Tag>{rated} rating(s)</Tag>
        <Button type="primary" icon={<ExperimentOutlined />} loading={busy} onClick={run} disabled={!selected.length && !rated}>Run analysis</Button>
      </Space>
      {summary}
      <Tabs items={[
        { key: 'search', label: '1 · Occurrence & search', children: <Row gutter={12}>
          <Col xs={24} xl={9}>
            <Card size="small" title="What is known so far">
              <Input.TextArea rows={10} disabled={readOnly} value={model.narrative} onChange={(e) => set({ narrative: e.target.value })}
                placeholder="Initial notification, interviews, recordings… in your own words" />
              <Button style={{ marginTop: 8 }} icon={<SearchOutlined />} loading={busy} onClick={search}>Search the case library</Button>
              {hits?.detected_factors?.length > 0 && <div style={{ marginTop: 10 }}>
                <div className="small muted">Factors recognised in the text — suggestions, not ratings:</div>
                {hits.detected_factors.map((f: string) => <Tag key={f} style={{ marginTop: 4, cursor: readOnly ? undefined : 'pointer' }} color={ratings[`f:${f}`] ? 'green' : undefined}
                  onClick={() => !readOnly && !ratings[`f:${f}`] && rate(`f:${f}`, 'S')}>{f}{!ratings[`f:${f}`] && !readOnly ? ' + rate Support' : ''}</Tag>)}
              </div>}
              <Typography.Paragraph className="small muted" style={{ marginTop: 10, marginBottom: 0 }}>Notes</Typography.Paragraph>
              <Input.TextArea rows={3} disabled={readOnly} value={model.notes} onChange={(e) => set({ notes: e.target.value })} />
            </Card>
          </Col>
          <Col xs={24} xl={15}>
            <Card size="small" title="Similar past occurrences" extra={<span className="small muted">Tick up to 5 to compare in step 3</span>}>
              {hits ? <Table size="small" rowKey="id" dataSource={hits.results} pagination={false}
                rowSelection={readOnly ? undefined : { selectedRowKeys: selected, onChange: (k) => set({ selected: (k as number[]).slice(0, 5) }) }}
                columns={[
                  { title: 'Case', dataIndex: 'ref', width: 90, render: (v, r: any) => <a href={`/cases/${r.id}`} target="_blank" rel="noreferrer">{v}</a> },
                  { title: 'Title', dataIndex: 'title', render: (v, r: any) => <div>{v}<div>{r.matched_terms.map((t: string) => <Tag key={t} style={{ fontSize: 10.5, marginTop: 2 }}>{t}</Tag>)}</div></div> },
                  { title: 'Shared factors', dataIndex: 'matched_factors', width: 190, render: (v: string[]) => v.map((f) => <div key={f} className="mono" style={{ fontSize: 10.5 }}>{f}</div>) },
                  { title: 'Score', dataIndex: 'score', width: 120, render: (v) => <Progress percent={Math.round(v * 100)} size="small" /> },
                ]} />
                : selected.length ? <div>{cases.map((c) => <div key={c.id}><a href={`/cases/${c.id}`} target="_blank" rel="noreferrer">{c.ref}</a> {c.title}</div>)}
                  <div className="small muted" style={{ marginTop: 6 }}>Search again to change the selection.</div></div>
                  : <Empty description="Search to find similar approved cases" />}
            </Card>
          </Col>
        </Row> },
        { key: 'ratings', label: `2 · Evidence ratings (${rated})`, children: <div>
          <Alert type="info" showIcon style={{ marginBottom: 10 }} title="Rate each factor for the current occurrence"
            description="Strongly support / oppose: established by physical or recorded evidence (e.g. radar replay, RT recording, lab test). Support / oppose: from witnesses or interviews. Leave “Not provided” when unknown — the system then asks for it as a clue. A factor rated here applies to every case that uses it." />
          <Table size="small" rowKey="key" dataSource={rows} pagination={false}
            columns={[
              { title: 'Layer', dataIndex: 'layer', width: 70, render: (l) => <Tooltip title={LAYER_NAME[l]}><Tag color={LAYER_COLOR[l]} style={{ color: '#111' }}>{l}</Tag></Tooltip>,
                filters: ['O', 'R', 'L', 'I', 'E'].map((l) => ({ text: LAYER_NAME[l], value: l })), onFilter: (v, r: any) => r.layer === v },
              { title: 'Factor', dataIndex: 'label', render: (v, r: any) => <span>{v} <span className="mono muted" style={{ fontSize: 10 }}>{r.code}</span></span> },
              { title: 'In selected cases', width: 180, render: (_, r: any) => (inCases[r.key] ?? []).join(', ') },
              { title: 'BN clue', width: 80, render: (_, r: any) => r.key.startsWith('f:') && bnClue[r.code] ? <Tag color={bnClue[r.code] <= 3 ? 'volcano' : undefined}>#{bnClue[r.code]}</Tag> : null },
              { title: 'Rating', width: 180, render: (_, r: any) => <Select size="small" style={{ width: 170 }} disabled={readOnly} value={ratings[r.key] ?? 'NP'} options={RATE_OPTS} onChange={(v) => rate(r.key, v)} /> },
            ]} />
        </div> },
        { key: 'maps', label: '3 · AcciMaps (fuzzy inference)', children: selected.length === 0 ? <Empty description="Select cases in step 1" /> : <Row gutter={12}>
          <Col xs={24} xl={17}>
            {cases.map((c) => {
              const res = fz?.cases?.find((x: any) => x.id === c.id)
              const ins = inputsOf(c.model)
              return <Card key={c.id} size="small" style={{ marginBottom: 12 }} title={<span><a href={`/cases/${c.id}`} target="_blank" rel="noreferrer">{c.ref}</a> {c.title}</span>}>
                <AcciMap model={c.model} height={560} extra={(b) => (b.kind === 'evidence' || !ins[b.id].length)
                  ? <Select size="small" className="nodrag" style={{ width: '100%', marginTop: 4 }} disabled={readOnly} value={ratings[rkey(c.id, b)] ?? 'NP'} options={RATE_OPTS}
                      onChange={(v) => rate(rkey(c.id, b), v)} />
                  : <ResultBadge r={res?.blocks?.[b.id]} />} />
                {!res && <div className="small muted" style={{ marginTop: 4 }}>Run the analysis to see the inferred hypotheses and finding.</div>}
              </Card>
            })}
          </Col>
          <Col xs={24} xl={7}>
            <Card size="small" title="Clues from the past cases">
              {fz?.clues?.length ? fz.clues.map((k: any) => <div key={k.key} style={{ marginBottom: 8 }}>
                <Tag color={LAYER_COLOR[k.layer]} style={{ color: '#111' }}>{k.layer}</Tag><b>{k.label}</b>
                <div className="small muted">needed by {k.cases.map((x: any) => `${x.ref} (${x.for.join(', ')})`).join('; ')} · priority {k.priority.toFixed(2)}</div>
              </div>) : <Empty description={fz ? 'No open clues' : 'Run the analysis'} />}
            </Card>
          </Col>
        </Row> },
        { key: 'bn', label: '4 · Bayesian network & ranked clues', children: !bn ? <Empty description="Run the analysis" /> : <Row gutter={12}>
          <Col xs={24} xl={9}>
            <Card size="small" title={`Mechanism: prior vs posterior · ${bn.n_cases} cases`}
              extra={!readOnly && <Button size="small" icon={<ApartmentOutlined />} onClick={exportBn}>Open as BBN study</Button>}>
              <ReactECharts style={{ height: 300 }} option={{
                grid: { left: 190, right: 30, top: 30, bottom: 30 }, legend: { top: 0 }, tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${(v * 100).toFixed(1)}%` },
                xAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${v * 100}%` } },
                yAxis: { type: 'category', inverse: true, data: mechs.map((m) => `${m.code} ${m.label.length > 26 ? m.label.slice(0, 25) + '…' : m.label}`) },
                series: [{ name: 'Prior', type: 'bar', data: mechs.map((m) => bn.prior[m.code]), itemStyle: { color: '#C9CED6' } },
                  { name: 'Posterior', type: 'bar', data: mechs.map((m) => bn.posterior[m.code]), itemStyle: { color: '#1F3A5F' } }],
              }} />
              <div className="small muted">Uncertainty H(C | evidence) = {bn.entropy_bits} bits · evidence used: {bn.evidence_used.join(', ') || 'none'} · {bn.engine_version}</div>
            </Card>
          </Col>
          <Col xs={24} xl={15}>
            <Card size="small" title="Ranked clues — evidence worth collecting next (value of information)">
              <Table size="small" rowKey="factor" dataSource={bn.clues.slice(0, 12)} pagination={false}
                columns={[
                  { title: '#', width: 36, render: (_, __, i) => i + 1 },
                  { title: 'Factor', dataIndex: 'label', render: (v, r: any) => <span><Tag color={LAYER_COLOR[r.layer]} style={{ color: '#111' }}>{r.layer}</Tag>{v}</span> },
                  { title: 'P(yes)', dataIndex: 'p_present', width: 70, render: (v) => `${(v * 100).toFixed(0)}%` },
                  { title: 'VOI bits', dataIndex: 'voi_bits', width: 80, render: (v) => v.toFixed(3) },
                  { title: <Tooltip title="Leading mechanism if the factor is found present / absent">If yes / no</Tooltip>, width: 110, render: (_, r: any) => <span className="small">{r.if_present.mechanism} {(r.if_present.p * 100).toFixed(0)}% / {r.if_absent.mechanism} {(r.if_absent.p * 100).toFixed(0)}%</span> },
                  { title: 'Rate', width: 140, render: (_, r: any) => <Select size="small" style={{ width: 130 }} disabled={readOnly} value={ratings[`f:${r.factor}`] ?? 'NP'} options={RATE_OPTS} onChange={(v) => rate(`f:${r.factor}`, v)} /> },
                ]} />
              <div className="small muted" style={{ marginTop: 6 }}>VOI is the expected reduction in uncertainty about the mechanism if the factor were established. Collect perishable evidence first. Rate a clue, then run the analysis again.</div>
            </Card>
          </Col>
        </Row> },
      ]} />
    </div>
  )
}
