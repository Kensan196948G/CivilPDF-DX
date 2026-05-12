// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Dashboard } from '../pages/Dashboard'
import { useAuthStore } from '../store/auth'

vi.mock('../api/documents', () => ({ listDocuments: vi.fn() }))
vi.mock('../api/projects', () => ({ listProjects: vi.fn() }))
vi.mock('../api/workflows', () => ({ listWorkflows: vi.fn() }))

import { listDocuments } from '../api/documents'
import { listProjects } from '../api/projects'
import { listWorkflows } from '../api/workflows'

const mockUser = {
  id: 'user-1',
  email: 'admin@example.com',
  username: 'admin',
  full_name: '管理者',
  role: 'admin' as const,
  status: 'active' as const,
  created_at: '2026-01-01T00:00:00Z',
  last_login: null,
}

const mockDoc = {
  id: 'doc-1',
  title: '橋梁設計図',
  document_type: 'drawing',
  status: 'approved',
  filename: 'bridge.pdf',
  file_size: 102400,
  page_count: 10,
  is_pdfa: true,
  tags: [],
  project_id: 'proj-1',
  owner_id: 'user-1',
  created_at: '2026-05-01T00:00:00Z',
  updated_at: null,
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

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ user: mockUser, isAuthenticated: true })
  })

  it('shows user greeting', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])
    vi.mocked(listWorkflows).mockResolvedValueOnce([])

    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText(/ようこそ、管理者 さん/)).toBeInTheDocument()
    })
  })

  it('shows stat cards with counts', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([mockDoc, { ...mockDoc, id: 'doc-2' }])
    vi.mocked(listProjects).mockResolvedValueOnce([{ id: 'p1', name: 'P1', code: 'P1', description: null, is_active: true, created_at: '' }])
    vi.mocked(listWorkflows).mockResolvedValueOnce([
      { id: 'wf-1', document_id: 'doc-1', document_title: '橋梁設計図', status: 'in_progress', created_at: '', completed_at: null, step_count: 2, pending_step_count: 1 },
    ])

    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('ドキュメント')).toBeInTheDocument()
      expect(screen.getByText('プロジェクト')).toBeInTheDocument()
      expect(screen.getByText('ワークフロー')).toBeInTheDocument()
      expect(screen.getByText('承認待ち')).toBeInTheDocument()
    })
  })

  it('shows pending workflow count only for in_progress status', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])
    vi.mocked(listWorkflows).mockResolvedValueOnce([
      { id: 'wf-1', document_id: 'd1', document_title: 'Doc1', status: 'in_progress', created_at: '', completed_at: null, step_count: 1, pending_step_count: 1 },
      { id: 'wf-2', document_id: 'd2', document_title: 'Doc2', status: 'approved', created_at: '', completed_at: null, step_count: 1, pending_step_count: 0 },
    ])

    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      // Total workflows = 2, pending (in_progress only) = 1
      const statValues = screen.getAllByRole('paragraph').filter((el) =>
        el.className.includes('text-3xl')
      )
      expect(statValues.some((el) => el.textContent === '2')).toBe(true)
      expect(statValues.some((el) => el.textContent === '1')).toBe(true)
    })
  })

  it('shows empty state when no documents', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])
    vi.mocked(listWorkflows).mockResolvedValueOnce([])

    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('ドキュメントがありません')).toBeInTheDocument()
    })
  })

  it('shows recent documents list (up to 5)', async () => {
    const docs = Array.from({ length: 7 }, (_, i) => ({ ...mockDoc, id: `doc-${i}`, title: `図面 ${i}` }))
    vi.mocked(listDocuments).mockResolvedValueOnce(docs)
    vi.mocked(listProjects).mockResolvedValueOnce([])
    vi.mocked(listWorkflows).mockResolvedValueOnce([])

    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('図面 0')).toBeInTheDocument()
      expect(screen.getByText('図面 4')).toBeInTheDocument()
      expect(screen.queryByText('図面 5')).not.toBeInTheDocument()
    })
  })

  it('falls back to email when full_name is absent', async () => {
    useAuthStore.setState({
      user: { ...mockUser, full_name: '' },
      isAuthenticated: true,
    })
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])
    vi.mocked(listWorkflows).mockResolvedValueOnce([])

    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText(/admin@example\.com さん/)).toBeInTheDocument()
    })
  })
})
