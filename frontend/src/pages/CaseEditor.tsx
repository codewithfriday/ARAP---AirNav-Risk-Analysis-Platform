import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Descriptions, Empty, Form, Input, InputNumber, Row, Select, Space, Spin, Table, Tabs, Tag, Tooltip, Typography } from 'antd'
import { CheckCircleOutlined, DeleteOutlined, ExperimentOutlined, PlusOutlined, SaveOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Link, useNavigate, useParams, useBlocker } from 'react-router-dom'
import { api } from '../api'
import { canEdit, isAdmin, useAuth } from '../store'
import AcciMap, { LAYERS, LAYER_COLOR, LAYER_NAME, PROB_COLOR, PROB_LABEL, PROB_TERMS, SUPPORT_COLOR, SUPPORT_LABEL, SUPPORT_TERMS, edgeId } from '../components/AcciMap'
import type { AModel, Block } from '../components/AcciMap'
import { useIesMeta } from './CaseLibrary'

const supportOpts = SUPPORT_TERMS.map((t) => ({ value: t, label: SUPPORT_LABEL[t] }))
const probOpts = PROB_TERMS.map((t) => ({ value: t, label: PROB_LABEL[t] }))

export function inputsOf(m: AModel): Record<string, string[]> {
  const ins: Record<string, string[]> = {}
  m.blocks.forEach((b) => { ins[b.id] = [] })
  m.edges.forEach((e) => { if ((e.role ?? 'input') === 'input' && ins[e.target]) ins[e.target].push(e.source) })
  return ins
}

export function ResultBadge({ r, mechLabel }: { r: any; mechLabel?: (m: string) => string }) {
  if (!r) return null
  if (r.kind === 'hypothesis') return r.determined
    ? <Tag color={SUPPORT_COLOR[r.term]} style={{ marginTop: 4 }}>{SUPPORT_LABEL[r.term]} · {r.crisp?.toFixed(1)}</Tag>
    : <Tag style={{ marginTop: 4 }}>not determined</Tag>
  if (r.kind === 'finding') {
    if (!r.determined) return <Tag style={{ marginTop: 4 }}>not determined</Tag>
    const outs = Object.entries(r.outputs ?? {}).filter(([, o]: any) => o.crisp !== null).sort((a: any, b: any) => b[1].crisp - a[1].crisp).slice(0, 3)
    return <div style={{ marginTop: 4 }}>{outs.map(([m, o]: any) => <div key={m}><Tag color={PROB_COLOR[o.term]} style={{ marginBottom: 2 }}>{m} {PROB_LABEL[o.term]} · {o.crisp.toFixed(1)}</Tag>
      {mechLabel && <span className="small muted">{mechLabel(m)}</span>}</div>)}</div>
  }
  return null
}

