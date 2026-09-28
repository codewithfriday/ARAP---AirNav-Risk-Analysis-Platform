import { useEffect, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider } from '@xyflow/react'
import type { Edge, Node, NodeProps } from '@xyflow/react'
import ELK from 'elkjs/lib/elk.bundled.js'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button, Card, Col, Empty, Input, Popconfirm, Row, Select, Space, Table, Tabs, Tag } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { api } from '../api'
import { fmtSci } from '../risk'
import type { EditorProps } from './types'

const elk = new ELK()
const W = 210, H = 56

function TaskNode({ data }: NodeProps) {
  const d = data as any
  const t = d.task
  return (
    <div style={{ width: W }}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ minHeight: H, border: `2px solid ${d.selected ? '#2A7F8E' : '#1F3A5F'}`, background: d.selected ? '#E3F1F3' : '#fff', borderRadius: 4, padding: '4px 6px', fontSize: 10.5, lineHeight: 1.25, position: 'relative' }}>
        <b style={{ color: '#1F3A5F' }}>{t.id}</b> {t.title}
        {(t.error_modes ?? []).length > 0 && <div style={{ position: 'absolute', top: -8, right: -8, background: '#D98E04', color: '#fff', borderRadius: 10, fontSize: 9, padding: '0 5px' }} title={t.error_modes.join('\n')}>{t.error_modes.length} EM</div>}
        {d.hep !== undefined && <div style={{ fontSize: 9, color: '#B23A3A' }}>HEP {fmtSci(d.hep, 2)}</div>}
      </div>
      {t.plan && d.hasKids && <div style={{ fontSize: 9, color: '#2A7F8E', fontStyle: 'italic', marginTop: 2, lineHeight: 1.15 }}>Plan {t.id}: {t.plan}</div>}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>)
}
const nodeTypes = { task: TaskNode }

const sortKey = (id: string) => id.split('.').map((x) => x.padStart(4, '0')).join('.')

