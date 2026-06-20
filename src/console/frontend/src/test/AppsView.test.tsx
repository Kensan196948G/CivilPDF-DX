// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { AppsView } from "../components/enterprise/views/AppsView";

vi.mock("../api/apps", () => ({
  getAppsReleases: vi.fn(),
  getReleaseNotes: vi.fn(),
  getBuildInfo: vi.fn(),
  getDownloadUrl: vi.fn(),
}));

import {
  getAppsReleases,
  getReleaseNotes,
  getBuildInfo,
  getDownloadUrl,
} from "../api/apps";

const releases = {
  stable_version: "v2.4.1",
  packages: [
    {
      id: "mac-pkg",
      platform: "macos",
      format: "pkg",
      label: "インストーラー (.pkg)",
      filename: "CivilPDF-Editor-2.4.1.pkg",
      version: "2.4.1",
      size_label: "84.0 MB",
      sha256: null,
      download_path: "/api/v1/apps/download/mac-pkg",
      available: false,
    },
  ],
  channels: [
    {
      id: "stable",
      label: "Stable",
      version: "v2.4.1",
      release_date: "2026-04-28",
      description: "本番推奨",
      user_count: 211,
    },
  ],
};

const notes = {
  notes: [
    {
      version: "2.4.1",
      channel: "stable" as const,
      release_date: "2026-04-28",
      summary: "PDF/A変換精度向上・セキュリティ修正",
      items: [{ type: "FIX" as const, text: "フォント埋め込みエラーを修正" }],
      highlights: "v2.4.1 highlights",
    },
    {
      version: "2.5.0-beta.3",
      channel: "beta" as const,
      release_date: "2026-05-07",
      summary: "Teams連携・新承認フロー",
      items: [{ type: "FEAT" as const, text: "Teams通知連携を追加" }],
      highlights: "beta highlights",
    },
  ],
};

const buildInfo = {
  product: "CivilPDF Editor Client",
  stable_version: "v2.4.1",
  build_number: "2.4.1+build.1287",
  git_commit: "abc1234",
  build_date: "2026-04-28",
  channel: "stable",
  runtime: "ランタイム同梱（外部依存なし）",
  supported_os: ["Windows 10 / 11 (64bit)", "macOS 13 Ventura+ (Universal)"],
  min_supported_version: "2.3.0",
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
      <AppsView {...props} />
    </QueryClientProvider>,
  );
  return props;
}

describe("AppsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAppsReleases).mockResolvedValue(releases);
    vi.mocked(getReleaseNotes).mockResolvedValue(notes);
    vi.mocked(getBuildInfo).mockResolvedValue(buildInfo);
  });

  it("renders the macOS .pkg package from the releases API", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getByText("インストーラー (.pkg)")).toBeInTheDocument();
    });
  });

  it("renders release notes from the API", async () => {
    renderView();
    await waitFor(() => {
      expect(
        screen.getByText("PDF/A変換精度向上・セキュリティ修正"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Teams連携・新承認フロー")).toBeInTheDocument();
  });

  it("filters release notes by channel", async () => {
    const user = userEvent.setup();
    renderView();
    await waitFor(() => {
      expect(screen.getByText("Teams連携・新承認フロー")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Beta" }));
    expect(screen.getByText("Teams連携・新承認フロー")).toBeInTheDocument();
    expect(
      screen.queryByText("PDF/A変換精度向上・セキュリティ修正"),
    ).not.toBeInTheDocument();
  });

  it("loads build info into a modal", async () => {
    const user = userEvent.setup();
    const props = renderView();
    await waitFor(() => {
      expect(screen.getByText("ビルド情報")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "ビルド情報" }));
    await waitFor(() => {
      expect(getBuildInfo).toHaveBeenCalled();
      expect(props.onShowModal).toHaveBeenCalledWith(
        expect.objectContaining({ title: "ビルド情報" }),
      );
    });
  });

  it("shows a coming-soon modal when a package is not yet available", async () => {
    const user = userEvent.setup();
    const props = renderView();
    await waitFor(() => {
      expect(screen.getByText("インストーラー (.pkg)")).toBeInTheDocument();
    });
    await user.click(screen.getByText("インストーラー (.pkg)"));
    expect(props.onShowModal).toHaveBeenCalled();
    expect(getDownloadUrl).not.toHaveBeenCalled();
  });

  it("marks deploy targets and KPI as demo data", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getAllByText("デモ").length).toBeGreaterThanOrEqual(2);
    });
  });
});