export default function CaseEditor() {
  const { id } = useParams()
  const user = useAuth((s) => s.user)
  const nav = useNavigate()
  const qc = useQueryClient()
  const { message, modal } = App.useApp()
  const { data: meta } = useIesMeta()
  const { data: c, refetch } = useQuery({ queryKey: ['case', id], queryFn: () => api.get(`/cases/${id}`) })
  const [doc, setDoc] = useState<any>(null)
  const [dirty, setDirty] = useState(false)
  const [sel, setSel] = useState<string | null>(null)
  const [selEdge, setSelEdge] = useState<string | null>(null)
  const [test, setTest] = useState<Record<string, string | null>>({})
  const [testRes, setTestRes] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (c) { setDoc(c); setDirty(false) } }, [c])
  const blocker = useBlocker(dirty)
  useEffect(() => {
    if (blocker.state === 'blocked') modal.confirm({ title: 'Unsaved changes', content: 'Leave without saving?', onOk: () => blocker.proceed(), onCancel: () => blocker.reset() })
  }, [blocker, modal])
  const model: AModel = doc?.model ?? { blocks: [], edges: [] }
  const ins = useMemo(() => inputsOf(model), [model])
  if (!doc || !meta) return <Spin />
  const cat = meta.categories[doc.category]
  const factors: any[] = cat?.factors ?? []
  const mechs: any[] = cat?.mechanisms ?? []
  const editable = canEdit(user)
  const set = (patch: any) => { setDoc({ ...doc, ...patch }); setDirty(true) }
  const setModel = (m: AModel) => set({ model: m })
  const b = model.blocks.find((x) => x.id === sel)
  const e = model.edges.find((x) => edgeId(x) === selEdge)
  const updBlock = (patch: Partial<Block>) => setModel({ ...model, blocks: model.blocks.map((x) => (x.id === sel ? { ...x, ...patch } : x)) })
  const stale = model.blocks.filter((x) => x.kind !== 'evidence' && ins[x.id].length > 0).filter((x) => {
    const rs = model.rules?.[x.id]
    if (!rs?.length) return true
    const keys = new Set(rs.flatMap((r: any) => Object.keys(r.when)))
    return [...keys].some((k) => !ins[x.id].includes(k)) || !rs.some((r: any) => ins[x.id].every((i) => i in r.when))
  }).map((x) => x.id)

  const addBlock = (kind: Block['kind']) => {
    const n = model.blocks.filter((x) => x.kind === kind).length + 1
    const pre = kind === 'evidence' ? 'e' : kind === 'hypothesis' ? 'h' : 'f'
    let bid = `${pre}${n}`
    while (model.blocks.some((x) => x.id === bid)) bid = `${bid}x`
    const layer = kind === 'finding' ? 'E' : kind === 'hypothesis' ? 'I' : 'L'
    const past = kind === 'finding' ? Object.fromEntries(mechs.map((m) => [m.code, 'HU'])) : 'S'
    setModel({ ...model, blocks: [...model.blocks, { id: bid, layer, kind, label: '', text: '', factor: null, past }] })
    setSel(bid)
  }
  const regen = async () => {
    try {
      const rules = await api.post('/ies/default-rules', { model })
      setModel({ ...model, rules })
      message.success('Default rules generated from the past states')
    } catch (err: any) { message.error(err.message) }
  }
  const save = async () => {
    setSaving(true)
    try {
      await api.put(`/cases/${doc.id}`, { ref: doc.ref, title: doc.title, category: doc.category, source: doc.source, occurred: doc.occurred, summary: doc.summary, model })
      setDirty(false); message.success('Saved'); refetch(); qc.invalidateQueries({ queryKey: ['cases'] })
    } catch (err: any) { message.error(err.message) } finally { setSaving(false) }
  }
  const approve = async () => {
    try { await api.post(`/cases/${doc.id}/approve`); message.success(`${doc.ref} approved`); refetch(); qc.invalidateQueries({ queryKey: ['cases'] }) } catch (err: any) { message.error(err.message) }
  }
  const remove = () => modal.confirm({ title: `Delete ${doc.ref}?`, okButtonProps: { danger: true }, okText: 'Delete', onOk: async () => {
    try { await api.del(`/cases/${doc.id}`); setDirty(false); qc.invalidateQueries({ queryKey: ['cases'] }); setTimeout(() => nav('/cases'), 0) } catch (err: any) { message.error(err.message) }
  } })
  const runTest = async () => {
    const states: Record<string, string | null> = {}
    model.blocks.filter((x) => x.kind === 'evidence' || ins[x.id].length === 0).forEach((x) => { states[x.id] = x.id in test ? test[x.id] : (typeof x.past === 'string' ? x.past : 'S') })
    try { setTestRes(await api.post('/ies/infer-model', { model, states, category: doc.category })) } catch (err: any) { message.error(err.message) }
  }

  const panel = b ? (
    <Card size="small" title={`Block ${b.id}`} extra={editable && <Button size="small" danger icon={<DeleteOutlined />}
      onClick={() => { setModel({ ...model, blocks: model.blocks.filter((x) => x.id !== b.id), edges: model.edges.filter((x) => x.source !== b.id && x.target !== b.id) }); setSel(null) }}>Delete</Button>}>
      <Form layout="vertical" size="small" disabled={!editable}>
        <Form.Item label="Label"><Input value={b.label} onChange={(ev) => updBlock({ label: ev.target.value })} /></Form.Item>
        <Space.Compact block>
          <Form.Item label="Layer" style={{ width: '50%' }}><Select value={b.layer} onChange={(v) => updBlock({ layer: v, y: undefined })} options={LAYERS.map((l) => ({ value: l, label: `${l} · ${LAYER_NAME[l]}` }))} /></Form.Item>
          <Form.Item label="Kind" style={{ width: '50%' }}><Select value={b.kind} onChange={(v) => updBlock({ kind: v, past: v === 'finding' ? Object.fromEntries(mechs.map((m) => [m.code, 'HU'])) : 'S' })}
            options={['evidence', 'hypothesis', 'finding'].map((k) => ({ value: k, label: k }))} /></Form.Item>
        </Space.Compact>
        {b.kind !== 'finding' && <Form.Item label="ORLIO factor (links the block across cases and to the Bayesian network)">
          <Select allowClear showSearch optionFilterProp="label" value={b.factor ?? undefined} onChange={(v) => updBlock({ factor: v ?? null })}
            options={factors.map((f) => ({ value: f.code, label: `${f.code}${f.atsb ? ` [ATSB ${f.atsb}]` : ''} — ${f.label}` }))} /></Form.Item>}
        {b.kind !== 'finding'
          ? <Form.Item label={b.kind === 'evidence' ? 'State in the past occurrence' : 'Conclusion in the past occurrence'}><Select value={b.past} onChange={(v) => updBlock({ past: v })} options={supportOpts} /></Form.Item>
          : <Form.Item label="Past finding — verbal probability per mechanism">
            {mechs.map((m) => <div key={m.code} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 4 }}>
              <b style={{ width: 34 }}>{m.code}</b><Select size="small" style={{ width: 170 }} value={b.past?.[m.code] ?? 'HU'} options={probOpts}
                onChange={(v) => updBlock({ past: { ...(b.past ?? {}), [m.code]: v } })} /><span className="small muted">{m.label}</span></div>)}
          </Form.Item>}
        <Form.Item label="Detail"><Input.TextArea rows={2} value={b.text} onChange={(ev) => updBlock({ text: ev.target.value })} /></Form.Item>
        <Form.Item label={<Space>Quote from the report{b.quote ? (b.quote_verified === false ? <Tag color="red">not found in text</Tag> : b.quote_verified ? <Tag color="green">verified</Tag> : null) : null}</Space>}>
          <Input.TextArea rows={3} value={b.quote} onChange={(ev) => updBlock({ quote: ev.target.value, quote_verified: undefined })} />
        </Form.Item>
      </Form>
      {ins[b.id]?.length > 0 && <div className="small muted">Inputs: {ins[b.id].join(', ')}</div>}
    </Card>
  ) : e ? (
    <Card size="small" title={`Link ${e.source} → ${e.target}`} extra={editable && <Button size="small" danger icon={<DeleteOutlined />}
      onClick={() => { setModel({ ...model, edges: model.edges.filter((x) => edgeId(x) !== selEdge) }); setSelEdge(null) }}>Delete</Button>}>
      <Select disabled={!editable} style={{ width: '100%' }} value={e.role ?? 'input'} onChange={(v) => setModel({ ...model, edges: model.edges.map((x) => (edgeId(x) === selEdge ? { ...x, role: v } : x)) })}
        options={[{ value: 'input', label: 'Input — used by the rules of the target block' }, { value: 'context', label: 'Context — shown, not used in inference' }]} />
    </Card>
  ) : <Card size="small"><Empty description="Select a block or link. Drag from a block's lower handle to another block to link them; drag a block into another lane to change its layer." /></Card>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <div>
          <Space wrap>
            <Tag color="#1F3A5F" style={{ fontSize: 13, padding: '2px 8px' }}>{doc.ref}</Tag>
            <b style={{ fontSize: 18, color: '#1F3A5F' }}>{doc.title}</b>
            {doc.status === 'approved' ? <Tag color="green">approved by {doc.approved_by}</Tag> : <Tag color="orange">draft</Tag>}
            {doc.provenance?.method === 'llm' && <Tag color="purple">AI draft · {doc.provenance.model}</Tag>}
            {doc.provenance?.method === 'heuristic' && <Tag color="blue">offline draft</Tag>}
          </Space>
          <div className="muted small" style={{ marginTop: 4 }}><Link to="/cases">← Case library</Link> · {cat?.name} · Manual Appendix E</div>
        </div>
        <Space wrap>
          {editable && <Button icon={<ThunderboltOutlined />} onClick={regen}>Default rules</Button>}
          {['admin', 'reviewer'].includes(user?.role ?? '') && doc.status !== 'approved' && <Button icon={<CheckCircleOutlined />} disabled={dirty} onClick={approve}>Approve</Button>}
          {(isAdmin(user) || (editable && doc.status !== 'approved')) && <Button danger icon={<DeleteOutlined />} onClick={remove}>Delete</Button>}
          {editable && <Button type="primary" icon={<SaveOutlined />} loading={saving} disabled={!dirty} onClick={save}>{dirty ? 'Save' : 'Saved'}</Button>}
        </Space>
      </div>
      {doc.status === 'approved' && editable && <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Saving a change returns this case to draft; it must be approved again before the expert system uses it." />}
      {stale.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={`Rules missing or out of date for ${stale.join(', ')}`}
        action={editable && <Button size="small" onClick={regen}>Generate default rules</Button>} />}
      <Tabs items={[
        { key: 'map', label: 'AcciMap', children: <Row gutter={12}>
          <Col xs={24} xl={16}>
            {editable && <Space style={{ marginBottom: 8 }}>
              <Button size="small" icon={<PlusOutlined />} onClick={() => addBlock('evidence')}>Evidence</Button>
              <Button size="small" icon={<PlusOutlined />} onClick={() => addBlock('hypothesis')}>Hypothesis</Button>
              <Button size="small" icon={<PlusOutlined />} onClick={() => addBlock('finding')} disabled={model.blocks.some((x) => x.kind === 'finding')}>Finding</Button>
              <span className="small muted">Solid link: rule input · dashed: context</span>
            </Space>}
            <AcciMap model={model} editable={editable} selected={sel} selectedEdge={selEdge} onSelect={setSel} onSelectEdge={setSelEdge} onChange={setModel} height={680} />
          </Col>
          <Col xs={24} xl={8}>{panel}</Col>
        </Row> },
        { key: 'details', label: 'Details', children: <Form layout="vertical" disabled={!editable} style={{ maxWidth: 820 }}>
          <Space.Compact block>
            <Form.Item label="Reference" style={{ width: '25%' }}><Input value={doc.ref} onChange={(ev) => set({ ref: ev.target.value })} /></Form.Item>
            <Form.Item label="Title" style={{ width: '75%' }}><Input value={doc.title} onChange={(ev) => set({ title: ev.target.value })} /></Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item label="Occurrence category" style={{ width: '50%' }}><Select value={doc.category} onChange={(v) => set({ category: v })} options={Object.entries(meta.categories).map(([k, v]: any) => ({ value: k, label: v.name }))} /></Form.Item>
            <Form.Item label="Date of occurrence" style={{ width: '50%' }}><Input value={doc.occurred} onChange={(ev) => set({ occurred: ev.target.value })} placeholder="YYYY-MM-DD" /></Form.Item>
          </Space.Compact>
          <Form.Item label="Source"><Input.TextArea rows={2} value={doc.source} onChange={(ev) => set({ source: ev.target.value })} /></Form.Item>
          <Form.Item label="Summary (searched)"><Input.TextArea rows={5} value={doc.summary} onChange={(ev) => set({ summary: ev.target.value })} /></Form.Item>
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="Created by">{doc.created_by}</Descriptions.Item>
            <Descriptions.Item label="Drafted by">{doc.provenance?.method ?? 'manual'}{doc.provenance?.at ? ` · ${doc.provenance.at}` : ''}</Descriptions.Item>
          </Descriptions>
        </Form> },
        { key: 'rules', label: `Rules (${Object.values(model.rules ?? {}).reduce((n: number, r: any) => n + r.length, 0)})`, children: <RulesTab model={model} setModel={setModel} ins={ins} editable={editable} mechs={mechs} /> },
        { key: 'test', label: 'Test', children: <Row gutter={12}>
          <Col xs={24} xl={9}>
            <Card size="small" title="Evidence states" extra={<Button type="primary" size="small" icon={<ExperimentOutlined />} onClick={runTest}>Run inference</Button>}>
              <div className="small muted" style={{ marginBottom: 8 }}>Defaults are the states in the past occurrence; with them the finding should reproduce the past finding.</div>
              {model.blocks.filter((x) => x.kind === 'evidence' || ins[x.id].length === 0).map((x) => <div key={x.id} style={{ display: 'flex', gap: 6, marginBottom: 4, alignItems: 'center' }}>
                <Tag color={LAYER_COLOR[x.layer]} style={{ color: '#111' }}>{x.id}</Tag>
                <span style={{ flex: 1 }} className="small">{x.label}</span>
                <Select size="small" style={{ width: 150 }} value={x.id in test ? (test[x.id] ?? 'NP') : (typeof x.past === 'string' ? x.past : 'S')}
                  onChange={(v) => setTest({ ...test, [x.id]: v === 'NP' ? null : v })} options={[...supportOpts, { value: 'U', label: 'Unsure' }, { value: 'NP', label: 'Not provided' }]} />
              </div>)}
            </Card>
          </Col>
          <Col xs={24} xl={15}>
            {testRes ? <>
              <AcciMap model={model} height={520} extra={(x) => <ResultBadge r={testRes.blocks[x.id]} />} />
              {testRes.clues.length > 0 && <Alert style={{ marginTop: 8 }} type="warning" showIcon title="Clues — evidence needed to reach a conclusion"
                description={testRes.clues.map((k: any) => <div key={k.block}>{k.block} {k.label} <span className="muted small">(for {k.for.join(', ')}; priority {k.priority.toFixed(2)})</span></div>)} />}
              <div className="small muted" style={{ marginTop: 6 }}>{testRes.engine_version}</div>
            </> : <Empty description="Run the inference to test the rules" />}
          </Col>
        </Row> },
        ...(doc.report_text ? [{ key: 'report', label: 'Report text', children: <ReportTab text={doc.report_text} blocks={model.blocks} /> }] : []),
      ]} />
      <Typography.Paragraph className="small muted" style={{ marginTop: 10 }}>
        Mechanisms of this category: {mechs.map((m) => `${m.code} ${m.label}`).join(' · ')}.
      </Typography.Paragraph>
    </div>
  )
}

