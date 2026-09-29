import { useMemo, useRef } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, CellValueChangedEvent } from 'ag-grid-community'
import { themeQuartz } from 'ag-grid-community'
import type { Scheme } from '../risk'
import { classify, fmtSci, objective } from '../risk'

const theme = themeQuartz.withParams({ headerBackgroundColor: '#1F3A5F', headerTextColor: '#ffffff', fontSize: 12.5, rowHeight: 34, headerHeight: 36, wrapperBorderRadius: 8 })

/** Security risk = likelihood × max(C, I, A) on 1–5 scales (Manual §29.3). */
export function secRisk(r: any) {
  const imp = Math.max(Number(r?.c) || 0, Number(r?.i) || 0, Number(r?.a) || 0), l = Number(r?.likelihood) || 0
  if (!imp || !l) return null
  const score = imp * l
  const [level, color] = score >= 15 ? ['Very high', '#B23A3A'] : score >= 10 ? ['High', '#D98E04'] : score >= 5 ? ['Medium', '#C9A227'] : ['Low', '#3C8D5A']
  return { score, level, color }
}

/** Organisational function map: list the open issues of a row (Manual Appendix D). */
export function ofmGaps(r: any): string[] {
  const g: string[] = []
  const owner = String(r?.new_owner ?? '').trim()
  if (!owner || owner === '—' || owner === '-') g.push('no owner')
  if (r?.competence === 'gap') g.push('competence')
  if (r?.capacity === 'stretched' || r?.capacity === 'overloaded') g.push(`capacity ${r.capacity}`)
  if (r?.authority === 'pending' || r?.authority === 'none') g.push(`authority ${r.authority}`)
  if (r?.handover === 'not planned') g.push('no handover')
  if ([r?.competence, r?.capacity, r?.authority, r?.handover].some((v) => !v || v === 'unknown')) g.push('to assess')
  return g
}
const RAG: Record<string, string> = { green: '#D5ECDD', amber: '#FBE7C2', red: '#F4CACA' }

export type ColSpec = [string, string, number, string?]

/** Generic spreadsheet-style worksheet driven by the method template columns (SRS HZD/HZP/JHA/FME/FHA). */
export function Worksheet({ columns, rows, onChange, scheme, readOnly, options, onSelect, height = 520 }: {
  columns: ColSpec[]; rows: any[]; onChange: (rows: any[]) => void; scheme?: Scheme; readOnly?: boolean
  options?: Record<string, string[]>; onSelect?: (rows: any[]) => void; height?: number
}) {
  const ref = useRef<AgGridReact>(null)
  const colDefs = useMemo<ColDef[]>(() => columns.map(([field, header, width, kind]) => {
    const base: ColDef = { field, headerName: header, width, editable: !readOnly && field !== 'id' && kind !== 'computed' && kind !== 'risk',
      wrapText: true, autoHeight: true, cellStyle: { lineHeight: '1.35', paddingTop: '6px', paddingBottom: '6px' }, filter: true, resizable: true }
    if (field === 'id') { base.pinned = 'left' }
    if (kind === 'severity') return { ...base, cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['', 'A', 'B', 'C', 'D', 'E'] } }
    if (kind === 'likelihood') return { ...base, cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['', 5, 4, 3, 2, 1] }, valueParser: (p) => (p.newValue === '' ? null : Number(p.newValue)) }
    if (kind === 'int5') return { ...base, cellEditor: 'agNumberCellEditor', cellEditorParams: { min: 1, max: 5, precision: 0 } }
    if (kind === 'computed' && field === 'sec_risk') return { ...base, filter: false, valueGetter: (p) => secRisk(p.data)?.score ?? null,
      cellRenderer: (p: any) => { const r = secRisk(p.data); return r ? <span className="risk-cell" style={{ background: r.color }}>{r.score} {r.level}</span> : '' } }
    if (kind === 'computed' && field === 'gap') return { ...base, filter: false, valueGetter: (p) => ofmGaps(p.data).join(', ') || 'OK',
      cellRenderer: (p: any) => { const g = ofmGaps(p.data); return g.length ? g.map((x) => <span key={x} className="risk-cell" style={{ background: x === 'to assess' ? '#9CA3AF' : x.includes('stretched') ? '#D98E04' : '#B23A3A', marginRight: 3, fontSize: 10.5 }}>{x}</span>) : <span className="risk-cell" style={{ background: '#3C8D5A' }}>OK</span> } }
    if (kind === 'rag') return { ...base, cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['', 'green', 'amber', 'red'] }, cellStyle: (p: any) => ({ ...(base.cellStyle as any), background: RAG[p.value] ?? undefined, fontWeight: 600 }) as any }
    if (kind === 'int10') return { ...base, cellEditor: 'agNumberCellEditor', cellEditorParams: { min: 1, max: 10, precision: 0 } }
    if (kind === 'number') return { ...base, cellEditor: 'agNumberCellEditor', valueFormatter: (p) => (p.value === null || p.value === undefined || p.value === '' ? '' : fmtSci(Number(p.value))) }
    if (kind === 'bool') return { ...base, cellDataType: 'boolean', cellEditor: 'agCheckboxCellEditor', cellRenderer: 'agCheckboxCellRenderer' }
    if (kind && options?.[kind]) return { ...base, cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['', ...options[kind]] } }
    if (kind === 'risk') return { ...base, editable: false, filter: false,
      valueGetter: (p) => classify(scheme, p.data.severity, p.data.likelihood)?.index ?? '',
      cellRenderer: (p: any) => { const c = classify(scheme, p.data.severity, p.data.likelihood); return c ? <span className="risk-cell" style={{ background: c.color }}>{c.index}</span> : '' } }
    if (kind === 'computed' && field === 'rpn') return { ...base, valueGetter: (p) => (p.data.s && p.data.o && p.data.d ? p.data.s * p.data.o * p.data.d : null),
      cellStyle: (p: any) => ({ fontWeight: 700, color: p.value >= 100 ? '#B23A3A' : p.value >= 60 ? '#D98E04' : '#1f2937' }) as any, sort: 'desc' }
    if (kind === 'computed' && field === 'objective') return { ...base, valueGetter: (p) => objective(scheme, p.data.severity), valueFormatter: (p) => (p.value ? `≤ ${fmtSci(p.value, 0)}` : '') }
    return base
  }), [columns, readOnly, scheme, options])

  const changed = (e: CellValueChangedEvent) => {
    const all: any[] = []
    e.api.forEachNode((n) => all.push(n.data))
    onChange(all)
  }

  return (
    <div style={{ height, width: '100%' }}>
      <AgGridReact ref={ref} theme={theme} rowData={rows} columnDefs={colDefs} getRowId={(p) => String(p.data.id)}
        onCellValueChanged={changed} rowSelection={readOnly ? undefined : { mode: 'multiRow', checkboxes: true, headerCheckbox: true, enableClickSelection: false }}
        onSelectionChanged={(e) => onSelect?.(e.api.getSelectedRows())} stopEditingWhenCellsLoseFocus singleClickEdit={false}
        defaultColDef={{ sortable: true }} />
    </div>
  )
}
