import { type FC } from 'react'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

interface ConnCard {
  id: string
  logoClass: string
  logoText: string
  title: string
  desc: string
  status: 'connected' | 'disconnected'
  rows: { k: string; v: string }[]
  modalBody: string
}

interface SyncRow {
  id: string
  site: string
  library: string
  mapping: string
  direction: '双方向' | '↓ 取込のみ' | '↑ 書出のみ'
  count: string
  lastSync: string
  status: 'active' | 'warn' | 'inactive'
  modalBody: string
}

const CONN_CARDS: ConnCard[] = [
  {
    id: 'sp',
    logoClass: 'ep-conn-logo sp',
    logoText: 'SP',
    title: 'SharePoint',
    desc: 'ドキュメントライブラリ同期・サイト連携',
    status: 'connected',
    rows: [
      { k: 'テナント', v: 'civilpdf.sharepoint.com' },
      { k: '同期サイト数', v: '7' },
      { k: '最終同期', v: '2分前' },
    ],
    modalBody:
      'SharePoint 接続設定\n\nテナント: civilpdf.sharepoint.com\nクライアントID: 9a1b2c3d-...\n認証方式: Entra ID App登録 (OAuth2)\n\n同期サイト数: 7\n同期ドキュメント数: 1,284\n最終同期: 2026-05-11 14:30:15\n\nステータス: 正常接続中',
  },
  {
    id: 'entra',
    logoClass: 'ep-conn-logo ent',
    logoText: 'EID',
    title: 'Entra ID',
    desc: 'OIDC/SAML 2.0 IdP・ユーザー同期',
    status: 'connected',
    rows: [
      { k: 'テナント', v: 'civilpdf.onmicrosoft.com' },
      { k: '同期ユーザー数', v: '248' },
      { k: 'MFA強制', v: '有効' },
    ],
    modalBody:
      'Entra ID 接続設定\n\nテナント: civilpdf.onmicrosoft.com\nプロトコル: OIDC / SAML 2.0\nライブラリ: MSAL\n\n同期ユーザー数: 248\n同期グループ数: 12\nMFA強制: 全ユーザー対象\n\nユーザー同期: リアルタイム (Graph API)',
  },
  {
    id: 'teams',
    logoClass: 'ep-conn-logo tm',
    logoText: 'TM',
    title: 'Teams',
    desc: '承認通知・コメント・ファイル共有連携',
    status: 'connected',
    rows: [
      { k: 'Bot', v: 'CivilPDF Bot' },
      { k: '通知チャンネル数', v: '14' },
      { k: '今月の通知数', v: '1,847' },
    ],
    modalBody:
      'Microsoft Teams 接続設定\n\nBot名: CivilPDF Bot\nBot ID: 4f5e6d7c-...\n\n機能:\n- 承認依頼通知\n- コメント通知\n- ファイル共有リンク生成\n\n通知チャンネル数: 14\n今月の送信通知数: 1,847',
  },
  {
    id: 'od',
    logoClass: 'ep-conn-logo od',
    logoText: 'OD',
    title: 'OneDrive',
    desc: '個人作業領域のファイル同期・バックアップ',
    status: 'connected',
    rows: [
      { k: '連携ユーザー', v: '211名' },
      { k: '同期容量', v: '842 GB / 2 TB' },
      { k: '最終バックアップ', v: '1時間前' },
    ],
    modalBody:
      'OneDrive 接続設定\n\n連携方式: Microsoft Graph API\n連携ユーザー数: 211名\n使用容量: 842 GB / 2 TB\n\n機能:\n- 個人作業ファイルの自動バックアップ\n- モバイル端末との同期\n- バージョン履歴（90日）',
  },
  {
    id: 'ex',
    logoClass: 'ep-conn-logo ex',
    logoText: 'EX',
    title: 'Exchange',
    desc: 'メール通知・承認メール・アラート配信',
    status: 'connected',
    rows: [
      { k: 'ドメイン', v: 'civilpdf.co.jp' },
      { k: '今月の送信数', v: '4,231' },
      { k: 'バウンス率', v: '0.02%' },
    ],
    modalBody:
      'Exchange Online 接続設定\n\nドメイン: civilpdf.co.jp\n送信方式: Microsoft Graph API (Mail.Send)\n差出人: noreply@civilpdf.co.jp\n\n今月の送信数: 4,231\nバウンス率: 0.02%\n開封率: 78.3%',
  },
  {
    id: 'fg',
    logoClass: 'ep-conn-logo fg',
    logoText: 'FG',
    title: 'FortiGate',
    desc: 'ゼロトラスト・IP制限・VPN連携',
    status: 'connected',
    rows: [
      { k: 'モデル', v: 'FortiGate 200F' },
      { k: '許可IPレンジ', v: '34件' },
      { k: 'ブロック（今日）', v: '7件' },
    ],
    modalBody:
      'FortiGate 接続設定\n\nモデル: FortiGate 200F\nファームウェア: v7.4.3\nAPI連携: REST API (read-only)\n\n許可IPレンジ数: 34\n今日のブロック試行: 7\n\n機能:\n- IP制限ポリシーの自動同期\n- VPN接続ユーザーの動的許可\n- 脅威インテリジェンス連携',
  },
]

