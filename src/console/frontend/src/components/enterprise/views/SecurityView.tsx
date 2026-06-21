import { type FC, useState, useEffect } from "react";
import {
  getSecurityStats,
  getSecurityConfig,
  type SecurityStatsResponse,
  type SecurityConfigResponse,
} from "../../../api/stats";

interface ViewProps {
  onNavigate: (view: string) => void;
  onShowModal: (content: { title: string; body: string }) => void;
  onShowToast: (message: string, type?: "ok" | "warn" | "error") => void;
}

// Data provenance for each card / policy.
//  - "live"   : computed from real audit-log / DB data via the API
//  - "config" : the server's actual configuration (config.py / RBAC enum) — static, not real-time
//  - "demo"   : illustrative only; the backing feature is not yet implemented
type Provenance = "live" | "config" | "demo";

const PROVENANCE_LABEL: Record<Provenance, string> = {
  live: "実データ",
  config: "設定ベース",
  demo: "デモ",
};

const PROVENANCE_CLASS: Record<Provenance, string> = {
  live: "ep-pill-ok",
  config: "ep-pill-info",
  demo: "ep-pill-warn",
};

interface SecurityCard {
  id: string;
  title: string;
  icon: string;
  desc: string;
  statLabel: string;
  provenance: Provenance;
  // resolve the live/config value; return null to fall back to staticValue
  resolve: (
    stats: SecurityStatsResponse | null,
    config: SecurityConfigResponse | null,
  ) => string | null;
  staticValue: string;
  modalBody: (
    stats: SecurityStatsResponse | null,
    config: SecurityConfigResponse | null,
  ) => string;
}

