import { useEffect, useMemo, useRef, useState } from 'react'
import { Alert, App, Badge, Button, Card, Checkbox, Col, Collapse, Empty, Form, Input, List, Radio, Row, Select, Space, Switch, Table, Tabs, Tag, Tooltip, TreeSelect, Typography } from 'antd'
import { ApartmentOutlined, PlusOutlined, SendOutlined, DeleteOutlined, FileTextOutlined } from '@ant-design/icons'
import AtsbReport from './AtsbReport'
import ReactECharts from 'echarts-for-react'
import { api } from '../api'
import { useAtsbMeta, useAtsbScheme } from '../hooks'
import { RiskMatrix } from '../components/Risk'
import EditableTable, { nextId } from '../components/EditableTable'
import AcciMap, { LAYER_COLOR } from '../components/AcciMap'
import type { AModel } from '../components/AcciMap'
import type { EditorProps } from './types'

const FT: Record<string, { label: string; color: string }> = {
  contributing: { label: 'Contributing safety factor', color: '#B23A3A' }, other: { label: 'Other safety factor', color: '#D98E04' },
  positive: { label: 'Positive safety factor', color: '#3C8D5A' }, pending: { label: 'Tests pending', color: 'default' },
  not_established: { label: 'Existence not established', color: '#9CA3AF' }, not_safety_factor: { label: 'Not a safety factor', color: '#9CA3AF' },
  excluded: { label: 'Not analysed further', color: '#9CA3AF' },
}
const LEVEL_COLOR: Record<string, string> = { critical: '#B23A3A', significant: '#D98E04', broadly_acceptable: '#3C8D5A' }
const LEVEL_NAME: Record<string, string> = { critical: 'Critical', significant: 'Significant', broadly_acceptable: 'Broadly acceptable' }
const SEV_COLOR: Record<string, string> = { error: 'red', warning: 'orange', info: 'blue' }

const toDate = (t?: string) => {
  const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?(?:[ T](\d{1,2}):(\d{2}))?/.exec(t ?? '')
  return m ? Date.UTC(+m[1], +m[2] - 1, +(m[3] ?? 1), +(m[4] ?? 0), +(m[5] ?? 0)) : null
}
const toSec = (t?: string) => {
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(t ?? '')
  return m ? Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3] ?? 0) : null
}

