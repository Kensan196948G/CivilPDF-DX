// @vitest-environment jsdom
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { SecurityView } from "../components/enterprise/views/SecurityView";

vi.mock("../api/stats", () => ({
  getSecurityStats: vi.fn(),
  getSecurityConfig: vi.fn(),
}));

import {
  getSecurityStats,
  getSecurityConfig,
  type SecurityStatsResponse,
  type SecurityConfigResponse,
} from "../api/stats";

const makeStats = (
  overrides: Partial<SecurityStatsResponse> = {},
): SecurityStatsResponse => ({
  total_events: 1234,
  login_success_total: 980,
  login_failed_total: 42,
  login_failed_30d: 7,
  provision_events_total: 15,
  active_sessions: 88,
  ...overrides,
});

const makeConfig = (
  overrides: Partial<SecurityConfigResponse> = {},
): SecurityConfigResponse => ({
  access_token_expire_minutes: 60,
  refresh_token_expire_days: 7,
  jwt_algorithm: "HS256",
  max_file_size_mb: 100,
  rbac_roles: ["admin", "manager", "engineer", "viewer"],
  audit_chain_enabled: true,
  audit_hash_algorithm: "SHA-256",
  ...overrides,
});

function makeProps() {
  return {
    onNavigate: vi.fn(),
    onShowModal: vi.fn(),
    onShowToast: vi.fn(),
  };
}

describe("SecurityView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getSecurityStats).mockResolvedValue(makeStats());
    vi.mocked(getSecurityConfig).mockResolvedValue(makeConfig());
  });

  it("calls the real security stats + config APIs on mount", async () => {
    render(<SecurityView {...makeProps()} />);
    await waitFor(() => {
      expect(getSecurityStats).toHaveBeenCalledTimes(1);
      expect(getSecurityConfig).toHaveBeenCalledTimes(1);
    });
  });

  it("renders live audit-log derived values (active sessions, failed logins, total events)", async () => {
    render(<SecurityView {...makeProps()} />);
    await waitFor(() => {
      // active_sessions = 88
      expect(screen.getByText("88")).toBeInTheDocument();
    });
    // login_failed_30d = 7
    expect(screen.getByText("7")).toBeInTheDocument();
    // total_events = 1,234 (toLocaleString)
    expect(screen.getByText("1,234")).toBeInTheDocument();
    // provision_events_total = 15
    expect(screen.getByText("15")).toBeInTheDocument();
  });

  it("renders config-based value (access token expiry from config.py)", async () => {
    render(<SecurityView {...makeProps()} />);
    await waitFor(() => {
      // access_token_expire_minutes = 60 surfaced on the encryption/token card
      expect(screen.getByText("60")).toBeInTheDocument();
    });
  });

  it("labels each card with its data provenance (実データ / 設定ベース / デモ)", async () => {
    render(<SecurityView {...makeProps()} />);
    await waitFor(() => {
      // live cards
      expect(screen.getByTestId("provenance-sso")).toHaveTextContent(
        "実データ",
      );
      expect(screen.getByTestId("provenance-auditlog")).toHaveTextContent(
        "実データ",
      );
    });
    // config card
    expect(screen.getByTestId("provenance-enc")).toHaveTextContent(
      "設定ベース",
    );
    // demo cards must be honestly labelled, never as live metrics
    expect(screen.getByTestId("provenance-dlp")).toHaveTextContent("デモ");
    expect(screen.getByTestId("provenance-ip")).toHaveTextContent("デモ");
    expect(screen.getByTestId("provenance-watermark")).toHaveTextContent(
      "デモ",
    );
  });

  it("shows a loading placeholder before the API resolves (non-demo cards)", () => {
    vi.mocked(getSecurityStats).mockReturnValueOnce(new Promise(() => {}));
    vi.mocked(getSecurityConfig).mockReturnValueOnce(new Promise(() => {}));
    render(<SecurityView {...makeProps()} />);
    // live/config cards show the ellipsis loading marker
    expect(screen.getAllByText("…").length).toBeGreaterThanOrEqual(1);
  });

  it("falls back to placeholder when the security stats API fails (no fabricated values)", async () => {
    vi.mocked(getSecurityStats).mockRejectedValueOnce(new Error("network"));
    vi.mocked(getSecurityConfig).mockResolvedValueOnce(makeConfig());
    render(<SecurityView {...makeProps()} />);
    await waitFor(() => {
      // config still renders (token expiry), proving allSettled isolation
      expect(screen.getByText("60")).toBeInTheDocument();
    });
    // live values are not invented: SSO active sessions falls back to "—"
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(1);
  });

  it("opens a modal with real login event counts when an SSO card is activated", async () => {
    const props = makeProps();
    render(<SecurityView {...props} />);
    await waitFor(() => {
      expect(screen.getByText("認証 / SSO")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("認証 / SSO"));
    expect(props.onShowModal).toHaveBeenCalledWith(
      expect.objectContaining({ title: "認証 / SSO" }),
    );
    const body = props.onShowModal.mock.calls[0][0].body as string;
    expect(body).toContain("ログイン成功（累計）: 980");
    expect(body).toContain("ログイン失敗（累計）: 42");
    expect(body).toContain("60分（config.py 実値）");
  });

  it("derives config-based policies from the real RBAC role list", async () => {
    const props = makeProps();
    render(<SecurityView {...props} />);
    await waitFor(() => {
      expect(screen.getByText("RBAC ロール定義")).toBeInTheDocument();
    });
    // desc text contains the real roles joined
    expect(
      screen.getByText(/admin \/ manager \/ engineer \/ viewer/),
    ).toBeInTheDocument();
  });

  it("filters the policy list to demo-only when the デモ pill is clicked", async () => {
    render(<SecurityView {...makeProps()} />);
    await waitFor(() => {
      expect(screen.getByText("RBAC ロール定義")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "デモ" }));
    await waitFor(() => {
      expect(screen.getByText("MFA必須ポリシー（デモ）")).toBeInTheDocument();
    });
    // config-based policy hidden under demo filter
    expect(screen.queryByText("RBAC ロール定義")).not.toBeInTheDocument();
  });

  it("filters out demo policies under the 重大 (critical) filter", async () => {
    render(<SecurityView {...makeProps()} />);
    await waitFor(() => {
      expect(screen.getByText("RBAC ロール定義")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "重大" }));
    await waitFor(() => {
      expect(screen.getByText("監査ログ改ざん防止")).toBeInTheDocument();
    });
    // demo critical policy must not appear under 重大 (demo is excluded)
    expect(
      screen.queryByText("機密文書DLPブロック（デモ）"),
    ).not.toBeInTheDocument();
  });
});
