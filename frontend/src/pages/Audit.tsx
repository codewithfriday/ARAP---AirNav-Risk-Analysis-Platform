import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Select, Table, Tag } from 'antd'
import { api } from '../api'
import { PageHeader } from '../components/common'

export default function Audit() {
  const [entity, setEntity] = useState<string | undefined>()
  const { data = [], isLoading } = useQuery({ queryKey: ['audit', entity], queryFn: () => api.get(`/audit?limit=500${entity ? `&entity=${entity}` : ''}`) })
  return (
    <div>
      <PageHeader title="Audit trail" sub="Append-only record of every create, change, approval and export (SEC-05)."
        extra={<Select allowClear placeholder="Filter entity" style={{ width: 200 }} value={entity} onChange={setEntity}
          options={['assessment', 'study', 'hazard', 'action', 'project', 'user', 'risk_scheme'].map((v) => ({ value: v, label: v }))} />} />
      <Card>
        <Table rowKey="id" loading={isLoading} dataSource={data} size="small" pagination={{ pageSize: 25 }}
          columns={[
            { title: 'When', dataIndex: 'at', width: 160, render: (v) => v.slice(0, 19).replace('T', ' ') },
            { title: 'User', dataIndex: 'username', width: 110 },
            { title: 'Entity', dataIndex: 'entity', width: 110, render: (v, r: any) => `${v} #${r.entity_id}` },
            { title: 'Action', dataIndex: 'action', width: 110, render: (v) => <Tag>{v}</Tag> },
            { title: 'Change', render: (_, r: any) => <span className="mono small">{r.after ? JSON.stringify(r.after).slice(0, 180) : r.before ? `deleted ${JSON.stringify(r.before).slice(0, 120)}` : ''}</span> },
          ]} />
      </Card>
    </div>
  )
}
