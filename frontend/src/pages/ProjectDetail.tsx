import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Descriptions, Form, Input, Modal, Select, Table, Tag, App, Spin } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { canEdit, useAuth } from '../store'
import { PageHeader, StatusTag } from '../components/common'

export default function ProjectDetail() {
  const { id } = useParams()
  const user = useAuth((s) => s.user)
  const nav = useNavigate()
  const qc = useQueryClient()
  const { message } = App.useApp()
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()
  const [tpl, setTpl] = useState<any>(null)
  const { data: p } = useQuery({ queryKey: ['project', id], queryFn: () => api.get(`/projects/${id}`) })
  const { data: templates = [] } = useQuery({ queryKey: ['assessment-templates'], queryFn: () => api.get('/assessment-templates'), enabled: open })
  const pickTemplate = (key: string | undefined) => {
    const t = templates.find((x: any) => x.key === key) ?? null
    setTpl(t)
    if (t) form.setFieldsValue({ title: t.title, scope: t.scope, environment: t.environment, assumptions: t.assumptions })
  }
  if (!p) return <Spin />

  const create = async (v: any) => {
    try {
      const a = await api.post('/assessments', { ...v, project_id: p.id, template: tpl?.key })
      qc.invalidateQueries({ queryKey: ['project', id] })
      nav(`/assessments/${a.id}`)
    } catch (e: any) {
      message.error(e.message)
    }
  }

  return (
    <div>
      <PageHeader title={`${p.code} — ${p.title}`} sub={<Link to="/projects">← All projects</Link>}
        extra={canEdit(user) && <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>New assessment</Button>} />
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, md: 2 }} size="small">
          <Descriptions.Item label="Type of change">{p.change_type}</Descriptions.Item>
          <Descriptions.Item label="Sponsor">{p.sponsor || '—'}</Descriptions.Item>
          <Descriptions.Item label="Units">{p.units || '—'}</Descriptions.Item>
          <Descriptions.Item label="Status">{p.status}</Descriptions.Item>
          <Descriptions.Item label="Description" span={2}>{p.description || '—'}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="Assessments">
        <Table rowKey="id" dataSource={p.assessments} pagination={false}
          columns={[
            { title: 'Assessment', dataIndex: 'title', render: (v, r: any) => <Link to={`/assessments/${r.id}`}>{v}</Link> },
            { title: 'Version', dataIndex: 'version', width: 90 },
            { title: 'Studies', dataIndex: 'study_count', width: 90 },
            { title: 'Status', dataIndex: 'status', width: 130, render: (s) => <StatusTag s={s} /> },
            { title: 'Created by', dataIndex: 'created_by', width: 140 },
          ]} />
      </Card>
      <Modal title="New safety assessment" open={open} onCancel={() => setOpen(false)} footer={null} destroyOnHidden width={720} afterClose={() => { setTpl(null); form.resetFields() }}>
        <Form layout="vertical" onFinish={create} form={form}>
          <Form.Item label="Start from (optional)">
            <Select allowClear placeholder="Blank assessment" value={tpl?.key} onChange={pickTemplate}
              options={templates.map((t: any) => ({ value: t.key, label: t.name }))} />
          </Form.Item>
          {tpl && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={`${tpl.studies.length} pre-filled studies will be created (Manual ${tpl.manual})`}
            description={<div><div className="small">{tpl.summary}</div><div style={{ marginTop: 6 }}>{tpl.studies.map((s: any) => <Tag key={s.key} style={{ marginBottom: 3 }}>{s.method.toUpperCase()}</Tag>)}</div>
              <div className="small muted" style={{ marginTop: 6 }}>Content is proposed: review it, rate likelihoods and confirm severities in the workshops.</div></div>} />}
          <Form.Item name="title" label="Title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="scope" label="Scope and system boundary (Manual §2.3)" rules={[{ required: true }]}><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="environment" label="Operational environment"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="assumptions" label="Assumptions"><Input.TextArea rows={2} /></Form.Item>
          <Button type="primary" htmlType="submit">Create</Button>
        </Form>
      </Modal>
    </div>
  )
}
