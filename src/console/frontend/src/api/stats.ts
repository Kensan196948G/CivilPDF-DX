import { api } from "./client";

export interface StatsResponse {
  total_documents: number;
  pending_approvals: number;
  active_users: number;
  approved_this_month: number;
  uploaded_this_week: number;
  total_file_size_bytes: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}

export async function getStats(): Promise<StatsResponse> {
  const res = await api.get<StatsResponse>("/stats/");
  return res.data;
}

export interface ProjectStatItem {
  id: string;
  name: string;
  code: string;
  total: number;
  ok: number;
  ng: number;
  warn: number;
}

export interface ProjectStatsResponse {
  period: number;
  items: ProjectStatItem[];
}

export async function getProjectStats(
  period = 30,
): Promise<ProjectStatsResponse> {
  const res = await api.get<ProjectStatsResponse>("/stats/projects", {
    params: { period },
  });
  return res.data;
}

export interface DailyStatPoint {
  date: string;
  count: number;
}

export interface DailyStatsResponse {
  period: number;
  series: DailyStatPoint[];
}

export async function getDailyStats(period = 30): Promise<DailyStatsResponse> {
  const res = await api.get<DailyStatsResponse>("/stats/daily", {
    params: { period },
  });
  return res.data;
}