const SECURITY_CARDS: SecurityCard[] = [
  {
    id: "sso",
    title: "認証 / SSO",
    icon: "🔑",
    desc: "Entra ID OIDC/SAML 2.0 + HENNGE ONE による多要素認証。MSAL トークン管理でゼロトラスト認証を実現。",
    statLabel: "アクティブセッション",
    provenance: "live",
    resolve: (stats) => (stats ? stats.active_sessions.toLocaleString() : null),
    staticValue: "—",
    modalBody: (stats, config) =>
      "認証・SSO 設定詳細\n\n" +
      "IdP: Microsoft Entra ID\n" +
      "プロトコル: OIDC / SAML 2.0\n" +
      "ゲートウェイ: HENNGE ONE\n" +
      `トークン有効期限: ${config ? `${config.access_token_expire_minutes}分（config.py 実値）` : "—"}\n` +
      `リフレッシュトークン: ${config ? `${config.refresh_token_expire_days}日（config.py 実値）` : "—"}\n` +
      `署名アルゴリズム: ${config ? config.jwt_algorithm : "—"}\n\n` +
      "── セキュリティイベント（監査ログ実データ）──\n" +
      `アクティブアカウント数: ${stats ? stats.active_sessions.toLocaleString() : "—"}\n` +
      `ログイン成功（累計）: ${stats ? stats.login_success_total.toLocaleString() : "—"}\n` +
      `ログイン失敗（累計）: ${stats ? stats.login_failed_total.toLocaleString() : "—"}\n` +
      `ログイン失敗（直近30日）: ${stats ? stats.login_failed_30d.toLocaleString() : "—"}`,
  },
  {
    id: "loginfail",
    title: "認証失敗監視",
    icon: "🚫",
    desc: "監査ログに記録された認証失敗イベント（m365_login_failed / user_not_found）を集計。異常な失敗増加の検知に利用。",
    statLabel: "ログイン失敗（直近30日）",
    provenance: "live",
    resolve: (stats) =>
      stats ? stats.login_failed_30d.toLocaleString() : null,
    staticValue: "—",
    modalBody: (stats) =>
      "認証失敗監視（監査ログ実データ）\n\n" +
      "集計対象アクション:\n" +
      "- m365_login_failed\n" +
      "- m365_user_not_found\n\n" +
      `ログイン失敗（累計）: ${stats ? stats.login_failed_total.toLocaleString() : "—"}\n` +
      `ログイン失敗（直近30日）: ${stats ? stats.login_failed_30d.toLocaleString() : "—"}\n` +
      `ログイン成功（累計）: ${stats ? stats.login_success_total.toLocaleString() : "—"}\n\n` +
      "全イベントは append-only 監査ログ（SHA-256 ハッシュチェーン）に追記専用で記録されます。",
  },
  {
    id: "provision",
    title: "アカウント権限変更",
    icon: "👤",
    desc: "SSO 経由のユーザー自動プロビジョニング（権限付与）イベントを監査ログから集計。",
    statLabel: "プロビジョニング数（累計）",
    provenance: "live",
    resolve: (stats) =>
      stats ? stats.provision_events_total.toLocaleString() : null,
    staticValue: "—",
    modalBody: (stats, config) =>
      "アカウント権限変更（監査ログ実データ）\n\n" +
      "集計対象アクション:\n" +
      "- m365_user_provisioned\n\n" +
      `プロビジョニング（累計）: ${stats ? stats.provision_events_total.toLocaleString() : "—"}\n\n` +
      "── RBAC ロール（実定義・設定ベース）──\n" +
      (config ? config.rbac_roles.map((r) => `- ${r}`).join("\n") : "—"),
  },
  {
    id: "enc",
    title: "暗号化 / トークン",
    icon: "🔐",
    desc: "転送中（TLS）・保存時暗号化に加え、JWT 署名と有効期限をサーバ設定で管理。下記はサーバ稼働設定（config.py 実値）。",
    statLabel: "トークン有効期限（分）",
    provenance: "config",
    resolve: (_stats, config) =>
      config ? `${config.access_token_expire_minutes}` : null,
    staticValue: "—",
    modalBody: (_stats, config) =>
      "暗号化・トークン設定詳細（config.py 実値）\n\n" +
      `アクセストークン有効期限: ${config ? `${config.access_token_expire_minutes}分` : "—"}\n` +
      `リフレッシュトークン有効期限: ${config ? `${config.refresh_token_expire_days}日` : "—"}\n` +
      `JWT 署名アルゴリズム: ${config ? config.jwt_algorithm : "—"}\n` +
      `最大ファイルサイズ: ${config ? `${config.max_file_size_mb} MB` : "—"}\n\n` +
      "注: 転送暗号化(TLS)・保存暗号化(AES) は運用インフラ層の設定であり、本コンソールからは取得していません。",
  },
  {
    id: "auditlog",
    title: "監査ログ",
    icon: "📋",
    desc: "ハッシュチェーン改ざん防止付き監査ログ。全操作を追記専用で記録。総イベント数は監査ログDBの実データ。",
    statLabel: "総イベント数",
    provenance: "live",
    resolve: (stats) => (stats ? stats.total_events.toLocaleString() : null),
    staticValue: "—",
    modalBody: (stats, config) =>
      "監査ログ設定詳細\n\n" +
      "記録方式: 追記専用（DELETE不可）\n" +
      `改ざん防止: ${config ? config.audit_hash_algorithm : "SHA-256"} ハッシュチェーン` +
      `${config ? `（有効: ${config.audit_chain_enabled ? "ON" : "OFF"}）` : ""}\n\n` +
      "── 実データ ──\n" +
      `総イベント数: ${stats ? stats.total_events.toLocaleString() : "—"}\n` +
      `ログイン成功: ${stats ? stats.login_success_total.toLocaleString() : "—"}\n` +
      `ログイン失敗: ${stats ? stats.login_failed_total.toLocaleString() : "—"}\n\n` +
      "整合性検証エンドポイント: GET /api/v1/audit-logs/verify",
  },
  {
    id: "dlp",
    title: "DLP（デモ）",
    icon: "🛡️",
    desc: "機密文書の外部漏洩防止。※本機能は未実装のため、表示はデモ用の参考値です（リアルタイム集計ではありません）。",
    statLabel: "ブロック数（デモ）",
    provenance: "demo",
    resolve: () => null,
    staticValue: "デモ",
    modalBody: () =>
      "DLP（データ漏洩防止）— デモ表示\n\n" +
      "⚠️ 本機能はバックエンド未実装です。以下は将来像を示す参考情報であり、\n" +
      "実際の集計値・リアルタイムイベントではありません。\n\n" +
      "想定ブロック条件:\n" +
      "- 外部メール添付（機密PDF）\n" +
      "- USB書き込み（未承認端末）\n" +
      "- クラウドストレージ直接アップロード",
  },
  {
    id: "ip",
    title: "IP制限（デモ）",
    icon: "🌐",
    desc: "FortiGate連携によるIP許可リスト管理。※本機能は未実装のため、表示はデモ用の参考値です。",
    statLabel: "許可IPレンジ数（デモ）",
    provenance: "demo",
    resolve: () => null,
    staticValue: "デモ",
    modalBody: () =>
      "IP制限設定 — デモ表示\n\n" +
      "⚠️ 本機能はバックエンド未実装です。以下は将来像を示す参考情報であり、\n" +
      "実際の許可レンジ・ブロック試行回数ではありません。\n\n" +
      "想定構成:\n" +
      "- 許可リスト方式（本社 / 支店 / 現場VPN）\n" +
      "- HENNGE ONE 経由のテレワーク許可",
  },
  {
    id: "watermark",
    title: "透かし（デモ）",
    icon: "💧",
    desc: "閲覧・印刷時の動的透かし。※本機能は未実装のため、表示はデモ用の参考値です。",
    statLabel: "透かし付きDL数（デモ）",
    provenance: "demo",
    resolve: () => null,
    staticValue: "デモ",
    modalBody: () =>
      "透かし設定 — デモ表示\n\n" +
      "⚠️ 本機能はバックエンド未実装です。以下は将来像を示す参考情報であり、\n" +
      "実際の付与件数ではありません。\n\n" +
      "想定内容:\n" +
      "- 可視透かし（氏名 / 日時 / 社外秘ラベル）\n" +
      "- 不可視透かし（ユーザーID / セッションID）",
  },
];

