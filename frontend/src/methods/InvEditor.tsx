import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button, Card, Checkbox, Col, DatePicker, Input, Row, Select, Space, Tabs, Tag } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../api'
import EditableTable, { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

const STATUS_COLOR: Record<string, string> = { failed: '#B23A3A', absent: '#D98E04', missing: '#D98E04', effective: '#3C8D5A' }

function Box({ children, color, title }: { children: React.ReactNode; color: string; title?: string }) {
  return <div title={title} style={{ border: `1.5px solid ${color}`, borderLeft: `5px solid ${color}`, background: '#fff', borderRadius: 4, padding: '4px 6px', fontSize: 10.5, lineHeight: 1.25, marginBottom: 6 }}>{children}</div>
}

/** Classic SOAM chart: organisational factors → contextual conditions → human involvement → barriers → occurrence. */
function SoamChart({ soam, occ }: { soam: any; occ: any }) {
  const col = (title: string, color: string, body: React.ReactNode) => (
    <div style={{ flex: 1, minWidth: 150 }}><div style={{ fontWeight: 700, fontSize: 11, color, marginBottom: 6, textAlign: 'center' }}>{title}</div>{body}</div>)
  return (
    <div style={{ display: 'flex', gap: 10, overflowX: 'auto', padding: 10, background: '#fbfcfd', border: '1px solid #e5e7eb', borderRadius: 8 }}>
      {col('Organisational factors', '#7C3AED', (soam.orgfactors ?? []).map((o: any, i: number) => <Box key={i} color="#7C3AED"><b>{o.category}</b><div>{o.text}</div></Box>))}
      {col('Contextual conditions', '#A16207', (soam.contextual ?? []).map((o: any, i: number) => <Box key={i} color="#A16207"><b>{o.category}</b><div>{o.text}</div></Box>))}
      {col('Human involvement', '#2A7F8E', (soam.human ?? []).map((t: string, i: number) => <Box key={i} color="#2A7F8E">{t}</Box>))}
      {col('Absent / failed barriers', '#B23A3A', (soam.barriers ?? []).filter((b: any) => b.status !== 'effective').map((b: any, i: number) => <Box key={i} color={STATUS_COLOR[b.status]}><b>{b.category}</b> · {b.status}<div>{b.text}</div></Box>))}
      <div style={{ minWidth: 150, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: 11, color: '#1F3A5F', textAlign: 'center', marginBottom: 6 }}>Occurrence</div>
        <div style={{ border: '2px solid #1F3A5F', borderRadius: 6, padding: 8, fontSize: 11, background: '#EEF2F6' }}><b>{occ.ref}</b><div>{String(occ.summary ?? '').slice(0, 160)}</div></div>
        {(soam.barriers ?? []).some((b: any) => b.status === 'effective') && <div style={{ marginTop: 8 }}>
          <div style={{ fontWeight: 700, fontSize: 10.5, color: '#3C8D5A' }}>Barriers that worked</div>
          {(soam.barriers ?? []).filter((b: any) => b.status === 'effective').map((b: any, i: number) => <Box key={i} color="#3C8D5A">{b.text}</Box>)}</div>}
      </div>
    </div>)
}

export default function InvEditor({ model, setModel, readOnly, template, promote }: EditorProps) {
  const occ = model.occurrence ?? {}
  const soam = model.soam ?? { barriers: [], human: [], contextual: [], orgfactors: [], actions: [] }
  const hfacs = model.hfacs ?? { selected: {} }
  const tripod = model.tripod ?? { events: [] }
  const { data: barriers = [] } = useQuery({ queryKey: ['barriers'], queryFn: () => api.get('/barriers') })
  const setOcc = (k: string, v: any) => setModel({ ...model, occurrence: { ...occ, [k]: v } })
  const setSoam = (k: string, v: any) => setModel({ ...model, soam: { ...soam, [k]: v } })
  const setSel = (s: any) => setModel({ ...model, hfacs: { ...hfacs, selected: s } })
  const setEvents = (e: any[]) => setModel({ ...model, tripod: { ...tripod, events: e } })
  const bOpts = barriers.map((b: any) => ({ value: `${b.study_id}:${b.barrier_id}`, label: `${b.barrier_id} ${b.text} — ${b.study_title}` }))
  const failed = (soam.barriers ?? []).filter((b: any) => b.status !== 'effective')

  const doPromote = () => promote([{ row_id: occ.ref || 'OCC', title: `Occurrence ${occ.ref ?? ''}: ${String(occ.summary ?? '').slice(0, 120)}`,
    causes: [...(soam.orgfactors ?? []).map((o: any) => `${o.category}: ${o.text}`), ...(soam.contextual ?? []).map((o: any) => o.text)].join('; '),
    controls: (soam.actions ?? []).map((a: any) => a.text) }])

  return (
    <Tabs items={[
      { key: 'occ', label: 'Occurrence', children: (
        <Card size="small">
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Space wrap><Input prefix="Reference" value={occ.ref} disabled={readOnly} onChange={(e) => setOcc('ref', e.target.value)} style={{ width: 220 }} />
              <DatePicker value={occ.date ? dayjs(occ.date) : null} disabled={readOnly} onChange={(d) => setOcc('date', d ? d.format('YYYY-MM-DD') : null)} />
              <Input prefix="Location" value={occ.location} disabled={readOnly} onChange={(e) => setOcc('location', e.target.value)} style={{ width: 340 }} /></Space>
            <Input.TextArea autoSize={{ minRows: 4 }} placeholder="Factual summary of the sequence of events" value={occ.summary} disabled={readOnly} onChange={(e) => setOcc('summary', e.target.value)} />
            <Space wrap>
              <Tag color="red">{failed.length} barrier(s) failed or absent</Tag>
              <Tag>{Object.keys(hfacs.selected ?? {}).length} HFACS categories</Tag>
              <Tag>{(soam.actions ?? []).length} safety actions</Tag>
              {!readOnly && <Button size="small" type="primary" ghost onClick={doPromote}>Send occurrence to hazard log</Button>}
            </Space>
          </Space>
        </Card>) },
      { key: 'soam', label: 'SOAM', children: (
        <div>
          <SoamChart soam={soam} occ={occ} />
          <Row gutter={12} style={{ marginTop: 12 }}>
            <Col xs={24} xl={14}>
              <Card size="small" title="Barriers" extra={<span className="small muted">link failed barriers to the bowtie they belong to</span>}>
                <EditableTable readOnly={readOnly} rows={soam.barriers ?? []} onChange={(r) => setSoam('barriers', r)} newRow={() => ({ text: '', category: template.soam_barriers?.[0], status: 'failed', bowtie_link: null })}
                  scrollX={820} columns={[{ key: 'text', title: 'Barrier', type: 'textarea', width: 230 }, { key: 'category', title: 'Type', type: 'select', options: template.soam_barriers ?? [], width: 150 },
                    { key: 'status', title: 'Status', type: 'select', options: ['failed', 'absent', 'effective'], width: 100 },
                    { key: 'bowtie_link', title: 'Bowtie barrier', width: 220, render: (b: any, i: number) => readOnly
                      ? (b.bowtie_link ? <Link to={`/studies/${b.bowtie_link.split(':')[0]}`}>{b.bowtie_link.split(':')[1]}</Link> : '')
                      : <Select size="small" allowClear showSearch optionFilterProp="label" style={{ width: '100%' }} value={b.bowtie_link} options={bOpts}
                          onChange={(v) => setSoam('barriers', soam.barriers.map((x: any, j: number) => (j === i ? { ...x, bowtie_link: v ?? null } : x)))} /> }]} />
              </Card>
              <Card size="small" title="Human involvement (actions and non-actions)" style={{ marginTop: 12 }}>
                <EditableTable readOnly={readOnly} rows={(soam.human ?? []).map((t: string) => ({ t }))} onChange={(r) => setSoam('human', r.map((x) => x.t ?? ''))} newRow={() => ({ t: '' })}
                  columns={[{ key: 't', title: 'Act / decision', type: 'textarea' }]} />
              </Card>
            </Col>
            <Col xs={24} xl={10}>
              <Card size="small" title="Contextual conditions">
                <EditableTable readOnly={readOnly} rows={soam.contextual ?? []} onChange={(r) => setSoam('contextual', r)} newRow={() => ({ category: template.soam_contextual?.[0], text: '' })}
                  columns={[{ key: 'category', title: 'Category', type: 'select', options: template.soam_contextual ?? [], width: 170 }, { key: 'text', title: 'Condition', type: 'textarea' }]} />
              </Card>
              <Card size="small" title="Organisational factors" style={{ marginTop: 12 }}>
                <EditableTable readOnly={readOnly} rows={soam.orgfactors ?? []} onChange={(r) => setSoam('orgfactors', r)} newRow={() => ({ category: template.soam_orgfactors?.[0], text: '' })}
                  columns={[{ key: 'category', title: 'Factor', type: 'select', options: template.soam_orgfactors ?? [], width: 170 }, { key: 'text', title: 'Finding', type: 'textarea' }]} />
              </Card>
              <Card size="small" title="Safety actions" style={{ marginTop: 12 }}>
                <EditableTable readOnly={readOnly} rows={soam.actions ?? []} onChange={(r) => setSoam('actions', r)} newRow={() => ({ text: '', addresses: '', owner: '' })}
                  columns={[{ key: 'text', title: 'Action', type: 'textarea' }, { key: 'addresses', title: 'Addresses', width: 130 }, { key: 'owner', title: 'Owner', width: 110 }]} />
              </Card>
            </Col>
          </Row>
        </div>) },
      { key: 'hfacs', label: 'HFACS', children: (
        <Row gutter={[12, 12]}>
          {Object.entries<string[]>(template.hfacs ?? {}).reverse().map(([tier, cats]) => (
            <Col xs={24} xl={12} key={tier}>
              <Card size="small" title={tier}>
                {cats.map((c) => {
                  const on = c in (hfacs.selected ?? {})
                  return (
                    <div key={c} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 6 }}>
                      <Checkbox checked={on} disabled={readOnly} style={{ width: 230 }} onChange={(e) => { const s = { ...hfacs.selected }; if (e.target.checked) s[c] = ''; else delete s[c]; setSel(s) }}>{c}</Checkbox>
                      {on && <Input.TextArea size="small" autoSize placeholder="Evidence" value={hfacs.selected[c]} disabled={readOnly} onChange={(e) => setSel({ ...hfacs.selected, [c]: e.target.value })} />}
                    </div>)
                })}
              </Card>
            </Col>))}
        </Row>) },
      { key: 'tripod', label: 'Tripod Beta', children: (
        <div>
          {!readOnly && <Button icon={<PlusOutlined />} style={{ marginBottom: 10 }} onClick={() => setEvents([...(tripod.events ?? []), { id: nextId(tripod.events ?? [], 'EV', 1), agent: '', object: '', event: '', barriers: [] }])}>Event trio</Button>}
          {(tripod.events ?? []).map((ev: any, i: number) => {
            const updEv = (patch: any) => setEvents(tripod.events.map((x: any, j: number) => (j === i ? { ...x, ...patch } : x)))
            return (
              <Card key={ev.id} size="small" style={{ marginBottom: 12 }} title={`${ev.id} — ${ev.event || 'event'}`}
                extra={!readOnly && <Button size="small" danger icon={<DeleteOutlined />} onClick={() => setEvents(tripod.events.filter((_x: any, j: number) => j !== i))} />}>
                <Row gutter={8} style={{ marginBottom: 8 }}>
                  {[['agent', 'Agent (hazard)', '#D98E04'], ['object', 'Object (target)', '#2A7F8E'], ['event', 'Event', '#B23A3A']].map(([k, l, c]) => (
                    <Col span={8} key={k}><div className="small" style={{ color: c, fontWeight: 600 }}>{l}</div>
                      <Input.TextArea size="small" autoSize value={ev[k]} disabled={readOnly} onChange={(e) => updEv({ [k]: e.target.value })} style={{ borderColor: c }} /></Col>))}
                </Row>
                <div className="small muted" style={{ marginBottom: 4 }}>Failed or missing barriers: immediate cause → precondition → underlying cause (latent failure) → Basic Risk Factor</div>
                <EditableTable readOnly={readOnly} rows={ev.barriers ?? []} onChange={(r) => updEv({ barriers: r })} scrollX={1000}
                  newRow={() => ({ barrier: '', status: 'failed', immediate_cause: '', precondition: '', underlying_cause: '', brf: undefined })}
                  columns={[{ key: 'barrier', title: 'Barrier', type: 'textarea', width: 160 }, { key: 'status', title: 'Status', type: 'select', options: ['failed', 'missing', 'effective'], width: 100 },
                    { key: 'immediate_cause', title: 'Immediate cause', type: 'textarea', width: 170 }, { key: 'precondition', title: 'Precondition', type: 'textarea', width: 170 },
                    { key: 'underlying_cause', title: 'Underlying cause', type: 'textarea', width: 170 }, { key: 'brf', title: 'BRF', type: 'select', options: template.tripod_brf ?? [], width: 170 }]} />
              </Card>)
          })}
          {(tripod.events ?? []).length > 0 && <Card size="small" title="Basic Risk Factor profile">
            <Space wrap>{(template.tripod_brf ?? []).map((b: string) => { const n = tripod.events.flatMap((e: any) => e.barriers ?? []).filter((x: any) => x.brf === b).length; return <Tag key={b} color={n ? 'red' : 'default'}>{b}: {n}</Tag> })}</Space>
          </Card>}
        </div>) },
    ]} />
  )
}
