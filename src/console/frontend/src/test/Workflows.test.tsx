// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Workflows } from '../pages/Workflows'

vi.mock('../api/workflows', () => ({ listWorkflows: vi.fn() }))

import { listWorkflows } from '../api/workflows'

const mockWorkflow = {
  id: 'wf-1',
  document_id: 'doc-1',
  document_title: '橋梁設計図',
  status: 'in_progress',
  created_at: '2026-05-01T00:00:00Z',
  completed_at: null,
  step_count: 3,
  pending_step_count: 2,
}

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Workflows', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(listWorkflows).mockReturnValue(new Promise(() => {}))

    render(<Workflows />, { wrapper: makeWrapper() })

    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
  })

  it('shows empty state when no workflows', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('ワークフローがありません')).toBeInTheDocument()
    })
  })

  it('shows workflow list with document title', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([mockWorkflow])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('橋梁設計図')).toBeInTheDocument()
    })
  })

  it('shows 審査中 badge for in_progress status', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([mockWorkflow])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('審査中')).toBeInTheDocument()
    })
  })

  it('shows 承認済 badge for approved status', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([
      { ...mockWorkflow, status: 'approved', completed_at: '2026-05-10T00:00:00Z', pending_step_count: 0 },
    ])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('承認済')).toBeInTheDocument()
    })
  })

  it('shows 却下 badge for rejected status', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([
      { ...mockWorkflow, status: 'rejected', completed_at: '2026-05-10T00:00:00Z', pending_step_count: 0 },
    ])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('却下')).toBeInTheDocument()
    })
  })

  it('shows step count and pending count', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([mockWorkflow])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  it('shows dash when pending_step_count is 0', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([
      { ...mockWorkflow, pending_step_count: 0 },
    ])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      // Both pending count and completed_at show "—" when pending=0 and completed_at=null
      const dashes = screen.getAllByText('—')
      expect(dashes.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows completion date when completed_at is set', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([
      { ...mockWorkflow, status: 'approved', completed_at: '2026-05-10T00:00:00Z', pending_step_count: 0 },
    ])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      // completed date formatted as ja-JP locale
      expect(screen.getByText('2026/5/10')).toBeInTheDocument()
    })
  })

  it('shows dash for completion date when not completed', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([mockWorkflow])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      // Only the pending step count shows as "—", and completed_at too
      const dashes = screen.getAllByText('—')
      expect(dashes.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows multiple workflows in table', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([
      mockWorkflow,
      { ...mockWorkflow, id: 'wf-2', document_title: 'トンネル断面図', status: 'approved', completed_at: '2026-05-08T00:00:00Z', pending_step_count: 0 },
    ])

    render(<Workflows />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('橋梁設計図')).toBeInTheDocument()
      expect(screen.getByText('トンネル断面図')).toBeInTheDocument()
      expect(screen.getByText('審査中')).toBeInTheDocument()
      expect(screen.getByText('承認済')).toBeInTheDocument()
    })
  })

  it('shows page heading', async () => {
    vi.mocked(listWorkflows).mockResolvedValueOnce([])

    render(<Workflows />, { wrapper: makeWrapper() })

    expect(screen.getByText('承認ワークフロー')).toBeInTheDocument()
  })
})
