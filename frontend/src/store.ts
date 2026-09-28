import { create } from 'zustand'

export type User = {
  id: number
  username: string
  full_name: string
  role: 'admin' | 'assessor' | 'reviewer' | 'authority' | 'viewer'
  unit: string
  authority_scope: string[]
  lang: string
}

type AuthState = {
  token: string | null
  user: User | null
  setToken: (t: string | null) => void
  setUser: (u: User | null) => void
  logout: () => void
}

function readToken(): string | null {
  try {
    return localStorage.getItem('arap_token')
  } catch {
    return null
  }
}

export const useAuth = create<AuthState>((set) => ({
  token: readToken(),
  user: null,
  setToken: (t) => {
    try {
      if (t) localStorage.setItem('arap_token', t)
      else localStorage.removeItem('arap_token')
    } catch {
      /* storage unavailable */
    }
    set({ token: t })
  },
  setUser: (u) => set({ user: u }),
  logout: () => {
    try {
      localStorage.removeItem('arap_token')
    } catch {
      /* ignore */
    }
    set({ token: null, user: null })
  },
}))

export const canEdit = (u: User | null) => !!u && ['admin', 'assessor', 'reviewer'].includes(u.role)
export const isAdmin = (u: User | null) => u?.role === 'admin'
