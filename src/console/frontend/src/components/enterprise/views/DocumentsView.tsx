import { useState, useCallback, useRef, useEffect } from 'react'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

interface Document {
  id: string
  title: string
  type: 'DWG' | 'SPC' | 'QTY' | 'SAF' | 'PHT'
  project: string
  rev: string
  status: '回覧中' | '差戻し' | '承認済' | '提出済' | '完了' | 'NGあり' | 'レビュー中'
  signed: boolean
  size: string
  updated: string
  retentionExpiresAt?: string  // ISO date; 電子帳簿保存法 7-year retention
}

const DOCUMENTS: Document[] = [
  { id: 'doc-001', title: '県道○○号 詳細図', type: 'DWG', project: '2024-038', rev: 'Rev.04', status: '回覧中', signed: false, size: '218MB', updated: '2024-06-12', retentionExpiresAt: '2031-06-12' },
  { id: 'doc-002', title: '特記仕様書 R6-04 rev2', type: 'SPC', project: '2024-038', rev: 'Rev.02', status: '差戻し', signed: false, size: '3.1MB', updated: '2024-06-11', retentionExpiresAt: '2026-06-01' },
  { id: 'doc-003', title: '数量計算書 R6-04', type: 'QTY', project: '2024-038', rev: 'Rev.01', status: '承認済', signed: true, size: '22MB', updated: '2024-06-10', retentionExpiresAt: '2026-05-25' },
  { id: 'doc-004', title: 'グリーンファイル', type: 'SAF', project: '2024-038', rev: '—', status: '提出済', signed: true, size: '8.4MB', updated: '2024-06-09', retentionExpiresAt: '2031-06-09' },
  { id: 'doc-005', title: '△△橋 詳細設計図', type: 'DWG', project: '2024-041', rev: 'Rev.07', status: '承認済', signed: true, size: '412MB', updated: '2024-06-08', retentionExpiresAt: '2031-06-08' },
  { id: 'doc-006', title: '工事写真台帳', type: 'PHT', project: '2024-038', rev: '—', status: '完了', signed: false, size: '128MB', updated: '2024-06-07', retentionExpiresAt: '2024-12-31' },
  { id: 'doc-007', title: '××トンネル 換気仕様書', type: 'SPC', project: '2024-052', rev: 'Rev.03', status: 'レビュー中', signed: false, size: '14.8MB', updated: '2024-06-06', retentionExpiresAt: '2031-06-06' },
  { id: 'doc-008', title: '下水道第3期数量計算書', type: 'QTY', project: '2024-061', rev: 'Rev.02', status: 'NGあり', signed: false, size: '324MB', updated: '2024-06-05', retentionExpiresAt: '2031-06-05' },
]

const FILTERS = [
  { key: 'all', label: 'すべて', count: 2418 },
  { key: '図面', label: '図面', count: 1128 },
  { key: '仕様書', label: '仕様書', count: 412 },
  { key: '数量', label: '数量', count: 298 },
  { key: '安全', label: '安全', count: 324 },
  { key: '帳票', label: '帳票', count: 186 },
]

type FilterKey = typeof FILTERS[number]['key']

const TYPE_FILTER_MAP: Record<FilterKey, string[]> = {
  all: [],
  '図面': ['DWG'],
  '仕様書': ['SPC'],
  '数量': ['QTY'],
  '安全': ['SAF'],
  '帳票': ['PHT'],
}

function statusPillClass(status: Document['status']): string {
  switch (status) {
    case '回覧中': return 'ep-pill ep-pill-info-2'
    case '差戻し': return 'ep-pill ep-pill-warn'
    case '承認済': return 'ep-pill ep-pill-ok'
    case '提出済': return 'ep-pill ep-pill-ok'
    case '完了': return 'ep-pill ep-pill-muted'
    case 'NGあり': return 'ep-pill ep-pill-ng'
    case 'レビュー中': return 'ep-pill ep-pill-info'
    default: return 'ep-pill ep-pill-muted'
  }
}

function typeIconClass(type: Document['type']): string {
  switch (type) {
    case 'DWG': return 'dwg'
    case 'SPC': return 'spec'
    case 'QTY': return 'qty'
    case 'SAF': return 'safe'
    case 'PHT': return 'rep'
    default: return ''
  }
}

type RetentionStatus = 'expired' | 'warning' | 'ok' | null

function retentionStatus(expiresAt: string | undefined): RetentionStatus {
  if (!expiresAt) return null
  const now = new Date()
  const expiry = new Date(expiresAt)
  const daysLeft = Math.floor((expiry.getTime() - now.getTime()) / 86_400_000)
  if (daysLeft < 0) return 'expired'
  if (daysLeft <= 30) return 'warning'
  return 'ok'
}

function RetentionBadge({ expiresAt }: { expiresAt: string | undefined }) {
  const status = retentionStatus(expiresAt)
  if (!status || status === 'ok') return null
  const isExpired = status === 'expired'
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '2px',
        fontSize: '10px',
        fontWeight: 600,
        padding: '1px 5px',
        borderRadius: '3px',
        background: isExpired ? 'var(--danger, #e53e3e)' : '#f6ad55',
        color: '#fff',
        marginLeft: '6px',
        verticalAlign: 'middle',
      }}
      title={`保存期限: ${expiresAt}`}
    >
      ⚠️ {isExpired ? '期限切れ' : '期限間近'}
    </span>
  )
}