function RulesTab({ model, setModel, ins, editable, mechs }: { model: AModel; setModel: (m: AModel) => void; ins: Record<string, string[]>; editable: boolean; mechs: any[] }) {
  const derived = model.blocks.filter((b) => b.kind !== 'evidence' && ins[b.id]?.length)
  if (!derived.length) return <Empty description="No hypothesis or finding block with inputs yet" />
  const setRules = (bid: string, rs: any[]) => setModel({ ...model, rules: { ...(model.rules ?? {}), [bid]: rs } })
  return <div>
    <Alert type="info" showIcon style={{ marginBottom: 10 }} title="IF every listed input is in one of the selected states THEN the output. An empty input cell means “any state”."
      description="Default rules: the confirming rule (the past occurrence's states → the past conclusion), a weakening rule for each input (that input only “No effect”), and a contradicting rule for each input (that input opposed)." />
    {derived.map((b) => {
      const rs = model.rules?.[b.id] ?? []
      const cols: any[] = [{ title: '#', width: 40, render: (_: any, __: any, i: number) => i + 1 },
        { title: 'Kind', dataIndex: 'kind', width: 110, render: (v: string) => v ? <Tag>{v}</Tag> : <Tag>custom</Tag> },
        ...ins[b.id].map((i) => ({ title: i, width: 150, render: (_: any, r: any, k: number) => <Select mode="multiple" size="small" style={{ width: '100%' }} disabled={!editable}
          value={r.when[i] ?? []} maxTagCount="responsive" options={SUPPORT_TERMS.map((t) => ({ value: t, label: t }))}
          onChange={(v) => setRules(b.id, rs.map((x, j) => (j === k ? { ...x, when: Object.fromEntries(Object.entries({ ...x.when, [i]: v }).filter(([, t]: any) => t.length)) } : x)))} /> })),
        { title: 'Then', render: (_: any, r: any, k: number) => b.kind === 'hypothesis'
          ? <Select size="small" style={{ width: 150 }} disabled={!editable} value={r.then} options={supportOpts} onChange={(v) => setRules(b.id, rs.map((x, j) => (j === k ? { ...x, then: v } : x)))} />
          : <Space size={2} wrap>{mechs.map((m) => <Tooltip key={m.code} title={m.label}><Select size="small" style={{ width: 78 }} disabled={!editable} value={r.then?.[m.code]} allowClear placeholder={m.code}
            options={PROB_TERMS.map((t) => ({ value: t, label: `${m.code} ${t}` }))} onChange={(v) => setRules(b.id, rs.map((x, j) => (j === k ? { ...x, then: Object.fromEntries(Object.entries({ ...x.then, [m.code]: v }).filter(([, t]) => t)) } : x)))} /></Tooltip>)}</Space> },
        { title: 'Weight', width: 80, render: (_: any, r: any, k: number) => <InputNumber size="small" min={0} max={1} step={0.1} disabled={!editable} value={r.weight ?? 1} onChange={(v) => setRules(b.id, rs.map((x, j) => (j === k ? { ...x, weight: v ?? 1 } : x)))} /> },
        { title: '', width: 40, render: (_: any, __: any, k: number) => editable && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => setRules(b.id, rs.filter((_x, j) => j !== k))} /> }]
      return <Card key={b.id} size="small" style={{ marginBottom: 10 }} title={<Space><Tag color={LAYER_COLOR[b.layer]} style={{ color: '#111' }}>{b.id}</Tag>{b.label}<span className="muted small">{b.kind}</span></Space>}
        extra={editable && <Button size="small" icon={<PlusOutlined />} onClick={() => setRules(b.id, [...rs, { when: {}, then: b.kind === 'hypothesis' ? 'NE' : {}, weight: 1 }])}>Rule</Button>}>
        <Table size="small" rowKey={(_r, i) => String(i)} dataSource={rs} columns={cols} pagination={false} scroll={{ x: true }} />
      </Card>
    })}
  </div>
}

function ReportTab({ text, blocks }: { text: string; blocks: Block[] }) {
  const quoted = blocks.filter((b) => b.quote)
  return <Row gutter={12}>
    <Col xs={24} xl={10}>
      <Table size="small" rowKey="id" dataSource={quoted} pagination={false} columns={[
        { title: 'Block', dataIndex: 'id', width: 60 },
        { title: 'Quote', dataIndex: 'quote', render: (v: string) => <span className="small">{v}</span> },
        { title: '', dataIndex: 'quote_verified', width: 90, render: (v: boolean) => v ? <Tag color="green">found</Tag> : <Tag color="red">not found</Tag> }]} />
    </Col>
    <Col xs={24} xl={14}><Card size="small" title="Report text"><div style={{ whiteSpace: 'pre-wrap', maxHeight: 640, overflow: 'auto', fontSize: 12.5 }}>{text}</div></Card></Col>
  </Row>
}
