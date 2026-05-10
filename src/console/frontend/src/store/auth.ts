import { create } from 'zustand'
import type { UserResponse } from '../api/auth'

interface AuthState {
  user: UserResponse | null
  isAuthenticated: boolean
  setUser: (user: UserResponse | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  logout: () => {
    localStorage.clear()
    set({ user: null, isAuthenticated: false })
  },
}))
