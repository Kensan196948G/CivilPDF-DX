import { useState, useCallback } from 'react'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

interface DashboardViewProps extends ViewProps {
  subView: 'overview' | 'stats' | 'dist' | 'users'
  period: number
  filter: string
}

// ======= Overview sub-view =======

interface ActivityItem {
  id: string
  type: 'run' | 'ok' | 'ng' | 'warn' | 'user' | 'app'
  line: string
  highlight: string
  time: string
}

interface RecentJob {
  id: string
  title: string
  project: string
  pages: number
  ngCount: number
  status: string
  time: string
}

const ACTIVITY_ITEMS: ActivityItem[] = [
  { id: 'a1', type: 'ok', line: 'が承認されました', highlight: '特記仕様書 R6-04rev2', time: '3分前' },
  { id: 'a2', type: 'ng', line: 'でNGを検出', highlight: '数量計算書 R6-04', time: '12分前' },
  { id: 'a3', type: 'run', line: 'の処理が完了', highlight: '県道○○号 詳細図', time: '28分前' },
  { id: 'a4', type: 'user', line: 'がログイン', highlight: '山田 直人', time: '1時間前' },
  { id: 'a5', type: 'app', line: 'が配布されました', highlight: 'v2.4.1 アップデート', time: '2時間前' },
]

const RECENT_JOBS: RecentJob[] = [
  { id: 'j1', title: '特記仕様書 R6-04rev2', project: '2024-038', pages: 42, ngCount: 0, status: '承認済', time: '3分前' },
  { id: 'j2', title: '数量計算書 R6-04', project: '2024-038', pages: 18, ngCount: 3, status: 'NGあり', time: '12分前' },
  { id: 'j3', title: '県道○○号 詳細図', project: '2024-038', pages: 8, ngCount: 2, status: '回覧中', time: '28分前' },
  { id: 'j4', title: '△△橋 詳細設計図', project: '2024-041', pages: 56, ngCount: 0, status: '承認済', time: '1時間前' },
  { id: 'j5', title: 'グリーンファイル一式', project: '2024-038', pages: 24, ngCount: 1, status: '差戻し', time: '2時間前' },
]

// ======= Stats sub-view =======

interface ProcessingTypeStat {
  type: string
  count: number
  max: number
  color: string
}

interface NgDetectionItem {
  rank: number
  category: string
  count: number
  rate: string
}

interface ProjectStat {
  id: string
  name: string
  total: number
  ok: number
  ng: number
  warn: number
}

const PROCESSING_TYPE_STATS: ProcessingTypeStat[] = [
  { type: 'OCR テキスト抽出', count: 1842, max: 2000, color: 'var(--accent)' },
  { type: '表データ抽出', count: 1124, max: 2000, color: 'var(--info)' },
  { type: '基準突合チェック', count: 968, max: 2000, color: 'var(--success)' },
]

const NG_DETECTION: NgDetectionItem[] = [
  { rank: 1, category: '縮尺表記の不一致', count: 142, rate: '11.1%' },
  { rank: 2, category: 'ファイル命名規則違反', count: 98, rate: '7.6%' },
  { rank: 3, category: 'PDF/A 非準拠', count: 76, rate: '5.9%' },
  { rank: 4, category: 'しおり構造エラー', count: 54, rate: '4.2%' },
  { rank: 5, category: 'メタデータ欠落', count: 32, rate: '2.5%' },
]

const PROJECT_STATS: ProjectStat[] = [
  { id: 'p1', name: '県道○○号線 道路改良工事 (2024-038)', total: 48, ok: 38, ng: 6, warn: 4 },
  { id: 'p2', name: '△△橋 詳細設計 (2024-041)', total: 32, ok: 30, ng: 1, warn: 1 },
  { id: 'p3', name: '××トンネル工事 (2024-052)', total: 18, ok: 14, ng: 3, warn: 1 },
  { id: 'p4', name: '下水道第3期工事 (2024-061)', total: 12, ok: 8, ng: 3, warn: 1 },
]

// ======= Distribution sub-view =======

interface AppVersion {
  version: string
  count: number
  total: number
  variant: 'stable' | 'beta' | 'danger'
}

interface SiteAdoption {
  site: string
  installed: number
  total: number
  rate: string
}

interface UpdateEvent {
  date: string
  version: string
  type: string
  count: number
}