function cardValue(
  card: SecurityCard,
  stats: SecurityStatsResponse | null,
  config: SecurityConfigResponse | null,
  loading: boolean,
): string {
  if (loading && card.provenance !== "demo") return "…";
  const v = card.resolve(stats, config);
  return v ?? card.staticValue;
}

type PolicyFilter = "all" | "重大" | "推奨" | "デモ";

interface Policy {
  id: string;
  name: string;
  desc: (config: SecurityConfigResponse | null) => string;
  scope: string;
  severity: "重大" | "推奨";
  provenance: Provenance;
  modalBody: (config: SecurityConfigResponse | null) => string;
}

// Policies derived from real server config where a source exists; demo otherwise.
const POLICIES: Policy[] = [
  {
    id: "POL-SESSION",
    name: "セッション / トークン有効期限",
    desc: (config) =>
      config
        ? `アクセストークン ${config.access_token_expire_minutes}分・リフレッシュ ${config.refresh_token_expire_days}日（config.py 実値）`
        : "サーバ設定のトークン有効期限",
    scope: "認証基盤",
    severity: "重大",
    provenance: "config",
    modalBody: (config) =>
      "セッション / トークン有効期限ポリシー（config.py 実値）\n\n" +
      `アクセストークン有効期限: ${config ? `${config.access_token_expire_minutes}分` : "—"}\n` +
      `リフレッシュトークン有効期限: ${config ? `${config.refresh_token_expire_days}日` : "—"}\n` +
      `署名アルゴリズム: ${config ? config.jwt_algorithm : "—"}\n\n` +
      "対象: Webコンソール・API（Bearer Token）",
  },
  {
    id: "POL-RBAC",
    name: "RBAC ロール定義",
    desc: (config) =>
      config
        ? `定義済みロール: ${config.rbac_roles.join(" / ")}（実装の UserRole 由来）`
        : "ロールベースアクセス制御",
    scope: "全ユーザー",
    severity: "重大",
    provenance: "config",
    modalBody: (config) =>
      "RBAC ロール定義（実装 UserRole enum 由来）\n\n" +
      "定義済みロール:\n" +
      (config ? config.rbac_roles.map((r) => `- ${r}`).join("\n") : "—") +
      "\n\n各ロールに応じて API 操作・閲覧範囲を制御します（例: 監査ログ閲覧は admin のみ）。",
  },
  {
    id: "POL-AUDIT",
    name: "監査ログ改ざん防止",
    desc: (config) =>
      `${config ? config.audit_hash_algorithm : "SHA-256"} ハッシュチェーンによる追記専用ログ（実装済み）`,
    scope: "監査ログDB",
    severity: "重大",
    provenance: "config",
    modalBody: (config) =>
      "監査ログ改ざん防止ポリシー（実装済み）\n\n" +
      `方式: ${config ? config.audit_hash_algorithm : "SHA-256"} ハッシュチェーン\n` +
      `状態: ${config ? (config.audit_chain_enabled ? "有効" : "無効") : "—"}\n` +
      "記録方式: 追記専用（DELETE不可）\n\n" +
      "整合性検証: GET /api/v1/audit-logs/verify\n" +
      "準拠: NIS2 / ISO 19650-5 / J-SOX",
  },
  {
    id: "POL-MFA",
    name: "MFA必須ポリシー（デモ）",
    desc: () => "多要素認証の強制適用（IdP 側設定・本コンソール未集計）",
    scope: "全ユーザー",
    severity: "重大",
    provenance: "demo",
    modalBody: () =>
      "MFA必須ポリシー — デモ表示\n\n" +
      "⚠️ MFA は Entra ID / HENNGE ONE 側で制御され、本コンソールからは\n" +
      "強制状況を集計していません。以下は想定構成です。\n\n" +
      "想定: 全ユーザーに TOTP / Push を強制、新規は72時間猶予",
  },
  {
    id: "POL-DLP",
    name: "機密文書DLPブロック（デモ）",
    desc: () => "機密ラベル付きPDFの外部送信ブロック（未実装）",
    scope: "機密文書",
    severity: "重大",
    provenance: "demo",
    modalBody: () =>
      "機密文書DLPブロックポリシー — デモ表示\n\n" +
      "⚠️ DLP 機能はバックエンド未実装です。以下は想定構成であり、\n" +
      "実際のブロックイベントは集計していません。",
  },
];

