import { useMemo, useState } from 'react'
import { Alert, Button, Card, Checkbox, Col, Input, Modal, Row, Select, Space, Table, Tag, Typography } from 'antd'
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Worksheet, secRisk, ofmGaps, type ColSpec } from '../components/Worksheet'
import { uid } from '../hooks'
import type { EditorProps } from './types'

const PREFIX: Record<string, string> = { hazid: 'HZ', hazop: 'HP', jha: 'S', fmea: 'FM', fha: 'FC', swift: 'W', sec: 'SR', orgmap: 'FN', spi: 'SPI' }

export default function WorksheetEditor({ method, model, setModel, readOnly, scheme, template, promote }: EditorProps & { method: string }) {
  const rows: any[] = model.rows ?? []
  const [selected, setSelected] = useState<any[]>([])
  const setRows = (r: any[]) => setModel({ ...model, rows: r })
  const nextId = () => {
    const nums = rows.map((r) => Number(String(r.id).split('-').pop())).filter((n) => !Number.isNaN(n))
    return `${PREFIX[method]}-${String((nums.length ? Math.max(...nums) : 0) + 1).padStart(2, '0')}`
  }
  const addRow = (extra: any = {}) => setRows([...rows, { id: nextId(), ...extra }])
  const delRows = () => setRows(rows.filter((r) => !selected.some((s) => s.id === r.id)))

  // a study may carry its own guideword list (e.g. organisational guidewords in a HAZID)
  const guidewords: string[] = model.guidewords ?? template.guidewords ?? []
  const options = useMemo(() => ({
    ...(template.options ?? {}),
    guideword: guidewords, method: ['bowtie', 'hazop', 'fmea', 'fta', 'lopa', 'stpa', 'fram', 'bbn', 'fatigue', 'jha'],
    hierarchy: template.hierarchy ?? [], failure_type: template.failure_types ?? [], threat_source: template.threat_sources ?? [],
  }), [template, guidewords.join('|')])

  const doPromote = () => {
    const src = (selected.length ? selected : rows).filter((r) => (method !== 'sec' || r.safety_severity) && (method !== 'swift' || r.consequence) && (method !== 'orgmap' || ofmGaps(r).some((g) => g !== 'to assess')))
    const mapped = src.map((r) => {
      if (method === 'hazid') return { row_id: r.id, title: r.hazard, causes: r.causes, consequences: r.consequences, controls: String(r.controls ?? '').split(/;\s*/), severity: r.severity || null, likelihood: r.likelihood || null, owner: r.owner }
      if (method === 'hazop') return { row_id: r.id, title: `${r.deviation} (${r.parameter} — ${r.guideword})`, causes: r.causes, consequences: r.consequences, controls: String(r.safeguards ?? '').split(/;\s*/), severity: r.severity || null, likelihood: r.likelihood || null }
      if (method === 'fmea') return { row_id: r.id, title: `${r.item}: ${r.failure_mode}`, causes: r.cause, consequences: r.end_effect, controls: [r.compensation, r.detection_method].filter(Boolean) }
      if (method === 'swift') return { row_id: r.id, title: r.consequence || r.what_if, causes: r.what_if, consequences: r.consequence, controls: [...String(r.safeguards ?? '').split(/;\s*/), r.recommendation].filter(Boolean), severity: r.severity || null, likelihood: r.likelihood || null, owner: r.owner }
      if (method === 'sec') return { row_id: r.id, title: `Security: ${r.threat} (${r.asset})`, causes: `${r.source ?? ''} — ${r.vulnerability ?? ''}`, consequences: `Security risk ${secRisk(r)?.score ?? '-'} (${secRisk(r)?.level ?? 'n/a'})`, controls: [...String(r.controls ?? '').split(/;\s*/), r.treatment].filter(Boolean), severity: r.safety_severity || null, owner: r.owner }
      if (method === 'orgmap') return { row_id: r.id, title: `Function “${r.function}” — ${ofmGaps(r).join(', ')}`, causes: `Current owner: ${r.old_owner || '—'}; new owner: ${r.new_owner || '—'}`, consequences: 'Safety-related function not performed, or performed without competence, capacity or authority', controls: [r.action].filter(Boolean) }
      if (method === 'fha') return { row_id: r.id, title: r.condition, consequences: r.effect, controls: String(r.requirements ?? '').split(/;\s*/) }
      return { row_id: r.id, title: `${r.step}: ${r.hazards}`, controls: [r.controls] }
    }).filter((x) => x.title && !String(x.title).startsWith('undefined') && !(method === 'hazop' && src.find((r) => r.id === x.row_id)?.not_meaningful))
    return promote(mapped)
  }

  // JHA warning: steps whose only control is administrative or PPE (JHA-02)
  const jhaWarn = method === 'jha' ? rows.filter((r) => ['Administrative', 'PPE'].includes(r.hierarchy)).map((r) => r.id) : []
  // FMEA: high severity rows regardless of RPN
  const fmeaHigh = method === 'fmea' ? rows.filter((r) => Number(r.s) >= 8).map((r) => `${r.id} (S=${r.s})`) : []
  // SEC: promote only rows with a safety effect (ED-205 safety impact)
  const secSafety = method === 'sec' ? rows.filter((r) => r.safety_severity) : []
  const secHigh = method === 'sec' ? rows.filter((r) => (secRisk(r)?.score ?? 0) >= 10).map((r) => r.id) : []
  // function map: open issues
  const ofm = method === 'orgmap' ? { gaps: rows.filter((r) => ofmGaps(r).some((g) => g !== 'to assess')), orphan: rows.filter((r) => ofmGaps(r).includes('no owner')), todo: rows.filter((r) => ofmGaps(r).includes('to assess')) } : null
  const spiAlert = method === 'spi' ? rows.filter((r) => r.status === 'red') : []
  // HAZID / SWIFT guideword coverage
  const coverage = method === 'hazid' || method === 'swift' ? guidewords.map((g) => ({ g, n: rows.filter((r) => r.guideword === g).length })) : []

  return (
    <div>
      {method === 'jha' && <JobHeader model={model} setModel={setModel} readOnly={readOnly} />}
      {method === 'hazop' && <HazopNodes model={model} setModel={setModel} readOnly={readOnly} template={template} addRows={(rs: any[]) => setRows([...rows, ...rs])} nextId={nextId} />}
      <Space style={{ marginBottom: 8 }} wrap>
        {!readOnly && <Button icon={<PlusOutlined />} onClick={() => addRow(method === 'hazop' && model.nodes?.length ? { node: model.nodes[0].id } : {})}>Add row</Button>}
        {!readOnly && <Button danger icon={<DeleteOutlined />} disabled={!selected.length} onClick={delRows}>Delete selected</Button>}
        {!readOnly && method !== 'spi' && <Button type="primary" ghost onClick={doPromote}>{selected.length ? `Send ${selected.length} selected to hazard log` : 'Send all rows to hazard log'}</Button>}
        <span className="muted small">Double-click a cell to edit. Tick rows to select.</span>
      </Space>
      {jhaWarn.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} title={`Steps ${jhaWarn.join(', ')} rely only on administrative controls or PPE — look higher up the hierarchy of controls (Manual §9.4).`} />}
      {fmeaHigh.length > 0 && <Alert type="info" showIcon style={{ marginBottom: 8 }} title={`High-severity failure modes to review regardless of RPN: ${fmeaHigh.join(', ')}`} />}
      <Worksheet columns={template.columns as ColSpec[]} rows={rows} onChange={setRows} scheme={scheme} readOnly={readOnly} options={options} onSelect={setSelected} />
      {ofm && <Alert type={ofm.gaps.length ? 'warning' : 'success'} showIcon style={{ marginBottom: 8 }}
        title={`${rows.length} functions mapped · ${ofm.gaps.length} with gaps · ${ofm.orphan.length} without a new owner · ${ofm.todo.length} still to assess`}
        description="Every row needs a named new owner with confirmed competence, adequate capacity, authority in place and a planned handover before go-live. Send rows with gaps to the hazard log." />}
      {method === 'spi' && spiAlert.length > 0 && <Alert type="error" showIcon style={{ marginBottom: 8 }} title={`At alert level: ${spiAlert.map((r) => r.id).join(', ')} — apply the agreed escalation`} />}
      {method === 'sec' && <Alert type="info" showIcon style={{ marginBottom: 8 }} title={`Security risk = L × max(C, I, A). ${secHigh.length ? `High / very high: ${secHigh.join(', ')}. ` : ''}${secSafety.length} threat scenario(s) have a safety effect — send those to the safety hazard log (ED-205 / Manual §29.3).`} />}
      {(method === 'hazid' || method === 'swift') && (
        <Card size="small" title={method === 'swift' ? 'Prompt category coverage' : 'Guideword coverage'} style={{ marginTop: 12 }}>
          <Space wrap>{coverage.map(({ g, n }) => <Tag key={g} color={n ? 'green' : 'default'}>{g}: {n}</Tag>)}</Space>
          {!readOnly && <div style={{ marginTop: 8 }}><Select size="small" placeholder="Record “no hazard identified” for a guideword" style={{ width: 360 }} value={null as any}
            onChange={(g) => addRow(method === 'swift' ? { guideword: g, what_if: 'Considered — no credible what-if identified' } : { guideword: g, hazard: 'No hazard identified' })} options={coverage.filter((c) => !c.n).map((c) => ({ value: c.g, label: c.g }))} /></div>}
        </Card>
      )}
    </div>
  )
}

