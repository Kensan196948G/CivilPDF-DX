// @vitest-environment jsdom
import { vi, describe, it, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "../api/client";
import { getAiConfig, updateAiConfig, testAiConfig } from "../api/aiSettings";

const configData = {
  model_name: "claude-haiku-4-5-20251001",
  enabled: false,
  has_api_key: false,
};

const updatedConfigData = {
  model_name: "claude-sonnet-4-6",
  enabled: true,
  has_api_key: true,
};

const testResultOk = {
  ok: true,
  message: "接続成功。モデル: claude-haiku-4-5-20251001",
  model: "claude-haiku-4-5-20251001",
};

const testResultFail = {
  ok: false,
  message: "APIキーが設定されていません。",
};

describe("aiSettings api client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getAiConfig calls GET /ai-config and returns data", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: configData });
    const result = await getAiConfig();
    expect(api.get).toHaveBeenCalledWith("/ai-config");
    expect(result).toEqual(configData);
  });

  it("updateAiConfig calls PUT /ai-config with body and returns data", async () => {
    vi.mocked(api.put).mockResolvedValue({ data: updatedConfigData });
    const body = {
      model_name: "claude-sonnet-4-6",
      enabled: true,
      api_key: "sk-ant-test",
    };
    const result = await updateAiConfig(body);
    expect(api.put).toHaveBeenCalledWith("/ai-config", body);
    expect(result).toEqual(updatedConfigData);
  });

  it("updateAiConfig with partial body sends only provided fields", async () => {
    vi.mocked(api.put).mockResolvedValue({
      data: { ...configData, enabled: true },
    });
    const body = { enabled: true };
    const result = await updateAiConfig(body);
    expect(api.put).toHaveBeenCalledWith("/ai-config", body);
    expect(result.enabled).toBe(true);
  });

  it("testAiConfig calls POST /ai-config/test and returns ok result", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: testResultOk });
    const result = await testAiConfig();
    expect(api.post).toHaveBeenCalledWith("/ai-config/test");
    expect(result.ok).toBe(true);
    expect(result.message).toContain("接続成功");
  });

  it("testAiConfig returns not-ok when API key missing", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: testResultFail });
    const result = await testAiConfig();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("APIキー");
  });
});
