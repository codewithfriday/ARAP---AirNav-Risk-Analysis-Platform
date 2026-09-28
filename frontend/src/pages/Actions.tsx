import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, DatePicker, Form, Input, Modal, Select, Table, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { canEdit, useAuth } from '../store'
import { PageHeader, StatusTag } from '../components/common'

export default function Actions() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const qc = useQueryClient()
  const { message } = App.useApp()
  const { data: actions = [], isLoading } = useQuery({ queryKey: ['actions'], queryFn: () => api.get('/actions') })
  const { data: hazards = [] } = useQuery({ queryKey: ['hazards'], queryFn: () => api.get('/hazards') })
  const [edit, setEdit] = useState<any | null>(null)
  const [form] = Form.useForm()

  const open = (a: any) => {
    setEdit(a)
    form.setFieldsValue(a ? { ...a, due_date: a.due_date ? dayjs(a.due_date) : null } : { status: 'open' })
  }
  const save = async () => {
    const v = await form.validateFields()
    const body = { ...v, due_date: v.due_date ? v.due_date.format('YYYY-MM-DD') : null, hazard_id: v.hazard_id ?? null, assessment_id: edit?.assessment_id ?? null }
    try {
      if (edit?.id) await api.put(`/actions/${edit.id}`, body)
      else await api.post('/actions', body)
      qc.invalidateQueries({ queryKey: ['actions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      setEdit(null)
    } catch (e: any) {
      message.error(e.message)
    }
  }
  const hz = Object.fromEntries(hazards.map((h: any) => [h.id, h]))

  return (
    <div>
      <PageHeader title={t('nav.actions')} sub="Risk-reduction actions with owners and due dates. Overdue actions are escalated on the dashboard (COM-12)."
        extra={canEdit(user) && <Button type="primary" icon={<PlusOutlined />} onClick={() => open({})}>New action</Button>} />
      <Card>
        <Table rowKey="id" loading={isLoading} dataSource={actions} size="middle"
          onRow={(r: any) => ({ onClick: () => open(r), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Ref', dataIndex: 'ref', width: 100 },
            { title: 'Action', dataIndex: 'text' },
            { title: 'Hazard', dataIndex: 'hazard_id', width: 110, render: (v) => (v && hz[v] ? hz[v].ref : '—') },
            { title: 'Owner', dataIndex: 'owner', width: 160 },
            { title: 'Due', dataIndex: 'due_date', width: 120, render: (v, r: any) => (v ? <Tag color={r.overdue ? 'red' : 'default'}>{v}</Tag> : '—'),
              sorter: (a: any, b: any) => (a.due_date ?? '').localeCompare(b.due_date ?? '') },
            { title: 'Status', dataIndex: 'status', width: 120, render: (s) => <StatusTag s={s} />,
              filters: ['open', 'in_progress', 'closed'].map((x) => ({ text: x, value: x })), onFilter: (v, r: any) => r.status === v },
          ]} />
      </Card>
      <Modal title={edit?.id ? edit.ref : 'New action'} open={!!edit} onCancel={() => setEdit(null)} onOk={save} okText="Save" destroyOnHidden>
        <Form form={form} layout="vertical">
          <Form.Item name="text" label="Action" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="hazard_id" label="Hazard"><Select allowClear showSearch optionFilterProp="label" options={hazards.map((h: any) => ({ value: h.id, label: `${h.ref} · ${h.title}` }))} /></Form.Item>
          <Form.Item name="owner" label="Owner"><Input /></Form.Item>
          <Form.Item name="due_date" label="Due date"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="status" label="Status"><Select options={['open', 'in_progress', 'closed'].map((v) => ({ value: v, label: v }))} /></Form.Item>
          <Form.Item name="closure_evidence" label="Closure evidence (required to close)"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