function JobHeader({ model, setModel, readOnly }: any) {
  const job = model.job ?? {}
  const set = (k: string, v: string) => setModel({ ...model, job: { ...job, [k]: v } })
  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      <Row gutter={12}>
        <Col span={10}><Input prefix="Job" value={job.title} disabled={readOnly} onChange={(e) => set('title', e.target.value)} /></Col>
        <Col span={7}><Input prefix="Location" value={job.location} disabled={readOnly} onChange={(e) => set('location', e.target.value)} /></Col>
        <Col span={7}><Input prefix="Permits" value={job.permits} disabled={readOnly} onChange={(e) => set('permits', e.target.value)} /></Col>
      </Row>
    </Card>
  )
}

function HazopNodes({ model, setModel, readOnly, template, addRows, nextId }: any) {
  const nodes: any[] = model.nodes ?? []
  const [gen, setGen] = useState<any | null>(null)
  const setNodes = (n: any[]) => setModel({ ...model, nodes: n })
  const generate = () => {
    const out: any[] = []
    let n = Number(String(nextId()).split('-').pop())
    for (const p of gen.parameters) for (const g of gen.guidewords) out.push({ id: `HP-${String(n++).padStart(2, '0')}`, node: gen.node, parameter: p, guideword: g, deviation: `${g} ${p.toLowerCase()}` })
    addRows(out)
    setGen(null)
  }
  const rows: any[] = model.rows ?? []
  return (
    <Card size="small" title="Nodes and design intent" style={{ marginBottom: 12 }}
      extra={!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => setNodes([...nodes, { id: `N${nodes.length + 1}`, name: 'New node', type: 'procedural', intent: '' }])}>Node</Button>}>
      <Table rowKey="id" size="small" pagination={false} dataSource={nodes} columns={[
        { title: 'ID', dataIndex: 'id', width: 60 },
        { title: 'Node', dataIndex: 'name', render: (v, r: any, i) => <Input size="small" value={v} disabled={readOnly} onChange={(e) => setNodes(nodes.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} /> },
        { title: 'Type', dataIndex: 'type', width: 130, render: (v, r: any, i) => <Select size="small" value={v} disabled={readOnly} style={{ width: 120 }} onChange={(t) => setNodes(nodes.map((x, j) => (j === i ? { ...x, type: t } : x)))} options={Object.keys(template.parameters).map((k) => ({ value: k, label: k }))} /> },
        { title: 'Design intent', dataIndex: 'intent', render: (v, r: any, i) => <Input.TextArea size="small" autoSize value={v} disabled={readOnly} onChange={(e) => setNodes(nodes.map((x, j) => (j === i ? { ...x, intent: e.target.value } : x)))} /> },
        { title: 'Progress', width: 110, render: (_, r: any) => { const rs = rows.filter((x) => x.node === r.id); const done = rs.filter((x) => x.not_meaningful || x.causes).length; return `${done}/${rs.length} analysed` } },
        { title: '', width: 130, render: (_, r: any) => !readOnly && <Button size="small" icon={<ThunderboltOutlined />} onClick={() => setGen({ node: r.id, parameters: template.parameters[r.type] ?? [], guidewords: template.guidewords })}>Deviations</Button> },
      ]} />
      <Modal open={!!gen} title="Generate deviations (parameter × guideword)" onCancel={() => setGen(null)} onOk={generate} okText="Generate rows" width={640}>
        {gen && <>
          <Typography.Text strong>Parameters</Typography.Text>
          <Checkbox.Group style={{ display: 'block', margin: '6px 0 12px' }} value={gen.parameters} options={Object.values(template.parameters).flat() as string[]} onChange={(v) => setGen({ ...gen, parameters: v })} />
          <Typography.Text strong>Guidewords</Typography.Text>
          <Checkbox.Group style={{ display: 'block', marginTop: 6 }} value={gen.guidewords} options={template.guidewords} onChange={(v) => setGen({ ...gen, guidewords: v })} />
          <div className="muted small" style={{ marginTop: 10 }}>{gen.parameters.length * gen.guidewords.length} rows will be added. Mark meaningless ones “N/A” in the worksheet.</div>
        </>}
      </Modal>
    </Card>
  )
}

export const _uid = uid
