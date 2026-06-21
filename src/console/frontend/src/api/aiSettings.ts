import { api } from "./client";

// Mirrors backend api/ai_settings.py AiConfig response model.
// api_key is write-only and never returned — has_api_key indicates presence.
export interface AiConfig {
  model_name: string;
  enabled: boolean;
  has_api_key: boolean;
}

// All fields optional; api_key is write-only (sent on update, never read back).
export interface AiConfigUpdate {
  model_name?: string;
  api_key?: string;
  enabled?: boolean;
}

export interface AiConfigTestResult {
  ok: boolean;
  message: string;
  model?: string;
}

export async function getAiConfig(): Promise<AiConfig> {
  const res = await api.get<AiConfig>("/ai-config");
  return res.data;
}

export async function updateAiConfig(body: AiConfigUpdate): Promise<AiConfig> {
  const res = await api.put<AiConfig>("/ai-config", body);
  return res.data;
}

export async function testAiConfig(): Promise<AiConfigTestResult> {
  const res = await api.post<AiConfigTestResult>("/ai-config/test");
  return res.data;
}
