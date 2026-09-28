import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Empty, Input, Row, Segmented, Select, Slider, Space, Table, Tag } from 'antd'
import { CalculatorOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { api } from '../api'
import { fmtSci } from '../risk'
import { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

export default function HraEditor({ model, setModel, results, setResults, readOnly }: EditorProps) {
  const { message } = App.useApp()
  const { data: libs } = useQuery({ queryKey: ['hra-libs'], queryFn: () => api.get('/meta/hra'), staleTime: Infinity })
  const tasks: any[] = model.tasks ?? []
  const [sel, setSel] = useState<string | null>(tasks[0]?.id ?? null)
  const setTasks = (t: any[]) => setModel({ ...model, tasks: t })
  const t = tasks.find((x) => x.id === sel)
  const upd = (patch: any) => setTasks(tasks.map((x) => (x.id === sel ? { ...x, ...patch } : x)))
  const lib = t && libs?.[t.library]
  const localHep = (x: any) => {
    const L = libs?.[x.library]; if (!L || !L.gtt[x.gtt]) return null
    return Math.min(1, x.epcs.reduce((a: number, e: any) => a * ((L.epc[e.code]?.max_effect ?? 1) - 1) * e.apoa + a, L.gtt[x.gtt].hep))
  }
  const run = async () => {
    try {
      const out = []
      for (const x of tasks) out.push({ id: x.id, ...(await api.post('/calc/hra', { library: x.library, gtt: x.gtt, epcs: x.epcs })) })
      setResults({ tasks: out })
    } catch (e: any) { message.error(e.message) }
  }
  const resOf = (id: string) => results?.tasks?.find((r: any) => r.id === id)

  return (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 12 }} title="HEP = GTT × Π[(EPC − 1) × APOA + 1]. Use CARA for controller tasks and HEART for other tasks (e.g. engineering). Justify every APOA; use the HEP in FTA, LOPA or ETA." />
      <Row gutter={16}>
        <Col xs={24} xl={10}>
          <Card size="small" title="Tasks" extra={!readOnly && <Button size="small" icon={<PlusOutlined />} onClick={() => { const id = nextId(tasks, 'T', 1); setTasks([...tasks, { id, task: 'New task', library: 'cara', gtt: 'F', epcs: [] }]); setSel(id) }}>Task</Button>}>
            <Table rowKey="id" size="small" pagination={false} dataSource={tasks} onRow={(r: any) => ({ onClick: () => setSel(r.id), style: { cursor: 'pointer', background: r.id === sel ? '#E3F1F3' : undefined } })}
              columns={[{ title: 'ID', dataIndex: 'id', width: 50 }, { title: 'Task', dataIndex: 'task' },
                { title: 'GTT', width: 90, render: (_, r: any) => <Tag>{r.library.toUpperCase()} {r.gtt}</Tag> },
                { title: 'HEP', width: 90, render: (_, r: any) => <b>{fmtSci(resOf(r.id)?.hep ?? localHep(r), 3)}</b> }]} />
            <Button type="primary" icon={<CalculatorOutlined />} style={{ marginTop: 10 }} onClick={run}>Calculate all (server)</Button>
          </Card>
        </Col>
        <Col xs={24} xl={14}>
          <Card size="small" title={t ? `Task ${t.id}` : 'Task'}>
            {!t || !lib ? <Empty /> : (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Input.TextArea autoSize value={t.task} disabled={readOnly} onChange={(e) => upd({ task: e.target.value })} />
                <Space wrap>
                  <Segmented value={t.library} disabled={readOnly} options={[{ label: 'CARA (ATC)', value: 'cara' }, { label: 'HEART', value: 'heart' }]}
                    onChange={(v) => upd({ library: v, gtt: Object.keys(libs[v as string].gtt)[0], epcs: [] })} />
                  <Select value={t.gtt} disabled={readOnly} style={{ width: 460 }} onChange={(v) => upd({ gtt: v })}
                    options={Object.entries(lib.gtt).map(([k, g]: any) => ({ value: k, label: `${k} — ${g.description} (${g.hep})` }))} />
                </Space>
                <Table rowKey="code" size="small" pagination={false} dataSource={t.epcs} title={() => <b>Error-producing conditions</b>}
                  footer={() => !readOnly && <Select size="small" placeholder="Add an error-producing condition" style={{ width: '100%' }} value={null as any}
                    onChange={(c) => upd({ epcs: [...t.epcs, { code: c, apoa: 0.1 }] })}
                    options={Object.entries(lib.epc).filter(([k]) => !t.epcs.some((e: any) => e.code === k)).map(([k, e]: any) => ({ value: k, label: `EPC ${k} — ${e.description} (×${e.max_effect})` }))} />}
                  columns={[
                    { title: 'EPC', dataIndex: 'code', width: 50 },
                    { title: 'Condition', render: (_, e: any) => lib.epc[e.code]?.description },
                    { title: 'Max', width: 55, render: (_, e: any) => `×${lib.epc[e.code]?.max_effect}` },
                    { title: 'APOA', width: 170, render: (_, e: any) => <Slider min={0} max={1} step={0.05} value={e.apoa} disabled={readOnly}
                      onChange={(v) => upd({ epcs: t.epcs.map((x: any) => (x.code === e.code ? { ...x, apoa: v } : x)) })} /> },
                    { title: 'Factor', width: 70, render: (_, e: any) => ((lib.epc[e.code]?.max_effect - 1) * e.apoa + 1).toFixed(2) },
                    { title: '', width: 36, render: (_, e: any) => !readOnly && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => upd({ epcs: t.epcs.filter((x: any) => x.code !== e.code) })} /> },
                  ]} />
                <div>Nominal HEP <b>{lib.gtt[t.gtt]?.hep}</b> → assessed HEP <b style={{ fontSize: 16, color: '#1F3A5F' }}>{fmtSci(localHep(t), 3)}</b></div>
                <Input.TextArea rows={2} placeholder="Justification of the task type and APOA values" value={t.justification} disabled={readOnly} onChange={(e) => upd({ justification: e.target.value })} />
              </Space>)}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
