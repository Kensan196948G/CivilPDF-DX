// @vitest-environment jsdom
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { DashboardView } from "../components/enterprise/views/DashboardView";

vi.mock("../api/stats", () => ({
  getStats: vi.fn(),
  getDailyStats: vi.fn(),
  getProjectStats: vi.fn(),
}));
vi.mock("../api/documents", () => ({
  listDocuments: vi.fn(),
}));
vi.mock("../api/auditLogs", () => ({
  listAuditLogs: vi.fn(),
}));
vi.mock("../api/users", () => ({
  listUsers: vi.fn(),
}));

import { getStats, getDailyStats } from "../api/stats";
import { listDocuments } from "../api/documents";
import { listAuditLogs } from "../api/auditLogs";

const mockStats = {
  total_documents: 128,
  pending_approvals: 4,
  active_users: 12,
  approved_this_month: 30,
  uploaded_this_week: 7,
  total_file_size_bytes: 1048576,
  by_type: { drawing: 20, report: 8 },
  by_status: { approved: 22, rejected: 3, pending_review: 3 },
};

const mockDaily = {
  period: 30,
  series: Array.from({ length: 30 }, (_, i) => ({
    date: `2026-06-${String(i + 1).padStart(2, "0")}`,
    count: i % 3,
  })),
};

const makeDoc = (overrides = {}) => ({
  id: "doc-1",
  title: "橋梁設計図",
  document_type: "drawing",
  status: "approved",
  filename: "bridge.pdf",
  file_size: 102400,
  page_count: 12,
  is_pdfa: true,
  tags: [],
  project_id: "proj-1",
  owner_id: "user-1",
  created_at: new Date().toISOString(),
  updated_at: null,
  ...overrides,
});

const makeAudit = (overrides = {}) => ({
  id: "log-1",
  user_id: "user-1",
  action: "m365_login_success",
  resource_type: "auth",
  resource_id: null,
  detail: null,
  ip_address: null,
  created_at: new Date().toISOString(),
  user: {
    id: "user-1",
    email: "yamada@example.com",
    username: "yamada",
    full_name: "山田直人",
    role: "engineer",
  },
  ...overrides,
});

function makeProps(overrides = {}) {
  return {
    subView: "overview" as const,
    period: 30,
    filter: "all",
    onNavigate: vi.fn(),
    onShowModal: vi.fn(),
    onShowToast: vi.fn(),
    ...overrides,
  };
}

describe("DashboardView > OverviewSubView (real data)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getDailyStats).mockResolvedValue(mockDaily);
    vi.mocked(listDocuments).mockResolvedValue([]);
    vi.mocked(listAuditLogs).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 8,
      pages: 0,
    });
  });

  it("shows loading state initially", () => {
    vi.mocked(getStats).mockReturnValueOnce(new Promise(() => {}));
    render(<DashboardView {...makeProps()} />);
    expect(screen.getByText("読み込み中...")).toBeInTheDocument();
  });

  it("renders KPI cards from real getStats() values", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("総ドキュメント数")).toBeInTheDocument();
    });
    expect(screen.getByText("128")).toBeInTheDocument(); // total_documents
    expect(screen.getByText("今週 +7件")).toBeInTheDocument(); // uploaded_this_week
    expect(screen.getByText("30")).toBeInTheDocument(); // approved_this_month
    expect(screen.getByText("3")).toBeInTheDocument(); // rejected (NG)
    expect(screen.getByText("4")).toBeInTheDocument(); // pending_approvals
    expect(screen.getByText("12")).toBeInTheDocument(); // active_users
  });

  it("renders recent documents from listDocuments()", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    vi.mocked(listDocuments).mockResolvedValueOnce([
      makeDoc({ id: "d1", title: "特記仕様書 R6" }),
    ]);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("特記仕様書 R6")).toBeInTheDocument();
    });
    expect(screen.getByText("図面")).toBeInTheDocument(); // doc type label
  });

  it("renders activity from real audit logs", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    vi.mocked(listAuditLogs).mockResolvedValueOnce({
      items: [makeAudit()],
      total: 1,
      page: 1,
      per_page: 8,
      pages: 1,
    });
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("山田直人")).toBeInTheDocument();
    });
    expect(screen.getByText("がログイン")).toBeInTheDocument();
  });

  it("shows empty document state when none returned", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    vi.mocked(listDocuments).mockResolvedValueOnce([]);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("ドキュメントがありません")).toBeInTheDocument();
    });
  });

  it("shows empty activity state when no audit logs", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(
        screen.getByText("該当するアクティビティはありません"),
      ).toBeInTheDocument();
    });
  });

  it("shows error state when getStats() rejects", async () => {
    vi.mocked(getStats).mockRejectedValueOnce(new Error("boom"));
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(
        screen.getByText("統計データの取得に失敗しました"),
      ).toBeInTheDocument();
    });
  });

  it("filters documents to rejected only when filter=ng", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    vi.mocked(listDocuments).mockResolvedValueOnce([
      makeDoc({ id: "d1", title: "承認済ドキュメント", status: "approved" }),
      makeDoc({ id: "d2", title: "却下ドキュメント", status: "rejected" }),
    ]);
    render(<DashboardView {...makeProps({ filter: "ng" })} />);

    await waitFor(() => {
      expect(screen.getByText("却下ドキュメント")).toBeInTheDocument();
    });
    expect(screen.queryByText("承認済ドキュメント")).not.toBeInTheDocument();
  });

  it("opens modal with document detail on row click", async () => {
    const onShowModal = vi.fn();
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    vi.mocked(listDocuments).mockResolvedValueOnce([
      makeDoc({ id: "d1", title: "クリック対象", page_count: 9 }),
    ]);
    render(<DashboardView {...makeProps({ onShowModal })} />);

    await waitFor(() => {
      expect(screen.getByText("クリック対象")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("クリック対象"));
    expect(onShowModal).toHaveBeenCalledWith(
      expect.objectContaining({ title: "クリック対象" }),
    );
  });

  it("shows empty trend message when daily series is empty", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    vi.mocked(getDailyStats).mockResolvedValueOnce({ period: 30, series: [] });
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(
        screen.getByText("該当期間のアップロードデータはありません"),
      ).toBeInTheDocument();
    });
  });
});
