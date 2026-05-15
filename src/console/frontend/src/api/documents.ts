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

export interface Iso19650Metadata {
  originator?: string
  functional_breakdown?: string
  form?: string
  discipline?: string
  number?: string
}

export async function uploadDocument(
  projectId: string,
  title: string,
  documentType: string,
  file: File,
  iso19650?: Iso19650Metadata
): Promise<DocumentResponse> {
  const form = new FormData()
  form.append('project_id', projectId)
  form.append('title', title)
  form.append('document_type', documentType)
  form.append('file', file)
  if (iso19650?.originator) form.append('iso19650_originator', iso19650.originator)
  if (iso19650?.functional_breakdown) form.append('iso19650_functional_breakdown', iso19650.functional_breakdown)
  if (iso19650?.form) form.append('iso19650_form', iso19650.form)
  if (iso19650?.discipline) form.append('iso19650_discipline', iso19650.discipline)
  if (iso19650?.number) form.append('iso19650_number', iso19650.number)
  const res = await api.post<DocumentResponse>('/documents/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`)
}

export async function fetchDocumentBlob(id: string): Promise<Blob> {
  const res = await api.get<Blob>(`/documents/${id}/download`, {
    responseType: 'blob',
  })
  return res.data
}
