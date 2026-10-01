import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Col, DatePicker, Empty, Input, Radio, Row, Select, Space, Table, Tabs, Tag } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../api'
import { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

const BAND: Record<string, string> = { red: '#B23A3A', amber: '#D98E04', green: '#3C8D5A' }
const bandOf = (v: number, bands: any[]) => bands.find((b) => v >= b.threshold)

export default function OrcEditor({ model, setModel, readOnly, promote }: EditorProps) {
  const { data: meta } = useQuery({ queryKey: ['orc-meta'], queryFn: () => api.get('/meta/orc'), staleTime: Infinity })
  const occ: any[] = model.occurrences ?? []
  const [sel, setSel] = useState<string | null>(occ[0]?.id ?? null)
  const setOcc = (o: any[]) => setModel({ ...model, occurrences: o })
  const o = occ.find((x) => x.id === sel)
  const upd = (patch: any) => setOcc(occ.map((x) => (x.id === sel ? { ...x, ...patch } : x)))
  if (!meta) return null
  const erc = (x: any) => {
    const r = meta.erc.outcomes.indexOf(x.outcome), c = meta.erc.barriers.indexOf(x.barriers)
    if (r < 0 || c < 0) return null
    const v = meta.erc.matrix[r][c]
    return { v, band: bandOf(v, meta.erc.bands) }
  }
  const rat = (x: any) => {
    let roc = 0, ctrl = 0
    for (const [k, item] of Object.entries<any>(meta.rat)) {
      const a = x.rat?.[k]; if (!a) continue
      const p = item.options[a]?.points ?? 0
      if (k === 'separation' || k === 'closure') roc += p; else ctrl += p
    }
    return { roc, ctrl, total: roc + ctrl }
  }

  return (
    <Row gutter={16}>
      <Col xs={24} xl={9}>
        <Card size="small" title="Occurrences" extra={!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => { const id = nextId(occ, 'OCC-', 3); setOcc([...occ, { id, title: '', outcome: undefined, barriers: undefined, rat: {} }]); setSel(id) }}>Occurrence</Button>}>
          <Table rowKey="id" size="small" pagination={false} dataSource={occ} onRow={(r: any) => ({ onClick: () => setSel(r.id), style: { cursor: 'pointer', background: r.id === sel ? '#E3F1F3' : undefined } })}
            columns={[{ title: 'ID', dataIndex: 'id', width: 80 }, { title: 'Occurrence', dataIndex: 'title', ellipsis: true },
              { title: 'ERC', width: 60, render: (_, r: any) => { const e = erc(r); return e ? <span className="risk-cell" style={{ background: BAND[e.band.band] }}>{e.v}</span> : '—' } },
              { title: 'RAT', width: 55, render: (_, r: any) => (r.rat && Object.keys(r.rat).length ? rat(r).total : '—') },
              { title: 'Class', dataIndex: 'severity_class', width: 55 }]} />
          {!readOnly && <Button style={{ marginTop: 10 }} onClick={() => promote(occ.filter((x) => erc(x)?.band.band === 'red').map((x) => ({ row_id: x.id, title: x.title, causes: x.notes })))}>Send red-band occurrences to hazard log</Button>}
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        {!o ? <Card><Empty /></Card> : (
          <Card size="small" title={o.id} extra={!readOnly && <Button size="small" danger icon={<DeleteOutlined />} onClick={() => { setOcc(occ.filter((x) => x.id !== o.id)); setSel(null) }} />}>
            <Space orientation="vertical" style={{ width: '100%' }}>
              <Input.TextArea autoSize placeholder="Short description" value={o.title} disabled={readOnly} onChange={(e) => upd({ title: e.target.value })} />
              <Space><DatePicker value={o.date ? dayjs(o.date) : null} disabled={readOnly} onChange={(d) => upd({ date: d ? d.format('YYYY-MM-DD') : null })} />
                <span className="small">ESARR 2 severity class (analyst)</span>
                <Select value={o.severity_class} style={{ width: 90 }} disabled={readOnly} allowClear onChange={(v) => upd({ severity_class: v })} options={['A', 'B', 'C', 'D', 'E'].map((v) => ({ value: v, label: v }))} /></Space>
              <Tabs items={[
                { key: 'erc', label: 'ARMS ERC', children: (
                  <div>
                    <div className="small" style={{ marginBottom: 6 }}><b>Q1.</b> If this event had escalated into an accident, what would have been the most credible outcome? <b>Q2.</b> How effective were the remaining barriers between this event and that accident? Click a cell.</div>
                    <table style={{ borderCollapse: 'separate', borderSpacing: 3 }}>
                      <thead><tr><th />{meta.erc.barriers.map((b: string) => <th key={b} className="small" style={{ fontWeight: 500, width: 110 }}>{b}</th>)}</tr></thead>
                      <tbody>{meta.erc.outcomes.map((out: string, r: number) => (
                        <tr key={out}><td className="small" style={{ textAlign: 'right', paddingRight: 6 }}>{out}</td>
                          {meta.erc.matrix[r].map((v: number, c: number) => {
                            const s = o.outcome === out && o.barriers === meta.erc.barriers[c]
                            return <td key={c}><div onClick={() => !readOnly && upd({ outcome: out, barriers: meta.erc.barriers[c] })}
                              style={{ background: BAND[bandOf(v, meta.erc.bands).band], color: '#fff', fontWeight: 700, textAlign: 'center', padding: '8px 0', borderRadius: 4, cursor: readOnly ? 'default' : 'pointer', outline: s ? '3px solid #1F3A5F' : 'none', opacity: o.outcome && !s ? 0.55 : 1 }}>{v}</div></td>
                          })}</tr>))}</tbody>
                    </table>
                    {erc(o) && <Alert style={{ marginTop: 8 }} type={erc(o)!.band.band === 'red' ? 'error' : erc(o)!.band.band === 'amber' ? 'warning' : 'success'} showIcon title={`Risk index ${erc(o)!.v}: ${erc(o)!.band.meaning}`} />}
                  </div>) },
                { key: 'rat', label: 'RAT scoring', children: (
                  <div>
                    {Object.entries<any>(meta.rat).map(([k, item]) => (
                      <div key={k} style={{ marginBottom: 8 }}>
                        <div className="small" style={{ fontWeight: 600 }}>{item.label}</div>
                        <Radio.Group size="small" disabled={readOnly} value={o.rat?.[k]} onChange={(e) => upd({ rat: { ...o.rat, [k]: e.target.value } })}
                          options={Object.entries<any>(item.options).map(([ok, ov]) => ({ value: ok, label: `${ov.label} (${ov.points})` }))} optionType="button" />
                      </div>))}
                    <Alert type="info" showIcon title={`Risk of collision ${rat(o).roc} + controllability ${rat(o).ctrl} = severity score ${rat(o).total}`}
                      description="Assign the ESARR 2 severity class with the EUROCONTROL RAT look-up table (not embedded in NAVRAP) and record it above." />
                  </div>) },
              ]} />
              <Input.TextArea rows={2} placeholder="Notes / rationale" value={o.notes} disabled={readOnly} onChange={(e) => upd({ notes: e.target.value })} />
            </Space>
          </Card>)}
      </Col>
    </Row>
  )
}