const SYNC_ROWS: SyncRow[] = [
  {
    id: 'SYNC-001',
    site: '本社 SP サイト',
    library: '電子納品ライブラリ',
    mapping: '/docs/delivery/',
    direction: '双方向',
    count: '342',
    lastSync: '2分前',
    status: 'active',
    modalBody: '同期マッピング — 本社 SP サイト\n\nSharePointサイト: https://civilpdf.sharepoint.com/sites/honsha\nライブラリ: 電子納品ライブラリ\nマッピング先: /docs/delivery/\n方向: 双方向\n同期ファイル数: 342\n最終同期: 2026-05-11 14:30:15\nステータス: 正常',
  },
  {
    id: 'SYNC-002',
    site: '大阪支店 SP',
    library: '設計図面ライブラリ',
    mapping: '/docs/drawings/osaka/',
    direction: '双方向',
    count: '218',
    lastSync: '5分前',
    status: 'active',
    modalBody: '同期マッピング — 大阪支店 SP\n\nSharePointサイト: https://civilpdf.sharepoint.com/sites/osaka\nライブラリ: 設計図面ライブラリ\nマッピング先: /docs/drawings/osaka/\n方向: 双方向\n同期ファイル数: 218\n最終同期: 2026-05-11 14:27:43',
  },
  {
    id: 'SYNC-003',
    site: '第3工区現場',
    library: '施工記録',
    mapping: '/docs/site3/records/',
    direction: '↑ 書出のみ',
    count: '87',
    lastSync: '12分前',
    status: 'active',
    modalBody: '同期マッピング — 第3工区現場\n\nSharePointサイト: 現場モバイル端末から書出\nライブラリ: 施工記録\nマッピング先: /docs/site3/records/\n方向: 書出のみ（現場→SP）\n同期ファイル数: 87\n最終同期: 2026-05-11 14:20:08',
  },
  {
    id: 'SYNC-004',
    site: '協力会社A SP',
    library: '納品書類',
    mapping: '/docs/vendor/a/submit/',
    direction: '↓ 取込のみ',
    count: '43',
    lastSync: '1時間前',
    status: 'warn',
    modalBody: '同期マッピング — 協力会社A SP\n\nSharePointサイト: 協力会社A提供サイト\nライブラリ: 納品書類\nマッピング先: /docs/vendor/a/submit/\n方向: 取込のみ（SP→DX）\n同期ファイル数: 43\n最終同期: 2026-05-11 13:32:00\n警告: 認証トークンの有効期限が近づいています',
  },
  {
    id: 'SYNC-005',
    site: '国交省電子納品',
    library: '成果品ライブラリ',
    mapping: '/docs/delivery/final/',
    direction: '↑ 書出のみ',
    count: '156',
    lastSync: '3時間前',
    status: 'active',
    modalBody: '同期マッピング — 国交省電子納品\n\nマッピング先: /docs/delivery/final/\n方向: 書出のみ（PDF/A準拠チェック後）\n同期ファイル数: 156\n最終同期: 2026-05-11 11:15:22\nPDF/A適合率: 99.4%',
  },
  {
    id: 'SYNC-006',
    site: '名古屋支店 SP',
    library: '安全管理書類',
    mapping: '/docs/safety/nagoya/',
    direction: '双方向',
    count: '91',
    lastSync: '昨日',
    status: 'warn',
    modalBody: '同期マッピング — 名古屋支店 SP\n\nSharePointサイト: https://civilpdf.sharepoint.com/sites/nagoya\nライブラリ: 安全管理書類\nマッピング先: /docs/safety/nagoya/\n方向: 双方向\n同期ファイル数: 91\n最終同期: 2026-05-10 09:41:00\n警告: 24時間以上同期が止まっています',
  },
  {
    id: 'SYNC-007',
    site: '福岡支店 SP',
    library: '工事写真',
    mapping: '/docs/photos/fukuoka/',
    direction: '↑ 書出のみ',
    count: '0',
    lastSync: '未設定',
    status: 'inactive',
    modalBody: '同期マッピング — 福岡支店 SP\n\nSharePointサイト: 設定予定\nライブラリ: 工事写真\nマッピング先: /docs/photos/fukuoka/\n方向: 書出のみ\n同期ファイル数: 0\nステータス: 設定未完了（接続テスト待ち）',
  },
]

