// @vitest-environment jsdom
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { DashboardView } from "../components/enterprise/views/DashboardView";

vi.mock("../api/users", () => ({
  listUsers: vi.fn(),
}));

vi.mock("../api/stats", () => ({
  getStats: vi.fn(),
}));

import { listUsers } from "../api/users";

const makeUser = (overrides: Partial<{
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: "admin" | "manager" | "engineer" | "viewer";
  status: "active" | "inactive" | "suspended";
  last_login: string | null;
  created_at: string;
}> = {}) => ({
  id: "user-1",
  email: "admin@example.com",
  username: "admin_user",
  full_name: "山田太郎",
  role: "admin" as const,
  status: "active" as const,
  last_login: "2026-06-15T09:30:00Z",
  created_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

function makeProps(overrides: Partial<Parameters<typeof DashboardView>[0]> = {}) {
  return {
    subView: "users" as const,
    period: 30,
    filter: "all",
    onNavigate: vi.fn(),
    onShowModal: vi.fn(),
    onShowToast: vi.fn(),
    ...overrides,
  };
}

describe("DashboardView > UsersSubView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", async () => {
    // Never resolves during the synchronous render phase
    vi.mocked(listUsers).mockReturnValueOnce(new Promise(() => {}));

    render(<DashboardView {...makeProps()} />);

    expect(screen.getByText("読み込み中...")).toBeInTheDocument();
  });

  it("renders user table after successful API call", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([makeUser()]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("山田太郎")).toBeInTheDocument();
    });
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getAllByText("管理者").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("admin_user")).toBeInTheDocument();
    expect(screen.getByText("有効")).toBeInTheDocument();
    expect(screen.getByText("2026-06-15 09:30")).toBeInTheDocument();
  });

  it("shows initials avatar from full_name", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([makeUser({ full_name: "鈴木花子" })]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("鈴木花子")).toBeInTheDocument();
    });
    expect(screen.getByText("鈴")).toBeInTheDocument();
  });

  it("shows 未ログイン when last_login is null", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([makeUser({ last_login: null })]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("未ログイン")).toBeInTheDocument();
    });
  });

  it("shows empty state when API returns empty list", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("該当ユーザーなし")).toBeInTheDocument();
    });
  });

  it("shows empty state on API error (error fallback)", async () => {
    vi.mocked(listUsers).mockRejectedValueOnce(new Error("Network error"));

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("該当ユーザーなし")).toBeInTheDocument();
    });
  });

  it("filters users by role when role filter pill is clicked", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([
      makeUser({ id: "u1", full_name: "管理者A", role: "admin" }),
      makeUser({ id: "u2", full_name: "エンジニアB", role: "engineer" }),
    ]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("管理者A")).toBeInTheDocument();
    });
    expect(screen.getByText("エンジニアB")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "管理者" }));

    await waitFor(() => {
      expect(screen.getByText("管理者A")).toBeInTheDocument();
      expect(screen.queryByText("エンジニアB")).not.toBeInTheDocument();
    });
  });

  it("filters out inactive users when filter=ng", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([
      makeUser({ id: "u1", full_name: "有効ユーザー", status: "active" }),
      makeUser({ id: "u2", full_name: "停止ユーザー", status: "suspended" }),
    ]);

    render(<DashboardView {...makeProps({ filter: "ng" })} />);

    await waitFor(() => {
      expect(screen.getByText("停止ユーザー")).toBeInTheDocument();
    });
    expect(screen.queryByText("有効ユーザー")).not.toBeInTheDocument();
  });

  it("shows only active users when filter=ok", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([
      makeUser({ id: "u1", full_name: "有効ユーザー", status: "active" }),
      makeUser({ id: "u2", full_name: "無効ユーザー", status: "inactive" }),
    ]);

    render(<DashboardView {...makeProps({ filter: "ok" })} />);

    await waitFor(() => {
      expect(screen.getByText("有効ユーザー")).toBeInTheDocument();
    });
    expect(screen.queryByText("無効ユーザー")).not.toBeInTheDocument();
  });

  it("calls onShowModal with user details when row is clicked", async () => {
    const onShowModal = vi.fn();
    vi.mocked(listUsers).mockResolvedValueOnce([
      makeUser({ full_name: "田中次郎", email: "tanaka@example.com", username: "tanaka", role: "manager" }),
    ]);

    render(<DashboardView {...makeProps({ onShowModal })} />);

    await waitFor(() => {
      expect(screen.getByText("田中次郎")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("田中次郎"));

    expect(onShowModal).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "田中次郎",
        body: expect.stringContaining("tanaka@example.com"),
      }),
    );
    expect(onShowModal.mock.calls[0][0].body).toContain("マネージャー");
  });

  it("renders all four role labels in role distribution panel", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([
      makeUser({ id: "u1", role: "admin" }),
      makeUser({ id: "u2", role: "manager" }),
      makeUser({ id: "u3", role: "engineer" }),
      makeUser({ id: "u4", role: "viewer" }),
    ]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getAllByText("管理者").length).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getAllByText("マネージャー").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("エンジニア").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("閲覧者").length).toBeGreaterThanOrEqual(1);
  });

  it("renders suspended status pill correctly", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([
      makeUser({ status: "suspended" }),
    ]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("停止中")).toBeInTheDocument();
    });
  });

  it("renders inactive status pill correctly", async () => {
    vi.mocked(listUsers).mockResolvedValueOnce([
      makeUser({ status: "inactive" }),
    ]);

    render(<DashboardView {...makeProps()} />);

    await waitFor(() => {
      expect(screen.getByText("無効")).toBeInTheDocument();
    });
  });
});
