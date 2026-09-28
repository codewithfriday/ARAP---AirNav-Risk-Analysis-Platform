import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Form, Input, Modal, Select, Switch, Table, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../api'
import { useScheme } from '../hooks'
import { PageHeader } from '../components/common'

export default function Users() {
  const qc = useQueryClient()
  const { message } = App.useApp()
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api.get('/users') })
  const { data: scheme } = useScheme()
  const [edit, setEdit] = useState<any | null>(null)
  const [form] = Form.useForm()
  const open = (u: any) => { setEdit(u); form.setFieldsValue({ role: 'viewer', active: true, authority_scope: [], ...u, password: '' }) }
  const save = async () => {
    const v = await form.validateFields()
    try {
      if (edit?.id) await api.put(`/users/${edit.id}`, { ...v, username: edit.username })
      else await api.post('/users', v)
      qc.invalidateQueries({ queryKey: ['users'] })
      setEdit(null)
    } catch (e: any) {
      message.error(e.message)
    }
  }
  return (
    <div>
      <PageHeader title="Users and roles" sub="Roles: admin, assessor, reviewer, authority (risk acceptance), viewer. In production, identities come from Keycloak / SSO."
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => open({})}>New user</Button>} />
      <Card>
        <Table rowKey="id" dataSource={users} size="middle" onRow={(r: any) => ({ onClick: () => open(r), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Username', dataIndex: 'username' }, { title: 'Name', dataIndex: 'full_name' },
            { title: 'Role', dataIndex: 'role', render: (r) => <Tag color="blue">{r}</Tag> }, { title: 'Unit', dataIndex: 'unit' },
            { title: 'May accept', dataIndex: 'authority_scope', render: (s: string[]) => s?.map((x) => <Tag key={x}>{x}</Tag>) },
            { title: 'Active', dataIndex: 'active', render: (a) => (a ? 'yes' : 'no') },
          ]} />
      </Card>
      <Modal title={edit?.id ? `Edit ${edit.username}` : 'New user'} open={!!edit} onOk={save} onCancel={() => setEdit(null)} destroyOnHidden>
        <Form form={form} layout="vertical">
          {!edit?.id && <Form.Item name="username" label="Username" rules={[{ required: true }]}><Input /></Form.Item>}
          <Form.Item name="full_name" label="Full name"><Input /></Form.Item>
          <Form.Item name="email" label="E-mail"><Input /></Form.Item>
          <Form.Item name="role" label="Role"><Select options={['admin', 'assessor', 'reviewer', 'authority', 'viewer'].map((v) => ({ value: v, label: v }))} /></Form.Item>
          <Form.Item name="unit" label="Unit"><Input /></Form.Item>
          <Form.Item name="authority_scope" label="Risk regions this user may accept"><Select mode="multiple" options={scheme?.data.regions.filter((r) => r.authority).map((r) => ({ value: r.key, label: r.name }))} /></Form.Item>
          <Form.Item name="password" label={edit?.id ? 'New password (leave blank to keep)' : 'Password (min. 8 characters)'} rules={edit?.id ? [] : [{ required: true, min: 8 }]}><Input.Password /></Form.Item>
          <Form.Item name="active" label="Active" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
