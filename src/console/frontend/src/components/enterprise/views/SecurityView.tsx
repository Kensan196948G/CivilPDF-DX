import { type FC, useState } from 'react'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

interface SecurityCard {
  id: string
  title: string
  icon: string
  desc: string
  stat: { label: string; value: string }
  modalBody: string
}

const SECURITY_CARDS: SecurityCard[] = [
  {
    id: 'sso',
    title: '認証 / SSO',
    icon: '🔑',
    desc: 'Entra ID OIDC/SAML 2.0 + HENNGE ONE による多要素認証。MSAL トークン管理でゼロトラスト認証を実現。',
    stat: { label: 'アクティブセッション', value: '248' },
    modalBody: `認証・SSO 設定詳細\n\nIdP: Microsoft Entra ID\nプロトコル: OIDC / SAML 2.0\nゲートウェイ: HENNGE ONE\nMFA: 必須（TOTP / Push通知）\nデバイス制御: Entra ID 条件付きアクセス\nトークン有効期限: 60分\nリフレッシュトークン: 90日\n\nアクティブセッション数: 248\n本日のログイン数: 1,284\n失敗ログイン数（今日）: 3`,
  },
  {
    id: 'dlp',
    title: 'DLP',
    icon: '🛡️',
    desc: '機密文書の外部漏洩を防止。ファイル種別・コンテンツ・宛先ポリシーで送信をブロック。',
    stat: { label: 'ブロック数（今月）', value: '12' },
    modalBody: `DLP（データ漏洩防止）設定詳細\n\nポリシー数: 8\n有効ポリシー: 8\n\nブロック条件:\n- 外部メール添付（機密PDF）\n- USB書き込み（未承認端末）\n- クラウドストレージ直接アップロード\n- スクリーンショット禁止（閲覧モード）\n\n今月のブロック数: 12\n重大インシデント: 0`,
  },
  {
    id: 'ip',
    title: 'IP制限',
    icon: '🌐',
    desc: 'FortiGate連携によるIP許可リスト管理。現場・支店・本社ごとに異なるアクセスポリシーを適用。',
    stat: { label: '許可IPレンジ数', value: '34' },
    modalBody: `IP制限設定詳細\n\n管理システム: FortiGate\nポリシーモード: 許可リスト方式\n\n許可ゾーン:\n- 本社 (203.0.113.0/24)\n- 大阪支店 (198.51.100.0/25)\n- 現場事務所 (動的 VPN)\n- テレワーク (HENNGE ONE 経由)\n\n許可IPレンジ数: 34\nブロック試行（今日）: 7`,
  },
  {
    id: 'enc',
    title: '暗号化',
    icon: '🔐',
    desc: '転送中（TLS 1.3）・保存時（AES-256）の二重暗号化。PDF自体にも暗号化オプションを提供。',
    stat: { label: '暗号化済みドキュメント', value: '1,241' },
    modalBody: `暗号化設定詳細\n\n転送暗号化: TLS 1.3（必須）\n保存暗号化: AES-256-GCM\nキー管理: Azure Key Vault\nPDF暗号化: 128bit RC4 / AES-256\n\n暗号化済みドキュメント: 1,241\n未暗号化ドキュメント: 43（レガシーファイル）\n証明書有効期限: 2026-03-15`,
  },
  {
    id: 'watermark',
    title: '透かし',
    icon: '💧',
    desc: '閲覧・印刷時に動的透かしを埋め込み。ユーザー名・日時・IPアドレスを不可視透かしとして記録。',
    stat: { label: '透かし付きDL数（今月）', value: '387' },
    modalBody: `透かし設定詳細\n\n透かし種別: 可視透かし + 不可視透かし\n\n可視透かし内容:\n- ユーザー氏名\n- アクセス日時\n- 「社外秘」ラベル（ポリシー対象）\n\n不可視透かし内容:\n- ユーザーID\n- セッションID\n- クライアントIP\n\n今月の透かし付きダウンロード数: 387\n流出検知時の追跡成功率: 100%`,
  },
  {
    id: 'auditlog',
    title: '監査',
    icon: '📋',
    desc: 'ハッシュチェーン改ざん防止付き監査ログ。全操作を追記専用で記録し、SIEM連携で外部分析も可能。',
    stat: { label: '総イベント数（今月）', value: '42,612' },
    modalBody: `監査ログ設定詳細\n\n記録方式: 追記専用（DELETE不可）\n改ざん防止: SHA-256 ハッシュチェーン\n保存期間: 7年（法的要件）\n\n記録イベント種別:\n- 認証（ログイン/ログアウト/失敗）\n- ドキュメント操作（閲覧/DL/印刷/編集）\n- 承認フロー（承認/否決/差戻し）\n- 管理操作（設定変更/ユーザー管理）\n\n今月の総イベント数: 42,612\nSIEM連携: Splunk（設定済み）`,
  },
]

type PolicyFilter = 'all' | '重大' | '推奨'

interface Policy {
  id: string
  name: string
  desc: string
  scope: string
  severity: '重大' | '推奨'
  status: 'active' | 'inactive'
  modalBody: string
}

