import { lazy, Suspense, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Input, Space, Spin, Tag, Tooltip } from 'antd'
import { SaveOutlined, TeamOutlined } from '@ant-design/icons'
import { Link, useParams, useBlocker } from 'react-router-dom'
import { api } from '../api'
import { useMethods, useScheme } from '../hooks'
import { canEdit, useAuth } from '../store'
import { METHOD_COLORS } from '../risk'
import type { PromoteRow } from '../methods/types'

const EDITORS: Record<string, any> = {
  bowtie: lazy(() => import('../methods/BowtieEditor')),
  fta: lazy(() => import('../methods/FtaEditor')),
  lopa: lazy(() => import('../methods/LopaEditor')),
  fatigue: lazy(() => import('../methods/FatigueEditor')),
  bbn: lazy(() => import('../methods/BbnEditor')),
  stpa: lazy(() => import('../methods/StpaEditor')),
  fram: lazy(() => import('../methods/FramEditor')),
  crm: lazy(() => import('../methods/CrmEditor')),
  eta: lazy(() => import('../methods/EtaEditor')),
  hra: lazy(() => import('../methods/HraEditor')),
  orc: lazy(() => import('../methods/OrcEditor')),
  gsn: lazy(() => import('../methods/GsnEditor')),
  cca: lazy(() => import('../methods/CcaEditor')),
  rbd: lazy(() => import('../methods/RbdEditor')),
  hta: lazy(() => import('../methods/HtaEditor')),
  sim: lazy(() => import('../methods/SimEditor')),
  sej: lazy(() => import('../methods/SejEditor')),
  inv: lazy(() => import('../methods/InvEditor')),
}
const Worksheet = lazy(() => import('../methods/WorksheetEditor'))

export default function StudyPage() {
  const { id } = useParams()
  const user = useAuth((s) => s.user)
  const qc = useQueryClient()
  const { message, modal } = App.useApp()
  const { data: study, refetch } = useQuery({ queryKey: ['study', id], queryFn: () => api.get(`/studies/${id}`) })
  const { data: methods } = useMethods()
  const { data: scheme } = useScheme()
  const [model, setModelState] = useState<any>(null)
  const [results, setResults] = useState<any>(null)
  const [title, setTitle] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (study) { setModelState(study.model ?? {}); setResults(study.results ?? {}); setTitle(study.title); setDirty(false) }
  }, [study])

  const blocker = useBlocker(dirty)
  useEffect(() => {
    if (blocker.state === 'blocked') modal.confirm({ title: 'Unsaved changes', content: 'Leave without saving?', onOk: () => blocker.proceed(), onCancel: () => blocker.reset() })
  }, [blocker, modal])

  if (!study || !methods || model === null) return <Spin />
  const m = methods[study.method]
  const readOnly = !canEdit(user) || study.locked
  const setModel = (x: any) => { setModelState(x); setDirty(true) }
  const setRes = (x: any) => { setResults(x); setDirty(true) }

  const save = async () => {
    setSaving(true)
    try {
      await api.put(`/studies/${study.id}`, { title, model, results })
      setDirty(false)
      message.success('Saved')
      qc.invalidateQueries({ queryKey: ['assessment'] })
      refetch()
    } catch (e: any) {
      message.error(e.message)
    } finally {
      setSaving(false)
    }
  }
  const promote = async (rows: PromoteRow[]) => {
    if (!rows.length) { message.warning('Nothing to send'); return }
    if (dirty) await save()
    try {
      const r = await api.post(`/studies/${study.id}/promote`, rows)
      message.success(`${r.length} hazard(s) created or updated in the hazard log: ${r.map((h: any) => h.ref).join(', ')}`)
      qc.invalidateQueries({ queryKey: ['hazards'] })
    } catch (e: any) {
      message.error(e.message)
    }
  }
  const Editor = EDITORS[study.method]
  const props = { model, setModel, results, setResults: setRes, readOnly, scheme: scheme?.data, template: m, promote }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <div>
          <Space>
            <Tag color={METHOD_COLORS[study.method]} style={{ fontSize: 13, padding: '2px 8px' }}>{m.name}</Tag>
            {readOnly ? <b style={{ fontSize: 18, color: '#1F3A5F' }}>{title}</b> :
              <Input value={title} onChange={(e) => { setTitle(e.target.value); setDirty(true) }} style={{ width: 460, fontWeight: 600 }} />}
          </Space>
          <div className="muted small" style={{ marginTop: 4 }}>
            <Link to={`/assessments/${study.assessment.id}`}>← {study.assessment.title}</Link> · Manual chapter {m.chapter} · template v{study.template_version}
          </div>
        </div>
        <Space>
          <Tooltip title={(study.participants ?? []).map((p: any) => `${p.name} (${p.role})`).join(', ') || 'No participants recorded'}>
            <Tag icon={<TeamOutlined />}>{(study.participants ?? []).length} participants</Tag>
          </Tooltip>
          {!readOnly && <Button type="primary" icon={<SaveOutlined />} loading={saving} disabled={!dirty} onClick={save}>{dirty ? 'Save' : 'Saved'}</Button>}
        </Space>
      </div>
      {study.locked && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={`The assessment is ${study.assessment.status}; this study is read-only.`} />}
      {!study.locked && !canEdit(user) && <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Read-only: your role cannot edit studies." />}
      <Card styles={{ body: { padding: 14 } }}>
        <Suspense fallback={<Spin />}>
          {Editor ? <Editor {...props} /> : <Worksheet {...props} method={study.method} />}
        </Suspense>
      </Card>
    </div>
  )
}
