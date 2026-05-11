import { type FC, useState } from 'react'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

type RnFilter = 'All' | 'Stable' | 'Beta' | 'Insider'

interface DownloadCard {
  os: string
  fmt: string
  size: string
  modalBody: string
}

interface Channel {
  id: string
  label: string
  ver: string
  desc: string
  users: string
  pillClass: string
  modalBody: string
}

interface ToggleItem {
  id: string
  label: string
  sub: string
}

interface DeployTarget {
  id: string
  name: string
  meta: string
  progress: number
  count: string
  status: string
  modalBody: string
}

interface ReleaseNote {
  ver: string
  date: string
  channel: RnFilter
  summary: string
  items: { tag: string; tagClass: string; text: string }[]
  modalBody: string
}

const DL_CARDS: DownloadCard[] = [
  {
    os: 'Windows',
    fmt: 'インストーラー (.exe)',
    size: '87.4 MB',
    modalBody:
      'PDF Editor Client — Windows インストーラー\n\nバージョン: v2.4.1 (Stable)\nファイル: CivilPDF-Editor-Setup-2.4.1.exe\nサイズ: 87.4 MB\nSHA-256: 3a4b5c6d...\n\n対応OS: Windows 10 / 11 (64bit)\n必要要件: .NET 8.0 Runtime\n\nインストール手順:\n1. exeをダウンロード\n2. 管理者権限で実行\n3. Entra IDでサインイン',
  },
  {
    os: 'Windows',
    fmt: 'ポータブル (.zip)',
    size: '94.1 MB',
    modalBody:
      'PDF Editor Client — ポータブル版\n\nバージョン: v2.4.1 (Stable)\nファイル: CivilPDF-Editor-Portable-2.4.1.zip\nサイズ: 94.1 MB\n\nインストール不要で使用可能。\nUSBメモリや持ち出し端末向け。\n\n注意: 透かし・DLPポリシーは適用されます。',
  },
  {
    os: 'macOS',
    fmt: 'ディスクイメージ (.dmg)',
    size: '82.6 MB',
    modalBody:
      'PDF Editor Client — macOS 版\n\nバージョン: v2.4.1 (Stable)\nファイル: CivilPDF-Editor-2.4.1.dmg\nサイズ: 82.6 MB\n\n対応OS: macOS 13 Ventura 以降\nApple Silicon / Intel 両対応 (Universal Binary)',
  },
  {
    os: 'Enterprise',
    fmt: 'Intune パッケージ',
    size: '91.2 MB',
    modalBody:
      'PDF Editor Client — Intune 展開パッケージ\n\nバージョン: v2.4.1 (Stable)\nファイル: CivilPDF-Editor-2.4.1.intunewin\nサイズ: 91.2 MB\n\nMicrosoft Endpoint Manager (Intune) 経由で\n一括展開が可能です。\n\n検出ルール・要件・依存関係は\nIntuneDeployGuide.pdf を参照してください。',
  },
]

const CHANNELS: Channel[] = [
  {
    id: 'stable',
    label: 'Stable',
    ver: 'v2.4.1',
    desc: '本番推奨。十分な検証済みリリース。',
    users: '211 ユーザー',
    pillClass: 'ep-pill ep-pill-stable',
    modalBody:
      'Stable チャンネル\n\nバージョン: v2.4.1\nリリース日: 2026-04-28\n\n対象: 全ユーザー（デフォルト）\n更新頻度: 月1回程度\n検証期間: Beta → 4週間テスト後リリース\n\n現在の参加ユーザー数: 211',
  },
  {
    id: 'beta',
    label: 'Beta',
    ver: 'v2.5.0-beta.3',
    desc: '機能検証版。次期安定版の先行確認。',
    users: '28 ユーザー',
    pillClass: 'ep-pill ep-pill-beta',
    modalBody:
      'Beta チャンネル\n\nバージョン: v2.5.0-beta.3\nリリース日: 2026-05-07\n\n対象: 技術担当者・検証チーム\n更新頻度: 2週間に1回程度\n\nBugReport 先: GitHub Issues\n現在の参加ユーザー数: 28',
  },
  {
    id: 'insider',
    label: 'Insider',
    ver: 'v2.5.0-alpha.9',
    desc: '開発最前線。破壊的変更が含まれる可能性あり。',
    users: '9 ユーザー',
    pillClass: 'ep-pill ep-pill-insider',
    modalBody:
      'Insider チャンネル\n\nバージョン: v2.5.0-alpha.9\nリリース日: 2026-05-10\n\n対象: 開発者・社内QAチームのみ\n更新頻度: 随時（CI通過時）\n\n警告: 本番業務には使用しないこと。\n現在の参加ユーザー数: 9',
  },
]

