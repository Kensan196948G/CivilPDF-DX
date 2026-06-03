import { api } from './client'

export interface NonPdfaDocumentInfo {
  id: string
  title: string
  filename: string
}

export interface DeliveryReadinessResponse {
  ready: boolean
  document_count: number
  pdfa_compliant_count: number
  non_pdfa_documents: NonPdfaDocumentInfo[]
  warnings: string[]
}

export async function checkDeliveryReadiness(projectId: string): Promise<DeliveryReadinessResponse> {
  const res = await api.get<DeliveryReadinessResponse>(
    `/projects/${projectId}/electronic-delivery/check`
  )
  return res.data
}

export async function downloadDeliveryZip(projectId: string, projectCode: string): Promise<void> {
  const res = await api.post<Blob>(
    `/projects/${projectId}/electronic-delivery`,
    {},
    { responseType: 'blob' }
  )
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const code = projectCode.replace(/[^A-Za-z0-9_]/g, '_').toUpperCase().slice(0, 16)
  a.download = `${code}_${date}.zip`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