export default function AtsbEditor({ model, setModel, results, setResults, readOnly, scheme, promote, assessmentId, studyId }: EditorProps & { assessmentId?: number; studyId?: number }) {
  const { message } = App.useApp()
  const { data: meta } = useAtsbMeta()
  const { data: atsbScheme } = useAtsbScheme()
  const [sel, setSel] = useState<string | null>(null)
  const [tab, setTab] = useState('events')
  const first = useRef(true)
  const m = { occurrence: {}, events: [], factors: [], key_findings: [], review: {}, ...model }
  const factors: any[] = m.factors
  const set = (patch: any) => setModel({ ...m, ...patch })
  const setFactor = (id: string, patch: any) => set({ factors: factors.map((f) => (f.id === id ? { ...f, ...patch } : f)) })

  useEffect(() => {
    if (first.current) { first.current = false; if (results?.engine_version) return }
    const h = setTimeout(() => { api.post('/calc/atsb', { model: m }).then(setResults).catch(() => { /* shown on next run */ }) }, 500)
    return () => clearTimeout(h)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model])

  const R = results ?? {}
  const fr = (id: string) => R.factors?.[id] ?? {}
  const taxTree = useMemo(() => {
    if (!meta) return {}
    const out: Record<string, any[]> = {}
    for (const [t, groups] of Object.entries<any>(meta.taxonomy)) {
      out[t] = groups.map((g: any) => ({ value: g.code, title: `${g.code} ${g.name}`, children: g.children.map((c: any) => ({ value: c.code, title: `${c.code} ${c.name}` })) }))
    }
    return out
  }, [meta])
  const mapModel: AModel = useMemoMap(factors, R, meta?.types ?? {})
  if (!meta) return null
  const T = meta.types
  const typeOpts = Object.entries<any>(T).map(([k, v]) => ({ value: k, label: `${v.name}` }))
  const probOpts = meta.probability.map((p: any) => ({ value: p.code, label: `${p.term}${p.lower ? ` (≥ ${p.lower}%)` : ''}` }))
  const factorOpts = factors.filter((f) => f.further !== false).map((f) => ({ value: f.id, label: `${f.id} — ${f.title}` }))
  const addFactor = (patch: any = {}) => {
    const id = nextId(factors, 'F', 1)
    set({ factors: [...factors, { id, title: '', type: 'LC', codes: [], further: true, existence: { items: [] }, influence: { items: [] }, ...patch }] })
    setSel(id); setTab('form')
    return id
  }
  const checksFor = (id: string) => (R.checks ?? []).filter((c: any) => c.ref === id)

  // ---------------------------------------------------------------- tab: occurrence & sequence of events
  const events: any[] = m.events
  const themes = [...new Set(events.map((e) => e.theme || '—'))]
  const dated = events.some((e) => toDate(e.start) !== null)
  const timed = events.map((e, i) => ({ ...e, s: dated ? (toDate(e.start) ?? null) : (toSec(e.start) ?? i * 60), e2: toSec(e.end) })).filter((e) => e.s !== null)
  const evTab = <Row gutter={12}>
    <Col xs={24} xl={17}>
      <Card size="small" title="Occurrence" style={{ marginBottom: 10 }}>
        <Form layout="vertical" size="small" disabled={readOnly}>
          <Space.Compact block>
            <Form.Item label="Reference" style={{ width: '18%' }}><Input value={m.occurrence.ref} onChange={(e) => set({ occurrence: { ...m.occurrence, ref: e.target.value } })} /></Form.Item>
            <Form.Item label="Date" style={{ width: '18%' }}><Input value={m.occurrence.date} placeholder="YYYY-MM-DD" onChange={(e) => set({ occurrence: { ...m.occurrence, date: e.target.value } })} /></Form.Item>
            <Form.Item label="Occurrence type" style={{ width: '24%' }}><Input value={m.occurrence.occurrence_type} onChange={(e) => set({ occurrence: { ...m.occurrence, occurrence_type: e.target.value } })} /></Form.Item>
            <Form.Item label="Title" style={{ width: '40%' }}><Input value={m.occurrence.title} onChange={(e) => set({ occurrence: { ...m.occurrence, title: e.target.value } })} /></Form.Item>
          </Space.Compact>
          <Form.Item label="Summary"><Input.TextArea autoSize value={m.occurrence.summary} onChange={(e) => set({ occurrence: { ...m.occurrence, summary: e.target.value } })} /></Form.Item>
        </Form>
      </Card>
      <Card size="small" title="Sequence of events list" extra={<span className="small muted">Title: subject + action verb. Estimated times: say so in comments.</span>}>
        <EditableTable readOnly={readOnly} rows={events} onChange={(rows) => set({ events: rows })} addLabel="Event" scrollX={1250}
          newRow={() => ({ id: nextId(events, 'E', 1), start: '', title: '', display: true })}
          columns={[
            { key: 'start', title: 'Start', width: 145 }, { key: 'end', title: 'End', width: 90 },
            { key: 'title', title: 'Title', width: 300, type: 'textarea' }, { key: 'comments', title: 'Comments', width: 190, type: 'textarea' },
            { key: 'source', title: 'Source', width: 140 }, { key: 'theme', title: 'Theme', width: 100 },
            { key: 'display', title: 'Chart', width: 55, type: 'bool' },
            { key: 'sf', title: 'Safety factor', width: 190, render: (e: any, i: number) => e.factor_id
              ? <Tag color="blue" style={{ cursor: 'pointer' }} onClick={() => { setSel(e.factor_id); setTab('form') }}>{e.factor_id} · {T[e.sf_type]?.name ?? ''}</Tag>
              : readOnly ? null : <Space.Compact size="small">
                <Select size="small" style={{ width: 120 }} placeholder="type" value={e.sf_type} options={meta.event_sf_types.map((k: string) => ({ value: k, label: T[k].name }))}
                  onChange={(v) => set({ events: events.map((x, j) => (j === i ? { ...x, sf_type: v, safety_factor: true } : x)) })} />
                <Button size="small" disabled={!e.sf_type} onClick={() => {
                  const id = nextId(factors, 'F', 1)
                  set({ events: events.map((x, j) => (j === i ? { ...x, safety_factor: true, factor_id: id } : x)),
                        factors: [...factors, { id, title: e.title, type: e.sf_type, codes: [], further: true, existence: { items: [] }, influence: { items: [] } }] })
                  message.success(`${id} added to the safety factors list`)
                }}>Add</Button>
              </Space.Compact> },
          ]} />
      </Card>
      {timed.filter((e) => e.display !== false).length > 0 && <Card size="small" title="Timeline" style={{ marginTop: 10 }}>
        <ReactECharts style={{ height: 80 + themes.length * 70 }} option={{
          grid: { left: 90, right: 30, top: 20, bottom: dated ? 50 : 30 }, tooltip: { formatter: (p: any) => `${p.data.t}<br/>${p.data.title}` },
          ...(dated ? { dataZoom: [{ type: 'slider', height: 14, bottom: 6 }, { type: 'inside' }] } : {}),
          xAxis: dated ? { type: 'time', scale: true }
            : { type: 'value', scale: true, axisLabel: { formatter: (v: number) => `${String(Math.floor(v / 3600) % 24).padStart(2, '0')}:${String(Math.floor(v / 60) % 60).padStart(2, '0')}` } },
          yAxis: { type: 'category', data: themes },
          series: [{ type: 'scatter', symbolSize: 12, data: timed.filter((e) => e.display !== false).map((e) => ({ value: [e.s, e.theme || '—'], t: e.start, title: e.title,
            itemStyle: { color: e.factor_id ? '#B23A3A' : '#1F3A5F' } })),
            label: { show: true, position: 'top', fontSize: 9, formatter: (p: any) => p.data.title.length > 28 ? `${p.data.title.slice(0, 27)}…` : p.data.title } }],
        }} />
        <div className="small muted">Red: events on the safety factors list.{dated && ' Dated events use a calendar axis — drag the slider to zoom into the occurrence.'}</div>
      </Card>}
    </Col>
    <Col xs={24} xl={7}>
      <Card size="small" title="Events to look for (ATSB)"><List size="small" dataSource={meta.events_to_look_for} renderItem={(x: string) => <List.Item style={{ padding: '3px 0' }}><span className="small">{x}</span></List.Item>} /></Card>
    </Col>
  </Row>

  // ---------------------------------------------------------------- tab: safety factors list
  const listTab = <div>
    <Space style={{ marginBottom: 8 }}>
      {!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => addFactor()}>Safety factor</Button>}
      {Object.entries<number>(R.counts ?? {}).map(([k, n]) => <Tag key={k} color={FT[k]?.color}>{FT[k]?.label ?? k}: {n}</Tag>)}
    </Space>
    <Table size="small" rowKey="id" pagination={false} dataSource={factors} scroll={{ x: 1200 }}
      onRow={(f: any) => ({ onDoubleClick: () => { setSel(f.id); setTab('form') } })}
      columns={[
        { title: 'ID', dataIndex: 'id', width: 55, render: (v) => <a onClick={() => { setSel(v); setTab('form') }}>{v}</a> },
        { title: 'Title', dataIndex: 'title', render: (v, f: any) => <span>{v || <i className="muted">untitled</i>}{checksFor(f.id).some((c: any) => c.severity !== 'info') && <Badge status="warning" style={{ marginLeft: 6 }} />}</span> },
        { title: 'Type', dataIndex: 'type', width: 170, render: (t) => <Tag color={LAYER_COLOR[T[t]?.level]} style={{ color: '#111' }}>{T[t]?.name ?? t}</Tag>,
          filters: Object.entries<any>(T).map(([k, v]) => ({ text: v.name, value: k })), onFilter: (v, f: any) => f.type === v },
        { title: 'Codes', dataIndex: 'codes', width: 100, render: (c: string[]) => (c ?? []).join(', ') },
        { title: 'Further analysis', dataIndex: 'further', width: 90, render: (v, f: any) => <Switch size="small" disabled={readOnly} checked={v !== false} onChange={(x) => setFactor(f.id, { further: x })} /> },
        { title: 'Existence', width: 90, render: (_, f: any) => { const e = fr(f.id).existence; return e === true ? <Tag color="green">yes</Tag> : e === false ? <Tag>no</Tag> : <span className="muted">—</span> } },
        { title: 'Finding type', width: 190, render: (_, f: any) => { const t = fr(f.id).finding_type; return t ? <Tag color={FT[t]?.color}>{FT[t]?.label}</Tag> : null },
          filters: Object.entries(FT).map(([k, v]) => ({ text: v.label, value: k })), onFilter: (v, f: any) => fr(f.id).finding_type === v },
        { title: 'Safety issue', width: 150, render: (_, f: any) => f.safety_issue ? (fr(f.id).issue_level
          ? <Tag color={LEVEL_COLOR[fr(f.id).issue_level]}>{fr(f.id).issue_level === 'broadly_acceptable' ? 'Not a safety issue' : LEVEL_NAME[fr(f.id).issue_level]}</Tag> : <Tag>potential</Tag>) : null },
        { title: 'Analysis complete', dataIndex: 'complete', width: 90, render: (v, f: any) => <Switch size="small" disabled={readOnly} checked={!!v} onChange={(x) => setFactor(f.id, { complete: x })} /> },
      ]} />
  </div>

  // ---------------------------------------------------------------- tab: safety factor form
  const f = factors.find((x) => x.id === sel)
  const formTab = !f ? <Empty description="Choose a safety factor in the list" /> : <FactorForm key={f.id} f={f} meta={meta} taxTree={taxTree} readOnly={readOnly}
    res={fr(f.id)} checks={checksFor(f.id)} probOpts={probOpts} factorOpts={factorOpts.filter((o) => o.value !== f.id)} factors={factors}
    scheme={scheme} atsbScheme={atsbScheme?.data} assessmentId={assessmentId}
    onChange={(patch: any) => setFactor(f.id, patch)} onOpen={(id: string) => setSel(id)}
    onDelete={() => { set({ factors: factors.filter((x) => x.id !== f.id), events: events.map((e) => (e.factor_id === f.id ? { ...e, factor_id: undefined } : e)) }); setSel(null) }}
    onAddExplaining={() => addFactor({ influence: { items: [], target: f.id } })} />

  // ---------------------------------------------------------------- tab: key findings
  const kfs: any[] = m.key_findings
  const kfTab = <div>
    <Alert type="info" showIcon style={{ marginBottom: 10 }} title="Basic evidence tables — required for every other key finding (Guidelines p.84)"
      description="Use them for findings that are not safety factors: resolving ambiguity, possible scenarios, intermediate findings about the reliability of evidence." />
    {kfs.map((k, i) => <Card key={k.id} size="small" style={{ marginBottom: 10 }} title={<Space>{k.id}<Tag>{meta.key_finding_kinds[k.kind] ?? k.kind}</Tag>
      {R.key_findings?.[k.id]?.supported ? <Tag color="green">supported</Tag> : R.key_findings?.[k.id]?.supported === false ? <Tag>not supported</Tag> : null}</Space>}
      extra={!readOnly && <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={() => set({ key_findings: kfs.filter((_x, j) => j !== i) })} />}>
      <Space.Compact block style={{ marginBottom: 8 }}>
        <Input disabled={readOnly} value={k.statement} placeholder="Finding statement" onChange={(e) => set({ key_findings: kfs.map((x, j) => (j === i ? { ...x, statement: e.target.value } : x)) })} />
        <Select disabled={readOnly} style={{ width: 220 }} value={k.kind} options={Object.entries<string>(meta.key_finding_kinds).map(([v, l]) => ({ value: v, label: l }))}
          onChange={(v) => set({ key_findings: kfs.map((x, j) => (j === i ? { ...x, kind: v } : x)) })} />
      </Space.Compact>
      <TestPanel t={k} meta={meta} probOpts={probOpts} readOnly={readOnly} questions={meta.set_criteria} qTitle="Evaluating the set of evidence"
        onChange={(t) => set({ key_findings: kfs.map((x, j) => (j === i ? { ...x, ...t } : x)) })} />
      <Checkbox disabled={readOnly} checked={k.add_to_key !== false} onChange={(e) => set({ key_findings: kfs.map((x, j) => (j === i ? { ...x, add_to_key: e.target.checked } : x)) })}>Add to the report's other key findings</Checkbox>
    </Card>)}
    {!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => set({ key_findings: [...kfs, { id: nextId(kfs, 'K', 1), statement: '', kind: 'other_key', items: [] }] })}>Key finding</Button>}
  </div>

  // ---------------------------------------------------------------- tab: safety factor map
  const mapTab = factors.length ? <div>
    <div className="small muted" style={{ marginBottom: 6 }}>Generated from the safety factors list: each verified influence is a link to the factor or the occurrence it influenced. Factors not analysed further are omitted.</div>
    <AcciMap model={mapModel} height={720} extra={(b) => { const r = fr(b.id); return r.finding_type ? <div style={{ marginTop: 3 }}>
      <Tag color={FT[r.finding_type]?.color} style={{ fontSize: 10 }}>{FT[r.finding_type]?.label}</Tag>
      {r.issue_level && r.issue_level !== 'broadly_acceptable' && <Tag color={LEVEL_COLOR[r.issue_level]} style={{ fontSize: 10 }}>{LEVEL_NAME[r.issue_level]} safety issue</Tag>}</div> : null }} />
  </div> : <Empty />

  // ---------------------------------------------------------------- tab: review & findings
  const F = R.findings ?? { contributing: [], other: [], other_key: [] }
  const sendIssues = async () => {
    const rows = (R.issues ?? []).filter((i: any) => i.level !== 'broadly_acceptable').map((i: any) => {
      const fx = factors.find((x) => x.id === i.id)!
      const ra = fx.risk ?? {}
      return { row_id: fx.id, title: fx.title, owner: fx.issue_owner ?? '',
        causes: (fr(fx.id).explained_by ?? []).map((x: string) => factors.find((y) => y.id === x)?.title).filter(Boolean).join('; '),
        consequences: `${ra.worst_credible ?? ''} [${LEVEL_NAME[i.level]} safety issue, ${ra.scheme === 'atsb' ? 'ATSB 6×6' : 'AirNav 5×5'} ${i.risk.index}]`,
        controls: (ra.existing_controls ?? []).map((c: any) => c.text).filter(Boolean),
        severity: ra.scheme === 'atsb' ? null : ra.consequence, likelihood: ra.scheme === 'atsb' ? null : ra.likelihood }
    })
    await promote(rows)
  }
  const rv = m.review ?? {}
  const reviewTab = <Row gutter={12}>
    <Col xs={24} xl={13}>
      <Card size="small" title="Findings (organised for the report)" style={{ marginBottom: 10 }}>
        {(['contributing', 'other', 'other_key'] as const).map((k) => <div key={k} style={{ marginBottom: 10 }}>
          <Typography.Text strong>{k === 'contributing' ? 'Contributing safety factors' : k === 'other' ? 'Other safety factors' : 'Other key findings'}</Typography.Text>
          <ol style={{ margin: '4px 0 0 18px', padding: 0 }}>{F[k].map((x: any) => <li key={x.id}><a onClick={() => { if (factors.some((y) => y.id === x.id)) { setSel(x.id); setTab('form') } }}>{x.title}</a>
            {x.safety_issue && <Tag color={LEVEL_COLOR[x.issue_level]} style={{ marginLeft: 6 }}>{LEVEL_NAME[x.issue_level]} safety issue</Tag>}
            {x.kind === 'positive' && <Tag color="green" style={{ marginLeft: 6 }}>positive</Tag>}</li>)}</ol>
          {!F[k].length && <div className="muted small">None yet</div>}
        </div>)}
      </Card>
    </Col>
    <Col xs={24} xl={11}>
      <Card size="small" title={<Space>Checks <Tag color="red">{R.check_counts?.error ?? 0}</Tag><Tag color="orange">{R.check_counts?.warning ?? 0}</Tag><Tag color="blue">{R.check_counts?.info ?? 0}</Tag></Space>} style={{ marginBottom: 10 }}>
        <div style={{ maxHeight: 360, overflow: 'auto' }}>
          {(R.checks ?? []).map((c: any, i: number) => <div key={i} style={{ marginBottom: 5 }}><Tag color={SEV_COLOR[c.severity]}>{c.code}</Tag>
            {c.ref && factors.some((x) => x.id === c.ref) ? <a className="small" onClick={() => { setSel(c.ref); setTab('form') }}>{c.message}</a> : <span className="small">{c.message}</span>}</div>)}
          {!(R.checks ?? []).length && <span className="muted">No issues found</span>}
        </div>
      </Card>
      <Card size="small" title="Analysis review (Guidelines pp.185–189)">
        {meta.review_checklist.map((c: any) => <div key={c.key} style={{ marginBottom: 6 }}>
          <Checkbox disabled={readOnly} checked={!!rv[c.key]} onChange={(e) => set({ review: { ...rv, [c.key]: e.target.checked } })}>
            <span className="small"><b>{c.group}:</b> {c.text}</span></Checkbox>
          {c.key === 'sufficiency' && <div className="small muted" style={{ marginLeft: 24 }}>{(R.checks ?? []).filter((x: any) => x.code === 'sufficiency').length} factor(s) flagged by the automatic test</div>}
          {c.key === 'fair_individual' && <div className="small muted" style={{ marginLeft: 24 }}>{(R.checks ?? []).filter((x: any) => x.code === 'fairness').length} individual action(s) without identified reasons</div>}
        </div>)}
        <Form.Item label="Stop rule — where and why the analysis stopped" layout="vertical" style={{ marginTop: 8 }}>
          <Input.TextArea disabled={readOnly} autoSize value={m.stop_rule} onChange={(e) => set({ stop_rule: e.target.value })} />
        </Form.Item>
      </Card>
    </Col>
    <Col xs={24} style={{ marginTop: 10 }}>
        <Card size="small" title="Safety issues" extra={!readOnly && <Button size="small" icon={<SendOutlined />} disabled={!(R.issues ?? []).some((i: any) => i.level !== 'broadly_acceptable')} onClick={sendIssues}>Send to hazard log</Button>}>
        <Table size="small" rowKey="id" pagination={false} dataSource={R.issues ?? []} columns={[
          { title: 'Safety issue', dataIndex: 'title', render: (v, i: any) => <a onClick={() => { setSel(i.id); setTab('form') }}>{v}</a> },
          { title: 'Risk', width: 120, render: (_, i: any) => <Tag color={i.risk.color}>{LEVEL_NAME[i.level]} · {i.risk.index}</Tag> },
          { title: 'Owner', dataIndex: 'owner', width: 140 },
          { title: 'Status', dataIndex: 'status', width: 130, render: (s) => meta.issue_status[s] },
          { title: 'Evaluation', dataIndex: 'evaluation', width: 120, render: (v) => v === 'no_further' ? <Tag color="green">no further action</Tag> : v === 'further' ? <Tag color="orange">further action</Tag> : '—' },
          { title: 'Follow-up', width: 100, render: (_, i: any) => fr(i.id).follow_up_due ?? '—' },
        ]} />
        <div className="small muted" style={{ marginTop: 6 }}>AirNav-rated issues go to the hazard log with their 5×5 rating; ATSB-rated issues carry the 6×6 rating in the consequence text, to be rated on the AirNav scheme in the log.</div>
      </Card>
    </Col>
  </Row>

  return <div>
    <Space style={{ marginBottom: 10 }} wrap>
      <Tag color="#1F3A5F">{m.occurrence.ref || 'Occurrence'}</Tag><span>{m.occurrence.title}</span>
      {Object.entries<number>(R.counts ?? {}).filter(([k]) => ['contributing', 'other', 'positive'].includes(k)).map(([k, n]) => <Tag key={k} color={FT[k].color}>{n} {FT[k].label.toLowerCase()}</Tag>)}
      {(R.issues ?? []).filter((i: any) => i.level !== 'broadly_acceptable').length > 0 && <Tag color="#D98E04">{(R.issues ?? []).filter((i: any) => i.level !== 'broadly_acceptable').length} safety issue(s)</Tag>}
      <span className="small muted">{R.engine_version}</span>
    </Space>
    <Tabs activeKey={tab} onChange={setTab} items={[
      { key: 'events', label: '1 · Occurrence & sequence of events', children: evTab },
      { key: 'list', label: `2 · Safety factors (${factors.length})`, children: listTab },
      { key: 'form', label: '3 · Safety factor form', children: formTab },
      { key: 'key', label: `4 · Other key findings (${kfs.length})`, children: kfTab },
      { key: 'map', label: <span><ApartmentOutlined /> 5 · Safety factor map</span>, children: mapTab },
      { key: 'review', label: <span>6 · Review & findings {(R.check_counts?.error ?? 0) + (R.check_counts?.warning ?? 0) > 0 && <Badge count={(R.check_counts?.error ?? 0) + (R.check_counts?.warning ?? 0)} size="small" />}</span>, children: reviewTab },
      { key: 'report', label: <span><FileTextOutlined /> 7 · Investigation report</span>, children: <AtsbReport m={m} set={set} meta={meta} readOnly={readOnly} studyId={studyId} /> },
    ]} />
  </div>
}

