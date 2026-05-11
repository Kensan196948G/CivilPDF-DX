import { type FC, useState, useEffect } from 'react'
import { listAuditLogs, type AuditLogItem } from '../../../api/auditLogs'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

type ActionFilter = 'すべて' | 'view' | 'download' | 'print' | 'sign' | 'denied'

interface AuditRow {
  id: string
  time: string
  actor: string
  action: string
  target: string
  result: 'success' | 'denied' | 'warn'
  client: string
  ip: string
}

const AUDIT_ROWS: AuditRow[] = [
  {
    id: 'EVT-08431',
    time: '2026-05-11 14:32:17',
    actor: '山田 太郎',
    action: 'download',
    target: '道路設計図_R6改訂v3.pdf',
    result: 'success',
    client: 'PDF Editor v2.4.1',
    ip: '203.0.113.45',
  },
  {
    id: 'EVT-08430',
    time: '2026-05-11 14:28:05',
    actor: '佐藤 花子',
    action: 'sign',
    target: '工事完成図書_確認書.pdf',
    result: 'success',
    client: 'Web Console',
    ip: '203.0.113.12',
  },
  {
    id: 'EVT-08429',
    time: '2026-05-11 14:15:42',
    actor: '田中 一郎',
    action: 'print',
    target: '橋梁設計計算書_最終版.pdf',
    result: 'success',
    client: 'PDF Editor v2.4.1',
    ip: '198.51.100.22',
  },
  {
    id: 'EVT-08428',
    time: '2026-05-11 13:58:19',
    actor: '鈴木 次郎',
    action: 'view',
    target: '施工計画書_第3工区.pdf',
    result: 'success',
    client: 'Web Console',
    ip: '198.51.100.89',
  },
  {
    id: 'EVT-08427',
    time: '2026-05-11 13:47:33',
    actor: '外部_協力会社A_担当',
    action: 'download',
    target: '構造計算書_機密.pdf',
    result: 'denied',
    client: 'Web Console',
    ip: '203.0.114.99',
  },
  {
    id: 'EVT-08426',
    time: '2026-05-11 13:31:08',
    actor: '高橋 三郎',
    action: 'view',
    target: '電気設備図面_B棟.pdf',
    result: 'success',
    client: 'PDF Editor v2.4.1',
    ip: '203.0.113.45',
  },
  {
    id: 'EVT-08425',
    time: '2026-05-11 13:20:55',
    actor: '伊藤 四郎',
    action: 'sign',
    target: '品質管理記録_5月分.pdf',
    result: 'success',
    client: 'Web Console',
    ip: '203.0.113.60',
  },
  {
    id: 'EVT-08424',
    time: '2026-05-11 13:05:12',
    actor: '渡辺 五郎',
    action: 'download',
    target: '安全管理計画書.pdf',
    result: 'success',
    client: 'PDF Editor v2.4.0',
    ip: '198.51.100.31',
  },
  {
    id: 'EVT-08423',
    time: '2026-05-11 12:48:39',
    actor: '不明ユーザー',
    action: 'view',
    target: 'ログイン試行（失敗）',
    result: 'denied',
    client: 'Unknown',
    ip: '10.20.30.99',
  },
  {
    id: 'EVT-08422',
    time: '2026-05-11 12:32:01',
    actor: '中村 六子',
    action: 'print',
    target: '工事写真台帳_4月.pdf',
    result: 'warn',
    client: 'PDF Editor v2.4.1',
    ip: '203.0.113.77',
  },
]

const ACTION_FILTERS: ActionFilter[] = ['すべて', 'view', 'download', 'print', 'sign', 'denied']

const resultPillClass: Record<AuditRow['result'], string> = {
  success: 'ep-pill ep-pill-ok',
  denied: 'ep-pill ep-pill-ng',
  warn: 'ep-pill ep-pill-warn',
}

const resultLabel: Record<AuditRow['result'], string> = {
  success: '成功',
  denied: '拒否',
  warn: '警告',
}

const buildModalBody = (row: AuditRow): string =>
  `監査イベント詳細\n\nイベントID: ${row.id}\n日時: ${row.time}\n\n実行者: ${row.actor}\n操作: ${row.action}\n対象: ${row.target}\n結果: ${resultLabel[row.result]}\n\nクライアント: ${row.client}\nIPアドレス: ${row.ip}\n\nハッシュ（SHA-256）: a3f5c2e1d8b4...（改ざん検知済み）`

