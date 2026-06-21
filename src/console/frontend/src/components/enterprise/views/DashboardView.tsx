import { useState, useCallback, useMemo, useEffect } from "react";
import {
  getStats,
  getProjectStats,
  getDailyStats,
  type StatsResponse,
  type ProjectStatItem,
  type DailyStatPoint,
} from "../../../api/stats";
import { listDocuments, type DocumentResponse } from "../../../api/documents";
import { listAuditLogs, type AuditLogItem } from "../../../api/auditLogs";
import {
  listUsers,
  type UserResponse,
  type UserRole,
} from "../../../api/users";

interface ViewProps {
  onNavigate: (view: string) => void;
  onShowModal: (content: { title: string; body: string }) => void;
  onShowToast: (message: string, type?: "ok" | "warn" | "error") => void;
}

interface DashboardViewProps extends ViewProps {
  subView: "overview" | "stats" | "dist" | "users";
  period: number;
  filter: string;
}

// ─── Real-data label maps ──────────────────────────────────────────────────────

const DOC_TYPE_LABELS: Record<string, string> = {
  drawing: "図面",
  photo: "写真台帳",
  inspection: "検査記録",
  safety: "安全書類",
  contract: "契約書",
  report: "報告書",
  correction: "是正指示書",
  other: "その他",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "下書き",
  pending_review: "レビュー待ち",
  approved: "承認済",
  rejected: "却下",
  archived: "アーカイブ",
};

function statusPillClass(status: string): string {
  switch (status) {
    case "approved":
      return "ep-pill ep-pill-ok";
    case "rejected":
      return "ep-pill ep-pill-ng";
    case "pending_review":
      return "ep-pill ep-pill-info-2";
    case "draft":
      return "ep-pill ep-pill-warn";
    default:
      return "ep-pill ep-pill-muted";
  }
}

function docTypeLabel(t: string): string {
  return DOC_TYPE_LABELS[t] ?? t;
}

function statusLabel(s: string): string {
  return STATUS_LABELS[s] ?? s;
}

