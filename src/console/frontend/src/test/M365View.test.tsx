// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { M365View } from "../components/enterprise/views/M365View";

vi.mock("../api/m365", () => ({
  getM365Config: vi.fn(),
  testM365Connection: vi.fn(),
}));

import { getM365Config, testM365Connection } from "../api/m365";

const configConnected = {
  tenant_id: "11111111-2222-3333-4444-555555555555",
  client_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  enabled: true,
  auto_provision: true,
  default_role: "viewer",
  has_client_secret: true,
};

const configIncomplete = {
  tenant_id: "11111111-2222-3333-4444-555555555555",
  client_id: "",
  enabled: true,
  auto_provision: false,
  default_role: "viewer",
  has_client_secret: false,
};

function makeProps() {
  return {
    onNavigate: vi.fn(),
    onShowModal: vi.fn(),
    onShowToast: vi.fn(),
  };
}

function renderView(props = makeProps()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <M365View {...props} />
    </QueryClientProvider>,
  );
  return props;
}

describe("M365View", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getM365Config).mockResolvedValue(configConnected);
    vi.mocked(testM365Connection).mockResolvedValue({
      ok: true,
      stage: "msal",
      detail: "token acquired",
    });
  });

  it("renders the real tenant id and configured state from GET /m365/config", async () => {
    renderView();
    await waitFor(() => {
      expect(
        screen.getByText("11111111-2222-3333-4444-555555555555"),
      ).toBeInTheDocument();
    });
    // "設定済み" appears twice: the status pill and the secret row.
    const configured = screen.getAllByText("設定済み");
    expect(configured.length).toBeGreaterThanOrEqual(2);
    // the connection status pill carries the ep-conn-status class
    expect(
      configured.some((el) => el.className.includes("ep-conn-status")),
    ).toBe(true);
    // client id is masked
    expect(screen.getByText("aaaaaaaa…")).toBeInTheDocument();
  });

  it("shows 設定未完了 when credentials are incomplete", async () => {
    vi.mocked(getM365Config).mockResolvedValue(configIncomplete);
    renderView();
    await waitFor(() => {
      expect(screen.getByText("設定未完了")).toBeInTheDocument();
    });
  });

  it("calls POST /m365/test-connection and shows success feedback", async () => {
    const user = userEvent.setup();
    const props = renderView();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "テスト接続" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "テスト接続" }));
    await waitFor(() => {
      expect(testM365Connection).toHaveBeenCalled();
    });
    expect(props.onShowToast).toHaveBeenCalledWith(
      "Microsoft 365 接続テストに成功しました",
      "ok",
    );
    expect(props.onShowModal).toHaveBeenCalledWith(
      expect.objectContaining({ title: "接続テスト結果 — 成功" }),
    );
  });

  it("surfaces backend stage/detail on a failed test-connection", async () => {
    const axiosErr = new AxiosError("Request failed");
    axiosErr.response = {
      data: {
        detail: { ok: false, stage: "config", detail: "tenant_id is missing" },
      },
      status: 503,
      statusText: "Service Unavailable",
      headers: {},
      // minimal config object — not used by the component
      config: {} as never,
    };
    vi.mocked(testM365Connection).mockRejectedValue(axiosErr);
    const user = userEvent.setup();
    const props = renderView();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "テスト接続" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "テスト接続" }));
    await waitFor(() => {
      expect(props.onShowToast).toHaveBeenCalledWith(
        "Microsoft 365 接続テストに失敗しました",
        "error",
      );
    });
    expect(props.onShowModal).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "接続テスト結果 — 失敗",
        body: expect.stringContaining("tenant_id is missing"),
      }),
    );
  });

  it("shows an error state with a retry button when the config fetch fails", async () => {
    vi.mocked(getM365Config).mockRejectedValue(new Error("network down"));
    renderView();
    await waitFor(() => {
      expect(screen.getByText("取得失敗")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "再取得" })).toBeInTheDocument();
    expect(screen.getByText("network down")).toBeInTheDocument();
  });

  it("does not render fabricated sync rows — sync history is marked 今後提供", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getByText("今後提供")).toBeInTheDocument();
    });
    // none of the old mock sites should appear
    expect(screen.queryByText("本社 SP サイト")).not.toBeInTheDocument();
    expect(screen.queryByText("大阪支店 SP")).not.toBeInTheDocument();
  });
});
