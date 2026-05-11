import { api } from './client'

export interface StatsResponse {
  total_documents: number
  pending_approvals: number
  active_users: number
  approved_this_month: number
  uploaded_this_week: number
  total_file_size_bytes: number
  by_type: Record<string, number>
  by_status: Record<string, number>
}

export async function getStats(): Promise<StatsResponse> {
  const res = await api.get<StatsResponse>('/stats/')
  return res.data
}
