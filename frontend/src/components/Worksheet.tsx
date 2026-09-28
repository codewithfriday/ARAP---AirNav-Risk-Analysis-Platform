import { useMemo, useRef } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, CellValueChangedEvent } from 'ag-grid-community'
import { themeQuartz } from 'ag-grid-community'
import type { Scheme } from '../risk'
import { classify, fmtSci, objective } from '../risk'

const theme = themeQuartz.withParams({ headerBackgroundColor: '#1F3A5F', headerTextColor: '#ffffff', fontSize: 12.5, rowHeight: 34, headerHeight: 36, wrapperBorderRadius: 8 })

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
