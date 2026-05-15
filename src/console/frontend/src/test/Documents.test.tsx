// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Documents } from '../pages/Documents'

vi.mock('../api/documents', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  fetchDocumentBlob: vi.fn(),
}))
vi.mock('../api/projects', () => ({ listProjects: vi.fn() }))

import { listDocuments, deleteDocument, fetchDocumentBlob } from '../api/documents'
import { listProjects } from '../api/projects'

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

const mockProject = {
  id: 'proj-1',
  name: '道路改良工事',
  code: 'RD-001',
  description: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
}

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Documents', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(listDocuments).mockReturnValue(new Promise(() => {}))
    vi.mocked(listProjects).mockReturnValue(new Promise(() => {}))

    render(<Documents />, { wrapper: makeWrapper() })

    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
  })

  it('shows empty state when no documents', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])

    render(<Documents />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('ドキュメントがありません')).toBeInTheDocument()
    })
  })

  it('shows document list', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([mockDoc])
    vi.mocked(listProjects).mockResolvedValueOnce([])

    render(<Documents />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('橋梁設計図')).toBeInTheDocument()
      expect(screen.getByText('drawing')).toBeInTheDocument()
      expect(screen.getByText('approved')).toBeInTheDocument()
      expect(screen.getByText('100 KB')).toBeInTheDocument()
    })
  })

  it('shows upload form when button clicked', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([mockProject])
    const user = userEvent.setup()

    render(<Documents />, { wrapper: makeWrapper() })

    await user.click(screen.getByRole('button', { name: '+ アップロード' }))

    expect(screen.getByText('ドキュメントのアップロード')).toBeInTheDocument()
    expect(screen.getByLabelText('タイトル')).toBeInTheDocument()
    expect(screen.getByLabelText('プロジェクト')).toBeInTheDocument()
    expect(screen.getByLabelText('種別')).toBeInTheDocument()
    expect(screen.getByLabelText('PDFファイル')).toBeInTheDocument()
  })

  it('hides upload form when cancel clicked', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])
    const user = userEvent.setup()

    render(<Documents />, { wrapper: makeWrapper() })

    await user.click(screen.getByRole('button', { name: '+ アップロード' }))
    expect(screen.getByText('ドキュメントのアップロード')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'キャンセル' }))
    expect(screen.queryByText('ドキュメントのアップロード')).not.toBeInTheDocument()
  })

  it('shows project options in upload form', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([mockProject])
    const user = userEvent.setup()

    render(<Documents />, { wrapper: makeWrapper() })

    await user.click(screen.getByRole('button', { name: '+ アップロード' }))

    await waitFor(() => {
      expect(screen.getByRole('option', { name: '道路改良工事' })).toBeInTheDocument()
    })
  })

  it('shows document type options in upload form', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])
    const user = userEvent.setup()

    render(<Documents />, { wrapper: makeWrapper() })

    await user.click(screen.getByRole('button', { name: '+ アップロード' }))

    expect(screen.getByRole('option', { name: '図面' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '仕様書' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '報告書' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '契約書' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'その他' })).toBeInTheDocument()
  })

  it('upload button is enabled by default in upload form', async () => {
    vi.mocked(listDocuments).mockResolvedValueOnce([])
    vi.mocked(listProjects).mockResolvedValueOnce([])
    const user = userEvent.setup()

    render(<Documents />, { wrapper: makeWrapper() })

    await user.click(screen.getByRole('button', { name: '+ アップロード' }))

    const uploadBtn = screen.getByRole('button', { name: 'アップロード' })
    expect(uploadBtn).not.toBeDisabled()
  })

  it('calls deleteDocument when delete button clicked', async () => {
    vi.mocked(listDocuments).mockResolvedValue([mockDoc])
    vi.mocked(listProjects).mockResolvedValue([])
    vi.mocked(deleteDocument).mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<Documents />, { wrapper: makeWrapper() })

    const deleteBtn = await screen.findByRole('button', { name: '削除' })
    await user.click(deleteBtn)

    await waitFor(() => {
      expect(vi.mocked(deleteDocument).mock.calls[0]?.[0]).toBe('doc-1')
    }, { timeout: 3000 })
  })

  it('opens preview modal when preview button clicked', async () => {
    vi.mocked(listDocuments).mockResolvedValue([mockDoc])
    vi.mocked(listProjects).mockResolvedValue([])
    vi.mocked(fetchDocumentBlob).mockResolvedValue(new Blob(['pdf'], { type: 'application/pdf' }))
    const createUrl = vi.fn(() => 'blob:mock-url')
    const revokeUrl = vi.fn()
    ;(URL as unknown as { createObjectURL: typeof createUrl }).createObjectURL = createUrl
    ;(URL as unknown as { revokeObjectURL: typeof revokeUrl }).revokeObjectURL = revokeUrl
    const user = userEvent.setup()

    render(<Documents />, { wrapper: makeWrapper() })

    const previewBtn = await screen.findByRole('button', { name: 'プレビュー' })
    await user.click(previewBtn)

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'ドキュメントプレビュー' })).toBeInTheDocument()
    })
  })

  it('shows multiple documents in table', async () => {
    const docs = [
      mockDoc,
      { ...mockDoc, id: 'doc-2', title: 'トンネル断面図', status: 'pending', document_type: 'specification' },
    ]
    vi.mocked(listDocuments).mockResolvedValueOnce(docs)
    vi.mocked(listProjects).mockResolvedValueOnce([])

    render(<Documents />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByText('橋梁設計図')).toBeInTheDocument()
      expect(screen.getByText('トンネル断面図')).toBeInTheDocument()
    })
  })
})
