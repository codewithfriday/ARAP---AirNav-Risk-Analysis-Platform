import { Button, Checkbox, Input, InputNumber, Select, Table } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'

export type ECol = {
  key: string
  title: React.ReactNode
  width?: number
  type?: 'text' | 'textarea' | 'number' | 'select' | 'bool' | 'multiselect' | 'tags' | 'readonly'
  options?: (string | { value: any; label: React.ReactNode })[]
  render?: (row: any, i: number) => React.ReactNode
  min?: number
  max?: number
  step?: number
}

/** Small inline-editable table for lists inside method models (keyed by position). */
export default function EditableTable({ columns, rows, onChange, readOnly, newRow, addLabel = 'Add', size = 'small', scrollX }: {
  columns: ECol[]; rows: any[]; onChange: (rows: any[]) => void; readOnly?: boolean; newRow?: () => any; addLabel?: string
  size?: 'small' | 'middle'; scrollX?: number
}) {
  const set = (i: number, k: string, v: any) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)))
  const opts = (o: ECol['options']) => (o ?? []).map((x) => (typeof x === 'string' ? { value: x, label: x } : x))
  const cols: any[] = columns.map((c) => ({
    title: c.title, dataIndex: c.key, width: c.width,
    render: (_: any, r: any) => {
      const i = r._k
      const v = rows[i]?.[c.key]
      if (c.render) return c.render(rows[i], i)
      if (readOnly || c.type === 'readonly') return Array.isArray(v) ? v.join(', ') : typeof v === 'boolean' ? (v ? 'Yes' : '') : v
      switch (c.type) {
        case 'number': return <InputNumber size="small" value={v} min={c.min} max={c.max} step={c.step} style={{ width: '100%' }} onChange={(x) => set(i, c.key, x)} />
        case 'select': return <Select size="small" value={v} allowClear style={{ width: '100%' }} options={opts(c.options)} onChange={(x) => set(i, c.key, x)} />
        case 'multiselect': return <Select size="small" mode="multiple" value={v ?? []} style={{ width: '100%' }} options={opts(c.options)} onChange={(x) => set(i, c.key, x)} />
        case 'tags': return <Select size="small" mode="tags" value={v ?? []} style={{ width: '100%' }} options={opts(c.options)} onChange={(x) => set(i, c.key, x)} />
        case 'bool': return <Checkbox checked={!!v} onChange={(e) => set(i, c.key, e.target.checked)} />
        case 'textarea': return <Input.TextArea size="small" autoSize value={v} onChange={(e) => set(i, c.key, e.target.value)} />
        default: return <Input size="small" value={v} onChange={(e) => set(i, c.key, e.target.value)} />
      }
    },
  }))
  if (!readOnly) cols.push({ title: '', width: 40, render: (_: any, r: any) => <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange(rows.filter((_x, j) => j !== r._k))} /> })
  return (
    <Table rowKey="_k" size={size} pagination={false} dataSource={rows.map((r, i) => ({ ...r, _k: i }))} columns={cols} scroll={scrollX ? { x: scrollX } : undefined}
      footer={!readOnly && newRow ? () => <Button size="small" icon={<PlusOutlined />} onClick={() => onChange([...rows, newRow()])}>{addLabel}</Button> : undefined} />
  )
}

export function nextId(rows: any[], prefix: string, pad = 2) {
  const nums = rows.map((r) => Number(String(r.id ?? '').replace(/^\D+/, '').split('-').pop())).filter((n) => !Number.isNaN(n))
  return `${prefix}${String((nums.length ? Math.max(...nums) : 0) + 1).padStart(pad, '0')}`
}
