import { Tag } from 'antd'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', in_review: 'processing', endorsed: 'cyan', accepted: 'success', rejected: 'error', closed: 'purple',
  superseded: 'default', open: 'warning', in_progress: 'processing',
}

export const StatusTag = ({ s }: { s: string }) => <Tag color={STATUS_COLORS[s] ?? 'default'}>{s.replace('_', ' ')}</Tag>

export function PageHeader({ title, sub, extra }: { title: React.ReactNode; sub?: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
      <div>
        <h1 className="page-title">{title}</h1>
        {sub && <div className="page-sub">{sub}</div>}
      </div>
      {extra && <div>{extra}</div>}
    </div>
  )
}