// ─── Relative time formatting (real timestamps) ────────────────────────────────

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diffSec = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (diffSec < 60) return `${diffSec}秒前`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}分前`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}時間前`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay}日前`;
}

// ─── Audit-log action → human label / icon ─────────────────────────────────────

type ActivityKind = "ok" | "ng" | "run" | "warn" | "user" | "app";

interface AuditActionMeta {
  kind: ActivityKind;
  line: string;
}

function auditActionMeta(action: string): AuditActionMeta {
  const a = action.toLowerCase();
  if (a.includes("login_success") || a.includes("login")) {
    return { kind: "user", line: "がログイン" };
  }
  if (a.includes("login_failed")) {
    return { kind: "warn", line: "のログインに失敗" };
  }
  if (a.includes("provisioned") || a.includes("user_created")) {
    return { kind: "user", line: "が登録されました" };
  }
  if (a.includes("approve")) {
    return { kind: "ok", line: "が承認されました" };
  }
  if (a.includes("reject")) {
    return { kind: "ng", line: "が却下されました" };
  }
  if (a.includes("deletion") || a.includes("delete")) {
    return { kind: "warn", line: "の削除が処理されました" };
  }
  if (a.includes("export")) {
    return { kind: "run", line: "がエクスポートされました" };
  }
  if (a.includes("upload") || a.includes("create")) {
    return { kind: "run", line: "が作成されました" };
  }
  if (a.includes("consent")) {
    return { kind: "ok", line: "の同意が記録されました" };
  }
  return { kind: "app", line: `: ${action}` };
}

interface ActivityItem {
  id: string;
  type: ActivityKind;
  line: string;
  highlight: string;
  time: string;
}

function auditLogToActivity(log: AuditLogItem): ActivityItem {
  const meta = auditActionMeta(log.action);
  const actor =
    log.user?.full_name || log.user?.username || log.user?.email || "システム";
  return {
    id: log.id,
    type: meta.kind,
    line: meta.line,
    highlight: actor,
    time: relativeTime(log.created_at),
  };
}

// ─── Static role data ──────────────────────────────────────────────────────────

type RoleKey = "all" | UserRole;

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "管理者",
  manager: "マネージャー",
  engineer: "エンジニア",
  viewer: "閲覧者",
};

function formatLastLogin(lastLogin: string | null): string {
  if (!lastLogin) return "未ログイン";
  return lastLogin.replace("T", " ").slice(0, 16);
}

const ROLE_FILTER_OPTIONS: { key: RoleKey; label: string }[] = [
  { key: "all", label: "すべて" },
  { key: "admin", label: "管理者" },
  { key: "manager", label: "マネージャー" },
  { key: "engineer", label: "エンジニア" },
  { key: "viewer", label: "閲覧者" },
];

// ─── Overview sub-view (real data) ─────────────────────────────────────────────

const TYPE_COLORS = [
  "var(--accent)",
  "var(--info)",
  "var(--success)",
  "var(--warn)",
  "var(--danger)",
];

function OverviewSubView({
  period,
  filter,
  onNavigate,
  onShowModal,
}: ViewProps & { period: number; filter: string }) {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [daily, setDaily] = useState<DailyStatPoint[]>([]);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  // null = still loading for the current period; number = period whose data is ready.
  const [loadedPeriod, setLoadedPeriod] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      getStats(),
      getDailyStats(period),
      listDocuments({ per_page: 20 }),
      listAuditLogs({ per_page: 8 }),
    ]).then((results) => {
      if (cancelled) return;
      const [statsR, dailyR, docsR, auditR] = results;
      if (statsR.status === "fulfilled") setStats(statsR.value);
      if (dailyR.status === "fulfilled") setDaily(dailyR.value.series);
      if (docsR.status === "fulfilled") setDocuments(docsR.value);
      if (auditR.status === "fulfilled")
        setActivity(auditR.value.items.map(auditLogToActivity));
      // Only treat as hard error when the primary KPI source failed.
      setError(statsR.status === "rejected");
      setLoadedPeriod(period);
    });
    return () => {
      cancelled = true;
    };
  }, [period]);

  const loading = loadedPeriod !== period;

  // ── KPI cards from real getStats() ──
  const ngCount = stats?.by_status?.rejected ?? 0;
  const pending = stats?.pending_approvals ?? 0;

  // ── Recent documents (replaces fabricated "jobs") ──
  const visibleDocs = useMemo(() => {
    let rows = documents;
    if (filter === "ok")
      rows = rows.filter(
        (d) => d.status === "approved" || d.status === "pending_review",
      );
    if (filter === "ng") rows = rows.filter((d) => d.status === "rejected");
    return rows.slice(0, 8);
  }, [documents, filter]);

  // ── Activity from real audit logs ──
  const visibleActivity = useMemo(() => {
    if (filter === "ok")
      return activity.filter((a) => a.type === "ok" || a.type === "run");
    if (filter === "ng")
      return activity.filter((a) => a.type === "ng" || a.type === "warn");
    return activity;
  }, [activity, filter]);

  // ── Daily trend bars from real upload counts ──
  const bars = useMemo(() => daily.map((d) => d.count), [daily]);
  const maxBar = useMemo(() => Math.max(1, ...bars), [bars]);
  const highlightFrom = Math.max(0, bars.length - 5);

  const handleActivityClick = useCallback(
    (item: ActivityItem) => {
      onShowModal({
        title: item.highlight,
        body: `アクション: ${item.line}\n時刻: ${item.time}`,
      });
    },
    [onShowModal],
  );

  const handleDocClick = useCallback(
    (doc: DocumentResponse) => {
      onShowModal({
        title: doc.title,
        body: `種別: ${docTypeLabel(doc.document_type)}\nページ数: ${doc.page_count ?? "—"}\n状態: ${statusLabel(doc.status)}\n登録日: ${new Date(doc.created_at).toLocaleString("ja-JP")}`,
      });
    },
    [onShowModal],
  );

  if (loading) {
    return (
      <div
        style={{
          padding: "40px",
          textAlign: "center",
          color: "var(--muted)",
          fontSize: "13px",
        }}
      >
        読み込み中...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: "40px",
          textAlign: "center",
          color: "var(--danger)",
          fontSize: "13px",
        }}
      >
        統計データの取得に失敗しました
      </div>
    );
  }

  return (
    <div>
      <div className="ep-stat-grid">
        <div className="ep-stat">
          <div className="lbl">総ドキュメント数</div>
          <div className="val">
            {(stats?.total_documents ?? 0).toLocaleString()}
          </div>
          <div className="delta up">
            今週 +{stats?.uploaded_this_week ?? 0}件
          </div>
        </div>
        <div className="ep-stat">
          <div className="lbl">却下件数</div>
          <div
            className="val"
            style={{
              color: ngCount === 0 ? "var(--success)" : "var(--danger)",
            }}
          >
            {ngCount.toLocaleString()}
          </div>
          <div className={`delta ${ngCount === 0 ? "up" : "down"}`}>
            {ngCount === 0 ? "— 0件" : "却下ステータス"}
          </div>
        </div>
        <div className="ep-stat">
          <div className="lbl">承認済（今月）</div>
          <div className="val" style={{ color: "var(--success)" }}>
            {(stats?.approved_this_month ?? 0).toLocaleString()}
          </div>
          <div className="delta up">↑ 今月実績</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">承認待ち</div>
          <div
            className="val"
            style={{
              color: pending > 0 ? "var(--warn-fg)" : "var(--success)",
            }}
          >
            {pending.toLocaleString()}
          </div>
          <div className="delta">件 処理中</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">稼働ユーザー</div>
          <div className="val">
            {(stats?.active_users ?? 0).toLocaleString()}
          </div>
          <div className="delta">アクティブ</div>
        </div>
      </div>

      <div className="ep-dash-grid">
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div className="ep-panel">
            <div className="ep-panel-head">
              <h3>アップロード件数推移</h3>
              <span className="meta">過去 {period} 日</span>
            </div>
            <div className="ep-panel-body" style={{ height: "180px" }}>
              {bars.length === 0 ? (
                <p
                  style={{
                    color: "var(--muted)",
                    fontSize: "12px",
                    textAlign: "center",
                    paddingTop: "60px",
                  }}
                >
                  該当期間のアップロードデータはありません
                </p>
              ) : (
                <svg
                  width="100%"
                  height="160"
                  aria-label={`アップロード件数推移 ${period}日グラフ`}
                >
                  {bars.map((v, i) => {
                    const totalBars = bars.length;
                    const barWidth = Math.max(
                      4,
                      Math.floor(420 / totalBars) - 2,
                    );
                    const gap = Math.max(
                      1,
                      Math.floor(420 / totalBars) - barWidth,
                    );
                    const x = i * (barWidth + gap) + 2;
                    const barH = Math.round((v / maxBar) * 140);
                    const y = 148 - barH;
                    const isRecent = i >= highlightFrom;
                    return (
                      <rect
                        key={daily[i]?.date ?? i}
                        x={x}
                        y={y}
                        width={barWidth}
                        height={barH}
                        rx={1}
                        fill={isRecent ? "var(--accent)" : "var(--border)"}
                        opacity={isRecent ? 0.85 : 0.55}
                      >
                        <title>{`${daily[i]?.date ?? ""}: ${v}件`}</title>
                      </rect>
                    );
                  })}
                  <line
                    x1="0"
                    y1="148"
                    x2="100%"
                    y2="148"
                    stroke="var(--border)"
                    strokeWidth="1"
                  />
                </svg>
              )}
            </div>
          </div>

          <div className="ep-panel" style={{ overflow: "hidden" }}>
            <div className="ep-panel-head">
              <h3>最近のドキュメント</h3>
              <button
                className="ep-btn ep-btn-secondary ep-btn-sm"
                type="button"
                onClick={() => onNavigate("documents")}
              >
                すべて表示
              </button>
            </div>
            {visibleDocs.length === 0 ? (
              <p
                style={{
                  padding: "16px",
                  color: "var(--muted)",
                  fontSize: "12px",
                  textAlign: "center",
                }}
              >
                {filter === "ok"
                  ? "承認済 / レビュー中のドキュメントはありません"
                  : filter === "ng"
                    ? "却下されたドキュメントはありません"
                    : "ドキュメントがありません"}
              </p>
            ) : (
              <table className="ep-tbl">
                <thead>
                  <tr>
                    <th>ドキュメント</th>
                    <th>種別</th>
                    <th className="num">ページ</th>
                    <th>状態</th>
                    <th>登録日時</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleDocs.map((doc) => (
                    <tr
                      key={doc.id}
                      style={{ cursor: "pointer" }}
                      onClick={() => handleDocClick(doc)}
                    >
                      <td style={{ fontWeight: 500 }}>{doc.title}</td>
                      <td className="id">{docTypeLabel(doc.document_type)}</td>
                      <td className="num">{doc.page_count ?? "—"}</td>
                      <td>
                        <span className={statusPillClass(doc.status)}>
                          {statusLabel(doc.status)}
                        </span>
                      </td>
                      <td
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          color: "var(--muted)",
                        }}
                      >
                        {relativeTime(doc.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="ep-panel" style={{ overflow: "hidden" }}>
          <div className="ep-panel-head">
            <h3>最近のアクティビティ</h3>
            <span className="meta">監査ログ</span>
          </div>
          {visibleActivity.length === 0 ? (
            <p
              style={{
                padding: "16px",
                color: "var(--muted)",
                fontSize: "12px",
                textAlign: "center",
              }}
            >
              該当するアクティビティはありません
            </p>
          ) : (
            <div className="ep-activity-list">
              {visibleActivity.map((item) => (
                <div
                  key={item.id}
                  className="ep-act-item"
                  style={{ cursor: "pointer" }}
                  onClick={() => handleActivityClick(item)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleActivityClick(item);
                  }}
                >
                  <div className={`ep-act-ic ${item.type}`} aria-hidden="true">
                    {item.type === "ok"
                      ? "✓"
                      : item.type === "ng"
                        ? "✕"
                        : item.type === "run"
                          ? "▶"
                          : item.type === "warn"
                            ? "!"
                            : item.type === "user"
                              ? "U"
                              : "A"}
                  </div>
                  <div>
                    <div className="ep-act-line">
                      <strong>{item.highlight}</strong>
                      {item.line}
                    </div>
                    <div className="ep-act-time">{item.time}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Stats sub-view (real data) ────────────────────────────────────────────────

function StatsSubView({ period, filter }: { period: number; filter: string }) {
  const [projectFilter, setProjectFilter] = useState<string>("all");
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [projectStats, setProjectStats] = useState<ProjectStatItem[]>([]);
  // null = still loading for the current period; number = period whose data is ready.
  const [loadedPeriod, setLoadedPeriod] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([getStats(), getProjectStats(period)]).then(
      (results) => {
        if (cancelled) return;
        const [statsR, projR] = results;
        if (statsR.status === "fulfilled") setStats(statsR.value);
        if (projR.status === "fulfilled") setProjectStats(projR.value.items);
        setError(statsR.status === "rejected" && projR.status === "rejected");
        setLoadedPeriod(period);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [period]);

  const loading = loadedPeriod !== period;

  // ── Processing-type stats from real by_type breakdown ──
  const typeStats = useMemo(() => {
    const entries = Object.entries(stats?.by_type ?? {});
    const max = Math.max(1, ...entries.map(([, c]) => c));
    return entries
      .sort((a, b) => b[1] - a[1])
      .map(([type, count], i) => ({
        type: docTypeLabel(type),
        count,
        max,
        color: TYPE_COLORS[i % TYPE_COLORS.length],
      }));
  }, [stats]);

  // ── Status breakdown from real by_status (replaces fabricated NG Top5) ──
  const statusList = useMemo(() => {
    const entries = Object.entries(stats?.by_status ?? {});
    const total = entries.reduce((a, [, c]) => a + c, 0);
    let rows = entries.sort((a, b) => b[1] - a[1]);
    if (filter === "ng") rows = rows.filter(([s]) => s === "rejected");
    if (filter === "ok")
      rows = rows.filter(
        (r) => r[0] === "approved" || r[0] === "pending_review",
      );
    return rows.map(([status, count], i) => ({
      rank: i + 1,
      status,
      category: statusLabel(status),
      count,
      rate: total > 0 ? ((count / total) * 100).toFixed(1) + "%" : "0.0%",
    }));
  }, [stats, filter]);

  // ── Per-project stats from real /stats/projects ──
  const projRows = useMemo(() => {
    const effective = projectFilter === "all" ? filter : projectFilter;
    let rows = projectStats;
    if (effective === "ok")
      rows = rows.filter((p) => p.ng === 0 && p.total > 0);
    if (effective === "ng") rows = rows.filter((p) => p.ng > 0);
    return rows;
  }, [projectStats, filter, projectFilter]);

  if (loading) {
    return (
      <div
        style={{
          padding: "40px",
          textAlign: "center",
          color: "var(--muted)",
          fontSize: "13px",
        }}
      >
        読み込み中...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: "40px",
          textAlign: "center",
          color: "var(--danger)",
          fontSize: "13px",
        }}
      >
        統計データの取得に失敗しました
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>種別別ドキュメント統計</h3>
          <span className="meta">全期間</span>
        </div>
        <div
          className="ep-panel-body"
          style={{ display: "flex", flexDirection: "column", gap: "14px" }}
        >
          {typeStats.length === 0 ? (
            <p
              style={{
                color: "var(--muted)",
                fontSize: "12px",
                textAlign: "center",
              }}
            >
              ドキュメントがありません
            </p>
          ) : (
            typeStats.map((stat) => (
              <div key={stat.type}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "5px",
                    fontSize: "12.5px",
                  }}
                >
                  <span style={{ color: "var(--fg-2)" }}>{stat.type}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--fg)",
                    }}
                  >
                    {stat.count.toLocaleString()}
                  </span>
                </div>
                <div className="ep-progress done" style={{ height: "6px" }}>
                  <div
                    style={{
                      width: `${(stat.count / stat.max) * 100}%`,
                      background: stat.color,
                    }}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}
      >
        <div className="ep-panel" style={{ overflow: "hidden" }}>
          <div className="ep-panel-head">
            <h3>ステータス別内訳</h3>
            <span className="meta">全期間</span>
          </div>
          {statusList.length === 0 ? (
            <p
              style={{
                padding: "16px",
                color: "var(--success)",
                fontSize: "12px",
                textAlign: "center",
              }}
            >
              該当ステータスなし
            </p>
          ) : (
            <table className="ep-tbl">
              <thead>
                <tr>
                  <th>#</th>
                  <th>ステータス</th>
                  <th className="num">件数</th>
                  <th className="num">比率</th>
                </tr>
              </thead>
              <tbody>
                {statusList.map((item) => (
                  <tr key={item.status}>
                    <td
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--muted)",
                        fontSize: "11px",
                      }}
                    >
                      {item.rank}
                    </td>
                    <td style={{ fontSize: "12px" }}>
                      <span className={statusPillClass(item.status)}>
                        {item.category}
                      </span>
                    </td>
                    <td
                      className={`num${item.status === "rejected" ? " ng-count" : ""}`}
                    >
                      {item.count}
                    </td>
                    <td
                      className="num"
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "var(--muted)",
                      }}
                    >
                      {item.rate}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="ep-panel" style={{ overflow: "hidden" }}>
          <div className="ep-panel-head">
            <h3>工事別処理件数</h3>
            <div style={{ display: "flex", gap: "4px" }}>
              {(["all", "ok", "ng"] as const).map((f) => (
                <button
                  key={f}
                  className={`ep-filter-pill${projectFilter === f ? " active" : ""}`}
                  type="button"
                  onClick={() => setProjectFilter(f)}
                >
                  {f === "all" ? "すべて" : f === "ok" ? "正常" : "NG"}
                </button>
              ))}
            </div>
          </div>
          {projRows.length === 0 ? (
            <p
              style={{
                padding: "16px",
                color: "var(--muted)",
                fontSize: "12px",
                textAlign: "center",
              }}
            >
              該当工事なし
            </p>
          ) : (
            <table className="ep-tbl">
              <thead>
                <tr>
                  <th>工事</th>
                  <th className="num">合計</th>
                  <th className="num">承認</th>
                  <th className="num">却下</th>
                  <th className="num">処理中</th>
                </tr>
              </thead>
              <tbody>
                {projRows.map((p) => (
                  <tr key={p.id}>
                    <td style={{ fontSize: "11.5px" }}>{p.name}</td>
                    <td className="num">{p.total}</td>
                    <td
                      className="num"
                      style={{
                        color: "var(--success)",
                        fontFamily: "var(--font-mono)",
                        fontSize: "12px",
                      }}
                    >
                      {p.ok}
                    </td>
                    <td className={`ng-count${p.ng === 0 ? " zero" : ""} num`}>
                      {p.ng}
                    </td>
                    <td
                      className="num"
                      style={{
                        color: "var(--warn-fg)",
                        fontFamily: "var(--font-mono)",
                        fontSize: "12px",
                      }}
                    >
                      {p.warn}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Distribution sub-view ─────────────────────────────────────────────────────
// App distribution metrics (version adoption / site rollout) are not yet exposed
// by a real backend endpoint. Rather than fabricate data we honestly surface a
// "not provided" state and point the user at the related view.

function DistSubView({ onNavigate }: { onNavigate: (view: string) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>アプリ配信状況</h3>
          <span className="meta">配信メトリクス</span>
        </div>
        <div
          className="ep-panel-body"
          style={{
            padding: "32px 16px",
            textAlign: "center",
            color: "var(--muted)",
            fontSize: "13px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            alignItems: "center",
          }}
        >
          <p>
            バージョン分布・拠点別導入状況・更新イベントの集計データは 現在 API
            で提供されていません。
          </p>
          <p style={{ fontSize: "12px" }}>
            利用可能なリリース情報は「アプリ配信」画面でご確認ください。
          </p>
          <button
            className="ep-btn ep-btn-secondary ep-btn-sm"
            type="button"
            onClick={() => onNavigate("apps")}
          >
            アプリ配信を開く
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Users sub-view (real data) ────────────────────────────────────────────────

function UsersSubView({
  filter,
  onShowModal,
}: Pick<ViewProps, "onShowModal"> & { filter: string }) {
  const [roleFilter, setRoleFilter] = useState<RoleKey>("all");
  const [liveUsers, setLiveUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listUsers()
      .then((users) => setLiveUsers(users))
      .catch(() => setLiveUsers([]))
      .finally(() => setLoading(false));
  }, []);

  const filteredUsers = useMemo(() => {
    let rows =
      roleFilter === "all"
        ? liveUsers
        : liveUsers.filter((u) => u.role === roleFilter);
    if (filter === "ok") rows = rows.filter((u) => u.status === "active");
    if (filter === "ng") rows = rows.filter((u) => u.status !== "active");
    return rows;
  }, [roleFilter, filter, liveUsers]);

  const activeCount =
    filter === "ng"
      ? liveUsers.filter((u) => u.status !== "active").length
      : filter === "ok"
        ? liveUsers.filter((u) => u.status === "active").length
        : liveUsers.length;

  // ── Login method distribution from real user records ──
  const loginCounts = useMemo(() => {
    const recent = liveUsers.filter((u) => u.last_login).length;
    const never = liveUsers.length - recent;
    return [
      {
        method: "ログイン実績あり",
        count: recent,
        total: Math.max(liveUsers.length, 1),
      },
      {
        method: "未ログイン",
        count: never,
        total: Math.max(liveUsers.length, 1),
      },
    ];
  }, [liveUsers]);

  const roleDist = (
    ["admin", "manager", "engineer", "viewer"] as UserRole[]
  ).map((role) => {
    const count = liveUsers.filter((u) => u.role === role).length;
    const max = Math.max(liveUsers.length, 1);
    const color =
      role === "admin"
        ? "var(--danger)"
        : role === "manager"
          ? "var(--accent)"
          : role === "engineer"
            ? "var(--success)"
            : "var(--muted)";
    return { role: ROLE_LABELS[role], count, max, color };
  });

  const handleUserClick = useCallback(
    (user: UserResponse) => {
      onShowModal({
        title: user.full_name,
        body: `メールアドレス: ${user.email}\nユーザー名: ${user.username}\nロール: ${ROLE_LABELS[user.role]}\n状態: ${user.status === "active" ? "有効" : user.status === "suspended" ? "停止中" : "無効"}\n最終ログイン: ${formatLastLogin(user.last_login)}`,
      });
    },
    [onShowModal],
  );

  if (loading) {
    return (
      <div
        style={{
          padding: "40px",
          textAlign: "center",
          color: "var(--muted)",
          fontSize: "13px",
        }}
      >
        読み込み中...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}
      >
        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>ロール分布</h3>
            <span className="meta">{activeCount} ユーザー</span>
          </div>
          <div
            className="ep-panel-body"
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            {roleDist.map((r) => (
              <div key={r.role}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "4px",
                    fontSize: "12.5px",
                  }}
                >
                  <span style={{ color: "var(--fg-2)" }}>{r.role}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--fg)",
                    }}
                  >
                    {r.count}
                  </span>
                </div>
                <div className="ep-progress done" style={{ height: "5px" }}>
                  <div
                    style={{
                      width: `${(r.count / r.max) * 100}%`,
                      background: r.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>ログイン状況</h3>
            <span className="meta">{activeCount} ユーザー</span>
          </div>
          <div
            className="ep-panel-body"
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            {loginCounts.map((a) => (
              <div key={a.method}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "4px",
                    fontSize: "12.5px",
                  }}
                >
                  <span style={{ color: "var(--fg-2)" }}>{a.method}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--fg)",
                    }}
                  >
                    {a.count}{" "}
                    <span style={{ color: "var(--muted)", fontSize: "10px" }}>
                      / {a.total}
                    </span>
                  </span>
                </div>
                <div className="ep-progress done" style={{ height: "5px" }}>
                  <div style={{ width: `${(a.count / a.total) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="ep-panel" style={{ overflow: "hidden" }}>
        <div className="ep-panel-head">
          <h3>ユーザー一覧</h3>
          <div style={{ display: "flex", gap: "4px" }}>
            {ROLE_FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                className={`ep-filter-pill${roleFilter === opt.key ? " active" : ""}`}
                type="button"
                onClick={() => setRoleFilter(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        {filteredUsers.length === 0 ? (
          <p
            style={{
              padding: "16px",
              color: "var(--muted)",
              fontSize: "12px",
              textAlign: "center",
            }}
          >
            {filter === "ng" ? "無効ユーザーはありません" : "該当ユーザーなし"}
          </p>
        ) : (
          <table className="ep-tbl">
            <thead>
              <tr>
                <th>ユーザー</th>
                <th>メールアドレス</th>
                <th>ロール</th>
                <th>ユーザー名</th>
                <th>状態</th>
                <th>最終ログイン</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr
                  key={user.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => handleUserClick(user)}
                >
                  <td>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <div
                        style={{
                          width: "26px",
                          height: "26px",
                          borderRadius: "50%",
                          background: "var(--fg)",
                          color: "var(--bg)",
                          display: "grid",
                          placeItems: "center",
                          fontSize: "10.5px",
                          fontWeight: 600,
                          flexShrink: 0,
                        }}
                      >
                        {user.full_name.charAt(0)}
                      </div>
                      <span style={{ fontWeight: 500 }}>{user.full_name}</span>
                    </div>
                  </td>
                  <td
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11.5px",
                      color: "var(--muted)",
                    }}
                  >
                    {user.email}
                  </td>
                  <td>
                    <span
                      className={
                        user.role === "admin"
                          ? "ep-pill ep-pill-ng"
                          : user.role === "manager"
                            ? "ep-pill ep-pill-info"
                            : user.role === "engineer"
                              ? "ep-pill ep-pill-ok"
                              : "ep-pill ep-pill-muted"
                      }
                    >
                      {ROLE_LABELS[user.role]}
                    </span>
                  </td>
                  <td style={{ fontSize: "12.5px", color: "var(--fg-2)" }}>
                    {user.username}
                  </td>
                  <td>
                    <span
                      className={
                        user.status === "active"
                          ? "ep-pill ep-pill-ok"
                          : user.status === "suspended"
                            ? "ep-pill ep-pill-ng"
                            : "ep-pill ep-pill-muted"
                      }
                    >
                      {user.status === "active"
                        ? "有効"
                        : user.status === "suspended"
                          ? "停止中"
                          : "無効"}
                    </span>
                  </td>
                  <td
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--muted)",
                    }}
                  >
                    {formatLastLogin(user.last_login)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Main export ───────────────────────────────────────────────────────────────

export function DashboardView({
  subView,
  period,
  filter,
  onNavigate,
  onShowModal,
  onShowToast,
}: DashboardViewProps) {
  const viewProps: ViewProps = { onNavigate, onShowModal, onShowToast };

  return (
    <div>
      {subView === "overview" && (
        <OverviewSubView {...viewProps} period={period} filter={filter} />
      )}
      {subView === "stats" && <StatsSubView period={period} filter={filter} />}
      {subView === "dist" && <DistSubView onNavigate={onNavigate} />}
      {subView === "users" && (
        <UsersSubView filter={filter} onShowModal={onShowModal} />
      )}

      <div
        style={{
          marginTop: "12px",
          fontSize: "11px",
          color: "var(--muted)",
          fontFamily: "var(--font-mono)",
          textAlign: "right",
        }}
      >
        表示期間: 過去 {period} 日間 · フィルター:{" "}
        {filter === "all" ? "すべて" : filter === "ok" ? "正常のみ" : "NGのみ"}
      </div>
    </div>
  );
}