function useMemoMap(factors: any[], R: any, T: any): AModel {
  return useMemo(() => {
    const fs = factors.filter((f) => f.further !== false && T[f.type])
    const blocks: any[] = fs.map((f) => ({ id: f.id, layer: T[f.type].level, kind: f.type === 'OE' ? 'finding' : 'evidence', kindLabel: T[f.type].name, label: f.title, factor: (f.codes ?? []).join(', ') || null }))
    const edges: any[] = []
    if (fs.some((f) => f.influence?.target === 'occurrence')) blocks.push({ id: 'occurrence', layer: 'E', kind: 'finding', kindLabel: 'Occurrence', label: 'The occurrence', factor: null })
    for (const f of fs) {
      const t = f.influence?.target
      if (t && blocks.some((b) => b.id === t) && R.factors?.[f.id]?.influence) edges.push({ source: f.id, target: t, role: 'input' })
      else if (t && blocks.some((b) => b.id === t)) edges.push({ source: f.id, target: t, role: 'context' })
    }
    return { blocks, edges }
  }, [factors, R, T])
}

function TestPanel({ t, meta, probOpts, readOnly, questions, qTitle, onChange, extra }: { t: any; meta: any; probOpts: any[]; readOnly: boolean; questions: string[]; qTitle: string; onChange: (t: any) => void; extra?: React.ReactNode }) {
  const items: any[] = t?.items ?? []
  const n = items.reduce((a: any, i: any) => ({ ...a, [i.rating]: (a[i.rating] ?? 0) + 1 }), {})
  return <Row gutter={10}>
    <Col xs={24} xl={17}>
      {extra}
      <EditableTable readOnly={readOnly} rows={items} onChange={(rows) => onChange({ ...t, items: rows })} addLabel="Evidence item" scrollX={1100}
        newRow={() => ({ id: nextId(items, 'i', 1), text: '', rating: 'supports', etype: 'tangible', relevance: 'direct' })}
        columns={[
          { key: 'text', title: 'Item of evidence', width: 260, type: 'textarea' }, { key: 'comments', title: 'Evaluative comments', width: 200, type: 'textarea' },
          { key: 'source', title: 'Source', width: 130 },
          { key: 'rating', title: 'Supports?', width: 105, type: 'select', options: Object.entries<string>(meta.item_ratings).map(([v, l]) => ({ value: v, label: l })) },
          { key: 'etype', title: 'Type', width: 110, type: 'select', options: Object.keys(meta.evidence_types).map((v) => ({ value: v, label: v })) },
          { key: 'relevance', title: 'Relevance', width: 115, type: 'select', options: Object.keys(meta.relevance).map((v) => ({ value: v, label: v })) },
          { key: 'concerns', title: 'Credibility concerns', width: 140, type: 'multiselect', options: meta.credibility },
          { key: 'expectation', title: 'Expected?', width: 150, type: 'select', options: Object.entries<string>(meta.expectation).filter(([v]) => v).map(([v, l]) => ({ value: v, label: l })) },
        ]} />
      <div className="small muted" style={{ margin: '4px 0 8px' }}>{n.supports ?? 0} supports · {n.opposes ?? 0} opposes · {n.no_effect ?? 0} no effect · {n.unsure ?? 0} unsure — the conclusion is a judgement on the whole pattern, not a count.</div>
      <Space wrap>
        <Radio.Group disabled={readOnly} value={t?.conclusion ?? ''} onChange={(e) => onChange({ ...t, conclusion: e.target.value })} optionType="button" size="small"
          options={[{ value: 'supported', label: 'Supported' }, { value: 'not_supported', label: 'Not supported' }, { value: '', label: 'Undecided' }]} />
        <Select disabled={readOnly} size="small" style={{ width: 240 }} placeholder="Probability expression" allowClear value={t?.probability} options={probOpts} onChange={(v) => onChange({ ...t, probability: v })} />
      </Space>
      <Input.TextArea disabled={readOnly} style={{ marginTop: 6 }} autoSize placeholder="Summary of the argument" value={t?.summary} onChange={(e) => onChange({ ...t, summary: e.target.value })} />
    </Col>
    <Col xs={24} xl={7}>
      <Collapse size="small" defaultActiveKey={['q']} items={[{ key: 'q', label: qTitle, children: <ul style={{ paddingLeft: 16, margin: 0 }}>{questions.map((q) => <li key={q} className="small">{q}</li>)}</ul> },
        { key: 'c', label: 'Evaluating an item of evidence', children: <ul style={{ paddingLeft: 16, margin: 0 }}>{meta.item_criteria.map((q: string) => <li key={q} className="small">{q}</li>)}</ul> }]} />
    </Col>
  </Row>
}

