import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Modal, Select, Space, Tabs, Tag } from 'antd'
import { PlusOutlined, DeleteOutlined, ImportOutlined } from '@ant-design/icons'
import { Worksheet, type ColSpec } from '../components/Worksheet'
import { api } from '../api'
import { nextId } from '../components/EditableTable'
import type { EditorProps } from './types'

const PFX: Record<string, string> = { zsa: 'Z-', pra: 'P-', cma: 'CM-' }

function Sheet({ part, model, setModel, readOnly, template, scheme, extra }: EditorProps & { part: 'zsa' | 'pra' | 'cma'; extra?: React.ReactNode }) {
  const rows: any[] = model[part] ?? []
  const [selected, setSelected] = useState<any[]>([])
  const setRows = (r: any[]) => setModel({ ...model, [part]: r })
  const options = { particular: template.particular_risks ?? [], cm_source: template.cm_sources ?? [], yesno: ['Yes', 'Partly', 'No'] }
  return (
    <div>
      <Space style={{ marginBottom: 8 }} wrap>
        {!readOnly && <Button icon={<PlusOutlined />} onClick={() => setRows([...rows, { id: nextId(rows, PFX[part], 2) }])}>Add row</Button>}
        {!readOnly && <Button danger icon={<DeleteOutlined />} disabled={!selected.length} onClick={() => setRows(rows.filter((r) => !selected.some((s) => s.id === r.id)))}>Delete selected</Button>}
        {extra}
      </Space>
      <Worksheet columns={template[`${part}_columns`] as ColSpec[]} rows={rows} onChange={setRows} scheme={scheme} readOnly={readOnly} options={options} onSelect={setSelected} height={440} />
    </div>
  )
}

/** Common cause analysis (ARP4761A): zonal safety analysis, particular risks analysis, common mode analysis. */
export default function CcaEditor(props: EditorProps) {
  const { model, setModel, readOnly, promote } = props
  const { message } = App.useApp()
  const [imp, setImp] = useState(false)
  const [fta, setFta] = useState<number | null>(null)
  const { data: ftas = [] } = useQuery({ queryKey: ['studies-index', 'fta'], queryFn: () => api.get('/studies?method=fta'), enabled: imp })

  const cma: any[] = model.cma ?? []
  const pra: any[] = model.pra ?? []
  const importAnd = async () => {
    if (!fta) return
    const s = await api.get(`/studies/${fta}`)
    const nodes = s.model?.tree?.nodes ?? {}
    const lab = (id: string) => `${id} ${nodes[id]?.label ?? ''}`.trim()
    const claims: any[] = []
    let rows = [...cma]
    for (const [id, n] of Object.entries<any>(nodes)) {
      if (!['and', 'vote'].includes(n.type) || !(n.children ?? []).length) continue
      const items = n.children.join(', ')
      if (rows.some((r) => r.items === items)) continue
      const c = { id: nextId(rows, 'CM-', 2), claim: `Inputs to ${n.type.toUpperCase()} gate ${lab(id)} fail independently`, items, source: undefined, analysis: `From FTA #${s.id}: ${n.children.map(lab).join('; ')}`, independent: undefined, action: '' }
      rows = [...rows, c]; claims.push(c)
    }
    setModel({ ...model, cma: rows })
    setImp(false)
    message.success(claims.length ? `${claims.length} independence claim(s) imported` : 'Every AND / vote gate in this FTA already has an independence claim')
  }
  const notIndep = cma.filter((r) => r.independent === 'No' || r.independent === 'Partly')
  const defeats = pra.filter((r) => r.redundancy_defeated)
  const unassessed = cma.filter((r) => !r.independent)

  return (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Every AND gate or redundancy claim in an FTA, RBD or FHA rests on independence. CCA checks it three ways: where items are installed (ZSA), what single events can hit several at once (PRA) and what they share by design (CMA)." />
      <Space style={{ marginBottom: 10 }} wrap>
        <Tag color={notIndep.length ? 'red' : 'green'}>{notIndep.length} independence claim(s) not supported</Tag>
        <Tag color={unassessed.length ? 'orange' : 'default'}>{unassessed.length} claim(s) not yet assessed</Tag>
        <Tag color={defeats.length ? 'red' : 'green'}>{defeats.length} particular risk(s) defeat redundancy</Tag>
        {!readOnly && <Button size="small" type="primary" ghost disabled={!notIndep.length && !defeats.length}
          onClick={() => promote([...notIndep.map((r) => ({ row_id: r.id, title: `Common-mode failure: ${r.claim}`, causes: `${r.source ?? ''}: ${r.analysis ?? ''}`, controls: r.action ? [r.action] : [] })),
            ...defeats.map((r) => ({ row_id: r.id, title: `${r.risk} defeats redundancy (${r.zones})`, consequences: r.effect, controls: String(r.mitigation ?? '').split(/;\s*/), severity: r.severity || null }))])}>
          Send failures of independence to hazard log</Button>}
      </Space>
      <Tabs items={[
        { key: 'zsa', label: `Zonal safety analysis (${(model.zsa ?? []).length})`, children: <Sheet {...props} part="zsa" /> },
        { key: 'pra', label: `Particular risks (${pra.length})`, children: <Sheet {...props} part="pra" /> },
        { key: 'cma', label: `Common mode analysis (${cma.length})`, children: <Sheet {...props} part="cma" extra={!readOnly && <Button icon={<ImportOutlined />} onClick={() => setImp(true)}>Import claims from FTA</Button>} /> },
      ]} />
      <Modal open={imp} title="Import independence claims from an FTA" onCancel={() => setImp(false)} onOk={importAnd} okText="Import" okButtonProps={{ disabled: !fta }}>
        <p className="small">One claim is created for each AND or k-out-of-n gate. Record the common-mode source and whether independence holds; dependencies found should go back into the FTA as common-cause (β-factor) events.</p>
        <Select style={{ width: '100%' }} placeholder="Select FTA study" value={fta} onChange={setFta} options={ftas.map((s: any) => ({ value: s.id, label: `#${s.id} ${s.title}` }))} />
      </Modal>
    </div>
  )
}
