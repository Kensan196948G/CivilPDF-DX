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
import {
  getM365Config,
  updateM365Config,
  testM365Connection,
} from "../api/m365";

const config = {
  tenant_id: "11111111-2222-3333-4444-555555555555",
  client_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  enabled: true,
  auto_provision: false,
  default_role: "viewer",
  has_client_secret: true,
};

describe("m365 api client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getM365Config calls GET /m365/config and returns data", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: config });
    const result = await getM365Config();
    expect(api.get).toHaveBeenCalledWith("/m365/config");
    expect(result).toEqual(config);
  });

  it("updateM365Config calls PUT /m365/config with the update body", async () => {
    const updated = { ...config, enabled: false };
    vi.mocked(api.put).mockResolvedValue({ data: updated });
    const body = { enabled: false, client_secret: "new-secret" };
    const result = await updateM365Config(body);
    expect(api.put).toHaveBeenCalledWith("/m365/config", body);
    expect(result).toEqual(updated);
  });

  it("testM365Connection calls POST /m365/test-connection and returns the result", async () => {
    const probe = { ok: true, stage: "msal", detail: "token acquired" };
    vi.mocked(api.post).mockResolvedValue({ data: probe });
    const result = await testM365Connection();
    expect(api.post).toHaveBeenCalledWith("/m365/test-connection");
    expect(result).toEqual(probe);
  });
});