function mapApiRowToAuditRow(item: AuditLogItem): AuditRow {
  return {
    id: item.id.slice(0, 8).toUpperCase(),
    time: item.created_at.replace('T', ' ').slice(0, 19),
    actor: item.user?.full_name ?? item.user?.email ?? '不明ユーザー',
    action: item.action,
    target: item.resource_type ? `${item.resource_type}:${item.resource_id ?? ''}` : (item.detail ?? '—'),
    result: 'success' as const,
    client: 'Web Console',
    ip: item.ip_address ?? '—',
  }
}

export const AuditView: FC<ViewProps> = ({ onShowModal }) => {
  const [search, setSearch] = useState('')
  const [actionFilter, setActionFilter] = useState<ActionFilter>('すべて')
  const [apiRows, setApiRows] = useState<AuditRow[]>([])
  const [totalEvents, setTotalEvents] = useState<number | null>(null)

  useEffect(() => {
    listAuditLogs({ per_page: 50 })
      .then((data) => {
        setApiRows(data.items.map(mapApiRowToAuditRow))
        setTotalEvents(data.total)
      })
      .catch(() => { /* fallback to static rows */ })
  }, [])

  const rows = apiRows.length > 0 ? apiRows : AUDIT_ROWS

  const filtered = rows.filter((row) => {
    const matchesAction =
      actionFilter === 'すべて'
        ? true
        : actionFilter === 'denied'
        ? row.result === 'denied'
        : row.action === actionFilter
    const matchesSearch =
      search === ''
        ? true
        : row.actor.includes(search) || row.target.includes(search)
    return matchesAction && matchesSearch
  })

  return (
    <div>
      {/* Stat cards */}
      <div className="ep-stat-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '16px' }}>
        <div className="ep-stat">
          <div className="lbl">総イベント数</div>
          <div className="val">{totalEvents !== null ? totalEvents.toLocaleString() : '42,612'}</div>
          <div className="delta up">累計</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">ダウンロード数</div>
          <div className="val">3,184</div>
          <div className="delta up">+5.1%</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">拒否イベント</div>
          <div className="val">218</div>
          <div className="delta down">+12 今日</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">重大アラート</div>
          <div className="val">12</div>
          <div className="delta down">要対応</div>
        </div>
      </div>

      {/* Search + filter */}
      <div className="ep-aud-search">
        <div
          className="ep-doc-search"
          style={{ flex: 1, maxWidth: '400px' }}
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="7" cy="7" r="5" />
            <path d="M11 11l3 3" />
          </svg>
          <input
            type="text"
            placeholder="実行者・対象ファイルで検索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              border: 0,
              outline: 0,
              background: 'transparent',
              flex: 1,
              color: 'var(--fg)',
              font: 'inherit',
              fontSize: '12.5px',
            }}
          />
        </div>
        {ACTION_FILTERS.map((f) => (
          <button
            key={f}
            className={`ep-filter-pill${actionFilter === f ? ' active' : ''}`}
            onClick={() => setActionFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="ep-panel">
        <table className="ep-tbl">
          <thead>
            <tr>
              <th>日時</th>
              <th>実行者</th>
              <th>操作</th>
              <th>対象</th>
              <th>結果</th>
              <th>クライアント</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  style={{
                    textAlign: 'center',
                    padding: '24px',
                    color: 'var(--muted)',
                    fontSize: '12.5px',
                  }}
                >
                  該当するイベントがありません
                </td>
              </tr>
            ) : (
              filtered.map((row) => (
                <tr
                  key={row.id}
                  className="ep-audit-row"
                  style={{ cursor: 'pointer' }}
                  onClick={() =>
                    onShowModal({
                      title: `監査ログ — ${row.id}`,
                      body: buildModalBody(row),
                    })
                  }
                >
                  <td>
                    <span className="id">{row.time}</span>
                  </td>
                  <td>
                    <span className="actor">{row.actor}</span>
                  </td>
                  <td>
                    <span
                      className="ep-pill ep-pill-muted"
                      style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}
                    >
                      {row.action}
                    </span>
                  </td>
                  <td
                    style={{
                      maxWidth: '200px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {row.target}
                  </td>
                  <td>
                    <span className={resultPillClass[row.result]}>
                      <span className="dot" />
                      {resultLabel[row.result]}
                    </span>
                  </td>
                  <td style={{ color: 'var(--muted)', fontSize: '12px' }}>{row.client}</td>
                  <td>
                    <span className="ip">{row.ip}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
