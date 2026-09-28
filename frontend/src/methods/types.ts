import type { Scheme } from '../risk'

export type PromoteRow = { row_id: string; title: string; causes?: string; consequences?: string; controls?: string[]; severity?: string | null; likelihood?: number | null; owner?: string }

export type EditorProps = {
  model: any
  setModel: (m: any) => void
  results: any
  setResults: (r: any) => void
  readOnly: boolean
  scheme?: Scheme
  template: any
  promote: (rows: PromoteRow[]) => Promise<void>
}
