import { api } from './client'

export interface ProjectResponse {
  id: string
  name: string
  code: string
  description: string | null
  status: string
  start_date: string | null
  end_date: string | null
  owner_id: string
  created_at: string
  updated_at: string | null
}

export interface CreateProjectRequest {
  name: string
  code: string
  description?: string
  start_date?: string
  end_date?: string
}

export async function listProjects(): Promise<ProjectResponse[]> {
  const res = await api.get<ProjectResponse[]>('/projects/')
  return res.data
}

export async function getProject(id: string): Promise<ProjectResponse> {
  const res = await api.get<ProjectResponse>(`/projects/${id}`)
  return res.data
}

export async function createProject(data: CreateProjectRequest): Promise<ProjectResponse> {
  const res = await api.post<ProjectResponse>('/projects/', data)
  return res.data
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`)
}
