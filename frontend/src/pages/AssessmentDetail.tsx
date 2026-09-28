import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Descriptions, Form, Input, Modal, Row, Select, Space, Spin, Table, Tag, Timeline, Tooltip, Typography } from 'antd'
import { DownloadOutlined, PlusOutlined, BranchesOutlined, EditOutlined } from '@ant-design/icons'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, download } from '../api'
import { useAuth, canEdit } from '../store'
import { useMethods, useScheme } from '../hooks'
import { RiskTag } from '../components/Risk'
import { PageHeader, StatusTag } from '../components/common'
import { METHOD_COLORS } from '../risk'

// Manual §4.1 recommended combinations (COM-03, advisory)
const RECOMMEND: Record<string, string[]> = {
  system: ['hazid', 'fha', 'fmea', 'fta', 'bowtie'],
  procedure: ['hazid', 'hazop', 'stpa', 'bowtie', 'lopa'],
  airspace: ['hazid', 'hazop', 'bowtie', 'lopa'],
  organisational: ['hazid', 'fatigue', 'jha', 'bowtie'],
  temporary: ['hazid', 'jha', 'bowtie'],
}

const ACTIONS: Record<string, { label: string; from: string[]; roles: string[]; danger?: boolean; comment?: boolean }> = {
  submit: { label: 'Submit for review', from: ['draft', 'rejected'], roles: ['assessor', 'reviewer'] },
  return: { label: 'Return to assessor', from: ['in_review'], roles: ['reviewer'], comment: true },
  endorse: { label: 'Endorse', from: ['in_review'], roles: ['reviewer'] },
  accept: { label: 'Accept residual risk', from: ['endorsed'], roles: ['authority'] },
  reject: { label: 'Reject', from: ['endorsed', 'in_review'], roles: ['reviewer', 'authority'], danger: true, comment: true },
  close: { label: 'Close', from: ['accepted'], roles: ['reviewer', 'authority'] },
}