const TOGGLES: ToggleItem[] = [
  { id: 'autoUpdate', label: '自動アップデート', sub: 'バックグラウンドで最新版を自動適用' },
  { id: 'forceMin', label: '最低バージョン強制', sub: 'v2.3.0未満はアクセスをブロック' },
  { id: 'telemetry', label: 'テレメトリー収集', sub: 'クラッシュレポート・使用状況を収集（匿名）' },
]

const DEPLOY_TARGETS: DeployTarget[] = [
  {
    id: 'DT-001',
    name: '本社ビル (東京)',
    meta: 'Windows 11 · 98台',
    progress: 100,
    count: '98 / 98',
    status: '完了',
    modalBody: '本社ビル (東京)\n\n対象台数: 98台\nOS: Windows 11\nインストール方式: Intune\nバージョン: v2.4.1\nステータス: 全台展開済み\n最終更新: 2026-04-29',
  },
  {
    id: 'DT-002',
    name: '大阪支店',
    meta: 'Windows 10/11 · 54台',
    progress: 96,
    count: '52 / 54',
    status: '展開中',
    modalBody: '大阪支店\n\n対象台数: 54台\nOS: Windows 10 / 11\nインストール方式: Intune\nバージョン: v2.4.1\nステータス: 展開中 (52/54)\n残り2台: オフライン端末',
  },
  {
    id: 'DT-003',
    name: '名古屋支店',
    meta: 'Windows 10 · 31台',
    progress: 87,
    count: '27 / 31',
    status: '展開中',
    modalBody: '名古屋支店\n\n対象台数: 31台\nOS: Windows 10\nインストール方式: グループポリシー\nバージョン: v2.4.1\nステータス: 展開中 (27/31)',
  },
  {
    id: 'DT-004',
    name: '第3工区現場事務所',
    meta: 'Windows 10 · 8台',
    progress: 75,
    count: '6 / 8',
    status: '展開中',
    modalBody: '第3工区現場事務所\n\n対象台数: 8台\nOS: Windows 10\nインストール方式: 手動（USB）\nバージョン: v2.4.1\nステータス: 展開中 (6/8)\n残り2台: 次回訪問時に対応予定',
  },
  {
    id: 'DT-005',
    name: '協力会社A (外部)',
    meta: 'Windows 11 · 12台',
    progress: 100,
    count: '12 / 12',
    status: '完了',
    modalBody: '協力会社A (外部)\n\n対象台数: 12台\nOS: Windows 11\nインストール方式: ポータブル版配布\nバージョン: v2.4.1\nステータス: 全台展開済み\n有効期限: 2026-08-31',
  },
  {
    id: 'DT-006',
    name: '福岡支店',
    meta: 'Windows 10/11 · 22台',
    progress: 0,
    count: '0 / 22',
    status: '未開始',
    modalBody: '福岡支店\n\n対象台数: 22台\nOS: Windows 10 / 11\nインストール方式: Intune（予定）\nバージョン: v2.4.1\nステータス: 未開始\n予定日: 2026-05-20',
  },
]

