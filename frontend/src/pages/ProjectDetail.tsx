import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Descriptions, Form, Input, Modal, Table, App, Spin } from 'antd'
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
  const { data: p } = useQuery({ queryKey: ['project', id], queryFn: () => api.get(`/projects/${id}`) })
  if (!p) return <Spin />

  const create = async (v: any) => {
    try {
      const a = await api.post('/assessments', { ...v, project_id: p.id })
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
      <Modal title="New safety assessment" open={open} onCancel={() => setOpen(false)} footer={null} destroyOnHidden width={640}>
        <Form layout="vertical" onFinish={create}>
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
