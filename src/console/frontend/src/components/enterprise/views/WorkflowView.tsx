import { useState, useCallback } from 'react'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

type WfStatus = '審査中' | '差戻し' | '承認済' | '却下' | 'レビュー中' | '配布済'

interface WfItem {
  id: string
  title: string
  from: string
  due: string
  dueSoon: boolean
  status: WfStatus
}

type StageStatus = 'done' | 'current' | 'pending'

interface WfStage {
  id: string
  label: string
  who: string
  when: string
  status: StageStatus
}

interface Stamp {
  id: string
  name: string
  person: string
  pending: boolean
  date?: string
}

interface Comment {
  id: string
  initials: string
  author: string
  time: string
  body: string
}

const WF_ITEMS: WfItem[] = [
  { id: 'wf1', title: '特記仕様書R6-04rev2', from: '田中 太郎', due: '2024-06-14', dueSoon: true, status: '審査中' },
  { id: 'wf2', title: '県道○○号 詳細図 Rev.04', from: '鈴木 花子', due: '2024-06-18', dueSoon: false, status: 'レビュー中' },
  { id: 'wf3', title: '数量計算書 R6-04', from: '佐藤 一郎', due: '2024-06-20', dueSoon: false, status: '承認済' },
  { id: 'wf4', title: 'グリーンファイル一式', from: '山本 次郎', due: '2024-06-10', dueSoon: true, status: '差戻し' },
  { id: 'wf5', title: '△△橋 詳細設計図 Rev.07', from: '中村 三郎', due: '2024-06-25', dueSoon: false, status: '承認済' },
  { id: 'wf6', title: '下水道第3期 数量計算書', from: '小林 四郎', due: '2024-06-16', dueSoon: true, status: 'レビュー中' },
  { id: 'wf7', title: '××トンネル 換気仕様書', from: '加藤 五郎', due: '2024-06-30', dueSoon: false, status: '審査中' },
]

const WF_STAGES: WfStage[] = [
  { id: 's1', label: '申請', who: '田中 太郎', when: '2024-06-10 09:32', status: 'done' },
  { id: 's2', label: '設計レビュー', who: '鈴木 花子', when: '2024-06-11 14:15', status: 'done' },
  { id: 's3', label: '主任承認', who: '山田 直人', when: '審査中', status: 'current' },
  { id: 's4', label: '部長承認', who: '佐々木 部長', when: '待機中', status: 'pending' },
  { id: 's5', label: '配布', who: '配布先各位', when: '待機中', status: 'pending' },
]

const STAMPS: Stamp[] = [
  { id: 'st1', name: '承認印', person: '山田 直人', pending: true },
  { id: 'st2', name: '確認印', person: '鈴木 花子', pending: false, date: '2024-06-11' },
  { id: 'st3', name: '担当印', person: '田中 太郎', pending: false, date: '2024-06-10' },
]

const COMMENTS: Comment[] = [
  { id: 'cm1', initials: '田', author: '田中 太郎', time: '2024-06-10 09:32', body: '特記仕様書を承認フローに登録しました。確認の程よろしくお願いします。' },
  { id: 'cm2', initials: '鈴', author: '鈴木 花子', time: '2024-06-11 14:15', body: '設計レビュー完了。p.4 の材料規格記載を修正済みで問題ありません。主任承認をお願いします。' },
  { id: 'cm3', initials: '山', author: '山田 直人', time: '2024-06-12 10:00', body: '内容確認中。縮尺表記について確認事項あり。折り返し連絡します。' },
]

function wfStatusPillClass(status: WfStatus): string {
  switch (status) {
    case '審査中': return 'ep-pill ep-pill-info-2'
    case 'レビュー中': return 'ep-pill ep-pill-info'
    case '承認済': return 'ep-pill ep-pill-ok'
    case '差戻し': return 'ep-pill ep-pill-warn'
    case '却下': return 'ep-pill ep-pill-ng'
    case '配布済': return 'ep-pill ep-pill-muted'
    default: return 'ep-pill ep-pill-muted'
  }
}