const RN_ITEMS: ReleaseNote[] = [
  {
    ver: 'v2.4.1',
    date: '2026-04-28',
    channel: 'Stable',
    summary: 'PDF/A変換精度向上・セキュリティ修正',
    items: [
      { tag: 'FIX', tagClass: 'fix', text: 'PDF/A-1b変換時のフォント埋め込みエラーを修正' },
      { tag: 'SEC', tagClass: 'sec', text: 'XSS脆弱性 (CVE-2026-1234) を修正' },
      { tag: 'IMP', tagClass: 'imp', text: 'A0/A1大判図面のレンダリング速度を40%改善' },
    ],
    modalBody: 'v2.4.1 — リリースノート\n\nリリース日: 2026-04-28\nチャンネル: Stable\n\n変更内容:\n- PDF/A-1b変換時のフォント埋め込みエラーを修正\n- XSS脆弱性 (CVE-2026-1234) を修正\n- A0/A1大判図面のレンダリング速度を40%改善\n\n影響範囲: 全ユーザー（即時適用推奨）',
  },
  {
    ver: 'v2.5.0-beta.3',
    date: '2026-05-07',
    channel: 'Beta',
    summary: 'Teams連携・新承認フロー',
    items: [
      { tag: 'FEAT', tagClass: 'feat', text: 'Microsoft Teams通知連携を追加' },
      { tag: 'FEAT', tagClass: 'feat', text: '承認フロー画面をリデザイン' },
      { tag: 'FIX', tagClass: 'fix', text: 'OCR日本語縦書き認識精度を改善' },
    ],
    modalBody: 'v2.5.0-beta.3 — リリースノート\n\nリリース日: 2026-05-07\nチャンネル: Beta\n\n変更内容:\n- Microsoft Teams通知連携を追加\n- 承認フロー画面をリデザイン（多段承認の可視化）\n- OCR日本語縦書き認識精度を改善\n\nBeta参加者のフィードバックをお願いします。',
  },
  {
    ver: 'v2.5.0-alpha.9',
    date: '2026-05-10',
    channel: 'Insider',
    summary: 'AI文書分類・PDF生成エンジン刷新',
    items: [
      { tag: 'FEAT', tagClass: 'feat', text: 'Claude API連携による文書自動分類（実験的）' },
      { tag: 'FEAT', tagClass: 'feat', text: 'PDF生成エンジンをpdf-lib v2に更新' },
      { tag: 'IMP', tagClass: 'imp', text: 'メモリ使用量を30%削減（大判図面）' },
    ],
    modalBody: 'v2.5.0-alpha.9 — リリースノート\n\nリリース日: 2026-05-10\nチャンネル: Insider\n\n変更内容:\n- Claude API連携による文書自動分類（実験的機能）\n- PDF生成エンジンをpdf-lib v2に更新\n- メモリ使用量を30%削減（A0/A1大判図面）\n\n警告: 本番利用不可。フィードバック歓迎。',
  },
]

const RN_FILTER_OPTIONS: RnFilter[] = ['All', 'Stable', 'Beta', 'Insider']

const rnChannelPill: Record<RnFilter, string> = {
  All: '',
  Stable: 'ep-pill ep-pill-stable',
  Beta: 'ep-pill ep-pill-beta',
  Insider: 'ep-pill ep-pill-insider',
}

