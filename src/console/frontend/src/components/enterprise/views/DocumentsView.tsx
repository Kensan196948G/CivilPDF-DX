import { useState, useCallback, useRef, useEffect } from "react";
import { listDocuments, type DocumentResponse } from "../../../api/documents";

interface ViewProps {
  onNavigate: (view: string) => void;
  onShowModal: (content: { title: string; body: string }) => void;
  onShowToast: (message: string, type?: "ok" | "warn" | "error") => void;
}

interface Document {
  id: string;
  title: string;
  type: "DWG" | "SPC" | "QTY" | "SAF" | "PHT";
  project: string;
  rev: string;
  status:
    | "回覧中"
    | "差戻し"
    | "承認済"
    | "提出済"
    | "完了"
    | "NGあり"
    | "レビュー中";
  signed: boolean;
  size: string;
  updated: string;
  retentionExpiresAt?: string; // ISO date; 電子帳簿保存法 7-year retention
}

// Mapping helpers: backend enum values → display values
function mapDocType(t: string): Document["type"] {
  switch (t) {
    case "drawing":
      return "DWG";
    case "photo":
    case "report":
      return "PHT";
    case "safety":
      return "SAF";
    default:
      return "SPC";
  }
}

function mapStatus(s: string): Document["status"] {
  switch (s) {
    case "draft":
      return "回覧中";
    case "pending_review":
      return "レビュー中";
    case "approved":
      return "承認済";
    case "rejected":
      return "差戻し";
    case "archived":
      return "完了";
    default:
      return "回覧中";
  }
}

