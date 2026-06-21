// @vitest-environment jsdom
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { UploadView } from "../components/enterprise/views/UploadView";
import type { ProjectResponse } from "../api/projects";

// UploadView is wired to the real document/project API. Mock both modules so
// the upload contract (project -> uploadDocument) can be asserted offline.
vi.mock("../api/documents", () => ({
  uploadDocument: vi.fn(),
}));
vi.mock("../api/projects", () => ({
  listProjects: vi.fn(),
}));

import { uploadDocument } from "../api/documents";
import { listProjects } from "../api/projects";

const project: ProjectResponse = {
  id: "p1",
  name: "プロジェクトA",
  code: "PRJ-001",
  description: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

function makeProps() {
  return {
    onNavigate: vi.fn(),
    onShowModal: vi.fn(),
    onShowToast: vi.fn(),
  };
}

function renderView(props = makeProps()) {
  const result = render(<UploadView {...props} />);
  return { props, ...result };
}

function fileInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector('input[type="file"]');
  if (!input) throw new Error("file input not found");
  return input as HTMLInputElement;
}

describe("UploadView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listProjects).mockResolvedValue([]);
  });

  it("loads projects on mount and renders the selector", async () => {
    vi.mocked(listProjects).mockResolvedValue([project]);
    renderView();
    await waitFor(() => {
      expect(listProjects).toHaveBeenCalled();
    });
    expect(
      await screen.findByText("プロジェクトA (PRJ-001)"),
    ).toBeInTheDocument();
  });

  it("hides the project selector when the project list fails to load", async () => {
    vi.mocked(listProjects).mockRejectedValue(new Error("network"));
    renderView();
    await waitFor(() => {
      expect(listProjects).toHaveBeenCalled();
    });
    expect(screen.queryByLabelText("プロジェクト:")).not.toBeInTheDocument();
  });

  it("uploads a selected file to the active project", async () => {
    vi.mocked(listProjects).mockResolvedValue([project]);
    vi.mocked(uploadDocument).mockResolvedValue({} as never);
    const { props, container } = renderView();
    await screen.findByText("プロジェクトA (PRJ-001)");

    const file = new File(["pdf-bytes"], "test.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput(container), { target: { files: [file] } });

    await waitFor(() => {
      expect(uploadDocument).toHaveBeenCalledWith(
        "p1",
        "test",
        "drawing",
        file,
        {},
      );
    });
    expect(props.onShowToast).toHaveBeenCalledWith(
      "test.pdf をアップロードしました",
      "ok",
    );
    expect(await screen.findByText("完了")).toBeInTheDocument();
  });

  it("marks the file as warn and toasts an error when upload fails", async () => {
    vi.mocked(listProjects).mockResolvedValue([project]);
    vi.mocked(uploadDocument).mockRejectedValue(new Error("500"));
    const { props, container } = renderView();
    await screen.findByText("プロジェクトA (PRJ-001)");

    const file = new File(["pdf-bytes"], "broken.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput(container), { target: { files: [file] } });

    await waitFor(() => {
      expect(props.onShowToast).toHaveBeenCalledWith(
        "broken.pdf のアップロードに失敗しました",
        "error",
      );
    });
    expect(await screen.findByText("警告")).toBeInTheDocument();
  });

  it("warns and does not navigate when 処理を実行 is clicked with no completed files", async () => {
    const { props } = renderView();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /処理を実行/ }));

    expect(props.onShowToast).toHaveBeenCalledWith(
      "アップロード完了のファイルがありません",
      "warn",
    );
    expect(props.onNavigate).not.toHaveBeenCalled();
  });

  it("toggles a processing option and updates the enabled count", async () => {
    renderView();
    const user = userEvent.setup();

    // 5 of 7 options enabled by default.
    expect(screen.getByText("5/7 有効")).toBeInTheDocument();

    await user.click(screen.getByRole("switch", { name: "OCR テキスト抽出" }));

    expect(screen.getByText("4/7 有効")).toBeInTheDocument();
  });
});
