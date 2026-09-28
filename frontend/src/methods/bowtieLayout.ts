import type { Edge, Node } from '@xyflow/react'
import { MarkerType } from '@xyflow/react'

export type Barrier = { id: string; text: string; kind: string; owner: string; effectiveness: string; critical: boolean; verification: string; spi?: string }
export type Path = { id: string; text: string; barriers: string[]; severity?: string }
export type Escalation = { id: string; text: string; barrier: string; ef_barriers: string[] }
export type BowtieModel = { hazard: string; top_event: string; threats: Path[]; consequences: Path[]; barriers: Record<string, Barrier>; escalation: Escalation[] }

export const emptyBowtie = (): BowtieModel => ({ hazard: 'Hazard', top_event: 'Top event', threats: [], consequences: [], barriers: {}, escalation: [] })

export const EFFECTIVENESS_COLORS: Record<string, string> = { 'very good': '#1F7A4D', good: '#3C8D5A', poor: '#D98E04', 'very poor': '#B23A3A', unknown: '#9CA3AF' }
const KIND_COLORS: Record<string, string> = { hardware: '#1F3A5F', software: '#7C3AED', human: '#2A7F8E', 'human-hardware': '#0E7490', procedure: '#6B7280', organisational: '#A16207' }
const PALETTE = ['#2A7F8E', '#D98E04', '#7C3AED', '#1F3A5F', '#B23A3A', '#3C8D5A', '#A16207', '#0E7490']
const hash = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7)

export function barrierColor(b: Barrier, by: string) {
  if (by === 'kind') return KIND_COLORS[b.kind] ?? '#9CA3AF'
  if (by === 'owner') return b.owner ? PALETTE[hash(b.owner) % PALETTE.length] : '#9CA3AF'
  return EFFECTIVENESS_COLORS[b.effectiveness] ?? '#9CA3AF'
}

const TOP = 150, SIDE_W = 180, BAR_W = 130, SLOT = 150, GAP = 64, ROW = 120, EF_ROW = 118

/**
 * Deterministic bowtie layout: threats fan in on the left, consequences fan out on the right,
 * barriers sit in columns along each path, escalation factors hang below the barrier they degrade.
 */
export function layoutBowtie(m: BowtieModel, colorBy: string, selected: string | null): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []
  const usage: Record<string, number> = {}
  for (const p of [...m.threats, ...m.consequences]) for (const b of p.barriers) usage[b] = (usage[b] ?? 0) + 1
  const efByBarrier: Record<string, Escalation[]> = {}
  for (const e of m.escalation) (efByBarrier[e.barrier] ??= []).push(e)

  const side = (paths: Path[], dir: -1 | 1) => {
    const maxB = Math.max(1, ...paths.map((p) => p.barriers.length))
    const heights = paths.map((p) => ROW + (p.barriers.some((b) => efByBarrier[b]?.length) ? EF_ROW : 0))
    const total = heights.reduce((a, b) => a + b, 0)
    let y = -total / 2
    paths.forEach((p, i) => {
      const cy = y + ROW / 2 - 10
      y += heights[i]
      const endX = dir === -1 ? -TOP / 2 - GAP - maxB * SLOT - SIDE_W : TOP / 2 + GAP + maxB * SLOT
      const pathType = dir === -1 ? 'threat' : 'cons'
      nodes.push({ id: p.id, type: pathType, position: { x: endX, y: cy - 28 }, data: { path: p, selected: selected === p.id }, draggable: false })
      const chain: string[] = []
      p.barriers.forEach((bid, k) => {
        const b = m.barriers[bid]
        if (!b) return
        const nid = `${p.id}:${bid}`
        const x = dir === -1 ? endX + SIDE_W + 30 + k * SLOT : TOP / 2 + GAP + k * SLOT
        nodes.push({ id: nid, type: 'barrier', position: { x, y: cy - 28 }, draggable: false,
          data: { barrier: b, color: barrierColor(b, colorBy), shared: usage[bid] > 1 ? usage[bid] : 0, selected: selected === bid, efs: efByBarrier[bid]?.length ?? 0 } })
        chain.push(nid)
        ;(efByBarrier[bid] ?? []).forEach((ef, j) => {
          const eid = `${nid}:${ef.id}`
          nodes.push({ id: eid, type: 'ef', position: { x: x - 10 + j * 14, y: cy + 58 + j * 8 }, draggable: false, data: { ef, selected: selected === ef.id } })
          edges.push({ id: `e-${eid}`, source: eid, target: nid, sourceHandle: 'top', targetHandle: 'bottom', style: { stroke: '#D98E04', strokeDasharray: '5 4' },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#D98E04' } })
        })
      })
      const seq = dir === -1 ? [p.id, ...chain, 'top'] : ['top', ...chain, p.id]
      for (let k = 0; k < seq.length - 1; k++) {
        const last = k === seq.length - 2
        edges.push({ id: `e-${p.id}-${k}`, source: seq[k], target: seq[k + 1], type: (dir === -1 && last) || (dir === 1 && k === 0) ? 'default' : 'straight',
          sourceHandle: seq[k] === 'top' ? 'right' : undefined, targetHandle: seq[k + 1] === 'top' ? 'left' : undefined,
          style: { stroke: '#6B7280', strokeWidth: 1.4 }, markerEnd: last ? { type: MarkerType.ArrowClosed, color: '#6B7280' } : undefined })
      }
    })
    return total
  }

  const hl = side(m.threats, -1)
  const hr = side(m.consequences, 1)
  const top = Math.min(-hl / 2, -hr / 2, -TOP / 2)
  nodes.push({ id: 'top', type: 'top', position: { x: -TOP / 2, y: -TOP / 2 }, data: { text: m.top_event, selected: selected === 'top' }, draggable: false })
  nodes.push({ id: 'hazard', type: 'hazard', position: { x: -130, y: top - 150 }, data: { text: m.hazard, selected: selected === 'hazard' }, draggable: false })
  edges.push({ id: 'e-hazard', source: 'hazard', target: 'top', targetHandle: 'topin', style: { stroke: '#D98E04', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#D98E04' } })
  return { nodes, edges }
}

export function bowtieChecks(m: BowtieModel): string[] {
  const w: string[] = []
  if (/collision|accident|crash|fatal|injur|damage/i.test(m.top_event)) w.push('Top event looks like a consequence (loss of control should come before damage) — Manual §6.4.')
  for (const p of m.threats) if (p.barriers.length < 2) w.push(`Threat “${p.text}” has fewer than two prevention barriers.`)
  for (const p of m.consequences) if (p.barriers.length < 2) w.push(`Consequence “${p.text}” has fewer than two recovery barriers.`)
  for (const b of Object.values(m.barriers)) {
    if (!b.owner) w.push(`Barrier “${b.text}” has no owner.`)
    if (!Object.values([...m.threats, ...m.consequences]).some((p) => p.barriers.includes(b.id))) w.push(`Barrier “${b.text}” is not on any path.`)
  }
  return w
}
