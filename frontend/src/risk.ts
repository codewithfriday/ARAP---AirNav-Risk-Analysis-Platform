// Client-side mirror of the backend risk engine (display only; the server remains authoritative).
export type Region = { key: string; name: string; color: string; authority: string | null; action: string; cells: string[] }
export type Scheme = {
  version: number
  severity: { code: string; name: string; name_id?: string }[]
  likelihood: { level: number; name: string; name_id?: string; lower: number | null; upper: number | null }[]
  quantitative_unit: string
  regions: Region[]
  region_order: string[]
}

export function classify(scheme: Scheme | undefined, sev?: string | null, lik?: number | string | null) {
  if (!scheme || !sev || !lik) return null
  const index = `${lik}${String(sev).toUpperCase()}`
  const r = scheme.regions.find((x) => x.cells.includes(index))
  return r ? { index, region: r.key, name: r.name, color: r.color, authority: r.authority } : null
}

export function objective(scheme: Scheme | undefined, sev?: string | null, target = 'tolerable_lower'): number | null {
  if (!scheme || !sev) return null
  const ok = scheme.region_order.slice(scheme.region_order.indexOf(target))
  const levels = [...scheme.likelihood].sort((a, b) => b.level - a.level)
  for (const l of levels) {
    const c = classify(scheme, sev, l.level)
    if (c && ok.includes(c.region)) return l.upper
  }
  return null
}

export const fmtSci = (v: number | null | undefined, d = 2) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v === 0 ? '0' : Math.abs(v) >= 0.01 && Math.abs(v) < 1000 ? v.toPrecision(3) : v.toExponential(d)

export const METHOD_COLORS: Record<string, string> = {
  bowtie: '#B23A3A', hazid: '#2A7F8E', hazop: '#2A7F8E', jha: '#6B7280', fmea: '#1F3A5F', lopa: '#D98E04',
  fha: '#1F3A5F', stpa: '#7C3AED', fta: '#1F3A5F', fatigue: '#D98E04', fram: '#3C8D5A', bbn: '#7C3AED',
  crm: '#0E7490', eta: '#B23A3A', hra: '#2A7F8E', orc: '#D98E04', gsn: '#1F3A5F', cca: '#A16207', rbd: '#0E7490',
  swift: '#2A7F8E', hta: '#3C8D5A', sim: '#7C3AED', sej: '#A16207', sec: '#4B5563', inv: '#B23A3A', wildlife: '#3C8D5A', orgmap: '#A16207', spi: '#0E7490', ies: '#7C3AED',
}