export default function HtaEditor({ model, setModel, readOnly, template }: EditorProps) {
  const tasks: any[] = model.tasks ?? [{ id: '0', parent: null, title: 'Overall goal', plan: '' }]
  const [sel, setSel] = useState<string | null>('0')
  const [graph, setGraph] = useState<{ nodes: Node[]; edges: Edge[] }>({ nodes: [], edges: [] })
  const { data: hraStudies = [] } = useQuery({ queryKey: ['studies-index', 'hra'], queryFn: () => api.get('/studies?method=hra') })
  const { data: hraStudy } = useQuery({ queryKey: ['study', model.hra_study], queryFn: () => api.get(`/studies/${model.hra_study}`), enabled: !!model.hra_study })
  const hraTasks: any[] = hraStudy?.model?.tasks ?? []
  const hepOf = (ref?: string) => hraStudy?.results?.tasks?.find((x: any) => x.id === ref)?.hep
  const setTasks = (t: any[]) => setModel({ ...model, tasks: t })
  const kids = (id: string) => tasks.filter((t) => t.parent === id)

  useEffect(() => {
    (async () => {
      const g = await elk.layout({ id: 'r', layoutOptions: { 'elk.algorithm': 'mrtree', 'elk.direction': 'RIGHT', 'elk.spacing.nodeNode': '14' } as any,
        children: tasks.map((t) => ({ id: t.id, width: W, height: H + (t.plan && kids(t.id).length ? 34 : 6) })),
        edges: tasks.filter((t) => t.parent && tasks.some((p) => p.id === t.parent)).map((t) => ({ id: `e${t.id}`, sources: [t.parent], targets: [t.id] })) })
      const pos = Object.fromEntries((g.children ?? []).map((c) => [c.id, { x: c.x ?? 0, y: c.y ?? 0 }]))
      setGraph({
        nodes: tasks.map((t) => ({ id: t.id, type: 'task', position: pos[t.id] ?? { x: 0, y: 0 }, draggable: false, data: { task: t, selected: t.id === sel, hasKids: kids(t.id).length > 0, hep: t.hra ? hepOf(t.hra) : undefined } })),
        edges: tasks.filter((t) => t.parent).map((t) => ({ id: `e${t.id}`, source: t.parent, target: t.id, type: 'step', style: { stroke: '#4B5563' } })),
      })
    })()
  }, [model, sel, hraStudy]) // eslint-disable-line react-hooks/exhaustive-deps

  const t = tasks.find((x) => x.id === sel)
  const upd = (patch: any) => setTasks(tasks.map((x) => (x.id === sel ? { ...x, ...patch } : x)))
  const addChild = () => {
    const ks = kids(sel!)
    const nums = ks.map((k) => Number(k.id.split('.').pop())).filter((x) => !Number.isNaN(x))
    const n = (nums.length ? Math.max(...nums) : 0) + 1
    const id = sel === '0' ? String(n) : `${sel}.${n}`
    setTasks([...tasks, { id, parent: sel, title: 'New sub-task', error_modes: [] }])
    setSel(id)
  }
  const desc = (id: string): string[] => kids(id).flatMap((k) => [k.id, ...desc(k.id)])
  const del = () => { const gone = new Set([sel!, ...desc(sel!)]); setTasks(tasks.filter((x) => !gone.has(x.id))); setSel(t?.parent ?? null) }
  const ordered = [...tasks].sort((a, b) => sortKey(a.id).localeCompare(sortKey(b.id)))
  const depth = (x: any): number => (x.parent ? 1 + depth(tasks.find((p) => p.id === x.parent) ?? {}) : 0)
  const missingPlans = tasks.filter((x) => kids(x.id).length > 0 && !x.plan).map((x) => x.id)
  const em = tasks.filter((x) => (x.error_modes ?? []).length)

  const panel = (
    <Card size="small" title={t ? `Task ${t.id}` : 'Task'} extra={t && !readOnly && <Space>
      <Button size="small" icon={<PlusOutlined />} onClick={addChild}>Sub-task</Button>
      {t.parent && <Popconfirm title="Delete this task and its sub-tasks?" onConfirm={del}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>}</Space>}>
      {!t ? <Empty /> : <Space orientation="vertical" style={{ width: '100%' }}>
        <Input.TextArea autoSize value={t.title} disabled={readOnly} onChange={(e) => upd({ title: e.target.value })} placeholder="Task stated as a verb + object" />
        <Input.TextArea autoSize value={t.plan} disabled={readOnly} onChange={(e) => upd({ plan: e.target.value })} placeholder={kids(t.id).length ? 'Plan: when and in what order the sub-tasks are done' : 'Plan (only needed if the task has sub-tasks)'} />
        <div className="small muted">Error modes (SHERPA-style taxonomy)</div>
        <Select mode="multiple" style={{ width: '100%' }} value={t.error_modes ?? []} disabled={readOnly} onChange={(v) => upd({ error_modes: v })} options={(template.error_modes ?? []).map((x: string) => ({ value: x, label: x }))} />
        <Input.TextArea autoSize value={t.notes} disabled={readOnly} onChange={(e) => upd({ notes: e.target.value })} placeholder="Consequence of error / recovery opportunities / remedies" />
        <Space wrap><span className="small">HRA task</span>
          <Select size="small" style={{ width: 240 }} allowClear value={t.hra} disabled={readOnly || !model.hra_study} onChange={(v) => upd({ hra: v })}
            placeholder={model.hra_study ? 'Link to HRA task' : 'Select an HRA study below first'} options={hraTasks.map((x: any) => ({ value: x.id, label: `${x.id} ${x.task}` }))} />
          {t.hra && hepOf(t.hra) !== undefined && <Tag color="red">HEP {fmtSci(hepOf(t.hra), 3)}</Tag>}</Space>
      </Space>}
    </Card>)

  return (
    <div>
      <Space style={{ marginBottom: 8 }} wrap>
        <span className="small">Linked HRA study</span>
        <Select size="small" style={{ width: 380 }} allowClear value={model.hra_study} disabled={readOnly} onChange={(v) => setModel({ ...model, hra_study: v })}
          options={hraStudies.map((s: any) => ({ value: s.id, label: `#${s.id} ${s.title}` }))} />
        {model.hra_study && <Link to={`/studies/${model.hra_study}`}>open</Link>}
        <Tag>{tasks.length} tasks</Tag><Tag color={em.length ? 'orange' : 'default'}>{em.length} with error modes</Tag>
        {missingPlans.length > 0 && <Tag color="red">No plan: {missingPlans.join(', ')}</Tag>}
      </Space>
      <Tabs items={[
        { key: 'tree', label: 'Tree', children: (
          <Row gutter={12}>
            <Col xs={24} xxl={16}><div className="flow-wrap"><ReactFlowProvider>
              <ReactFlow nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} fitView nodesConnectable={false} onNodeClick={(_, n) => setSel(n.id)} minZoom={0.15}>
                <Background gap={24} color="#e5e7eb" /><Controls showInteractive={false} /></ReactFlow></ReactFlowProvider></div></Col>
            <Col xs={24} xxl={8}>{panel}</Col>
          </Row>) },
        { key: 'outline', label: 'Outline', children: (
          <Row gutter={12}>
            <Col xs={24} xxl={16}>
              <Table size="small" rowKey="id" pagination={false} dataSource={ordered} onRow={(r: any) => ({ onClick: () => setSel(r.id), style: { cursor: 'pointer', background: r.id === sel ? '#E3F1F3' : undefined } })}
                columns={[
                  { title: 'Task', render: (_, r: any) => <span style={{ paddingLeft: depth(r) * 18 }}><b>{r.id}</b> {r.title}</span> },
                  { title: 'Plan', dataIndex: 'plan', width: 260, render: (v) => <i className="small">{v}</i> },
                  { title: 'Error modes', dataIndex: 'error_modes', width: 240, render: (v: string[]) => (v ?? []).map((x) => <Tag key={x} style={{ marginBottom: 2 }}>{x}</Tag>) },
                  { title: 'HEP', width: 90, render: (_, r: any) => (r.hra ? fmtSci(hepOf(r.hra), 2) : '') },
                ]} />
            </Col>
            <Col xs={24} xxl={8}>{panel}</Col>
          </Row>) },
      ]} />
    </div>
  )
}
