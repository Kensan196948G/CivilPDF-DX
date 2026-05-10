import { api } from './client'

export interface WorkflowStep {
  id: string
  step_number: number
  step_name: string
  approver_id: string
  status: string
  comment: string | null
  decided_at: string | null
}

export interface WorkflowResponse {
  id: string
  document_id: string
  title: string
  status: string
  created_by: string
  created_at: string
  updated_at: string | null
  steps: WorkflowStep[]
}

export interface CreateWorkflowRequest {
  document_id: string
  title: string
  approver_ids: string[]
}

export async function listWorkflows(): Promise<WorkflowResponse[]> {
  const res = await api.get<WorkflowResponse[]>('/workflows/')
  return res.data
}

export async function getWorkflow(id: string): Promise<WorkflowResponse> {
  const res = await api.get<WorkflowResponse>(`/workflows/${id}`)
  return res.data
}

export async function createWorkflow(data: CreateWorkflowRequest): Promise<WorkflowResponse> {
  const res = await api.post<WorkflowResponse>('/workflows/', data)
  return res.data
}

export async function decideStep(
  workflowId: string,
  stepId: string,
  decision: 'approve' | 'reject',
  comment?: string,
): Promise<WorkflowResponse> {
  const res = await api.post<WorkflowResponse>(
    `/workflows/${workflowId}/steps/${stepId}/decide`,
    { decision, comment },
  )
  return res.data
}