export const SecurityView: FC<ViewProps> = ({ onShowModal }) => {
  const [filter, setFilter] = useState<PolicyFilter>("all");
  const [stats, setStats] = useState<SecurityStatsResponse | null>(null);
  const [config, setConfig] = useState<SecurityConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([getSecurityStats(), getSecurityConfig()])
      .then(([s, c]) => {
        if (s.status === "fulfilled") setStats(s.value);
        if (c.status === "fulfilled") setConfig(c.value);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredPolicies = POLICIES.filter((p) => {
    if (filter === "all") return true;
    if (filter === "デモ") return p.provenance === "demo";
    return p.severity === filter && p.provenance !== "demo";
  });

  return (
    <div>
      {/* Security card grid */}
      <div className="ep-sec-grid" style={{ marginBottom: "20px" }}>
        {SECURITY_CARDS.map((card) => (
          <div
            key={card.id}
            className="ep-panel ep-sec-card"
            onClick={() =>
              onShowModal({
                title: card.title,
                body: card.modalBody(stats, config),
              })
            }
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ")
                onShowModal({
                  title: card.title,
                  body: card.modalBody(stats, config),
                });
            }}
          >
            <div className="h">
              <h4>{card.title}</h4>
              <div className="ic">{card.icon}</div>
            </div>
            <p>{card.desc}</p>
            <div className="stat">
              <span>
                {card.statLabel}
                <span
                  className={`ep-pill ${PROVENANCE_CLASS[card.provenance]}`}
                  style={{ marginLeft: 6, fontSize: "0.7em" }}
                  data-testid={`provenance-${card.id}`}
                >
                  {PROVENANCE_LABEL[card.provenance]}
                </span>
              </span>
              <strong>{cardValue(card, stats, config, loading)}</strong>
            </div>
          </div>
        ))}
      </div>

      {/* Policy list */}
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>セキュリティポリシー一覧</h3>
          <div style={{ display: "flex", gap: "4px" }}>
            {(["all", "重大", "推奨", "デモ"] as PolicyFilter[]).map((f) => (
              <button
                key={f}
                className={`ep-filter-pill${filter === f ? " active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "すべて" : f}
              </button>
            ))}
          </div>
        </div>
        <div className="ep-policy-list">
          {filteredPolicies.length === 0 ? (
            <div className="ep-policy" style={{ opacity: 0.6 }}>
              <div>
                <div className="nm">該当ポリシーなし</div>
              </div>
            </div>
          ) : (
            filteredPolicies.map((policy) => (
              <div
                key={policy.id}
                className="ep-policy"
                onClick={() =>
                  onShowModal({
                    title: policy.name,
                    body: policy.modalBody(config),
                  })
                }
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ")
                    onShowModal({
                      title: policy.name,
                      body: policy.modalBody(config),
                    });
                }}
              >
                <div>
                  <div className="nm">{policy.name}</div>
                  <div className="ds">{policy.desc(config)}</div>
                </div>
                <span className="scope">{policy.scope}</span>
                <span
                  className={`ep-pill ${PROVENANCE_CLASS[policy.provenance]}`}
                >
                  <span className="dot" />
                  {PROVENANCE_LABEL[policy.provenance]}
                </span>
                <span
                  className={`ep-pill ${
                    policy.severity === "重大" ? "ep-pill-ng" : "ep-pill-info"
                  }`}
                >
                  <span className="dot" />
                  {policy.severity}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