export function WorkflowView({ onNavigate, onShowModal, onShowToast }: ViewProps) {
  const [activeWfId, setActiveWfId] = useState<string>('wf1')

  const activeWf = WF_ITEMS.find((w) => w.id === activeWfId) ?? WF_ITEMS[0]

  const handleReject = useCallback(() => {
    onShowModal({
      title: '差戻し',
      body: `"${activeWf.title}" を差戻します。\n\n差戻し理由:\n・縮尺表記の不一致を修正してください\n・ファイル命名規則に準拠してください\n\n申請者に通知が送信されます。`,
    })
  }, [activeWf, onShowModal])

  const handleDismiss = useCallback(() => {
    onShowToast('却下しました', 'error')
  }, [onShowToast])

  const handleApprove = useCallback(() => {
    onShowToast('承認しました', 'ok')
  }, [onShowToast])

  return (
    <div>
      {/* Header actions */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', marginBottom: '14px', alignItems: 'center' }}>
        <button
          className="ep-btn ep-btn-secondary ep-btn-sm"
          type="button"
          onClick={() => onNavigate('viewer')}
        >
          PDFを開く ↗
        </button>
        <button
          className="ep-btn ep-btn-secondary ep-btn-sm"
          type="button"
          onClick={handleReject}
        >
          差戻し
        </button>
        <button
          className="ep-btn ep-btn-danger ep-btn-sm"
          type="button"
          onClick={handleDismiss}
        >
          却下
        </button>
        <button
          className="ep-btn ep-btn-primary"
          type="button"
          onClick={handleApprove}
        >
          承認（電子印を押す）
        </button>
      </div>

      {/* WF grid */}
      <div className="ep-wf-grid">
        {/* Left: WF list */}
        <div className="ep-wf-list">
          <div className="ep-wf-list-head">
            <span>承認待ち ({WF_ITEMS.length})</span>
            <span style={{ color: 'var(--danger)', fontSize: '9.5px' }}>期限超過 2</span>
          </div>
          {WF_ITEMS.map((wf) => (
            <div
              key={wf.id}
              className={`ep-wf-item${activeWfId === wf.id ? ' active' : ''}`}
              onClick={() => setActiveWfId(wf.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter') setActiveWfId(wf.id) }}
              aria-pressed={activeWfId === wf.id}
            >
              <h5>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {wf.title}
                </span>
                <span className={wfStatusPillClass(wf.status)}>
                  {wf.status}
                </span>
              </h5>
              <div className="from">申請: {wf.from}</div>
              <div className={`due${wf.dueSoon ? ' soon' : ''}`}>
                期限: {wf.due}{wf.dueSoon && ' ⚠'}
              </div>
            </div>
          ))}
        </div>

        {/* Right: WF detail */}
        <div className="ep-wf-detail">
          {/* Detail header */}
          <div className="ep-wf-detail-head">
            <div>
              <h2>{activeWf.title}</h2>
              <div className="from">
                申請者: {activeWf.from} · 期限: {activeWf.due}
                {activeWf.dueSoon && (
                  <span className="ep-pill ep-pill-warn" style={{ marginLeft: '6px' }}>期限近</span>
                )}
              </div>
            </div>
            <span className={wfStatusPillClass(activeWf.status)}>
              <span className="dot" />
              {activeWf.status}
            </span>
          </div>

          {/* Stages */}
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginBottom: '8px' }}>
              承認フロー
            </div>
            <div className="ep-wf-stages">
              {WF_STAGES.map((stage) => (
                <div key={stage.id} className={`ep-wf-stage ${stage.status}`}>
                  <h6>{stage.label}</h6>
                  <div className="who">{stage.who}</div>
                  <div className="when">{stage.when}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Stamps */}
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginBottom: '8px' }}>
              電子印鑑
            </div>
            <div className="ep-stamp-section">
              {STAMPS.map((stamp) => (
                <div key={stamp.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                  <div
                    className={`ep-stamp${stamp.pending ? ' pending' : ''}`}
                    role="button"
                    tabIndex={0}
                    onKeyDown={() => {}}
                    onClick={() => {
                      if (stamp.pending) {
                        onShowToast('承認しました', 'ok')
                      }
                    }}
                  >
                    {stamp.pending ? '未\n押印' : stamp.name.slice(0, 2)}
                  </div>
                  <div className="ep-stamp-info" style={{ textAlign: 'center' }}>
                    <strong>{stamp.name}</strong>
                    <div style={{ fontSize: '11px', color: 'var(--muted)' }}>
                      {stamp.person}
                    </div>
                    {stamp.date && (
                      <div style={{ fontSize: '10px', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
                        {stamp.date}
                      </div>
                    )}
                    {stamp.pending && (
                      <span className="ep-pill ep-pill-muted" style={{ marginTop: '2px' }}>未押印</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Comments */}
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
              <span>コメント ({COMMENTS.length})</span>
            </div>
            <div className="ep-wf-comments">
              {COMMENTS.map((comment) => (
                <div key={comment.id} className="ep-comment">
                  <div className="av">{comment.initials}</div>
                  <div className="bd">
                    <div className="h">
                      <strong>{comment.author}</strong>
                      <span className="t">{comment.time}</span>
                    </div>
                    <div className="body">{comment.body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