const APP_VERSIONS: AppVersion[] = [
  { version: 'v2.4.1', count: 232, total: 248, variant: 'stable' },
  { version: 'v2.4.0', count: 12, total: 248, variant: 'beta' },
  { version: 'v2.2.x (旧版)', count: 4, total: 248, variant: 'danger' },
]

const SITE_ADOPTION: SiteAdoption[] = [
  { site: '本社', installed: 48, total: 48, rate: '100%' },
  { site: '現場事務所', installed: 124, total: 142, rate: '87.3%' },
  { site: '協力会社', installed: 58, total: 64, rate: '90.6%' },
  { site: 'iPad (現場)', installed: 22, total: 34, rate: '64.7%' },
]

const UPDATE_EVENTS: UpdateEvent[] = [
  { date: '2024-06-10', version: 'v2.4.1', type: 'stable', count: 224 },
  { date: '2024-06-05', version: 'v2.4.0', type: 'beta', count: 18 },
  { date: '2024-05-20', version: 'v2.3.2', type: 'stable', count: 248 },
]

// ======= Users sub-view =======

type RoleKey = 'all' | 'admin' | 'reviewer' | 'operator' | 'external'

interface RoleDistribution {
  role: string
  count: number
  max: number
  color: string
}

interface AuthStat {
  method: string
  count: number
  total: number
}

interface UserRow {
  id: string
  initials: string
  name: string
  email: string
  role: RoleKey
  roleLabel: string
  dept: string
  status: 'active' | 'inactive'
  lastLogin: string
}

const ROLE_DISTRIBUTIONS: RoleDistribution[] = [
  { role: '管理者 (admin)', count: 8, max: 200, color: 'var(--danger)' },
  { role: 'レビュアー (reviewer)', count: 34, max: 200, color: 'var(--accent)' },
  { role: 'オペレーター (operator)', count: 142, max: 200, color: 'var(--success)' },
  { role: '外部 (external)', count: 16, max: 200, color: 'var(--muted)' },
]

const AUTH_STATS: AuthStat[] = [
  { method: 'パスキー (FIDO2)', count: 164, total: 200 },
  { method: 'Authenticator App', count: 28, total: 200 },
  { method: 'SMS OTP', count: 8, total: 200 },
]

const USER_ROWS: UserRow[] = [
  { id: 'u1', initials: '山', name: '山田 直人', email: 'yamada@example.co.jp', role: 'admin', roleLabel: '管理者', dept: '工務部', status: 'active', lastLogin: '2024-06-12 10:32' },
  { id: 'u2', initials: '鈴', name: '鈴木 花子', email: 'suzuki@example.co.jp', role: 'reviewer', roleLabel: 'レビュアー', dept: '設計部', status: 'active', lastLogin: '2024-06-12 09:14' },
  { id: 'u3', initials: '田', name: '田中 太郎', email: 'tanaka@example.co.jp', role: 'operator', roleLabel: 'オペレーター', dept: '現場A', status: 'active', lastLogin: '2024-06-12 08:55' },
  { id: 'u4', initials: '佐', name: '佐藤 一郎', email: 'sato@example.co.jp', role: 'operator', roleLabel: 'オペレーター', dept: '現場B', status: 'active', lastLogin: '2024-06-11 17:20' },
  { id: 'u5', initials: '中', name: '中村 三郎', email: 'nakamura@example.co.jp', role: 'reviewer', roleLabel: 'レビュアー', dept: '品質管理部', status: 'active', lastLogin: '2024-06-11 15:44' },
  { id: 'u6', initials: '小', name: '小林 四郎', email: 'kobayashi@example.co.jp', role: 'operator', roleLabel: 'オペレーター', dept: '現場C', status: 'inactive', lastLogin: '2024-06-08 12:00' },
  { id: 'u7', initials: '加', name: '加藤 五郎', email: 'kato@example.co.jp', role: 'operator', roleLabel: 'オペレーター', dept: '現場A', status: 'active', lastLogin: '2024-06-12 07:30' },
  { id: 'u8', initials: '木', name: '木村 六郎', email: 'kimura@partner.co.jp', role: 'external', roleLabel: '外部', dept: '協力会社A', status: 'active', lastLogin: '2024-06-10 11:22' },
  { id: 'u9', initials: '林', name: '林 七子', email: 'hayashi@partner.co.jp', role: 'external', roleLabel: '外部', dept: '協力会社B', status: 'active', lastLogin: '2024-06-09 16:05' },
  { id: 'u10', initials: '清', name: '清水 八郎', email: 'shimizu@example.co.jp', role: 'admin', roleLabel: '管理者', dept: '情報システム部', status: 'active', lastLogin: '2024-06-12 10:58' },
]

