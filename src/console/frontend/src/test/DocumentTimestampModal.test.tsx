// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { DocumentTimestampModal } from "../components/DocumentTimestampModal";

vi.mock("../api/documents", () => ({
  verifyTimestamp: vi.fn(),
  applyTimestamp: vi.fn(),
}));

import { verifyTimestamp, applyTimestamp } from "../api/documents";

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

const validVerifyData = {
  document_id: "doc-1",
  valid: true,
  message: "有効",
  file_hash: "abc123deadbeef",
  verified_at: "2026-06-01T10:00:00Z",
};

const invalidVerifyData = {
  document_id: "doc-1",
  valid: false,
  message: "ハッシュ不一致",
  file_hash: null,
  verified_at: null,
};

const applyResponseData = {
  document_id: "doc-1",
  file_hash: "abc123",
  token_type: "rfc3161" as const,
  tsa_url: "http://tsa.example.com",
  verified_at: "2026-06-01T10:00:00Z",
  token_present: true,
};

describe("DocumentTimestampModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state while fetching verify data", () => {
    vi.mocked(verifyTimestamp).mockReturnValue(new Promise(() => {}));
    render(
      <DocumentTimestampModal
        documentId="doc-1"
        documentTitle="テスト図面"
        onClose={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    expect(screen.getByText("確認中...")).toBeInTheDocument();
  });

  it("shows modal title and document title", () => {
    vi.mocked(verifyTimestamp).mockReturnValue(new Promise(() => {}));
    render(
      <DocumentTimestampModal
        documentId="doc-1"
        documentTitle="平面図"
        onClose={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    expect(screen.getByText("🔏 電子タイムスタンプ")).toBeInTheDocument();
    expect(screen.getByText("平面図")).toBeInTheDocument();
  });

  it("shows valid timestamp status with hash", async () => {
    vi.mocked(verifyTimestamp).mockResolvedValue(validVerifyData);
    render(
      <DocumentTimestampModal
        documentId="doc-1"
        documentTitle="テスト図面"
        onClose={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    await waitFor(() => {
      expect(screen.getByText("✅ 整合性確認済み")).toBeInTheDocument();
    });
    expect(screen.getByText(/SHA-256: abc123deadbeef/)).toBeInTheDocument();
    expect(screen.getByText(/タイムスタンプ付与日時:/)).toBeInTheDocument();
  });

  it("shows invalid timestamp status with error message", async () => {
    vi.mocked(verifyTimestamp).mockResolvedValue(invalidVerifyData);
    render(
      <DocumentTimestampModal
        documentId="doc-1"
        documentTitle="テスト図面"
        onClose={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    await waitFor(() => {
      expect(screen.getByText("❌ ハッシュ不一致")).toBeInTheDocument();
    });
  });

  it("shows success message after applying timestamp", async () => {
    vi.mocked(verifyTimestamp).mockResolvedValue(invalidVerifyData);
    vi.mocked(applyTimestamp).mockResolvedValue(applyResponseData);
    const user = userEvent.setup();
    render(
      <DocumentTimestampModal
        documentId="doc-1"
        documentTitle="テスト図面"
        onClose={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    await user.click(
      screen.getByRole("button", { name: /タイムスタンプ付与/ }),
    );
    await waitFor(() => {
      expect(
        screen.getByText("✅ タイムスタンプを付与しました。"),
      ).toBeInTheDocument();
    });
  });

  it("shows error message when apply fails", async () => {
    vi.mocked(verifyTimestamp).mockResolvedValue(invalidVerifyData);
    vi.mocked(applyTimestamp).mockRejectedValue(new Error("サーバーエラー"));
    const user = userEvent.setup();
    render(
      <DocumentTimestampModal
        documentId="doc-1"
        documentTitle="テスト図面"
        onClose={vi.fn()}
      />,
      { wrapper: makeWrapper() },
    );
    await user.click(
      screen.getByRole("button", { name: /タイムスタンプ付与/ }),
    );
    await waitFor(() => {
      expect(
        screen.getByText("❌ タイムスタンプ付与に失敗しました。"),
      ).toBeInTheDocument();
    });
  });

  it("calls onClose when footer close button clicked", async () => {
    vi.mocked(verifyTimestamp).mockReturnValue(new Promise(() => {}));
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <DocumentTimestampModal
        documentId="doc-1"
        documentTitle="図面"
        onClose={onClose}
      />,
      { wrapper: makeWrapper() },
    );
    await user.click(screen.getByText("閉じる"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
