import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Form, Input, Modal, Segmented, Select, Space, Switch, Table, Tabs, Tag, Tooltip, Upload } from 'antd'
import { FileSearchOutlined, PlusOutlined, RobotOutlined, UploadOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { canEdit, useAuth } from '../store'
import { PageHeader } from '../components/common'

export function useIesMeta() {
  return useQuery({ queryKey: ['ies-meta'], queryFn: () => api.get('/ies/meta'), staleTime: Infinity })
}

export default function CaseLibrary() {
  const user = useAuth((s) => s.user)
  const nav = useNavigate()
  const qc = useQueryClient()
  const { message } = App.useApp()
  const { data: meta } = useIesMeta()
  const [cat, setCat] = useState<string>('all')
  const [status, setStatus] = useState<string>('all')
  const [newOpen, setNewOpen] = useState(false)
  const [draftOpen, setDraftOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [src, setSrc] = useState<'text' | 'pdf'>('text')
  const [file, setFile] = useState<File | null>(null)
  const qs = new URLSearchParams({ ...(cat !== 'all' ? { category: cat } : {}), ...(status !== 'all' ? { status } : {}) }).toString()
  const { data: cases = [], isLoading } = useQuery({ queryKey: ['cases', cat, status], queryFn: () => api.get(`/cases${qs ? `?${qs}` : ''}`) })
  const cats = meta?.categories ?? {}
  const catOptions = Object.entries(cats).map(([k, v]: any) => ({ value: k, label: v.name }))

  const create = async (v: any) => {
    try {
      const c = await api.post('/cases', v)
      qc.invalidateQueries({ queryKey: ['cases'] })
      nav(`/cases/${c.id}`)
    } catch (e: any) { message.error(e.message) }
  }
  const draft = async (v: any) => {
    setBusy(true)
    try {
      let c
      if (src === 'pdf') {
        if (!file) { message.warning('Choose a PDF'); return }
        const fd = new FormData()
        fd.append('file', file); fd.append('category', v.category); fd.append('title', v.title)
        fd.append('source', v.source ?? ''); fd.append('use_ai', String(!!v.use_ai))
        const token = useAuth.getState().token
        const r = await fetch('/api/cases/draft-pdf', { method: 'POST', body: fd, headers: token ? { Authorization: `Bearer ${token}` } : {} })
        const j = await r.json()
        if (!r.ok) throw new Error(j.detail ?? r.statusText)
        c = j
      } else {
        c = await api.post('/cases/draft', { ...v, use_ai: !!v.use_ai })
      }
      message.success(`${c.ref} drafted with ${c.n_blocks} blocks${c.unverified_quotes ? ` — ${c.unverified_quotes} quote(s) not found in the text` : ''}. Review it before approval.`)
      qc.invalidateQueries({ queryKey: ['cases'] })
      nav(`/cases/${c.id}`)
    } catch (e: any) { message.error(e.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <PageHeader title="Investigation case library"
        sub="Past occurrences as ORLIO AcciMaps — the knowledge base of the investigation expert system (Manual Appendix E). Only approved cases are used by search, inference and the Bayesian network."
        extra={canEdit(user) && <Space>
          <Button icon={<RobotOutlined />} onClick={() => setDraftOpen(true)}>Draft from report</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setNewOpen(true)}>New case</Button>
        </Space>} />
      <Card title={<Space><FileSearchOutlined />Cases</Space>} extra={<Space wrap>
        <Select size="small" style={{ width: 240 }} value={cat} onChange={setCat} options={[{ value: 'all', label: 'All categories' }, ...catOptions]} />
        <Segmented size="small" value={status} onChange={(v) => setStatus(String(v))} options={[{ value: 'all', label: 'All' }, { value: 'approved', label: 'Approved' }, { value: 'draft', label: 'Draft' }]} />
      </Space>}>
        <Table rowKey="id" loading={isLoading} dataSource={cases} size="middle" pagination={{ pageSize: 15 }}
          columns={[
            { title: 'Ref', dataIndex: 'ref', width: 110, render: (v, r: any) => <Link to={`/cases/${r.id}`}>{v}</Link> },
            { title: 'Title', dataIndex: 'title' },
            { title: 'Category', dataIndex: 'category', width: 190, render: (v) => cats[v]?.name ?? v },
            { title: 'Mechanism', dataIndex: 'mechanism', width: 230, render: (v, r: any) => v ? <span><b>{v}</b> <span className="muted small">{cats[r.category]?.mechanisms.find((m: any) => m.code === v)?.label}</span></span> : '—' },
            { title: 'Blocks', dataIndex: 'n_blocks', width: 75 },
            { title: 'Source', dataIndex: 'provenance', width: 120, render: (p) => p?.method === 'llm' ? <Tag color="purple">AI draft</Tag> : p?.method === 'heuristic' ? <Tag color="blue">offline draft</Tag> : <Tag>manual</Tag> },
            { title: 'Status', dataIndex: 'status', width: 150, render: (s, r: any) => <Space size={4}>{s === 'approved' ? <Tag color="green">approved</Tag> : <Tag color="orange">draft</Tag>}
              {r.unverified_quotes > 0 && <Tooltip title="Quotes not found in the report text"><Tag color="red">{r.unverified_quotes} quote</Tag></Tooltip>}</Space> },
          ]} />
      </Card>

      <Modal title="New case" open={newOpen} onCancel={() => setNewOpen(false)} footer={null} destroyOnHidden>
        <Form layout="vertical" onFinish={create} initialValues={{ category: 'ats-los' }}>
          <Form.Item name="category" label="Occurrence category" rules={[{ required: true }]}><Select options={catOptions} /></Form.Item>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="source" label="Source (report number, agency, link)"><Input /></Form.Item>
          <Form.Item name="summary" label="Summary"><Input.TextArea rows={3} /></Form.Item>
          <Button type="primary" htmlType="submit">Create and open the AcciMap editor</Button>
        </Form>
      </Modal>

      <Modal title="Draft an AcciMap from a final report" open={draftOpen} onCancel={() => setDraftOpen(false)} footer={null} destroyOnHidden width={760}>
        <Alert type="info" showIcon style={{ marginBottom: 12 }} title="The result is a draft"
          description="Every block carries a quote from the report, checked against the text. An investigator reviews and completes the AcciMap and a reviewer approves it before the expert system uses it." />
        <Form layout="vertical" onFinish={draft} initialValues={{ category: 'ats-los', use_ai: false }}>
          <Space.Compact block>
            <Form.Item name="category" label="Occurrence category" style={{ width: '40%' }}><Select options={catOptions} /></Form.Item>
            <Form.Item name="title" label="Title" rules={[{ required: true }]} style={{ width: '60%' }}><Input /></Form.Item>
          </Space.Compact>
          <Form.Item name="source" label="Source (report number, agency, link)"><Input /></Form.Item>
          <Tabs activeKey={src} onChange={(k) => setSrc(k as any)} items={[
            { key: 'text', label: 'Paste text', children: <Form.Item name="text" rules={src === 'text' ? [{ required: true, min: 200 }] : []}><Input.TextArea rows={9} placeholder="Paste the history of the flight, analysis and findings sections" /></Form.Item> },
            { key: 'pdf', label: 'Upload PDF', children: <Upload beforeUpload={(f) => { setFile(f); return false }} maxCount={1} accept="application/pdf" onRemove={() => setFile(null)}>
              <Button icon={<UploadOutlined />}>Choose PDF (text-based, ≤ 30 MB)</Button></Upload> },
          ]} />
          <Form.Item name="use_ai" label="Drafter" valuePropName="checked" style={{ marginTop: 8 }}
            extra={meta?.ai_available
              ? `On: Claude (${meta.llm_model}) drafts the AcciMap. Only send published final reports — protected investigation records (ICAO Annex 13 §5.12) must not leave AirNav. Off: offline drafter (factor keywords).`
              : 'AI drafting is not configured on this server (ARAP_ANTHROPIC_API_KEY). The offline drafter matches sentences to the factor catalogue.'}>
            <Switch disabled={!meta?.ai_available} checkedChildren="AI (Claude)" unCheckedChildren="Offline" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={busy} icon={<RobotOutlined />}>Draft</Button>
        </Form>
      </Modal>
    </div>
  )
}