const ROLE_FILTER_OPTIONS: { key: RoleKey; label: string }[] = [
  { key: 'all', label: 'すべて' },
  { key: 'admin', label: '管理者' },
  { key: 'reviewer', label: 'レビュアー' },
  { key: 'operator', label: 'オペレーター' },
  { key: 'external', label: '外部' },
]

// ======= Overview sub-component =======

function OverviewSubView({ onNavigate, onShowModal }: ViewProps) {
  const handleActivityClick = useCallback((item: ActivityItem) => {
    onShowModal({ title: item.highlight, body: `アクション: ${item.line}\n時刻: ${item.time}` })
  }, [onShowModal])

  const handleJobClick = useCallback((job: RecentJob) => {
    onShowModal({
      title: job.title,
      body: `工事番号: ${job.project}\nページ数: ${job.pages}\nNG件数: ${job.ngCount}\n状態: ${job.status}\n処理時刻: ${job.time}`,
    })
  }, [onShowModal])

  return (
    <div>
      {/* Stat grid */}
      <div className="ep-stat-grid">
        <div className="ep-stat">
          <div className="lbl">処理件数</div>
          <div className="val">1,284</div>
          <div className="delta up">↑ +38 (今週)</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">NG件数</div>
          <div className="val" style={{ color: 'var(--danger)' }}>248</div>
          <div className="delta down">↑ +12 (今週)</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">合格率</div>
          <div className="val" style={{ color: 'var(--success)' }}>97.3%</div>
          <div className="delta up">↑ +0.4pt</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">承認待ち</div>
          <div className="val" style={{ color: 'var(--warn-fg)' }}>14</div>
          <div className="delta">件 処理中</div>
        </div>
        <div className="ep-stat">
          <div className="lbl">稼働ユーザー</div>
          <div className="val">12</div>
          <div className="delta">/ 200 ユーザー</div>
        </div>
      </div>

      <div className="ep-dash-grid">
        {/* Main chart area */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="ep-panel">
            <div className="ep-panel-head">
              <h3>処理件数推移</h3>
              <span className="meta">過去30日</span>
            </div>
            <div className="ep-panel-body" style={{ height: '180px' }}>
              {/* SVG bar chart */}
              <svg width="100%" height="160" aria-label="処理件数推移グラフ">
                {[52, 68, 45, 78, 92, 61, 74, 88, 55, 72, 80, 65, 90, 45, 70, 58, 84, 96, 72, 60, 78, 55, 88, 72, 64, 91, 78, 82, 68, 75].map((v, i) => {
                  const barWidth = 11
                  const gap = 3
                  const x = i * (barWidth + gap) + 2
                  const maxVal = 100
                  const barH = Math.round((v / maxVal) * 140)
                  const y = 148 - barH
                  const isLast5 = i >= 25
                  return (
                    <rect
                      key={i}
                      x={x}
                      y={y}
                      width={barWidth}
                      height={barH}
                      rx={2}
                      fill={isLast5 ? 'var(--accent)' : 'var(--border)'}
                      opacity={isLast5 ? 0.85 : 0.6}
                    />
                  )
                })}
                {/* Axis */}
                <line x1="0" y1="148" x2="100%" y2="148" stroke="var(--border)" strokeWidth="1" />
              </svg>
            </div>
          </div>

          {/* Recent jobs table */}
          <div className="ep-panel" style={{ overflow: 'hidden' }}>
            <div className="ep-panel-head">
              <h3>最近の処理ジョブ</h3>
              <button
                className="ep-btn ep-btn-secondary ep-btn-sm"
                type="button"
                onClick={() => onNavigate('documents')}
              >
                すべて表示
              </button>
            </div>
            <table className="ep-tbl">
              <thead>
                <tr>
                  <th>ドキュメント</th>
                  <th>工事</th>
                  <th className="num">ページ</th>
                  <th className="num">NG</th>
                  <th>状態</th>
                  <th>時刻</th>
                </tr>
              </thead>
              <tbody>
                {RECENT_JOBS.map((job) => (
                  <tr
                    key={job.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleJobClick(job)}
                  >
                    <td style={{ fontWeight: 500 }}>{job.title}</td>
                    <td className="id">{job.project}</td>
                    <td className="num">{job.pages}</td>
                    <td className={`ng-count${job.ngCount === 0 ? ' zero' : ''} num`}>{job.ngCount}</td>
                    <td>
                      <span className={
                        job.status === '承認済' ? 'ep-pill ep-pill-ok' :
                        job.status === 'NGあり' ? 'ep-pill ep-pill-ng' :
                        job.status === '回覧中' ? 'ep-pill ep-pill-info-2' :
                        job.status === '差戻し' ? 'ep-pill ep-pill-warn' :
                        'ep-pill ep-pill-muted'
                      }>
                        {job.status}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--muted)' }}>
                      {job.time}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Activity feed */}
        <div className="ep-panel" style={{ overflow: 'hidden' }}>
          <div className="ep-panel-head">
            <h3>アクティビティ</h3>
            <span className="meta">リアルタイム</span>
          </div>
          <div className="ep-activity-list">
            {ACTIVITY_ITEMS.map((item) => (
              <div
                key={item.id}
                className="ep-act-item"
                style={{ cursor: 'pointer' }}
                onClick={() => handleActivityClick(item)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter') handleActivityClick(item) }}
              >
                <div className={`ep-act-ic ${item.type}`} aria-hidden="true">
                  {item.type === 'ok' ? '✓' : item.type === 'ng' ? '✕' : item.type === 'run' ? '▶' : item.type === 'warn' ? '!' : item.type === 'user' ? 'U' : 'A'}
                </div>
                <div>
                  <div className="ep-act-line">
                    <strong>{item.highlight}</strong>{item.line}
                  </div>
                  <div className="ep-act-time">{item.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ======= Stats sub-component =======

function StatsSubView({ filter }: { filter: string }) {
  const [projectFilter, setProjectFilter] = useState<string>('all')

  const filteredProjects = projectFilter === 'all'
    ? PROJECT_STATS
    : PROJECT_STATS.filter((p) => {
        if (filter === 'ok') return p.ng === 0
        if (filter === 'ng') return p.ng > 0
        return true
      })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Processing type breakdown */}
      <div className="ep-panel">
        <div className="ep-panel-head">
          <h3>処理タイプ別統計</h3>
          <span className="meta">累計</span>
        </div>
        <div className="ep-panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {PROCESSING_TYPE_STATS.map((stat) => (
            <div key={stat.type}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '12.5px' }}>
                <span style={{ color: 'var(--fg-2)' }}>{stat.type}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--fg)' }}>{stat.count.toLocaleString()}</span>
              </div>
              <div className="ep-progress done" style={{ height: '6px' }}>
                <div style={{ width: `${(stat.count / stat.max) * 100}%`, background: stat.color }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        {/* NG detection top 5 */}
        <div className="ep-panel" style={{ overflow: 'hidden' }}>
          <div className="ep-panel-head">
            <h3>NG検出 Top 5</h3>
            <span className="meta">全期間</span>
          </div>
          <table className="ep-tbl">
            <thead>
              <tr>
                <th>#</th>
                <th>カテゴリー</th>
                <th className="num">件数</th>
                <th className="num">比率</th>
              </tr>
            </thead>
            <tbody>
              {NG_DETECTION.map((item) => (
                <tr key={item.rank}>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--muted)', fontSize: '11px' }}>
                    {item.rank}
                  </td>
                  <td style={{ fontSize: '12px' }}>{item.category}</td>
                  <td className="ng-count num">{item.count}</td>
                  <td className="num" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--muted)' }}>
                    {item.rate}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Project processing table */}
        <div className="ep-panel" style={{ overflow: 'hidden' }}>
          <div className="ep-panel-head">
            <h3>工事別処理件数</h3>
            <div style={{ display: 'flex', gap: '4px' }}>
              {['all', 'ok', 'ng'].map((f) => (
                <button
                  key={f}
                  className={`ep-filter-pill${projectFilter === f ? ' active' : ''}`}
                  type="button"
                  onClick={() => setProjectFilter(f)}
                >
                  {f === 'all' ? 'すべて' : f === 'ok' ? '正常' : 'NG'}
                </button>
              ))}
            </div>
          </div>
          <table className="ep-tbl">
            <thead>
              <tr>
                <th>工事</th>
                <th className="num">合計</th>
                <th className="num">OK</th>
                <th className="num">NG</th>
                <th className="num">警告</th>
              </tr>
            </thead>
            <tbody>
              {filteredProjects.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontSize: '11.5px' }}>{p.name}</td>
                  <td className="num">{p.total}</td>
                  <td className="num" style={{ color: 'var(--success)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{p.ok}</td>
                  <td className={`ng-count${p.ng === 0 ? ' zero' : ''} num`}>{p.ng}</td>
                  <td className="num" style={{ color: 'var(--warn-fg)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{p.warn}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ======= Distribution sub-component =======

function DistSubView() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        {/* Version distribution */}
        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>バージョン分布</h3>
            <span className="meta">248 インストール済み</span>
          </div>
          <div className="ep-panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {APP_VERSIONS.map((v) => (
              <div key={v.version}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '12.5px' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontWeight: 500 }}>{v.version}</span>
                    <span className={
                      v.variant === 'stable' ? 'ep-pill ep-pill-ok' :
                      v.variant === 'beta' ? 'ep-pill ep-pill-warn' :
                      'ep-pill ep-pill-ng'
                    }>
                      {v.variant === 'stable' ? '最新' : v.variant === 'beta' ? 'beta' : '旧版'}
                    </span>
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: v.variant === 'danger' ? 'var(--danger)' : 'var(--fg)' }}>
                    {v.count}
                  </span>
                </div>
                <div className="ep-progress done" style={{ height: '6px' }}>
                  <div
                    style={{
                      width: `${(v.count / v.total) * 100}%`,
                      background: v.variant === 'stable' ? 'var(--success)' : v.variant === 'beta' ? 'var(--warn)' : 'var(--danger)',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Site adoption */}
        <div className="ep-panel" style={{ overflow: 'hidden' }}>
          <div className="ep-panel-head">
            <h3>拠点別導入状況</h3>
          </div>
          <table className="ep-tbl">
            <thead>
              <tr>
                <th>拠点</th>
                <th className="num">導入</th>
                <th className="num">合計</th>
                <th className="num">率</th>
              </tr>
            </thead>
            <tbody>
              {SITE_ADOPTION.map((s) => (
                <tr key={s.site}>
                  <td>{s.site}</td>
                  <td className="num">{s.installed}</td>
                  <td className="num" style={{ color: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{s.total}</td>
                  <td className="num">
                    <span className={parseFloat(s.rate) >= 90 ? 'ep-pill ep-pill-ok' : parseFloat(s.rate) >= 70 ? 'ep-pill ep-pill-warn' : 'ep-pill ep-pill-ng'}>
                      {s.rate}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Update event history */}
      <div className="ep-panel" style={{ overflow: 'hidden' }}>
        <div className="ep-panel-head">
          <h3>更新イベント履歴</h3>
        </div>
        <table className="ep-tbl">
          <thead>
            <tr>
              <th>日付</th>
              <th>バージョン</th>
              <th>チャンネル</th>
              <th className="num">配布数</th>
            </tr>
          </thead>
          <tbody>
            {UPDATE_EVENTS.map((ev, i) => (
              <tr key={i}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--muted)' }}>
                  {ev.date}
                </td>
                <td style={{ fontWeight: 500 }}>{ev.version}</td>
                <td>
                  <span className={ev.type === 'stable' ? 'ep-pill ep-pill-stable' : 'ep-pill ep-pill-beta'}>
                    {ev.type}
                  </span>
                </td>
                <td className="num">{ev.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ======= Users sub-component =======

function UsersSubView({ onShowModal }: Pick<ViewProps, 'onShowModal'>) {
  const [roleFilter, setRoleFilter] = useState<RoleKey>('all')

  const filteredUsers = roleFilter === 'all'
    ? USER_ROWS
    : USER_ROWS.filter((u) => u.role === roleFilter)

  const handleUserClick = useCallback((user: UserRow) => {
    onShowModal({
      title: user.name,
      body: `メールアドレス: ${user.email}\nロール: ${user.roleLabel}\n所属: ${user.dept}\n状態: ${user.status === 'active' ? '有効' : '無効'}\n最終ログイン: ${user.lastLogin}`,
    })
  }, [onShowModal])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        {/* Role distribution */}
        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>ロール分布</h3>
            <span className="meta">200 ユーザー</span>
          </div>
          <div className="ep-panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {ROLE_DISTRIBUTIONS.map((r) => (
              <div key={r.role}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '12.5px' }}>
                  <span style={{ color: 'var(--fg-2)' }}>{r.role}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--fg)' }}>{r.count}</span>
                </div>
                <div className="ep-progress done" style={{ height: '5px' }}>
                  <div style={{ width: `${(r.count / r.max) * 100}%`, background: r.color }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Auth stats */}
        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>認証方法</h3>
            <span className="meta">200 ユーザー</span>
          </div>
          <div className="ep-panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {AUTH_STATS.map((a) => (
              <div key={a.method}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '12.5px' }}>
                  <span style={{ color: 'var(--fg-2)' }}>{a.method}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--fg)' }}>
                    {a.count} <span style={{ color: 'var(--muted)', fontSize: '10px' }}>/ {a.total}</span>
                  </span>
                </div>
                <div className="ep-progress done" style={{ height: '5px' }}>
                  <div style={{ width: `${(a.count / a.total) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* User table */}
      <div className="ep-panel" style={{ overflow: 'hidden' }}>
        <div className="ep-panel-head">
          <h3>ユーザー一覧</h3>
          <div style={{ display: 'flex', gap: '4px' }}>
            {ROLE_FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                className={`ep-filter-pill${roleFilter === opt.key ? ' active' : ''}`}
                type="button"
                onClick={() => setRoleFilter(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <table className="ep-tbl">
          <thead>
            <tr>
              <th>ユーザー</th>
              <th>メールアドレス</th>
              <th>ロール</th>
              <th>所属</th>
              <th>状態</th>
              <th>最終ログイン</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr
                key={user.id}
                style={{ cursor: 'pointer' }}
                onClick={() => handleUserClick(user)}
              >
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '26px', height: '26px', borderRadius: '50%', background: 'var(--fg)', color: 'var(--bg)', display: 'grid', placeItems: 'center', fontSize: '10.5px', fontWeight: 600, flexShrink: 0 }}>
                      {user.initials}
                    </div>
                    <span style={{ fontWeight: 500 }}>{user.name}</span>
                  </div>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11.5px', color: 'var(--muted)' }}>
                  {user.email}
                </td>
                <td>
                  <span className={
                    user.role === 'admin' ? 'ep-pill ep-pill-ng' :
                    user.role === 'reviewer' ? 'ep-pill ep-pill-info' :
                    user.role === 'external' ? 'ep-pill ep-pill-muted' :
                    'ep-pill ep-pill-ok'
                  }>
                    {user.roleLabel}
                  </span>
                </td>
                <td style={{ fontSize: '12.5px', color: 'var(--fg-2)' }}>{user.dept}</td>
                <td>
                  <span className={user.status === 'active' ? 'ep-pill ep-pill-ok' : 'ep-pill ep-pill-muted'}>
                    {user.status === 'active' ? '有効' : '無効'}
                  </span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--muted)' }}>
                  {user.lastLogin}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ======= Main DashboardView =======

export function DashboardView({ subView, period, filter, onNavigate, onShowModal, onShowToast }: DashboardViewProps) {
  const viewProps: ViewProps = { onNavigate, onShowModal, onShowToast }

  return (
    <div>
      {subView === 'overview' && (
        <OverviewSubView {...viewProps} />
      )}
      {subView === 'stats' && (
        <StatsSubView filter={filter} />
      )}
      {subView === 'dist' && (
        <DistSubView />
      )}
      {subView === 'users' && (
        <UsersSubView onShowModal={onShowModal} />
      )}
      {/* Period indicator — visible in all sub-views */}
      <div style={{ marginTop: '12px', fontSize: '11px', color: 'var(--muted)', fontFamily: 'var(--font-mono)', textAlign: 'right' }}>
        表示期間: 過去 {period} 日間 · フィルター: {filter === 'all' ? 'すべて' : filter === 'ok' ? '正常のみ' : 'NGのみ'}
      </div>
    </div>
  )
}
