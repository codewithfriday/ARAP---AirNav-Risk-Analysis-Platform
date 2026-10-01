import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { Scheme } from './risk'

export function useScheme() {
  return useQuery({ queryKey: ['scheme'], queryFn: () => api.get<{ version: number; data: Scheme }>('/risk/scheme'), staleTime: 60_000 })
}

export function useMethods() {
  return useQuery({ queryKey: ['methods'], queryFn: () => api.get<Record<string, any>>('/meta/methods'), staleTime: Infinity })
}

export const uid = (p = 'id') => `${p}${Math.random().toString(36).slice(2, 8)}`

export function useAtsbScheme() {
  return useQuery({ queryKey: ['atsb-scheme'], queryFn: () => api.get<{ data: Scheme & { severity: any[]; likelihood: any[] } }>('/risk/atsb-scheme'), staleTime: Infinity })
}

export function useAtsbMeta() {
  return useQuery({ queryKey: ['atsb-meta'], queryFn: () => api.get<any>('/meta/atsb'), staleTime: Infinity })
}

export function useSamnPerelliMeta() {
  return useQuery({ queryKey: ['sp-meta'], queryFn: () => api.get<any>('/meta/samn-perelli'), staleTime: Infinity })
}
