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

/**
 * Security event counts aggregated from the append-only audit log.
 * All values are real audit_logs data — not fabricated/real-time estimates.
 */
export interface SecurityStatsResponse {
  total_events: number;
  login_success_total: number;
  login_failed_total: number;
  login_failed_30d: number;
  provision_events_total: number;
  active_sessions: number;
}

export async function getSecurityStats(): Promise<SecurityStatsResponse> {
  const res = await api.get<SecurityStatsResponse>("/stats/security");
  return res.data;
}

/**
 * Server security configuration (config-based / static, NOT real-time traffic).
 * Reflects config.py and the RBAC role enum currently in effect.
 */
export interface SecurityConfigResponse {
  access_token_expire_minutes: number;
  refresh_token_expire_days: number;
  jwt_algorithm: string;
  max_file_size_mb: number;
  rbac_roles: string[];
  audit_chain_enabled: boolean;
  audit_hash_algorithm: string;
}

export async function getSecurityConfig(): Promise<SecurityConfigResponse> {
  const res = await api.get<SecurityConfigResponse>("/stats/security-config");
  return res.data;
}