function FactorForm({ f, meta, taxTree, readOnly, res, checks, probOpts, factorOpts, factors, scheme, atsbScheme, assessmentId, onChange, onOpen, onDelete, onAddExplaining }: any) {
  const { message } = App.useApp()
  const T = meta.types
  const tm = T[f.type] ?? {}
  const ra = f.risk ?? {}
  const ev = f.evaluation ?? {}
  const sch = ra.scheme === 'atsb' ? atsbScheme : scheme
  const schForMatrix = ra.scheme === 'atsb' && atsbScheme ? { ...atsbScheme, severity: atsbScheme.severity.map((s: any) => ({ ...s, name: s.short ?? s.name })) } : scheme
  const hints = (f.codes ?? []).map((c: string) => meta.coding_hints[c] && <div key={c} className="small"><b>{c}</b>: {meta.coding_hints[c]}</div>).filter(Boolean)
  const actions: any[] = f.actions ?? []
  const classOpts = Object.entries<string[]>(meta.action_classes).flatMap(([k, subs]) => (subs.length ? subs.map((s) => `${k}: ${s}`) : [k]))
  const track = async (a: any, i: number) => {
    try {
      const r = await api.post('/actions', { text: `[${f.id}] ${a.description}`, owner: a.organisation ?? '', assessment_id: assessmentId })
      onChange({ actions: actions.map((x, j) => (j === i ? { ...x, action_ref: r.ref } : x)) })
      message.success(`Tracked as ${r.ref}`)
    } catch (e: any) { message.error(e.message) }
  }
  const define = <Row gutter={12}>
    <Col xs={24} xl={15}>
      <Form layout="vertical" size="small" disabled={readOnly}>
        <Form.Item label="Title (complete sentence: subject + verb; neutral; one factor)"><Input.TextArea autoSize value={f.title} onChange={(e) => onChange({ title: e.target.value })} /></Form.Item>
        <Space.Compact block>
          <Form.Item label="Safety factor type" style={{ width: '40%' }}><Select value={f.type} onChange={(v) => onChange({ type: v, codes: [], safety_issue: T[v]?.issue_allowed ? f.safety_issue : false })}
            options={Object.entries<any>(T).map(([k, v]) => ({ value: k, label: v.name }))} /></Form.Item>
          <Form.Item label="ATSB safety factor type codes (multiple allowed)" style={{ width: '60%' }}>
            <TreeSelect multiple treeDefaultExpandAll={false} showSearch treeNodeFilterProp="title" value={f.codes ?? []} treeData={taxTree[f.type] ?? []}
              onChange={(v) => onChange({ codes: v })} placeholder={f.type === 'OE' ? 'Coded as an occurrence type' : 'Choose codes'} disabled={readOnly || f.type === 'OE'} />
          </Form.Item>
        </Space.Compact>
        <div className="small muted" style={{ marginTop: -6, marginBottom: 8 }}>{tm.hint}</div>
        {hints.length > 0 && <Alert type="info" style={{ marginBottom: 8 }} title="Coding guidance" description={hints} />}
        <Form.Item label="Description (context, where, when, extent; what it is not)"><Input.TextArea autoSize={{ minRows: 2 }} value={f.description} onChange={(e) => onChange({ description: e.target.value })} /></Form.Item>
        <Space.Compact block>
          {['IA', 'PA'].includes(f.type) && <>
            <Form.Item label="Individual's role" style={{ width: '50%' }}><Select allowClear value={f.role} options={meta.roles.map((r: string) => ({ value: r, label: r }))} onChange={(v) => onChange({ role: v })} /></Form.Item>
            {f.type === 'IA' && <Form.Item label="Error type" style={{ width: '50%' }}><Select allowClear value={f.error_type} options={Object.entries<string>(meta.error_types).map(([v, l]) => ({ value: v, label: l }))} onChange={(v) => onChange({ error_type: v })} /></Form.Item>}
          </>}
          {!['IA', 'PA', 'OE'].includes(f.type) && <Form.Item label="Functional area" style={{ width: '50%' }}><Select allowClear value={f.functional_area} options={meta.functional_areas.map((r: string) => ({ value: r, label: r }))} onChange={(v) => onChange({ functional_area: v })} /></Form.Item>}
          {f.type === 'RC' && <Form.Item label="Control function" style={{ width: '50%' }}><Select allowClear value={f.control_function} options={[{ value: 'preventive', label: 'Preventive' }, { value: 'recovery', label: 'Recovery' }]} onChange={(v) => onChange({ control_function: v })} /></Form.Item>}
          {f.type === 'OI' && <Form.Item label="Influence" style={{ width: '50%' }}><Select allowClear value={f.influence_kind} options={[{ value: 'internal', label: 'Internal organisational condition' }, { value: 'external', label: 'External influence' }]} onChange={(v) => onChange({ influence_kind: v })} /></Form.Item>}
        </Space.Compact>
        {['IA', 'PA'].includes(f.type) && <Form.Item label="Why did the action make sense to the person at the time? (local rationality — no blame)">
          <Input.TextArea autoSize={{ minRows: 2 }} value={f.rationale} placeholder="e.g. a routine task done many times; the procedure did not ask for a check; planning the next task"
            onChange={(e) => onChange({ rationale: e.target.value })} /></Form.Item>}
        <Space wrap style={{ marginBottom: 8 }}>
          <Tooltip title={tm.issue_allowed ? 'Characteristic of an organisation or system that can affect future operations' : 'Only local conditions, risk controls and organisational influences can be safety issues'}>
            <Checkbox disabled={readOnly || !tm.issue_allowed} checked={!!f.safety_issue} onChange={(e) => onChange({ safety_issue: e.target.checked })}>Potential safety issue</Checkbox>
          </Tooltip>
          {f.safety_issue && <Input size="small" style={{ width: 260 }} placeholder="Safety issue owner (organisation)" value={f.issue_owner} onChange={(e) => onChange({ issue_owner: e.target.value })} />}
          <Checkbox disabled={readOnly} checked={f.further !== false} onChange={(e) => onChange({ further: e.target.checked })}>Analyse further</Checkbox>
        </Space>
        {f.further === false && <Space.Compact block>
          <Form.Item label="Reason" style={{ width: '45%' }}><Select value={f.exclusion_reason} options={meta.exclusion_reasons.map((r: string) => ({ value: r, label: r }))} onChange={(v) => onChange({ exclusion_reason: v })} /></Form.Item>
          <Form.Item label="Justification" style={{ width: '55%' }}><Input value={f.further_justification} onChange={(e) => onChange({ further_justification: e.target.value })} /></Form.Item>
        </Space.Compact>}
      </Form>
      {!readOnly && <Button size="small" danger icon={<DeleteOutlined />} onClick={onDelete}>Delete factor</Button>}
    </Col>
    <Col xs={24} xl={9}>
      <Card size="small" title={`Questions — ${tm.name ?? ''}`}><ul style={{ paddingLeft: 16, margin: 0 }}>{(meta.level_questions[tm.level] ?? []).map((q: string) => <li key={q} className="small">{q}</li>)}</ul>
        <div className="small muted" style={{ marginTop: 6 }}>Focused questions: what increased its likelihood or magnitude? what could have reduced it, detected or corrected it, or prevented the effects?</div></Card>
    </Col>
  </Row>
  const influenceTarget = <Space style={{ marginBottom: 8 }}>
    <span>Factor influenced:</span>
    <Select disabled={readOnly} style={{ width: 460 }} value={f.influence?.target} placeholder="The occurrence or another safety factor" allowClear
      options={[{ value: 'occurrence', label: 'The occurrence (its likelihood or consequences)' }, ...factorOpts]} onChange={(v) => onChange({ influence: { ...(f.influence ?? {}), target: v } })} />
  </Space>
  const explaining = (res.explained_by ?? []).map((id: string) => factors.find((x: any) => x.id === id)).filter(Boolean)
  const tabs: any[] = [
    { key: 'define', label: 'Define', children: define },
    { key: 'exist', label: <span>Existence {res.existence === true ? <Tag color="green">yes</Tag> : res.existence === false ? <Tag>no</Tag> : null}</span>,
      children: <TestPanel t={f.existence} meta={meta} probOpts={probOpts} readOnly={readOnly} questions={meta.existence_q} qTitle="Test for existence" onChange={(t: any) => onChange({ existence: t })}
        extra={<div className="small muted" style={{ marginBottom: 6 }}>Did the potential safety factor exist (or probably exist)? Standard of proof: likely (≥ 66%). Absence of evidence is not evidence of absence.</div>} /> },
    { key: 'infl', label: <span>Influence {res.influence === true ? <Tag color="green">yes</Tag> : res.influence === false ? <Tag>no</Tag> : null}</span>, disabled: res.existence === false,
      children: <TestPanel t={f.influence} meta={meta} probOpts={probOpts} readOnly={readOnly} questions={meta.influence_q} qTitle="Test for influence" onChange={(t: any) => onChange({ influence: t })} extra={influenceTarget} /> },
    { key: 'imp', label: <span>Importance {res.importance === true ? <Tag color="green">yes</Tag> : res.importance === false ? <Tag>no</Tag> : null}</span>, disabled: !(res.existence && res.influence === false),
      children: <Row gutter={10}><Col xs={24} xl={16}>
        <div className="small muted" style={{ marginBottom: 6 }}>Influence was not shown. Is the factor still worth analysing further? (Not itself a risk analysis.)</div>
        <Radio.Group disabled={readOnly} value={f.importance?.passed ?? null} onChange={(e) => onChange({ importance: { ...(f.importance ?? {}), passed: e.target.value } })} optionType="button" size="small"
          options={[{ value: true, label: 'Important — other safety factor' }, { value: false, label: 'Not important' }, { value: null, label: 'Undecided' }]} />
        <Input.TextArea disabled={readOnly} style={{ marginTop: 8 }} autoSize={{ minRows: 3 }} placeholder="Justification" value={f.importance?.justification} onChange={(e) => onChange({ importance: { ...(f.importance ?? {}), justification: e.target.value } })} />
      </Col><Col xs={24} xl={8}><Card size="small" title="Test for importance"><ul style={{ paddingLeft: 16, margin: 0 }}>{meta.importance_q.map((q: string) => <li key={q} className="small">{q}</li>)}</ul></Card></Col></Row> },
    { key: 'explain', label: `Explain (${explaining.length})`, children: <div>
      <div className="small muted" style={{ marginBottom: 6 }}>Factors whose verified influence is on this factor. Ask the focused questions to find more; each new one starts on the safety factors list.</div>
      <List size="small" bordered dataSource={explaining} renderItem={(x: any) => <List.Item><a onClick={() => onOpen(x.id)}>{x.id} — {x.title}</a><Tag>{T[x.type]?.name}</Tag></List.Item>} />
      {!readOnly && <Button size="small" icon={<PlusOutlined />} style={{ marginTop: 8 }} onClick={onAddExplaining}>Add an explaining factor</Button>}
      <Form.Item label="Sufficiency note (if no further explaining factor will be sought)" layout="vertical" style={{ marginTop: 10 }}>
        <Input.TextArea disabled={readOnly} autoSize value={f.sufficiency_note} onChange={(e) => onChange({ sufficiency_note: e.target.value })} />
      </Form.Item>
    </div> },
  ]
  if (f.safety_issue) {
    tabs.push({ key: 'risk', label: <span>Risk analysis {res.issue_level && <Tag color={LEVEL_COLOR[res.issue_level]}>{LEVEL_NAME[res.issue_level]}</Tag>}</span>, children: <Row gutter={12}>
      <Col xs={24} xl={13}>
        <Form layout="vertical" size="small" disabled={readOnly}>
          <Form.Item label="1. Worst possible scenario (ignoring controls)"><Input.TextArea autoSize value={ra.worst_possible} onChange={(e) => onChange({ risk: { ...ra, worst_possible: e.target.value } })} /></Form.Item>
          <Form.Item label="2. Existing risk controls and their effectiveness">
            <EditableTable readOnly={readOnly} rows={ra.existing_controls ?? []} onChange={(rows) => onChange({ risk: { ...ra, existing_controls: rows } })} newRow={() => ({ text: '', effectiveness: '' })} addLabel="Control"
              columns={[{ key: 'text', title: 'Control', type: 'textarea', width: 220 }, { key: 'effectiveness', title: 'Effectiveness', type: 'textarea', width: 220 }]} />
          </Form.Item>
          <Form.Item label="3. Worst credible scenario (allow one more control failure, not several)"><Input.TextArea autoSize value={ra.worst_credible} onChange={(e) => onChange({ risk: { ...ra, worst_credible: e.target.value } })} /></Form.Item>
          <Form.Item label="Consequence justification"><Input.TextArea autoSize value={ra.consequence_justification} onChange={(e) => onChange({ risk: { ...ra, consequence_justification: e.target.value } })} /></Form.Item>
          <Form.Item label="Likelihood justification (exposure × probability; compare with data)"><Input.TextArea autoSize value={ra.likelihood_justification} onChange={(e) => onChange({ risk: { ...ra, likelihood_justification: e.target.value } })} /></Form.Item>
        </Form>
      </Col>
      <Col xs={24} xl={11}>
        <Radio.Group disabled={readOnly} size="small" optionType="button" value={ra.scheme ?? 'airnav'} style={{ marginBottom: 8 }}
          onChange={(e) => onChange({ risk: { ...ra, scheme: e.target.value, consequence: null, likelihood: null, sensitivity: {} }, evaluation: { ...ev, residual: {} } })}
          options={[{ value: 'airnav', label: 'AirNav 5×5' }, { value: 'atsb', label: 'ATSB 6×6 (option)' }]} />
        <div className="small" style={{ marginBottom: 4 }}>4–6. Consequence × likelihood — click a cell</div>
        <RiskMatrix scheme={schForMatrix} value={{ severity: ra.consequence, likelihood: ra.likelihood }} disabled={readOnly} size={40}
          onChange={(v: any) => onChange({ risk: { ...ra, consequence: v.severity, likelihood: v.likelihood } })} />
        {res.risk && !res.risk.error && <Alert style={{ marginTop: 8 }} type={res.issue_level === 'broadly_acceptable' ? 'success' : 'warning'} showIcon
          title={ra.scheme === 'atsb' ? `${res.risk.index} · ${res.risk.region_name}` : `${res.risk.index} · ${res.risk.region_name} → ${LEVEL_NAME[res.issue_level]}${res.issue_level === 'broadly_acceptable' ? ' (not a safety issue)' : ' safety issue'}`}
          description={<span className="small">{res.risk.action}{sch?.severity && ` Consequence: ${sch.severity.find((s: any) => s.code === ra.consequence)?.name}.`}</span>} />}
        <div className="small" style={{ margin: '10px 0 4px' }}>Sensitivity: an alternative rating if the team is uncertain</div>
        <RiskMatrix scheme={schForMatrix} value={{ severity: ra.sensitivity?.consequence, likelihood: ra.sensitivity?.likelihood }} disabled={readOnly} size={26}
          onChange={(v: any) => onChange({ risk: { ...ra, sensitivity: { consequence: v.severity, likelihood: v.likelihood } } })} />
        {res.sensitivity && !res.sensitivity.error && <div className="small" style={{ marginTop: 4 }}>Alternative: <Tag color={res.sensitivity.color}>{res.sensitivity.index}</Tag>{LEVEL_NAME[res.sensitivity.issue_level]}</div>}
      </Col>
    </Row> })
  }
  if (f.further !== false) {
    tabs.push({ key: 'action', label: `Safety / corrective action (${actions.length})`, children: <div>
      {!f.safety_issue && <div className="small muted" style={{ marginBottom: 8 }}>Corrective actions for every contributing factor feed Section 5 of the investigation report, ranked by the hierarchy of controls.</div>}
      {f.safety_issue && <Space style={{ marginBottom: 8 }} wrap>
        <span>Safety issue status</span>
        <Select disabled={readOnly} size="small" style={{ width: 210 }} value={f.issue_status ?? 'pending'} options={Object.entries<string>(meta.issue_status).map(([v, l]) => ({ value: v, label: l }))} onChange={(v) => onChange({ issue_status: v })} />
        {res.follow_up_due && <Tag color={res.follow_up_due < new Date().toISOString().slice(0, 10) ? 'red' : 'blue'}>follow-up due {res.follow_up_due}</Tag>}
      </Space>}
      {actions.map((a, i) => <Card key={a.id ?? i} size="small" style={{ marginBottom: 8 }} title={<Space>{a.id}<Tag>{meta.action_kinds[a.kind]?.split(' (')[0]}</Tag>{a.action_ref && <Tag color="blue">{a.action_ref}</Tag>}</Space>}
        extra={!readOnly && <Space>{!a.action_ref && <Button size="small" onClick={() => track(a, i)}>Track in Actions</Button>}
          <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={() => onChange({ actions: actions.filter((_x, j) => j !== i) })} /></Space>}>
        <Form layout="vertical" size="small" disabled={readOnly}>
          <Space.Compact block>
            <Form.Item label="Kind" style={{ width: '30%' }}><Select value={a.kind} options={Object.entries<string>(meta.action_kinds).map(([v, l]) => ({ value: v, label: l.split(' (')[0] }))} onChange={(v) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, kind: v } : x)) })} /></Form.Item>
            <Form.Item label="Organisation" style={{ width: '30%' }}><Input value={a.organisation} onChange={(e) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, organisation: e.target.value } : x)) })} /></Form.Item>
            <Form.Item label="Notified on" style={{ width: '20%' }}><Input value={a.notified_on} placeholder="YYYY-MM-DD" onChange={(e) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, notified_on: e.target.value } : x)) })} /></Form.Item>
            <Form.Item label="Status" style={{ width: '20%' }}><Select value={a.status} options={Object.entries<string>(meta.action_status).map(([v, l]) => ({ value: v, label: l }))} onChange={(v) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, status: v } : x)) })} /></Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item label="Hierarchy of controls" style={{ width: '35%' }}><Select allowClear value={a.hierarchy} options={(meta.hierarchy ?? []).map((h: any) => ({ value: h.key, label: <Tooltip title={h.hint}>{h.name}</Tooltip> }))} onChange={(v) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, hierarchy: v } : x)) })} /></Form.Item>
            <Form.Item label="Target date" style={{ width: '20%' }}><Input value={a.target_date} placeholder="YYYY-MM-DD" onChange={(e) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, target_date: e.target.value } : x)) })} /></Form.Item>
            <Form.Item label="Reference (e.g. recommendation number)" style={{ width: '45%' }}><Input value={a.ref} onChange={(e) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, ref: e.target.value } : x)) })} /></Form.Item>
          </Space.Compact>
          <Form.Item label="Safety action"><Input.TextArea autoSize value={a.description} onChange={(e) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)) })} /></Form.Item>
          <Form.Item label="Classification (coded at closure; several allowed)"><Select mode="multiple" value={a.classes ?? []} options={classOpts.map((c) => ({ value: c, label: c }))} onChange={(v) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, classes: v } : x)) })} /></Form.Item>
          <Form.Item label="Communication log">
            <EditableTable readOnly={readOnly} rows={a.log ?? []} onChange={(rows) => onChange({ actions: actions.map((x, j) => (j === i ? { ...x, log: rows } : x)) })} newRow={() => ({ date: new Date().toISOString().slice(0, 10), text: '' })} addLabel="Entry"
              columns={[{ key: 'date', title: 'Date', width: 110 }, { key: 'text', title: 'Communication', type: 'textarea', width: 380 }]} />
          </Form.Item>
        </Form>
      </Card>)}
      {!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => onChange({ actions: [...actions, { id: nextId(actions, 'A', 1), kind: 'org', status: 'proposed', log: [] }] })}>Safety action</Button>}
      {f.safety_issue && <Card size="small" title="Evaluate the safety action" style={{ marginTop: 10 }}>
        <Row gutter={12}><Col xs={24} xl={10}>
          <div className="small" style={{ marginBottom: 4 }}>Residual risk after the action</div>
          <RiskMatrix scheme={schForMatrix} value={{ severity: ev.residual?.consequence, likelihood: ev.residual?.likelihood }} disabled={readOnly} size={32}
            onChange={(v: any) => onChange({ evaluation: { ...ev, residual: { consequence: v.severity, likelihood: v.likelihood } } })} />
          <Checkbox disabled={readOnly} style={{ marginTop: 6 }} checked={!!ev.alarp} onChange={(e) => onChange({ evaluation: { ...ev, alarp: e.target.checked } })}>Residual risk is as low as reasonably practicable</Checkbox>
          {res.residual && !res.residual.error && <div style={{ marginTop: 6 }}><Tag color={res.residual.color}>{res.residual.index}</Tag>{LEVEL_NAME[res.residual.issue_level]} →{' '}
            {res.action_evaluation === 'no_further' ? <Tag color="green">No further action required</Tag> : <Tag color="orange">Further action required</Tag>}</div>}
        </Col><Col xs={24} xl={14}>
          <div className="small" style={{ marginBottom: 4 }}>Test for practicability</div>
          {meta.practicability.map((p: any) => <Input.TextArea key={p.key} disabled={readOnly} autoSize style={{ marginBottom: 4 }} placeholder={p.text} value={ev.practicability?.[p.key]}
            onChange={(e) => onChange({ evaluation: { ...ev, practicability: { ...(ev.practicability ?? {}), [p.key]: e.target.value } } })} />)}
        </Col></Row>
      </Card>}
    </div> })
  }
  return <div>
    <Space style={{ marginBottom: 8 }} wrap>
      <Tag color="#1F3A5F">{f.id}</Tag><b>{f.title || 'Untitled'}</b>
      <Tag color={LAYER_COLOR[tm.level]} style={{ color: '#111' }}>{tm.name}</Tag>
      {res.finding_type && <Tag color={FT[res.finding_type]?.color}>{FT[res.finding_type]?.label}</Tag>}
      {f.safety_issue && <Tag color={res.issue_level ? LEVEL_COLOR[res.issue_level] : undefined}>{res.issue_level ? `${LEVEL_NAME[res.issue_level]}${res.issue_level === 'broadly_acceptable' ? '' : ' safety issue'}` : 'potential safety issue'}</Tag>}
    </Space>
    {checks.length > 0 && <Alert type={checks.some((c: any) => c.severity === 'error') ? 'error' : 'warning'} showIcon style={{ marginBottom: 8 }}
      title={`${checks.length} check(s)`} description={<ul style={{ margin: 0, paddingLeft: 16 }}>{checks.map((c: any, i: number) => <li key={i} className="small">{c.message}</li>)}</ul>} />}
    <Tabs size="small" items={tabs} />
  </div>
}