function formatFileSize(bytes: number): string {
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
  if (bytes >= 1_048_576) return `${Math.round(bytes / 1_048_576)} MB`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${bytes} B`;
}

function apiToDoc(d: DocumentResponse): Document {
  return {
    id: d.id,
    title: d.title,
    type: mapDocType(d.document_type),
    project: d.project_id.slice(0, 8),
    rev: d.iso19650_number ? `Rev.${d.iso19650_number}` : "—",
    status: mapStatus(d.status),
    signed: d.is_pdfa,
    size: formatFileSize(d.file_size),
    updated: (d.updated_at ?? d.created_at).slice(0, 10),
    retentionExpiresAt: d.retention_expires_at?.slice(0, 10),
  };
}

// Filter definitions (counts are derived from live data in the component)
const FILTER_DEFS = [
  { key: "all", label: "すべて", types: [] as string[] },
  { key: "図面", label: "図面", types: ["DWG"] },
  { key: "仕様書", label: "仕様書", types: ["SPC"] },
  { key: "数量", label: "数量", types: ["QTY"] },
  { key: "安全", label: "安全", types: ["SAF"] },
  { key: "帳票", label: "帳票", types: ["PHT"] },
];

type FilterKey = (typeof FILTER_DEFS)[number]["key"];

function statusPillClass(status: Document["status"]): string {
  switch (status) {
    case "回覧中":
      return "ep-pill ep-pill-info-2";
    case "差戻し":
      return "ep-pill ep-pill-warn";
    case "承認済":
      return "ep-pill ep-pill-ok";
    case "提出済":
      return "ep-pill ep-pill-ok";
    case "完了":
      return "ep-pill ep-pill-muted";
    case "NGあり":
      return "ep-pill ep-pill-ng";
    case "レビュー中":
      return "ep-pill ep-pill-info";
    default:
      return "ep-pill ep-pill-muted";
  }
}

function typeIconClass(type: Document["type"]): string {
  switch (type) {
    case "DWG":
      return "dwg";
    case "SPC":
      return "spec";
    case "QTY":
      return "qty";
    case "SAF":
      return "safe";
    case "PHT":
      return "rep";
    default:
      return "";
  }
}

type RetentionStatus = "expired" | "warning" | "ok" | null;

function retentionStatus(expiresAt: string | undefined): RetentionStatus {
  if (!expiresAt) return null;
  const now = new Date();
  const expiry = new Date(expiresAt);
  const daysLeft = Math.floor((expiry.getTime() - now.getTime()) / 86_400_000);
  if (daysLeft < 0) return "expired";
  if (daysLeft <= 30) return "warning";
  return "ok";
}

function RetentionBadge({ expiresAt }: { expiresAt: string | undefined }) {
  const status = retentionStatus(expiresAt);
  if (!status || status === "ok") return null;
  const isExpired = status === "expired";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "2px",
        fontSize: "10px",
        fontWeight: 600,
        padding: "1px 5px",
        borderRadius: "3px",
        background: isExpired ? "var(--danger, #e53e3e)" : "#f6ad55",
        color: "#fff",
        marginLeft: "6px",
        verticalAlign: "middle",
      }}
      title={`保存期限: ${expiresAt}`}
    >
      ⚠️ {isExpired ? "期限切れ" : "期限間近"}
    </span>
  );
}

interface ContextMenu {
  visible: boolean;
  x: number;
  y: number;
  docId: string;
}

const CTX_ITEMS = [
  { label: "開く", key: "open", icon: "↗", shortcut: "⏎" },
  { label: "ダウンロード", key: "dl", icon: "↓", shortcut: "⌘D" },
  { label: "比較", key: "compare", icon: "⇄", shortcut: "" },
  { label: "WF送信", key: "wf", icon: "→", shortcut: "" },
  { label: "共有", key: "share", icon: "⤴", shortcut: "⌘S" },
  null,
  { label: "削除", key: "delete", icon: "✕", shortcut: "", danger: true },
];

export function DocumentsView({ onNavigate, onShowModal }: ViewProps) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");
  const [search, setSearch] = useState("");
  const [contextMenu, setContextMenu] = useState<ContextMenu>({
    visible: false,
    x: 0,
    y: 0,
    docId: "",
  });
  const ctxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listDocuments({ per_page: 200 })
      .then((data) => setDocs(data.map(apiToDoc)))
      .catch(() => {
        /* keep empty list on error */
      })
      .finally(() => setLoading(false));
  }, []);

  // Compute per-filter counts from live data
  const filters = FILTER_DEFS.map((f) => ({
    ...f,
    count:
      f.types.length === 0
        ? docs.length
        : docs.filter((d) => f.types.includes(d.type)).length,
  }));

  const filteredDocs = docs.filter((doc) => {
    const def = FILTER_DEFS.find((f) => f.key === activeFilter);
    const matchesType =
      !def || def.types.length === 0 || def.types.includes(doc.type);
    const q = search.toLowerCase();
    const matchesSearch =
      q === "" ||
      doc.title.toLowerCase().includes(q) ||
      doc.project.toLowerCase().includes(q);
    return matchesType && matchesSearch;
  });

  const handleRowClick = useCallback(
    (doc: Document) => {
      onShowModal({
        title: doc.title,
        body: `工事番号: ${doc.project}\n種別: ${doc.type}\nリビジョン: ${doc.rev}\n状態: ${doc.status}\nサイズ: ${doc.size}\n最終更新: ${doc.updated}`,
      });
    },
    [onShowModal],
  );

  const handleRightClick = useCallback((e: React.MouseEvent, docId: string) => {
    e.preventDefault();
    setContextMenu({ visible: true, x: e.clientX, y: e.clientY, docId });
  }, []);

  const closeCtx = useCallback(() => {
    setContextMenu((prev) => ({ ...prev, visible: false }));
  }, []);

  const handleCtxAction = useCallback(
    (key: string) => {
      closeCtx();
      if (key === "open") {
        onNavigate("viewer");
      } else if (key === "wf") {
        onNavigate("workflow");
      }
    },
    [closeCtx, onNavigate],
  );

  useEffect(() => {
    if (!contextMenu.visible) return;
    const handler = (e: MouseEvent) => {
      if (ctxRef.current && !ctxRef.current.contains(e.target as Node)) {
        closeCtx();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [contextMenu.visible, closeCtx]);

  return (
    <div>
      {/* Toolbar */}
      <div className="ep-doc-toolbar">
        <div className="ep-doc-filters">
          {filters.map((f) => (
            <button
              key={f.key}
              className={`ep-filter-pill${activeFilter === f.key ? " active" : ""}`}
              onClick={() => setActiveFilter(f.key)}
              type="button"
            >
              {f.label}
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  color: "var(--muted)",
                }}
              >
                {f.count.toLocaleString()}
              </span>
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <div className="ep-doc-search">
            <svg
              width="12"
              height="12"
              viewBox="0 0 16 16"
              fill="none"
              aria-hidden="true"
            >
              <circle
                cx="7"
                cy="7"
                r="5"
                stroke="currentColor"
                strokeWidth="1.5"
              />
              <path
                d="m11 11 3 3"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            <input
              type="text"
              placeholder="図書名・工事番号で検索…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="ドキュメント検索"
            />
          </div>
          <button
            className="ep-btn ep-btn-primary ep-btn-sm"
            type="button"
            onClick={() => onNavigate("upload")}
          >
            + 新規取込
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="ep-panel" style={{ overflow: "hidden" }}>
        <table className="ep-tbl">
          <thead>
            <tr>
              <th style={{ width: "32px" }}>
                <input type="checkbox" aria-label="全選択" />
              </th>
              <th>図書名</th>
              <th>工事</th>
              <th>Rev</th>
              <th>状態</th>
              <th>署名</th>
              <th className="num">サイズ</th>
              <th>更新</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td
                  colSpan={9}
                  style={{
                    textAlign: "center",
                    padding: "32px",
                    color: "var(--muted)",
                  }}
                >
                  読み込み中…
                </td>
              </tr>
            )}
            {!loading &&
              filteredDocs.map((doc) => (
                <tr
                  key={doc.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => handleRowClick(doc)}
                  onContextMenu={(e) => handleRightClick(e, doc.id)}
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" aria-label={`${doc.title}を選択`} />
                  </td>
                  <td>
                    <div className="ep-doc-name">
                      <div
                        className={`ep-doc-name ic ${typeIconClass(doc.type)}`}
                      >
                        {doc.type}
                      </div>
                      <div className="ep-doc-name ttl">
                        <strong>
                          {doc.title}
                          <RetentionBadge expiresAt={doc.retentionExpiresAt} />
                        </strong>
                        <small>{doc.id}</small>
                      </div>
                    </div>
                  </td>
                  <td className="id">{doc.project}</td>
                  <td>
                    {doc.rev !== "—" ? (
                      <span className="ep-rev-chip">{doc.rev}</span>
                    ) : (
                      <span style={{ color: "var(--muted)" }}>—</span>
                    )}
                  </td>
                  <td>
                    <span className={statusPillClass(doc.status)}>
                      <span className="dot" />
                      {doc.status}
                    </span>
                  </td>
                  <td>
                    {doc.signed ? (
                      <span className="ep-pill ep-pill-ok">済</span>
                    ) : (
                      <span style={{ color: "var(--muted)", fontSize: "12px" }}>
                        —
                      </span>
                    )}
                  </td>
                  <td
                    className="num"
                    style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}
                  >
                    {doc.size}
                  </td>
                  <td
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--muted)",
                    }}
                  >
                    {doc.updated}
                  </td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <button
                      className="ep-btn ep-btn-secondary ep-btn-sm"
                      type="button"
                      onClick={() => onNavigate("viewer")}
                    >
                      開く
                    </button>
                  </td>
                </tr>
              ))}
            {!loading && filteredDocs.length === 0 && (
              <tr>
                <td
                  colSpan={9}
                  style={{
                    textAlign: "center",
                    padding: "32px",
                    color: "var(--muted)",
                  }}
                >
                  該当するドキュメントがありません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Context Menu */}
      <div
        ref={ctxRef}
        className={`ep-ctx-menu${contextMenu.visible ? " open" : ""}`}
        style={{ left: contextMenu.x, top: contextMenu.y }}
        role="menu"
      >
        {CTX_ITEMS.map((item, idx) =>
          item === null ? (
            <div key={`sep-${idx}`} className="ep-ctx-sep" />
          ) : (
            <button
              key={item.key}
              className={`ep-ctx-item${item.danger ? " danger" : ""}`}
              type="button"
              role="menuitem"
              onClick={() => handleCtxAction(item.key)}
            >
              <span
                style={{ width: "14px", textAlign: "center", fontSize: "11px" }}
              >
                {item.icon}
              </span>
              {item.label}
              {item.shortcut && (
                <span className="ctx-key">{item.shortcut}</span>
              )}
            </button>
          ),
        )}
      </div>
    </div>
  );
}