export const AppsView: FC<ViewProps> = ({ onShowModal, onShowToast }) => {
  const [toggles, setToggles] = useState<Record<string, boolean>>({
    autoUpdate: true,
    forceMin: true,
    telemetry: false,
  })
  const [rnFilter, setRnFilter] = useState<RnFilter>('All')

  const toggleSwitch = (id: string) => {
    const next = !toggles[id]
    setToggles((prev) => ({ ...prev, [id]: next }))
    const label = TOGGLES.find((t) => t.id === id)?.label ?? id
    onShowToast(`${label}: ${next ? 'ON' : 'OFF'}`, next ? 'ok' : 'warn')
  }

  const filteredRn =
    rnFilter === 'All' ? RN_ITEMS : RN_ITEMS.filter((r) => r.channel === rnFilter)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* App hero */}
      <div className="ep-app-hero">
        {/* App card */}
        <div className="ep-panel ep-app-card">
          <div className="ep-app-card-top">
            <div className="ep-app-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <div>
              <h3>
                PDF Editor Client
                <span className="ep-pill ep-pill-stable">
                  <span className="dot" />
                  Stable
                </span>
              </h3>
              <p>建設・土木業向け高機能PDFエディター。電子印鑑・OCR・大判図面対応。</p>
              <div className="ep-app-meta">
                <span>バージョン v2.4.1</span>
                <span>Windows / macOS</span>
                <span>248 ライセンス</span>
              </div>
            </div>
          </div>
          {/* Download grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '7px',
              padding: '11px 16px',
              borderTop: '1px solid var(--border)',
            }}
          >
            {DL_CARDS.map((dl, i) => (
              <div
                key={i}
                className="ep-dl-card"
                onClick={() =>
                  onShowModal({ title: `${dl.os} — ${dl.fmt}`, body: dl.modalBody })
                }
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ')
                    onShowModal({ title: `${dl.os} — ${dl.fmt}`, body: dl.modalBody })
                }}
              >
                <div className="os">{dl.os}</div>
                <div className="fmt">{dl.fmt}</div>
                <div className="size">{dl.size}</div>
              </div>
            ))}
          </div>
          <div className="ep-app-card-actions">
            <button
              className="ep-btn ep-btn-secondary ep-btn-sm"
              onClick={() => onShowToast('リリースノートを確認中...', 'ok')}
            >
              リリースノート
            </button>
            <button
              className="ep-btn ep-btn-secondary ep-btn-sm"
              onClick={() => onShowToast('ビルド情報を取得中...', 'ok')}
            >
              ビルド情報
            </button>
          </div>
        </div>

        {/* Channel grid + toggles */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div className="ep-channel-grid">
            {CHANNELS.map((ch) => (
              <div
                key={ch.id}
                className={`ep-channel${ch.id === 'stable' ? ' active' : ''}`}
                onClick={() =>
                  onShowModal({ title: `${ch.label} チャンネル`, body: ch.modalBody })
                }
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ')
                    onShowModal({ title: `${ch.label} チャンネル`, body: ch.modalBody })
                }}
              >
                <div className="ep-channel-head">
                  <h4>{ch.label}</h4>
                  <span className={ch.pillClass}>
                    <span className="dot" />
                    {ch.label}
                  </span>
                </div>
                <div className="ver">{ch.ver}</div>
                <p>{ch.desc}</p>
                <div className="users">{ch.users}</div>
              </div>
            ))}
          </div>

          {/* Toggles */}
          <div className="ep-panel">
            <div className="ep-panel-head">
              <h3>配布設定</h3>
            </div>
            <div className="ep-panel-body">
              {TOGGLES.map((t) => (
                <div
                  key={t.id}
                  className="ep-opt-row"
                  style={{ cursor: 'pointer' }}
                  onClick={() => toggleSwitch(t.id)}
                >
                  <div className="lbl">
                    {t.label}
                    <small>{t.sub}</small>
                  </div>
                  <div
                    className={`ep-toggle${toggles[t.id] ? ' on' : ''}`}
                    role="switch"
                    aria-checked={toggles[t.id]}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        toggleSwitch(t.id)
                      }
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Deployment targets */}
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>展開対象</h3>
          <span className="meta">6 グループ</span>
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '8px',
            padding: '12px',
          }}
        >
          {DEPLOY_TARGETS.map((dt) => (
            <div
              key={dt.id}
              className="ep-target"
              onClick={() =>
                onShowModal({ title: dt.name, body: dt.modalBody })
              }
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ')
                  onShowModal({ title: dt.name, body: dt.modalBody })
              }}
            >
              <h5>
                {dt.name}
                <span
                  className={`ep-pill ${
                    dt.status === '完了'
                      ? 'ep-pill-ok'
                      : dt.status === '未開始'
                      ? 'ep-pill-muted'
                      : 'ep-pill-warn'
                  }`}
                >
                  {dt.status}
                </span>
              </h5>
              <div className="meta">{dt.meta}</div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '10.5px',
                  color: 'var(--muted)',
                  marginTop: '4px',
                }}
              >
                <span>{dt.count} 台</span>
                <span>{dt.progress}%</span>
              </div>
              <div className="ep-progress-mini">
                <div style={{ width: `${dt.progress}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* KPI stats */}
      <div className="ep-stat-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 0 }}>
        <div className="ep-stat">
          <div className="lbl">総展開台数</div>
          <div className="val">195</div>
          <div className="delta">/ 225 対象</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">展開率</div>
          <div className="val">86.7%</div>
          <div className="delta up">+3.2%</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">バージョン統一率</div>
          <div className="val">94.4%</div>
          <div className="delta up">v2.4.1</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">旧バージョン数</div>
          <div className="val">11</div>
          <div className="delta down">v2.3.x: 11台</div>
        </div>
      </div>

      {/* Release notes */}
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>リリースノート</h3>
          <div style={{ display: 'flex', gap: '4px' }}>
            {RN_FILTER_OPTIONS.map((f) => (
              <button
                key={f}
                className={`ep-filter-pill${rnFilter === f ? ' active' : ''}`}
                onClick={() => setRnFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        <div>
          {filteredRn.map((rn) => (
            <div
              key={rn.ver}
              className="ep-rn-item"
              style={{ cursor: 'pointer' }}
              onClick={() =>
                onShowModal({ title: `リリースノート ${rn.ver}`, body: rn.modalBody })
              }
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ')
                  onShowModal({ title: `リリースノート ${rn.ver}`, body: rn.modalBody })
              }}
            >
              <div className="ep-rn-meta">
                <div className="v">{rn.ver}</div>
                <div className="d">{rn.date}</div>
                <div style={{ marginTop: '4px' }}>
                  <span className={rnChannelPill[rn.channel]}>
                    <span className="dot" />
                    {rn.channel}
                  </span>
                </div>
              </div>
              <div className="ep-rn-body">
                <h5>{rn.summary}</h5>
                <ul>
                  {rn.items.map((item, i) => (
                    <li key={i}>
                      <span className={`ep-rn-tag ${item.tagClass}`}>{item.tag}</span>
                      <span>{item.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
