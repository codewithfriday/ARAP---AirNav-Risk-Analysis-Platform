import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, App } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { canEdit, useAuth } from '../store'
import { PageHeader, StatusTag } from '../components/common'

export default function Projects() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const qc = useQueryClient()
  const nav = useNavigate()
  const { message } = App.useApp()
  const [open, setOpen] = useState(false)
  const [showArchived, setShowArchived] = useState(false)
  const qs = showArchived ? '?include_archived=true' : ''
  const { data: projects = [], isLoading } = useQuery({ queryKey: ['projects', showArchived], queryFn: () => api.get(`/projects${qs}`) })
  const { data: assessments = [] } = useQuery({ queryKey: ['assessments', showArchived], queryFn: () => api.get(`/assessments${qs}`) })

  const create = async (v: any) => {
    try {
      const p = await api.post('/projects', v)
      qc.invalidateQueries({ queryKey: ['projects'] })
      setOpen(false)
      nav(`/projects/${p.id}`)
    } catch (e: any) {
      message.error(e.message)
    }
  }

  return (
    <div>
      <PageHeader title={t('nav.projects')} sub="A project is a change (system, procedure, airspace, organisational). Each has one or more safety assessments."
        extra={canEdit(user) && <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>New project</Button>} />
      <Card title="Projects" style={{ marginBottom: 16 }}
        extra={<Space><span className="small muted">Show archived</span><Switch size="small" checked={showArchived} onChange={setShowArchived} /></Space>}>
        <Table rowKey="id" loading={isLoading} dataSource={projects} pagination={false} size="middle"
          columns={[
            { title: 'Code', dataIndex: 'code', width: 130, render: (v, r: any) => <Space size={4}><Link to={`/projects/${r.id}`}>{v}</Link>{r.status === 'archived' && <Tag>archived</Tag>}</Space> },
            { title: 'Title', dataIndex: 'title' },
            { title: 'Type', dataIndex: 'change_type', width: 130 },
            { title: 'Units', dataIndex: 'units' },
            { title: 'Assessments', dataIndex: 'assessment_count', width: 120 },
          ]} />
      </Card>
      <Card title="All assessments">
        <Table rowKey="id" dataSource={assessments} pagination={{ pageSize: 10 }} size="middle"
          columns={[
            { title: 'Project', dataIndex: 'project_code', width: 130 },
            { title: 'Assessment', dataIndex: 'title', render: (v, r: any) => <Link to={`/assessments/${r.id}`}>{v}</Link> },
            { title: 'Version', dataIndex: 'version', width: 90 },
            { title: 'Status', dataIndex: 'status', width: 130, render: (s) => <StatusTag s={s} />,
              filters: ['draft', 'in_review', 'endorsed', 'accepted', 'rejected', 'closed', 'superseded'].map((x) => ({ text: x, value: x })),
              onFilter: (v, r: any) => r.status === v },
            { title: 'Updated', dataIndex: 'updated_at', width: 170, render: (v) => v?.slice(0, 16).replace('T', ' ') },
          ]} />
      </Card>
      <Modal title="New project" open={open} onCancel={() => setOpen(false)} footer={null} destroyOnHidden>
        <Form layout="vertical" onFinish={create} initialValues={{ change_type: 'system' }}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}><Input placeholder="e.g. ADSB-2027" /></Form.Item>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="change_type" label="Type of change">
            <Select options={['system', 'procedure', 'airspace', 'organisational', 'temporary'].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item name="units" label="Units affected"><Input /></Form.Item>
          <Form.Item name="sponsor" label="Change sponsor"><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea rows={3} /></Form.Item>
          <Button type="primary" htmlType="submit">{t('common.create')}</Button>
        </Form>
      </Modal>
    </div>
  )
}