const statusPill = (s: SyncRow['status']) => {
  if (s === 'active') return 'ep-pill ep-pill-ok'
  if (s === 'warn') return 'ep-pill ep-pill-warn'
  return 'ep-pill ep-pill-muted'
}

const statusLabel = (s: SyncRow['status']) => {
  if (s === 'active') return '正常'
  if (s === 'warn') return '警告'
  return '停止'
}

export const M365View: FC<ViewProps> = ({ onShowModal, onShowToast }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Connection cards */}
      <div className="ep-m365-grid">
        {CONN_CARDS.map((card) => (
          <div
            key={card.id}
            className="ep-panel ep-conn"
            onClick={() => onShowModal({ title: card.title, body: card.modalBody })}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ')
                onShowModal({ title: card.title, body: card.modalBody })
            }}
          >
            <div className="ep-conn-head">
              <div className="left">
                <div className={card.logoClass}>{card.logoText}</div>
                <div>
                  <h4>{card.title}</h4>
                  <div className="ds">{card.desc}</div>
                </div>
              </div>
              <span
                className={`ep-conn-status${card.status === 'disconnected' ? ' disc' : ''}`}
              >
                {card.status === 'connected' ? '接続中' : '切断'}
              </span>
            </div>
            <div className="ep-conn-rows">
              {card.rows.map((row) => (
                <div key={row.k} className="ep-conn-row">
                  <span className="k">{row.k}</span>
                  <span className="v">{row.v}</span>
                </div>
              ))}
            </div>
            <div className="ep-conn-actions" onClick={(e) => e.stopPropagation()}>
              <button
                className="ep-btn ep-btn-secondary ep-btn-sm"
                onClick={() => {
                  onShowToast(`${card.title}: テスト接続中...`, 'ok')
                }}
              >
                テスト接続
              </button>
              <button
                className="ep-btn ep-btn-secondary ep-btn-sm"
                onClick={() =>
                  onShowModal({ title: `${card.title} — 設定`, body: card.modalBody })
                }
              >
                設定
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* SP sync mapping table */}
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>SharePoint 同期マッピング</h3>
          <div style={{ display: 'flex', gap: '5px' }}>
            <button
              className="ep-btn ep-btn-secondary ep-btn-sm"
              onClick={() => onShowToast('全サイト手動同期を開始しました', 'ok')}
            >
              今すぐ同期
            </button>
            <button
              className="ep-btn ep-btn-primary ep-btn-sm"
              onClick={() =>
                onShowModal({
                  title: 'マッピングを追加',
                  body: '新しいSharePoint同期マッピングを追加します。\n\n- SharePointサイトURL\n- ライブラリ名\n- マッピング先フォルダ\n- 同期方向（双方向/取込/書出）\n\nを入力してください。',
                })
              }
            >
              + マッピング追加
            </button>
          </div>
        </div>
        <table className="ep-tbl">
          <thead>
            <tr>
              <th>SharePointサイト</th>
              <th>ライブラリ</th>
              <th>マッピング先</th>
              <th>方向</th>
              <th>同期数</th>
              <th>最終同期</th>
              <th>状態</th>
            </tr>
          </thead>
          <tbody>
            {SYNC_ROWS.map((row) => (
              <tr
                key={row.id}
                style={{ cursor: 'pointer' }}
                onClick={() =>
                  onShowModal({
                    title: `同期マッピング — ${row.site}`,
                    body: row.modalBody,
                  })
                }
              >
                <td>
                  <span style={{ fontWeight: 500 }}>{row.site}</span>
                </td>
                <td>{row.library}</td>
                <td>
                  <code>{row.mapping}</code>
                </td>
                <td>
                  <span
                    className="ep-pill ep-pill-muted"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}
                  >
                    {row.direction}
                  </span>
                </td>
                <td className="num">{row.count}</td>
                <td style={{ color: 'var(--muted)', fontSize: '12px' }}>{row.lastSync}</td>
                <td>
                  <span className={statusPill(row.status)}>
                    <span className="dot" />
                    {statusLabel(row.status)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
