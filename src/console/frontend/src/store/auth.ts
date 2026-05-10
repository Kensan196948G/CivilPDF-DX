import { create } from 'zustand'
import type { UserResponse } from '../api/auth'

interface AuthState {
  user: UserResponse | null
  isAuthenticated: boolean
  setUser: (user: UserResponse | null) => void
  logout: () => void
}

function getInitialAuthState(): boolean {
  try {
    return !!localStorage.getItem('access_token')
  } catch {
    return false
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: getInitialAuthState(),
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  logout: () => {
    localStorage.clear()
    set({ user: null, isAuthenticated: false })
  },
}))
