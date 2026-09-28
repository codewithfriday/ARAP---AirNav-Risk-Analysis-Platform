import { Tooltip } from 'antd'
import type { Scheme } from '../risk'
import { classify } from '../risk'

export function RiskTag({ scheme, sev, lik, risk }: { scheme?: Scheme; sev?: string | null; lik?: number | null; risk?: any }) {
  const r = risk ?? classify(scheme, sev, lik)
  if (!r) return <span className="muted">—</span>
  const name = r.region_name ?? r.name
  return (
    <Tooltip title={`${name}${r.authority ? ` · accept: ${r.authority}` : ''}`}>
      <span className="risk-cell" style={{ background: r.color }}>{r.index}</span>
    </Tooltip>
  )
}

/** Clickable 5×5 matrix. value = {severity, likelihood}; counts optional for heat display. */
export function RiskMatrix({ scheme, value, onChange, counts, size = 44, disabled }: {
  scheme?: Scheme; value?: { severity?: string | null; likelihood?: number | null }
  onChange?: (v: { severity: string; likelihood: number }) => void; counts?: Record<string, number>; size?: number; disabled?: boolean
}) {
  if (!scheme) return null
  const levels = [...scheme.likelihood].sort((a, b) => b.level - a.level)
  return (
    <div style={{ display: 'inline-block' }}>
      <table style={{ borderCollapse: 'separate', borderSpacing: 3 }}>
        <thead>
          <tr>
            <th />
            {scheme.severity.map((s) => (
              <th key={s.code} style={{ fontSize: 10.5, fontWeight: 500, color: '#6b7280', width: size }}>{s.name}<br />{s.code}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {levels.map((l) => (
            <tr key={l.level}>
              <td style={{ fontSize: 10.5, color: '#6b7280', textAlign: 'right', paddingRight: 6, whiteSpace: 'nowrap' }}>{l.name} {l.level}</td>
              {scheme.severity.map((s) => {
                const c = classify(scheme, s.code, l.level)!
                const sel = value?.severity === s.code && Number(value?.likelihood) === l.level
                const n = counts?.[c.index]
                return (
                  <td key={s.code}>
                    <Tooltip title={`${c.index} · ${c.name}`}>
                      <div onClick={() => !disabled && onChange?.({ severity: s.code, likelihood: l.level })}
                        style={{ width: size, height: size * 0.72, background: c.color, opacity: counts ? (n ? 1 : 0.35) : sel || !value?.severity ? 1 : 0.55,
                          borderRadius: 4, color: '#fff', fontWeight: 700, fontSize: 12, display: 'grid', placeItems: 'center',
                          cursor: onChange && !disabled ? 'pointer' : 'default', outline: sel ? '3px solid #1F3A5F' : 'none', outlineOffset: 1 }}>
                        {counts ? (n ?? '') : c.index}
                      </div>
                    </Tooltip>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
