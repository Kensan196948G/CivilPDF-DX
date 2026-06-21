import { api } from "./client";

// Mirrors backend api/m365.py M365Config (response_model). client_secret is
// write-only and never returned — the public shape only exposes whether one is
// configured via has_client_secret.
export interface M365Config {
  tenant_id: string;
  client_id: string;
  enabled: boolean;
  auto_provision: boolean;
  default_role: string;
  has_client_secret: boolean;
}

// Mirrors backend M365ConfigUpdate. All fields optional; client_secret is
// write-only (sent on update, never read back).
export interface M365ConfigUpdate {
  tenant_id?: string;
  client_id?: string;
  client_secret?: string;
  enabled?: boolean;
  auto_provision?: boolean;
  default_role?: string;
}

// Shape returned by POST /m365/test-connection. On success the backend returns
// { ok: true, ... }; on failure it raises HTTPException whose JSON body is the
// same diagnostic dict under `detail` (handled by callers via axios error).
export interface M365TestConnectionResult {
  ok: boolean;
  stage: "config" | "msal" | "unknown" | string;
  detail: string;
}

export async function getM365Config(): Promise<M365Config> {
  const res = await api.get<M365Config>("/m365/config");
  return res.data;
}

export async function updateM365Config(
  body: M365ConfigUpdate,
): Promise<M365Config> {
  const res = await api.put<M365Config>("/m365/config", body);
  return res.data;
}

export async function testM365Connection(): Promise<M365TestConnectionResult> {
  const res = await api.post<M365TestConnectionResult>("/m365/test-connection");
  return res.data;
}