const POLICIES: Policy[] = [
  {
    id: 'POL-001',
    name: 'MFA必須ポリシー',
    desc: '全ユーザーに多要素認証を強制適用',
    scope: '全ユーザー',
    severity: '重大',
    status: 'active',
    modalBody: 'MFA必須ポリシー\n\n対象: 全ユーザー（管理者・一般・協力会社）\nMFA方式: TOTP / Push通知 / SMS（補助）\n猶予期間: 新規ユーザーは72時間\n\n違反時の対応: アクセスブロック + 管理者通知',
  },
  {
    id: 'POL-002',
    name: '機密文書DLPブロック',
    desc: '機密ラベル付きPDFの外部送信をブロック',
    scope: '機密文書',
    severity: '重大',
    status: 'active',
    modalBody: '機密文書DLPブロックポリシー\n\n対象ラベル: 機密・極秘・社外秘\nブロック対象: 外部メール・USB・外部クラウド\n\n例外申請: 管理者承認フロー経由\n記録: 全ブロックイベントを監査ログに記録',
  },
  {
    id: 'POL-003',
    name: 'セッションタイムアウト',
    desc: '非アクティブ30分でセッション自動切断',
    scope: 'Webコンソール',
    severity: '推奨',
    status: 'active',
    modalBody: 'セッションタイムアウトポリシー\n\nタイムアウト時間: 30分（非アクティブ）\n強制ログアウト: 8時間経過後\nセッション延長: ユーザー操作で自動延長\n\n対象: Webコンソール・API（Bearer Token）',
  },
  {
    id: 'POL-004',
    name: 'IP制限（外部アクセス）',
    desc: '未登録IPからのアクセスをブロック',
    scope: 'APIエンドポイント',
    severity: '重大',
    status: 'active',
    modalBody: 'IP制限ポリシー\n\n許可モード: 許可リスト方式\n例外: HENNGE ONE VPN経由のテレワーク\n\nブロック時の対応:\n- 即時ブロック\n- 管理者Teamsアラート\n- 監査ログ記録',
  },
  {
    id: 'POL-005',
    name: 'PDF/A適合チェック',
    desc: '電子納品提出前のPDF/A-1b適合検証',
    scope: '電子納品フロー',
    severity: '推奨',
    status: 'active',
    modalBody: 'PDF/A適合チェックポリシー\n\n規格: PDF/A-1b（国交省電子納品要領準拠）\nチェックツール: veraPDF\n\nチェック項目:\n- フォント埋め込み\n- カラースペース\n- メタデータ\n- 暗号化なし\n\n不適合時: 自動変換または差戻し',
  },
  {
    id: 'POL-006',
    name: '透かし自動付与',
    desc: '機密文書ダウンロード時に透かしを付与',
    scope: '機密文書',
    severity: '推奨',
    status: 'active',
    modalBody: '透かし自動付与ポリシー\n\nトリガー: 機密・社外秘ラベル付き文書のダウンロード・印刷\n透かし内容: ユーザー名 / 日時 / IP / セッションID\n\n可視透かし: 右下にグレー文字で印字\n不可視透かし: ステガノグラフィー埋め込み',
  },
  {
    id: 'POL-007',
    name: '協力会社アカウント有効期限',
    desc: '外部協力会社アカウントに90日有効期限を設定',
    scope: '協力会社ユーザー',
    severity: '推奨',
    status: 'active',
    modalBody: '協力会社アカウント有効期限ポリシー\n\n有効期限: 90日（延長申請可）\n延長手続き: 監理技術者の承認が必要\n期限切れ: 自動無効化 + 通知（7日前・1日前）\n\nアクセス範囲: 担当現場のみ（他現場は不可視）',
  },
  {
    id: 'POL-008',
    name: '監査ログ改ざん防止',
    desc: 'ハッシュチェーンによる監査ログ整合性保護',
    scope: '監査ログDB',
    severity: '重大',
    status: 'active',
    modalBody: '監査ログ改ざん防止ポリシー\n\n方式: SHA-256 ハッシュチェーン\n検証: 1時間ごとに自動整合性チェック\n\n異常検知時の対応:\n- 管理者への即時アラート\n- 対象ログの隔離\n- インシデント対応フロー起動\n\n保存期間: 7年（法的保存要件）',
  },
]

export const SecurityView: FC<ViewProps> = ({ onShowModal }) => {
  const [filter, setFilter] = useState<PolicyFilter>('all')

  const filteredPolicies =
    filter === 'all' ? POLICIES : POLICIES.filter((p) => p.severity === filter)

  return (
    <div>
      {/* Security card grid */}
      <div className="ep-sec-grid" style={{ marginBottom: '20px' }}>
        {SECURITY_CARDS.map((card) => (
          <div
            key={card.id}
            className="ep-panel ep-sec-card"
            onClick={() =>
              onShowModal({ title: card.title, body: card.modalBody })
            }
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ')
                onShowModal({ title: card.title, body: card.modalBody })
            }}
          >
            <div className="h">
              <h4>{card.title}</h4>
              <div className="ic">{card.icon}</div>
            </div>
            <p>{card.desc}</p>
            <div className="stat">
              <span>{card.stat.label}</span>
              <strong>{card.stat.value}</strong>
            </div>
          </div>
        ))}
      </div>

      {/* Policy list */}
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>セキュリティポリシー一覧</h3>
          <div style={{ display: 'flex', gap: '4px' }}>
            {(['all', '重大', '推奨'] as PolicyFilter[]).map((f) => (
              <button
                key={f}
                className={`ep-filter-pill${filter === f ? ' active' : ''}`}
                onClick={() => setFilter(f)}
              >
                {f === 'all' ? 'すべて' : f}
              </button>
            ))}
          </div>
        </div>
        <div className="ep-policy-list">
          {filteredPolicies.map((policy) => (
            <div
              key={policy.id}
              className="ep-policy"
              onClick={() =>
                onShowModal({ title: policy.name, body: policy.modalBody })
              }
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ')
                  onShowModal({ title: policy.name, body: policy.modalBody })
              }}
            >
              <div>
                <div className="nm">{policy.name}</div>
                <div className="ds">{policy.desc}</div>
              </div>
              <span className="scope">{policy.scope}</span>
              <span
                className={`ep-pill ${
                  policy.severity === '重大' ? 'ep-pill-ng' : 'ep-pill-info'
                }`}
              >
                <span className="dot" />
                {policy.severity}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
