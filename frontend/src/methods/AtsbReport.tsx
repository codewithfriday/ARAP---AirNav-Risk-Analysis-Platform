import { useState } from 'react'
import { Alert, App, Button, Card, Col, Descriptions, Empty, Form, Input, Row, Space, Spin, Table, Typography, Upload } from 'antd'
import { DeleteOutlined, FilePdfOutlined, FileWordOutlined, EyeOutlined, UploadOutlined } from '@ant-design/icons'
import { api, download } from '../api'
import EditableTable from '../components/EditableTable'

type Block = { type: string; text?: string; level?: number; style?: string; items?: string[]; rows?: string[][]; header?: string[]; data?: string; caption?: string }

/** Renders the investigation report blocks returned by POST /studies/{id}/investigation-report (format json). */
export function ReportView({ report }: { report: any }) {
  const blk = (b: Block, k: number) => {
    switch (b.type) {
      case 'h': return <Typography.Title key={k} level={b.level === 3 ? 5 : 4} style={{ marginTop: 12 }}>{b.text}</Typography.Title>
      case 'p': return <Typography.Paragraph key={k} type={b.style === 'note' ? 'secondary' : undefined} italic={b.style === 'note' || b.style === 'definition'}>{b.text}</Typography.Paragraph>
      case 'bullets': return <ul key={k} className={b.style === 'evidence' ? 'small' : undefined} style={{ paddingLeft: 18 }}>{b.items!.map((x, i) => <li key={i}>{x}</li>)}</ul>
      case 'numbered': return <ol key={k} style={{ paddingLeft: 20 }}>{b.items!.map((x, i) => <li key={i} style={{ marginBottom: 4 }}>{x}</li>)}</ol>
      case 'kv': return <Descriptions key={k} size="small" bordered column={1} style={{ marginBottom: 8 }} styles={{ label: { width: 190 } }}
        items={b.rows!.map(([l, v], i) => ({ key: i, label: l, children: <span style={{ whiteSpace: 'pre-wrap' }}>{v}</span> }))} />
      case 'table': return <Table key={k} size="small" pagination={false} bordered style={{ marginBottom: 10 }} rowKey="__k"
        columns={b.header!.map((h, i) => ({ title: h, dataIndex: String(i), key: String(i) }))}
        dataSource={b.rows!.map((r, i) => ({ __k: i, ...Object.fromEntries(r.map((v, j) => [String(j), v])) }))} />
      case 'image': return <figure key={k} style={{ margin: '8px 0 14px', textAlign: 'center' }}>
        <img src={b.data} alt={b.caption} style={{ maxWidth: '100%', border: '1px solid #e5e7eb' }} />
        <figcaption className="small muted" style={{ textAlign: 'left' }}>{b.caption}</figcaption></figure>
      default: return null
    }
  }
  return <div style={{ maxWidth: 980 }}>
    <Typography.Title level={3} style={{ marginBottom: 0 }}>{report.title}</Typography.Title>
    <Typography.Text strong>{report.subtitle}</Typography.Text>
    <div className="small muted" style={{ margin: '4px 0 12px' }}>
      {[report.meta.report_no, report.meta.project, report.meta.status, report.meta.prepared_by, `generated ${report.meta.generated}`].filter(Boolean).join(' · ')}
    </div>
    {report.sections.map((s: any) => <section key={s.id}><Typography.Title level={3} style={{ color: '#1F3A5F', marginTop: 18 }}>{s.title}</Typography.Title>{s.blocks.map(blk)}</section>)}
  </div>
}