export default function AssessmentDetail() {
  const { id } = useParams()
  const user = useAuth((s) => s.user)!
  const nav = useNavigate()
  const qc = useQueryClient()
  const { message, modal } = App.useApp()
  const { data: a, refetch } = useQuery({ queryKey: ['assessment', id], queryFn: () => api.get(`/assessments/${id}`) })
  const { data: methods } = useMethods()
  const { data: scheme } = useScheme()
  const { data: project } = useQuery({ queryKey: ['project', a?.project_id], queryFn: () => api.get(`/projects/${a.project_id}`), enabled: !!a })
  const [addOpen, setAddOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [transition, setTransition] = useState<string | null>(null)
  if (!a || !methods) return <Spin />

  const editable = canEdit(user) && !a.locked
  const rec = RECOMMEND[project?.change_type ?? 'system'] ?? []
  const allowed = Object.entries(ACTIONS).filter(([, v]) => v.from.includes(a.status) && (user.role === 'admin' || v.roles.includes(user.role)))

  const doTransition = async (action: string, comment = '') => {
    try {
      await api.post(`/assessments/${a.id}/transition`, { action, comment })
      message.success(`Assessment ${({ submit: 'submitted', return: 'returned', endorse: 'endorsed', accept: 'accepted', reject: 'rejected', close: 'closed' } as Record<string, string>)[action] ?? action}`)
      setTransition(null)
      refetch()
      qc.invalidateQueries({ queryKey: ['assessments'] })
    } catch (e: any) {
      message.error(e.message)
    }
  }

  const newVersion = () => modal.confirm({ title: 'Create a new version?', content: 'The current version stays locked and is marked superseded. Studies are copied into an editable draft.',
    onOk: async () => { const b = await api.post(`/assessments/${a.id}/new-version`); nav(`/assessments/${b.id}`) } })

  const addStudy = async (v: any) => {
    try {
      const s = await api.post('/studies', { assessment_id: a.id, method: v.method, title: v.title || methods[v.method].name })
      nav(`/studies/${s.id}`)
    } catch (e: any) {
      message.error(e.message)
    }
  }

  const saveMeta = async (v: any) => {
    try {
      await api.put(`/assessments/${a.id}`, { ...v, project_id: a.project_id })
      setEditOpen(false)
      refetch()
    } catch (e: any) {
      message.error(e.message)
    }
  }

  return (
    <div>
      <PageHeader
        title={<Space>{a.title}<StatusTag s={a.status} /><Tag>v{a.version}</Tag></Space>}
        sub={<Link to={`/projects/${a.project.id}`}>← {a.project.code} — {a.project.title}</Link>}
        extra={
          <Space wrap>
            {allowed.map(([k, v]) => (
              <Button key={k} danger={v.danger} type={k === 'accept' || k === 'endorse' || k === 'submit' ? 'primary' : 'default'}
                onClick={() => (v.comment || k === 'accept' ? setTransition(k) : doTransition(k))}>{v.label}</Button>
            ))}
            {a.locked && canEdit(user) && a.status !== 'superseded' && <Button icon={<BranchesOutlined />} onClick={newVersion}>New version</Button>}
            <Button icon={<DownloadOutlined />} onClick={() => download(`/assessments/${a.id}/report.docx`, `ARAP-${a.project.code}-v${a.version}.docx`)}>Report (.docx)</Button>
          </Space>
        } />
      {a.locked && <Alert type="info" showIcon title={`This assessment is ${a.status} and locked. Create a new version to make changes.`} style={{ marginBottom: 16 }} />}
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Card title="Scope, environment and assumptions" extra={editable && <Button size="small" icon={<EditOutlined />} onClick={() => setEditOpen(true)}>Edit</Button>}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Scope">{a.scope || '—'}</Descriptions.Item>
              <Descriptions.Item label="Environment">{a.environment || '—'}</Descriptions.Item>
              <Descriptions.Item label="Assumptions">{a.assumptions || '—'}</Descriptions.Item>
              <Descriptions.Item label="Risk scheme">version {a.risk_scheme_version}</Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title={`Method studies (${a.studies.length})`} style={{ marginTop: 16 }}
            extra={editable && <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>Add study</Button>}>
            {editable && rec.length > 0 && (
              <div className="small muted" style={{ marginBottom: 10 }}>
                Suggested for a <b>{project?.change_type}</b> change (Manual §4.1): {rec.map((m) => <Tag key={m} color={METHOD_COLORS[m]}>{methods[m].name}</Tag>)}
              </div>
            )}
            <Table rowKey="id" dataSource={a.studies} pagination={false} size="small"
              columns={[
                { title: 'Method', dataIndex: 'method', width: 190, render: (m) => <Tag color={METHOD_COLORS[m]}>{methods[m]?.name}</Tag> },
                { title: 'Study', dataIndex: 'title', render: (v, r: any) => <Link to={`/studies/${r.id}`}>{v}</Link> },
                { title: 'Status', dataIndex: 'status', width: 100 },
                { title: 'Updated', dataIndex: 'updated_at', width: 150, render: (v) => v?.slice(0, 16).replace('T', ' ') },
              ]} />
          </Card>
          <Card title={`Hazards (${a.hazards.length})`} style={{ marginTop: 16 }} extra={<Link to="/hazards">Open hazard log →</Link>}>
            <Table rowKey="id" dataSource={a.hazards} pagination={false} size="small"
              columns={[
                { title: 'Ref', dataIndex: 'ref', width: 90, render: (v, r: any) => <Link to={`/hazards?open=${r.id}`}>{v}</Link> },
                { title: 'Hazard', dataIndex: 'title' },
                { title: 'Initial', width: 80, render: (_, r: any) => <RiskTag risk={r.initial_risk} /> },
                { title: 'Residual', width: 80, render: (_, r: any) => <RiskTag risk={r.residual_risk} /> },
                { title: 'Controls', width: 80, render: (_, r: any) => r.controls.length },
              ]} />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Risk acceptance">
            {a.worst_residual_region ? (
              <>
                <div>Worst current/residual region: <Tag color={scheme?.data.regions.find((r) => r.key === a.worst_residual_region)?.color}>
                  {scheme?.data.regions.find((r) => r.key === a.worst_residual_region)?.name}</Tag></div>
                <div style={{ marginTop: 8 }}>Acceptance authority: <b>{a.required_authority ?? 'cannot be accepted'}</b></div>
              </>
            ) : <Typography.Text type="secondary">No hazards rated yet.</Typography.Text>}
          </Card>
          <Card title={`Actions (${a.actions.length})`} style={{ marginTop: 16 }} extra={<Link to="/actions">All actions →</Link>}>
            {a.actions.map((x: any) => (
              <div key={x.id} style={{ marginBottom: 8 }}>
                <Tag>{x.ref}</Tag>{x.text}
                <div className="small muted">{x.owner} · due {x.due_date ?? '—'} · <StatusTag s={x.status} /></div>
              </div>
            ))}
            {!a.actions.length && <Typography.Text type="secondary">None</Typography.Text>}
          </Card>
          <Card title="Review and approval history" style={{ marginTop: 16 }}>
            {a.approvals.length ? (
              <Timeline items={a.approvals.map((x: any) => ({
                color: x.action === 'reject' ? 'red' : x.action === 'accept' ? 'green' : 'blue',
                content: <div><b>{x.action}</b> by {x.username}<div className="small muted">{x.at.slice(0, 16).replace('T', ' ')} · {x.from_status} → {x.to_status}</div>{x.comment && <div className="small">“{x.comment}”</div>}</div>,
              }))} />
            ) : <Typography.Text type="secondary">Not yet submitted.</Typography.Text>}
          </Card>
        </Col>
      </Row>

      <Modal title="Add method study" open={addOpen} onCancel={() => setAddOpen(false)} footer={null} destroyOnHidden width={620}>
        <Form layout="vertical" onFinish={addStudy}>
          <Form.Item name="method" label="Method" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={Object.entries(methods).map(([k, m]: any) => ({ value: k, label: `${m.name}${rec.includes(k) ? '  ★ suggested' : ''}`,
              title: m.summary }))} optionRender={(o) => <div><b>{o.label}</b><div className="small muted">{methods[o.value as string].summary} (Manual ch. {methods[o.value as string].chapter})</div></div>} />
          </Form.Item>
          <Form.Item name="title" label="Study title"><Input placeholder="e.g. HAZOP of cut-over plan" /></Form.Item>
          <Button type="primary" htmlType="submit">Create and open</Button>
        </Form>
      </Modal>
      <Modal title="Edit scope" open={editOpen} onCancel={() => setEditOpen(false)} footer={null} destroyOnHidden width={640}>
        <Form layout="vertical" onFinish={saveMeta} initialValues={a}>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="scope" label="Scope"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="environment" label="Environment"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="assumptions" label="Assumptions"><Input.TextArea rows={2} /></Form.Item>
          <Button type="primary" htmlType="submit">Save</Button>
        </Form>
      </Modal>
      <Modal title={transition ? ACTIONS[transition].label : ''} open={!!transition} onCancel={() => setTransition(null)} footer={null} destroyOnHidden>
        <Form layout="vertical" onFinish={(v) => doTransition(transition!, v.comment ?? '')}>
          {transition === 'accept' && (
            <Alert type="warning" showIcon style={{ marginBottom: 12 }}
              title={`You are accepting residual risk in region "${a.worst_residual_region ?? 'n/a'}". Required authority: ${a.required_authority ?? '—'}.`} />
          )}
          <Form.Item name="comment" label="Comment" rules={[{ required: !!(transition && ACTIONS[transition].comment) }]}><Input.TextArea rows={3} /></Form.Item>
          <Tooltip title="Recorded in the approval history and audit trail"><Button type="primary" htmlType="submit">Confirm</Button></Tooltip>
        </Form>
      </Modal>
    </div>
  )
}
