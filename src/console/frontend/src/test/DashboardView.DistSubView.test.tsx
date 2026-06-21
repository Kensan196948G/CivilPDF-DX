// @vitest-environment jsdom
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { DashboardView } from "../components/enterprise/views/DashboardView";

vi.mock("../api/stats", () => ({
  getStats: vi.fn(),
  getDailyStats: vi.fn(),
  getProjectStats: vi.fn(),
}));
vi.mock("../api/documents", () => ({ listDocuments: vi.fn() }));
vi.mock("../api/auditLogs", () => ({ listAuditLogs: vi.fn() }));
vi.mock("../api/users", () => ({ listUsers: vi.fn() }));

function makeProps(overrides = {}) {
  return {
    subView: "dist" as const,
    period: 30,
    filter: "all",
    onNavigate: vi.fn(),
    onShowModal: vi.fn(),
    onShowToast: vi.fn(),
    ...overrides,
  };
}

describe("DashboardView > DistSubView (honest not-provided state)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("honestly states distribution metrics are not provided by API", () => {
    render(<DashboardView {...makeProps()} />);
    expect(
      screen.getByText(/現在 API で提供されていません/),
    ).toBeInTheDocument();
  });

  it("navigates to apps view when button clicked", () => {
    const onNavigate = vi.fn();
    render(<DashboardView {...makeProps({ onNavigate })} />);
    fireEvent.click(screen.getByRole("button", { name: "アプリ配信を開く" }));
    expect(onNavigate).toHaveBeenCalledWith("apps");
  });
});
