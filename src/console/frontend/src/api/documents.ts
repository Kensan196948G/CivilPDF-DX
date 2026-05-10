import { api } from './client'

export interface DocumentResponse {
  id: string
  title: string
  document_type: string
  status: string
  filename: string
  file_size: number
  page_count: number | null
  is_pdfa: boolean
  tags: string[]
  project_id: string
  owner_id: string
  created_at: string
  updated_at: string | null
}

export interface ListDocumentsParams {
  project_id?: string
  document_type?: string
  status?: string
  page?: number
  per_page?: number
}

export async function listDocuments(params?: ListDocumentsParams): Promise<DocumentResponse[]> {
  const res = await api.get<DocumentResponse[]>('/documents/', { params })
  return res.data
}

export async function uploadDocument(
  projectId: string,
  title: string,
  documentType: string,
  file: File
): Promise<DocumentResponse> {
  const form = new FormData()
  form.append('project_id', projectId)
  form.append('title', title)
  form.append('document_type', documentType)
  form.append('file', file)
  const res = await api.post<DocumentResponse>('/documents/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`)
}
