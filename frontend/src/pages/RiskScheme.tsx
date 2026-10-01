import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Col, Row, Select, Space, Table, Tag, Alert } from 'antd'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { useAtsbScheme, useScheme } from '../hooks'
import { isAdmin, useAuth } from '../store'
import { RiskMatrix } from '../components/Risk'
import { PageHeader } from '../components/common'
import { fmtSci, type Scheme } from '../risk'

export default function RiskSchemePage() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const qc = useQueryClient()
  const { message } = App.useApp()
  const { data } = useScheme()
  const { data: atsb } = useAtsbScheme()
  const [draft, setDraft] = useState<Scheme | null>(null)
  const [paint, setPaint] = useState<string>('acceptable')
  useEffect(() => { if (data) setDraft(structuredClone(data.data)) }, [data])
  if (!draft || !data) return null
  const admin = isAdmin(user)

  const assign = ({ severity, likelihood }: { severity: string; likelihood: number }) => {
    const cell = `${likelihood}${severity}`
    setDraft({ ...draft, regions: draft.regions.map((r) => ({ ...r, cells: r.key === paint ? [...r.cells.filter((c) => c !== cell), cell] : r.cells.filter((c) => c !== cell) })) })
  }
  const save = async () => {
    try {
      await api.put('/risk/scheme', draft)
      message.success('New scheme version saved')
      qc.invalidateQueries({ queryKey: ['scheme'] })
    } catch (e: any) {
      message.error(e.message)
    }
  }

  return (
    <div>
      <PageHeader title={t('nav.scheme')} sub={`Active version ${data.version}. Changes create a new version and never alter locked assessments (ADM-01).`}
        extra={admin && <Button type="primary" onClick={save}>Save as new version</Button>} />
      {admin && <Alert type="info" showIcon style={{ marginBottom: 16 }} title="Administrator: choose a region below, then click matrix cells to reassign them." />}
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={11}>
          <Card title="Risk matrix" extra={admin && <Space>Paint region <Select size="small" value={paint} onChange={setPaint} style={{ width: 170 }}
            options={draft.regions.map((r) => ({ value: r.key, label: r.name }))} /></Space>}>
            <RiskMatrix scheme={draft} onChange={admin ? assign : undefined} size={56} />
          </Card>
        </Col>
        <Col xs={24} xl={13}>
          <Card title="Tolerability and acceptance authority">
            <Table rowKey="key" size="small" pagination={false} dataSource={draft.regions} columns={[
              { title: 'Region', dataIndex: 'name', render: (v, r) => <Tag color={r.color}>{v}</Tag> },
              { title: 'Cells', dataIndex: 'cells', render: (c: string[]) => [...c].sort().join(', ') },
              { title: 'Required action', dataIndex: 'action' },
              { title: 'Authority', dataIndex: 'authority', render: (v) => v ?? <b>Cannot be accepted</b> },
            ]} />
          </Card>
          <Card title="Likelihood levels" style={{ marginTop: 16 }}>
            <Table rowKey="level" size="small" pagination={false} dataSource={draft.likelihood} columns={[
              { title: 'Level', dataIndex: 'level', width: 70 }, { title: 'Name', dataIndex: 'name' }, { title: 'Nama', dataIndex: 'name_id' },
              { title: `Band (${draft.quantitative_unit})`, render: (_, l) => `${l.lower === null ? '< ' : fmtSci(l.lower, 0)}${l.lower !== null && l.upper !== null ? ' to ' : ''}${l.upper === null ? ' and above' : fmtSci(l.upper, 0)}` },
            ]} />
          </Card>
        </Col>
      </Row>
      {atsb && <Card style={{ marginTop: 16 }} title="Option: ATSB 6×6 matrix for safety issues (Manual Appendix F)"
        extra={<span className="small muted">Used when a safety issue in an ATSB analysis is rated on the ATSB scale</span>}>
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={11}>
            <RiskMatrix scheme={{ ...atsb.data, severity: atsb.data.severity.map((s: any) => ({ ...s, name: s.short ?? s.name })) } as any} size={50} />
          </Col>
          <Col xs={24} xl={13}>
            <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Colours follow the AirNav 5×5"
              description="ATSB rates a potential safety issue Critical, Significant or Broadly acceptable (not a safety issue). The published cell colours are not available as text, so NAVRAP fills the 6×6 by the same pattern as the AirNav matrix: critical = intolerable red, significant = the two tolerable bands (near-critical amber, lower yellow), broadly acceptable = green. Every Catastrophic cell is at least significant. A safety issue rated on the AirNav 5×5 maps to the same three levels." />
            <Table rowKey="key" size="small" pagination={false} dataSource={atsb.data.regions} columns={[
              { title: 'Level', dataIndex: 'name', render: (v, r: any) => <Tag color={r.color}>{v}</Tag> },
              { title: 'Cells', dataIndex: 'cells', render: (c: string[]) => [...c].sort().join(', ') },
              { title: 'Safety action', dataIndex: 'action' },
            ]} />
            <Table style={{ marginTop: 12 }} rowKey="level" size="small" pagination={false} dataSource={atsb.data.likelihood} columns={[
              { title: 'Level', dataIndex: 'level', width: 60 }, { title: 'Likelihood', dataIndex: 'name', width: 150 }, { title: 'Indicative', dataIndex: 'indicative' }]} />
            <Table style={{ marginTop: 12 }} rowKey="code" size="small" pagination={false} dataSource={atsb.data.severity} columns={[
              { title: 'Code', dataIndex: 'code', width: 60 }, { title: 'Consequence', dataIndex: 'name', width: 190 }, { title: 'Guide (passenger operations)', dataIndex: 'description' }]} />
          </Col>
        </Row>
      </Card>}
    </div>
  )
}
