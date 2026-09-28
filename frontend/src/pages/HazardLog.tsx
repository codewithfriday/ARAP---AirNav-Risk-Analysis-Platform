import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Col, DatePicker, Drawer, Form, Input, Row, Select, Space, Switch, Table, Tabs, Tag, Timeline, Alert } from 'antd'
import { DownloadOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { Link, useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import { useTranslation } from 'react-i18next'
import { api, download } from '../api'
import { useScheme } from '../hooks'
import { canEdit, useAuth } from '../store'
import { RiskMatrix, RiskTag } from '../components/Risk'
import { PageHeader, StatusTag } from '../components/common'

export default function HazardLog() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const { data: scheme } = useScheme()
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState('')
  const [region, setRegion] = useState<string | undefined>()
  const { data: hazards = [], isLoading } = useQuery({ queryKey: ['hazards'], queryFn: () => api.get('/hazards') })
  const openId = params.get('open')

  const filtered = useMemo(() => hazards.filter((h: any) =>
    (!q || `${h.ref} ${h.title} ${h.unit} ${h.system} ${h.owner}`.toLowerCase().includes(q.toLowerCase())) &&
    (!region || h.current_risk?.region === region)), [hazards, q, region])

  return (
    <div>
      <PageHeader title={t('nav.hazards')} sub="Single register of hazards from every method study, with current and residual risk, controls and owners (Manual §32.2)."
        extra={<Space>
          {canEdit(user) && <Button type="primary" icon={<PlusOutlined />} onClick={() => setParams({ open: 'new' })}>New hazard</Button>}
          <Button icon={<DownloadOutlined />} onClick={() => download('/hazards/export.csv', 'hazard-log.csv')}>CSV</Button>
        </Space>} />
      <Card>
        <Space style={{ marginBottom: 12 }} wrap>
          <Input.Search placeholder={t('common.search')} allowClear onChange={(e) => setQ(e.target.value)} style={{ width: 280 }} />
          <Select placeholder="Risk region" allowClear style={{ width: 200 }} value={region} onChange={setRegion}
            options={scheme?.data.regions.map((r) => ({ value: r.key, label: r.name }))} />
          <span className="muted small">{filtered.length} of {hazards.length}</span>
        </Space>
        <Table rowKey="id" loading={isLoading} dataSource={filtered} size="middle" pagination={{ pageSize: 15 }}
          onRow={(r: any) => ({ onClick: () => setParams({ open: String(r.id) }), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Ref', dataIndex: 'ref', width: 90, sorter: (a: any, b: any) => a.ref.localeCompare(b.ref) },
            { title: 'Hazard', dataIndex: 'title' },
            { title: 'Unit', dataIndex: 'unit', width: 170 },
            { title: 'System', dataIndex: 'system', width: 120 },
            { title: 'Owner', dataIndex: 'owner', width: 140 },
            { title: 'Initial', width: 80, render: (_, r: any) => <RiskTag risk={r.initial_risk} /> },
            { title: 'Residual', width: 85, render: (_, r: any) => <RiskTag risk={r.residual_risk} /> },
            { title: 'Controls', width: 85, render: (_, r: any) => r.controls.length },
            { title: 'Review', dataIndex: 'review_date', width: 110, render: (v, r: any) => v ? <Tag color={r.review_overdue ? 'red' : 'default'}>{v}</Tag> : '—' },
            { title: 'Status', dataIndex: 'status', width: 90, render: (s) => <StatusTag s={s} /> },
          ]} />
      </Card>
      <HazardDrawer id={openId} onClose={() => setParams({})} />
    </div>
  )
}

const CONTROL_DEFAULT = { text: '', kind: 'procedure', side: 'prevention', owner: '', verification: 'existing-unverified', effectiveness: 'unknown', critical: false, spi: '' }

function HazardDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const user = useAuth((s) => s.user)
  const qc = useQueryClient()
  const { message } = App.useApp()
  const { data: scheme } = useScheme()
  const isNew = id === 'new'
  const { data: h } = useQuery({ queryKey: ['hazard', id], queryFn: () => api.get(`/hazards/${id}`), enabled: !!id && !isNew })
  const [form] = Form.useForm()
  const [controls, setControls] = useState<any[]>([])
  const [initial, setInitial] = useState<any>({})
  const [residual, setResidual] = useState<any>({})
  const [similar, setSimilar] = useState<any[]>([])

  useEffect(() => {
    if (isNew) {
      form.resetFields(); setControls([]); setInitial({}); setResidual({})
    } else if (h) {
      form.setFieldsValue({ ...h, review_date: h.review_date ? dayjs(h.review_date) : null })
      setControls(h.controls.map((c: any) => ({ ...c })))
      setInitial({ severity: h.initial_severity, likelihood: h.initial_likelihood })
      setResidual({ severity: h.residual_severity, likelihood: h.residual_likelihood })
    }
  }, [h, isNew, form])

  const editable = canEdit(user)
  const save = async () => {
    const v = await form.validateFields()
    const body = { ...v, review_date: v.review_date ? v.review_date.format('YYYY-MM-DD') : null,
      initial_severity: initial.severity ?? null, initial_likelihood: initial.likelihood ?? null,
      residual_severity: residual.severity ?? null, residual_likelihood: residual.likelihood ?? null,
      controls: controls.filter((c) => c.text.trim()).map(({ id: _i, hazard_id: _h, ...c }) => c), assessment_id: h?.assessment_id ?? null }
    try {
      if (isNew) await api.post('/hazards', body)
      else await api.put(`/hazards/${id}`, body)
      message.success('Saved')
      qc.invalidateQueries({ queryKey: ['hazards'] })
      qc.invalidateQueries({ queryKey: ['hazard', id] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      if (isNew) onClose()
    } catch (e: any) {
      message.error(e.message)
    }
  }
  const checkSimilar = async (text: string) => {
    if (!isNew || text.length < 8) return setSimilar([])
    setSimilar(await api.get(`/hazards/similar?text=${encodeURIComponent(text)}`))
  }
  const setC = (i: number, k: string, v: any) => setControls((cs) => cs.map((c, j) => (j === i ? { ...c, [k]: v } : c)))

  return (
    <Drawer open={!!id} onClose={onClose} size={880} destroyOnHidden
      title={isNew ? 'New hazard' : h ? `${h.ref} — ${h.title}` : '…'}
      extra={editable && <Button type="primary" onClick={save}>Save</Button>}>
      <Tabs items={[
        { key: 'd', label: 'Details and risk', children: (
          <Form form={form} layout="vertical" disabled={!editable}>
            {similar.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title="Possible duplicates (COM-06)"
              description={similar.map((s) => <div key={s.id}>{s.ref} · {s.title} ({Math.round(s.similarity * 100)}%)</div>)} />}
            <Form.Item name="title" label="Hazard" rules={[{ required: true }]}><Input onBlur={(e) => checkSimilar(e.target.value)} /></Form.Item>
            <Row gutter={12}>
              <Col span={12}><Form.Item name="causes" label="Causes / threats"><Input.TextArea rows={2} /></Form.Item></Col>
              <Col span={12}><Form.Item name="consequences" label="Consequences"><Input.TextArea rows={2} /></Form.Item></Col>
              <Col span={8}><Form.Item name="unit" label="Unit"><Input /></Form.Item></Col>
              <Col span={8}><Form.Item name="system" label="System"><Input /></Form.Item></Col>
              <Col span={8}><Form.Item name="owner" label="Owner"><Input /></Form.Item></Col>
              <Col span={8}><Form.Item name="status" label="Status" initialValue="open"><Select options={['open', 'monitoring', 'closed'].map((v) => ({ value: v, label: v }))} /></Form.Item></Col>
              <Col span={8}><Form.Item name="review_date" label="Review date"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Initial / current risk <RiskTag scheme={scheme?.data} sev={initial.severity} lik={initial.likelihood} /></div>
                <RiskMatrix scheme={scheme?.data} value={initial} onChange={setInitial} size={40} disabled={!editable} />
              </Col>
              <Col span={12}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Residual risk <RiskTag scheme={scheme?.data} sev={residual.severity} lik={residual.likelihood} />
                  {residual.severity && editable && <Button size="small" type="link" onClick={() => setResidual({})}>clear</Button>}</div>
                <RiskMatrix scheme={scheme?.data} value={residual} onChange={setResidual} size={40} disabled={!editable} />
              </Col>
            </Row>
            <Form.Item name="rationale" label="Rationale and evidence for the ratings (required for residual risk)" style={{ marginTop: 12 }}><Input.TextArea rows={2} /></Form.Item>
            <Form.Item name="description" label="Description / context"><Input.TextArea rows={2} /></Form.Item>
          </Form>) },
        { key: 'c', label: `Controls (${controls.length})`, children: (
          <div>
            <div className="small muted" style={{ marginBottom: 8 }}>Only “existing-verified” controls may be credited in the current risk (COM-09).</div>
            {controls.map((c, i) => (
              <Card key={i} size="small" style={{ marginBottom: 8 }}>
                <Space wrap align="start">
                  <Input.TextArea value={c.text} onChange={(e) => setC(i, 'text', e.target.value)} placeholder="Control / barrier" rows={1} style={{ width: 300 }} disabled={!editable} />
                  <Select value={c.side} onChange={(v) => setC(i, 'side', v)} style={{ width: 120 }} options={['prevention', 'recovery'].map((v) => ({ value: v, label: v }))} disabled={!editable} />
                  <Select value={c.kind} onChange={(v) => setC(i, 'kind', v)} style={{ width: 150 }} options={['hardware', 'software', 'human', 'human-hardware', 'procedure', 'organisational'].map((v) => ({ value: v, label: v }))} disabled={!editable} />
                  <Select value={c.verification} onChange={(v) => setC(i, 'verification', v)} style={{ width: 170 }} options={['existing-verified', 'existing-unverified', 'planned'].map((v) => ({ value: v, label: v }))} disabled={!editable} />
                  <Select value={c.effectiveness} onChange={(v) => setC(i, 'effectiveness', v)} style={{ width: 120 }} options={['very good', 'good', 'poor', 'very poor', 'unknown'].map((v) => ({ value: v, label: v }))} disabled={!editable} />
                  <Input value={c.owner} onChange={(e) => setC(i, 'owner', e.target.value)} placeholder="Owner" style={{ width: 150 }} disabled={!editable} />
                  <Space><Switch size="small" checked={c.critical} onChange={(v) => setC(i, 'critical', v)} disabled={!editable} /> critical</Space>
                  {editable && <Button danger size="small" icon={<DeleteOutlined />} onClick={() => setControls((cs) => cs.filter((_, j) => j !== i))} />}
                </Space>
              </Card>
            ))}
            {editable && <Button icon={<PlusOutlined />} onClick={() => setControls((cs) => [...cs, { ...CONTROL_DEFAULT }])}>Add control</Button>}
          </div>) },
        ...(!isNew && h ? [
          { key: 'l', label: 'Links', children: (
            <div>
              <p>Source: {h.source_study ? <Link to={`/studies/${h.source_study.id}`}>{h.source_study.title}</Link> : 'entered directly'}</p>
              <p>Assessment: {h.assessment_id ? <Link to={`/assessments/${h.assessment_id}`}>#{h.assessment_id}</Link> : '—'}</p>
              <h4>Actions</h4>
              {h.actions.map((x: any) => <div key={x.id}><Tag>{x.ref}</Tag>{x.text} · {x.owner} · due {x.due_date} <StatusTag s={x.status} /></div>)}
              {!h.actions.length && <span className="muted">None</span>}
            </div>) },
          { key: 'h', label: 'History', children: (
            <Timeline items={h.history.map((x: any) => ({ content: <div><b>{x.action}</b> by {x.username} <span className="muted small">{x.at.slice(0, 16).replace('T', ' ')}</span>
              {x.after && <div className="small mono muted">{Object.keys(x.after).join(', ')}</div>}</div> }))} />) },
        ] : []),
      ]} />
    </Drawer>
  )
}
