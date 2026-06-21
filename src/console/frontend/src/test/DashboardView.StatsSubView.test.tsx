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

import { getStats, getProjectStats } from "../api/stats";

const mockStats = {
  total_documents: 50,
  pending_approvals: 2,
  active_users: 8,
  approved_this_month: 20,
  uploaded_this_week: 5,
  total_file_size_bytes: 2048,
  by_type: { drawing: 30, report: 12, photo: 8 },
  by_status: { approved: 35, rejected: 5, pending_review: 10 },
};

const mockProjectStats = {
  period: 30,
  items: [
    {
      id: "p1",
      name: "県道改良工事",
      code: "2024-038",
      total: 10,
      ok: 7,
      ng: 2,
      warn: 1,
    },
    {
      id: "p2",
      name: "橋梁詳細設計",
      code: "2024-041",
      total: 5,
      ok: 5,
      ng: 0,
      warn: 0,
    },
  ],
};

function makeProps(overrides = {}) {
  return {
    subView: "stats" as const,
    period: 30,
    filter: "all",
    onNavigate: vi.fn(),
    onShowModal: vi.fn(),
    onShowToast: vi.fn(),
    ...overrides,
  };
}

describe("DashboardView > StatsSubView (real data)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProjectStats).mockResolvedValue(mockProjectStats);
  });

  it("shows loading state initially", () => {
    vi.mocked(getStats).mockReturnValueOnce(new Promise(() => {}));
    vi.mocked(getProjectStats).mockReturnValueOnce(new Promise(() => {}));
    render(<DashboardView {...makeProps()} />);
    expect(screen.getByText("読み込み中...")).toBeInTheDocument();
  });

  it("renders type breakdown from real by_type", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("種別別ドキュメント統計")).toBeInTheDocument();
    });
    expect(screen.getByText("図面")).toBeInTheDocument();
    expect(screen.getByText("報告書")).toBeInTheDocument();
    expect(screen.getByText("写真台帳")).toBeInTheDocument();
  });

  it("renders status breakdown from real by_status", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("ステータス別内訳")).toBeInTheDocument();
    });
    expect(screen.getByText("承認済")).toBeInTheDocument();
    // "却下" appears as both a status pill and the project table column header.
    expect(screen.getAllByText("却下").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("レビュー待ち")).toBeInTheDocument();
  });

  it("renders project rows from real getProjectStats()", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("県道改良工事")).toBeInTheDocument();
    });
    expect(screen.getByText("橋梁詳細設計")).toBeInTheDocument();
  });

  it("filters projects to NG only via project filter pill", async () => {
    vi.mocked(getStats).mockResolvedValueOnce(mockStats);
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("県道改良工事")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "NG" }));

    await waitFor(() => {
      expect(screen.getByText("県道改良工事")).toBeInTheDocument(); // ng=2
      expect(screen.queryByText("橋梁詳細設計")).not.toBeInTheDocument(); // ng=0
    });
  });

  it("shows empty type state when no documents", async () => {
    vi.mocked(getStats).mockResolvedValueOnce({
      ...mockStats,
      by_type: {},
      by_status: {},
    });
    vi.mocked(getProjectStats).mockResolvedValueOnce({ period: 30, items: [] });
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("ドキュメントがありません")).toBeInTheDocument();
    });
    expect(screen.getByText("該当工事なし")).toBeInTheDocument();
  });

  it("shows error state when both stats sources reject", async () => {
    vi.mocked(getStats).mockRejectedValueOnce(new Error("boom"));
    vi.mocked(getProjectStats).mockRejectedValueOnce(new Error("boom"));
    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(
        screen.getByText("統計データの取得に失敗しました"),
      ).toBeInTheDocument();
    });
  });
});
