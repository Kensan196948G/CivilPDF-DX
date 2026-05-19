// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Settings } from '../pages/Settings'
import { useAuthStore } from '../store/auth'

vi.mock('../api/stats', () => ({ getStats: vi.fn() }))

import { getStats } from '../api/stats'

const mockAdmin = {
  id: 'user-1',
  email: 'admin@example.com',
  username: 'admin',
  full_name: '管理者',
  role: 'admin' as const,
  status: 'active' as const,
  created_at: '2026-01-01T00:00:00Z',
  last_login: null,
}

const mockViewer = {
  ...mockAdmin,
  id: 'viewer-1',
  email: 'viewer@example.com',
  username: 'viewer1',
  full_name: '閲覧ユーザー',
  role: 'viewer' as const,
}

const mockStats = {
  total_documents: 42,
  pending_approvals: 5,
  active_users: 10,
  approved_this_month: 8,
  uploaded_this_week: 3,
  total_file_size_bytes: 1048576,
  by_type: {},
  by_status: {},
}

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ user: mockAdmin, isAuthenticated: true })
  })

  it('shows page title and subtitle', () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats)
    render(<Settings />, { wrapper })
    expect(screen.getByText('設定')).toBeInTheDocument()
    expect(screen.getByText('システム設定とプロフィール情報')).toBeInTheDocument()
  })

  it('shows profile section with user info', async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats)
    render(<Settings />, { wrapper })
    expect(screen.getByText('プロフィール')).toBeInTheDocument()
    expect(screen.getAllByText('管理者').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()
  })

  it('shows Japanese role label', () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats)
    render(<Settings />, { wrapper })
    expect(screen.getAllByText('管理者').length).toBeGreaterThanOrEqual(1)
  })

  it('shows system info panel for admin', async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats)
    render(<Settings />, { wrapper })
    await waitFor(() => {
      expect(screen.getByText('システム情報')).toBeInTheDocument()
    })
  })

  it('shows stats values in system info for admin', async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats)
    render(<Settings />, { wrapper })
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument()
      expect(screen.getByText('10')).toBeInTheDocument()
    })
  })

  it('does NOT show system info panel for viewer', () => {
    useAuthStore.setState({ user: mockViewer, isAuthenticated: true })
    render(<Settings />, { wrapper })
    expect(screen.queryByText('システム情報')).not.toBeInTheDocument()
    expect(vi.mocked(getStats)).not.toHaveBeenCalled()
  })

  it('shows security policy panel', () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats)
    render(<Settings />, { wrapper })
    expect(screen.getByText('セキュリティポリシー')).toBeInTheDocument()
    expect(screen.getByText('90日')).toBeInTheDocument()
    expect(screen.getByText('8時間')).toBeInTheDocument()
  })

  it('shows viewer role label for viewer user', () => {
    useAuthStore.setState({ user: mockViewer, isAuthenticated: true })
    render(<Settings />, { wrapper })
    expect(screen.getByText('閲覧のみ')).toBeInTheDocument()
    expect(screen.getByText('閲覧ユーザー')).toBeInTheDocument()
  })

  it('shows loading state while stats are fetching', async () => {
    vi.mocked(getStats).mockImplementation(() => new Promise(() => {}))
    render(<Settings />, { wrapper })
    await waitFor(() => {
      expect(screen.getByText('読み込み中...')).toBeInTheDocument()
    })
  })
})
