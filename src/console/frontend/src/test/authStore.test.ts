// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '../store/auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({ user: null, isAuthenticated: false })
  })

  it('initializes as unauthenticated when no token in localStorage', () => {
    const { isAuthenticated, user } = useAuthStore.getState()
    expect(isAuthenticated).toBe(false)
    expect(user).toBeNull()
  })

  it('setUser marks store as authenticated', () => {
    const mockUser = {
      id: '1',
      email: 'admin@test.com',
      username: 'admin',
      full_name: 'Admin',
      role: 'admin' as const,
      status: 'active' as const,
      created_at: '2026-01-01T00:00:00Z',
      last_login: null,
    }
    useAuthStore.getState().setUser(mockUser)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(useAuthStore.getState().user).toEqual(mockUser)
  })

  it('setUser(null) marks store as unauthenticated', () => {
    useAuthStore.setState({ isAuthenticated: true })
    useAuthStore.getState().setUser(null)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('logout clears localStorage and resets state', () => {
    localStorage.setItem('access_token', 'abc')
    localStorage.setItem('refresh_token', 'xyz')
    useAuthStore.setState({ isAuthenticated: true })

    useAuthStore.getState().logout()

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().user).toBeNull()
  })
})