/** Tab "7 · Investigation report": the factual content the analysis does not hold, attachments, preview and export. */
export default function AtsbReport({ m, set, meta, readOnly, studyId }: { m: any; set: (p: any) => void; meta: any; readOnly: boolean; studyId?: number }) {
  const { message } = App.useApp()
  const [preview, setPreview] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const rep = m.report ?? {}
  const occ = m.occurrence ?? {}
  const setRep = (patch: any) => set({ report: { ...rep, ...patch } })
  const setOcc = (patch: any) => set({ occurrence: { ...occ, ...patch } })
  const notes = rep.layer_notes ?? {}
  const att: any[] = rep.attachments ?? []
  const fname = (ext: string) => `${(rep.report_no || occ.ref || 'investigation-report').replace(/[^\w.-]+/g, '_')}.${ext}`

  const run = async (format: 'json' | 'docx' | 'pdf') => {
    if (!studyId) return
    setBusy(true)
    try {
      if (format === 'json') setPreview(await api.post(`/studies/${studyId}/investigation-report`, { model: m, format }))
      else await download(`/studies/${studyId}/investigation-report`, fname(format), { model: m, format })
    } catch (e: any) { message.error(e.message) } finally { setBusy(false) }
  }
  const addFile = (file: File) => {
    if (!file.type.startsWith('image/')) { message.error('Attach an image (PNG or JPEG)'); return false }
    if (file.size > 3_000_000) { message.error('Image larger than 3 MB — reduce it first (it is stored with the study)'); return false }
    const r = new FileReader()
    r.onload = () => setRep({ attachments: [...att, { id: `IMG${Date.now() % 100000}`, caption: file.name.replace(/\.[^.]+$/, ''), data: r.result }] })
    r.readAsDataURL(file)
    return false
  }

  return <Row gutter={12}>
    <Col xs={24} xl={preview ? 11 : 16}>
      <Alert type="info" showIcon style={{ marginBottom: 10 }} title="Investigation report"
        description={<span className="small">Sections 3–5 and Appendix C are generated from the analysis (safety factors, tests, safety issues and corrective actions).
          Enter here the factual information the analysis does not hold. Structure: 1 Executive summary · 2 Factual information · 3 ORLIO analysis framework ·
          4 Findings & contributing factors · 5 Safety recommendations & corrective actions · 6 Appendices.</span>} />
      <Form layout="vertical" size="small" disabled={readOnly}>
        <Card size="small" title="Report and synopsis (1)" style={{ marginBottom: 10 }}>
          <Space.Compact block>
            <Form.Item label="Report number" style={{ width: '30%' }}><Input value={rep.report_no} onChange={(e) => setRep({ report_no: e.target.value })} /></Form.Item>
            <Form.Item label="Status" style={{ width: '25%' }}><Input value={rep.status} placeholder="Draft" onChange={(e) => setRep({ status: e.target.value })} /></Form.Item>
            <Form.Item label="Prepared by" style={{ width: '45%' }}><Input value={rep.prepared_by} onChange={(e) => setRep({ prepared_by: e.target.value })} /></Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item label="Where" style={{ width: '40%' }}><Input value={occ.location} onChange={(e) => setOcc({ location: e.target.value })} /></Form.Item>
            <Form.Item label="Time" style={{ width: '20%' }}><Input value={occ.time} placeholder="e.g. 2126 LT" onChange={(e) => setOcc({ time: e.target.value })} /></Form.Item>
            <Form.Item label="Who (organisations)" style={{ width: '40%' }}><Input value={occ.operator} onChange={(e) => setOcc({ operator: e.target.value })} /></Form.Item>
          </Space.Compact>
          <Form.Item label="Consequences — injuries, damage, environmental impact"><Input.TextArea autoSize={{ minRows: 2 }} value={rep.consequences} onChange={(e) => setRep({ consequences: e.target.value })} /></Form.Item>
          <Form.Item label="Core finding (optional — leave empty to use the summary generated from the ORLIO analysis)"><Input.TextArea autoSize value={rep.core_finding} onChange={(e) => setRep({ core_finding: e.target.value })} /></Form.Item>
          <Form.Item label="Source / basis of the report"><Input value={rep.source} onChange={(e) => setRep({ source: e.target.value })} /></Form.Item>
        </Card>
        <Card size="small" title="Factual information (2)" style={{ marginBottom: 10 }}>
          <div className="small muted" style={{ marginBottom: 6 }}>2.1 The occurrence timeline is the sequence of events list (tab 1).</div>
          <Form.Item label="2.2 Personnel — experience, qualifications, duty">
            <EditableTable readOnly={readOnly} rows={rep.personnel ?? []} onChange={(rows) => setRep({ personnel: rows })} newRow={() => ({ role: '', details: '' })} addLabel="Person"
              columns={[{ key: 'role', title: 'Role', width: 200 }, { key: 'details', title: 'Details', type: 'textarea', width: 420 }]} />
          </Form.Item>
          <Form.Item label="2.2 Assets and equipment — types and configuration">
            <EditableTable readOnly={readOnly} rows={rep.assets ?? []} onChange={(rows) => setRep({ assets: rows })} newRow={() => ({ item: '', details: '' })} addLabel="Asset"
              columns={[{ key: 'item', title: 'Asset', width: 200 }, { key: 'details', title: 'Details', type: 'textarea', width: 420 }]} />
          </Form.Item>
          <Form.Item label="2.2 Environmental configuration (light, weather, layout)"><Input.TextArea autoSize value={rep.environment} onChange={(e) => setRep({ environment: e.target.value })} /></Form.Item>
          <Form.Item label="2.3 Immediate actions — emergency response, site preservation, stabilisation">
            <EditableTable readOnly={readOnly} rows={(rep.immediate_actions ?? []).map((t: string) => ({ text: t }))} onChange={(rows) => setRep({ immediate_actions: rows.map((r: any) => r.text) })}
              newRow={() => ({ text: '' })} addLabel="Action" columns={[{ key: 'text', title: 'Action taken', type: 'textarea', width: 620 }]} />
          </Form.Item>
        </Card>
        <Card size="small" title="ORLIO analysis — layer narratives (3)" style={{ marginBottom: 10 }}>
          {(meta.report_layers ?? []).map((l: any) => <Form.Item key={l.key} label={`${l.num} ${l.name}`} tooltip={l.definition}>
            <Input.TextArea autoSize value={notes[l.key]} placeholder={l.definition} onChange={(e) => setRep({ layer_notes: { ...notes, [l.key]: e.target.value } })} /></Form.Item>)}
        </Card>
        <Card size="small" title="Appendices (6)">
          <Form.Item label="Appendix A — photographs and diagrams of the scene and asset damage">
            {att.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No images" />}
            {att.map((a, i) => <Space key={a.id ?? i} align="start" style={{ marginBottom: 8, width: '100%' }}>
              <img src={a.data} alt="" style={{ width: 120, maxHeight: 90, objectFit: 'contain', border: '1px solid #e5e7eb' }} />
              <Input.TextArea style={{ width: 380 }} autoSize value={a.caption} placeholder="Caption" onChange={(e) => setRep({ attachments: att.map((x, j) => (j === i ? { ...x, caption: e.target.value } : x)) })} />
              {!readOnly && <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={() => setRep({ attachments: att.filter((_x, j) => j !== i) })} />}
            </Space>)}
            {!readOnly && <Upload accept="image/*" multiple showUploadList={false} beforeUpload={addFile}><Button size="small" icon={<UploadOutlined />}>Add image</Button></Upload>}
          </Form.Item>
          <Form.Item label="Appendix B — interview summaries and witness accounts">
            <EditableTable readOnly={readOnly} rows={rep.interviews ?? []} onChange={(rows) => setRep({ interviews: rows })} newRow={() => ({ person: '', summary: '' })} addLabel="Interview"
              columns={[{ key: 'person', title: 'Person', width: 180 }, { key: 'summary', title: 'Summary', type: 'textarea', width: 440 }]} />
          </Form.Item>
          <div className="small muted">Appendix C — the ORLIO factor map — is drawn from the safety factors and their influence links.</div>
        </Card>
      </Form>
    </Col>
    <Col xs={24} xl={preview ? 13 : 8}>
      <Card size="small" title="Generate" style={{ marginBottom: 10 }}>
        <Space wrap>
          <Button icon={<EyeOutlined />} loading={busy} disabled={!studyId} onClick={() => run('json')}>Preview</Button>
          <Button icon={<FileWordOutlined />} disabled={!studyId || busy} onClick={() => run('docx')}>Word (.docx)</Button>
          <Button icon={<FilePdfOutlined />} disabled={!studyId || busy} onClick={() => run('pdf')}>PDF</Button>
          {preview && <Button type="text" onClick={() => setPreview(null)}>Close preview</Button>}
        </Space>
        <div className="small muted" style={{ marginTop: 6 }}>Uses the current (also unsaved) content. Exports are recorded in the audit trail.</div>
      </Card>
      {busy && !preview && <Spin />}
      {preview && <Card size="small" style={{ maxHeight: '80vh', overflow: 'auto' }}><ReportView report={preview} /></Card>}
    </Col>
  </Row>
}