interface ContextMenu {
  visible: boolean
  x: number
  y: number
  docId: string
}

const CTX_ITEMS = [
  { label: '開く', key: 'open', icon: '↗', shortcut: '⏎' },
  { label: 'ダウンロード', key: 'dl', icon: '↓', shortcut: '⌘D' },
  { label: '比較', key: 'compare', icon: '⇄', shortcut: '' },
  { label: 'WF送信', key: 'wf', icon: '→', shortcut: '' },
  { label: '共有', key: 'share', icon: '⤴', shortcut: '⌘S' },
  null,
  { label: '削除', key: 'delete', icon: '✕', shortcut: '', danger: true },
]

export function DocumentsView({ onNavigate, onShowModal }: ViewProps) {
  const [activeFilter, setActiveFilter] = useState<FilterKey>('all')
  const [search, setSearch] = useState('')
  const [contextMenu, setContextMenu] = useState<ContextMenu>({ visible: false, x: 0, y: 0, docId: '' })
  const ctxRef = useRef<HTMLDivElement>(null)

  const filteredDocs = DOCUMENTS.filter((doc) => {
    const typeFilter = TYPE_FILTER_MAP[activeFilter]
    const matchesType = typeFilter.length === 0 || typeFilter.includes(doc.type)
    const q = search.toLowerCase()
    const matchesSearch = q === '' || doc.title.toLowerCase().includes(q) || doc.project.toLowerCase().includes(q)
    return matchesType && matchesSearch
  })

  const handleRowClick = useCallback((doc: Document) => {
    onShowModal({
      title: doc.title,
      body: `工事番号: ${doc.project}\n種別: ${doc.type}\nリビジョン: ${doc.rev}\n状態: ${doc.status}\nサイズ: ${doc.size}\n最終更新: ${doc.updated}`,
    })
  }, [onShowModal])

  const handleRightClick = useCallback((e: React.MouseEvent, docId: string) => {
    e.preventDefault()
    setContextMenu({ visible: true, x: e.clientX, y: e.clientY, docId })
  }, [])

  const closeCtx = useCallback(() => {
    setContextMenu((prev) => ({ ...prev, visible: false }))
  }, [])

  const handleCtxAction = useCallback((key: string) => {
    closeCtx()
    if (key === 'open') {
      onNavigate('viewer')
    } else if (key === 'wf') {
      onNavigate('workflow')
    }
  }, [closeCtx, onNavigate])

  useEffect(() => {
    if (!contextMenu.visible) return
    const handler = (e: MouseEvent) => {
      if (ctxRef.current && !ctxRef.current.contains(e.target as Node)) {
        closeCtx()
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [contextMenu.visible, closeCtx])

  return (
    <div>
      {/* Toolbar */}
      <div className="ep-doc-toolbar">
        <div className="ep-doc-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`ep-filter-pill${activeFilter === f.key ? ' active' : ''}`}
              onClick={() => setActiveFilter(f.key)}
              type="button"
            >
              {f.label}
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--muted)' }}>
                {f.count.toLocaleString()}
              </span>
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div className="ep-doc-search">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
              <path d="m11 11 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
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
            onClick={() => onNavigate('upload')}
          >
            + 新規取込
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="ep-panel" style={{ overflow: 'hidden' }}>
        <table className="ep-tbl">
          <thead>
            <tr>
              <th style={{ width: '32px' }}>
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
            {filteredDocs.map((doc) => (
              <tr
                key={doc.id}
                style={{ cursor: 'pointer' }}
                onClick={() => handleRowClick(doc)}
                onContextMenu={(e) => handleRightClick(e, doc.id)}
              >
                <td onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" aria-label={`${doc.title}を選択`} />
                </td>
                <td>
                  <div className="ep-doc-name">
                    <div className={`ep-doc-name ic ${typeIconClass(doc.type)}`}>
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
                  {doc.rev !== '—' ? (
                    <span className="ep-rev-chip">{doc.rev}</span>
                  ) : (
                    <span style={{ color: 'var(--muted)' }}>—</span>
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
                    <span style={{ color: 'var(--muted)', fontSize: '12px' }}>—</span>
                  )}
                </td>
                <td className="num" style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  {doc.size}
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--muted)' }}>
                  {doc.updated}
                </td>
                <td onClick={(e) => e.stopPropagation()}>
                  <button
                    className="ep-btn ep-btn-secondary ep-btn-sm"
                    type="button"
                    onClick={() => onNavigate('viewer')}
                  >
                    開く
                  </button>
                </td>
              </tr>
            ))}
            {filteredDocs.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: 'var(--muted)' }}>
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
        className={`ep-ctx-menu${contextMenu.visible ? ' open' : ''}`}
        style={{ left: contextMenu.x, top: contextMenu.y }}
        role="menu"
      >
        {CTX_ITEMS.map((item, idx) =>
          item === null ? (
            <div key={`sep-${idx}`} className="ep-ctx-sep" />
          ) : (
            <button
              key={item.key}
              className={`ep-ctx-item${item.danger ? ' danger' : ''}`}
              type="button"
              role="menuitem"
              onClick={() => handleCtxAction(item.key)}
            >
              <span style={{ width: '14px', textAlign: 'center', fontSize: '11px' }}>{item.icon}</span>
              {item.label}
              {item.shortcut && <span className="ctx-key">{item.shortcut}</span>}
            </button>
          )
        )}
      </div>
    </div>
  )
}
