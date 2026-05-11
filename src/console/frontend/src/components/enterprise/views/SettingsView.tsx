import { type FC, useState, useEffect } from 'react'
import { listUsers, createUser, updateUser, deleteUser, type UserResponse } from '../../../api/users'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

type SettingsSection =
  | 'general'
  | 'users'
  | 'security'
  | 'notifications'
  | 'integrations'
  | 'storage'
  | 'audit'
  | 'license'

const SECTIONS: { id: SettingsSection; label: string; icon: string }[] = [
  { id: 'general', label: '一般設定', icon: '⚙️' },
  { id: 'users', label: 'ユーザー管理', icon: '👥' },
  { id: 'security', label: 'セキュリティポリシー', icon: '🔒' },
  { id: 'notifications', label: '通知設定', icon: '🔔' },
  { id: 'integrations', label: '外部連携', icon: '🔗' },
  { id: 'storage', label: 'ストレージ', icon: '💾' },
  { id: 'audit', label: '監査設定', icon: '📋' },
  { id: 'license', label: 'ライセンス', icon: '🪪' },
]

/* ── Types ───────────────────────────────────────────────────── */
type UserRole = 'admin' | 'manager' | 'engineer' | 'viewer'
type UserStatus = 'active' | 'inactive' | 'suspended'
type AuthMethod = 'password' | 'm365'

interface UserRecord {
  id: string
  displayName: string
  email: string
  role: UserRole
  status: UserStatus
  authMethod: AuthMethod
  lastLogin: string | null
  createdAt: string
}

const ROLE_LABELS: Record<UserRole, string> = {
  admin: '管理者',
  manager: 'マネージャー',
  engineer: '技術担当',
  viewer: '閲覧のみ',
}

const ROLE_COLORS: Record<UserRole, string> = {
  admin: 'oklch(55% 0.2 270)',
  manager: 'oklch(55% 0.18 145)',
  engineer: 'oklch(55% 0.2 200)',
  viewer: 'oklch(55% 0.05 260)',
}

const STATUS_LABELS: Record<UserStatus, string> = {
  active: '有効',
  inactive: '無効',
  suspended: '停止中',
}

/* ── Mock user data ──────────────────────────────────────────── */
let _userSeq = 100
const INITIAL_USERS: UserRecord[] = [
  { id: 'u1', displayName: '田中 太郎', email: 'tanaka@civilpdf.example.com', role: 'admin', status: 'active', authMethod: 'password', lastLogin: '2026-05-11 09:12', createdAt: '2025-10-01' },
  { id: 'u2', displayName: '山田 花子', email: 'yamada@civilpdf.example.com', role: 'manager', status: 'active', authMethod: 'm365', lastLogin: '2026-05-11 08:45', createdAt: '2025-10-15' },
  { id: 'u3', displayName: '鈴木 一郎', email: 'suzuki@civilpdf.example.com', role: 'engineer', status: 'active', authMethod: 'm365', lastLogin: '2026-05-10 17:30', createdAt: '2025-11-01' },
  { id: 'u4', displayName: '佐藤 二郎', email: 'sato@civilpdf.example.com', role: 'engineer', status: 'active', authMethod: 'password', lastLogin: '2026-05-09 14:20', createdAt: '2025-11-10' },
  { id: 'u5', displayName: '高橋 美咲', email: 'takahashi@civilpdf.example.com', role: 'viewer', status: 'inactive', authMethod: 'm365', lastLogin: '2026-04-28 10:00', createdAt: '2025-12-01' },
  { id: 'u6', displayName: '中村 健', email: 'nakamura@civilpdf.example.com', role: 'engineer', status: 'suspended', authMethod: 'password', lastLogin: '2026-03-15 16:00', createdAt: '2026-01-05' },
  { id: 'u7', displayName: '伊藤 さくら', email: 'ito@civilpdf.example.com', role: 'manager', status: 'active', authMethod: 'm365', lastLogin: '2026-05-11 07:55', createdAt: '2026-02-01' },
  { id: 'u8', displayName: '渡辺 拓也', email: 'watanabe@civilpdf.example.com', role: 'viewer', status: 'active', authMethod: 'password', lastLogin: '2026-05-08 13:10', createdAt: '2026-03-01' },
]

/* ── UserModal ───────────────────────────────────────────────── */
interface UserModalProps {
  user: Partial<UserRecord> | null
  onSave: (data: Omit<UserRecord, 'id' | 'createdAt' | 'lastLogin'>) => void
  onClose: () => void
}

function UserModal({ user, onSave, onClose }: UserModalProps) {
  const isEdit = !!user?.id
  const [displayName, setDisplayName] = useState(user?.displayName ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [role, setRole] = useState<UserRole>(user?.role ?? 'viewer')
  const [status, setStatus] = useState<UserStatus>(user?.status ?? 'active')
  const [authMethod, setAuthMethod] = useState<AuthMethod>(user?.authMethod ?? 'password')
  const [nameErr, setNameErr] = useState('')
  const [emailErr, setEmailErr] = useState('')

  function validate(): boolean {
    let ok = true
    if (!displayName.trim()) { setNameErr('氏名を入力してください'); ok = false } else setNameErr('')
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setEmailErr('有効なメールアドレスを入力してください'); ok = false } else setEmailErr('')
    return ok
  }

  function handleSave() {
    if (!validate()) return
    onSave({ displayName: displayName.trim(), email: email.trim(), role, status, authMethod })
  }

  return (
    <div className="ep-modal-backdrop" onClick={onClose}>
      <div className="ep-modal" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
        <div className="ep-modal-header">
          <h2 className="ep-modal-title">{isEdit ? 'ユーザー編集' : '新規ユーザー追加'}</h2>
          <button className="ep-modal-close" onClick={onClose}>✕</button>
        </div>

        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Avatar preview */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="ep-user-avatar" style={{ width: '48px', height: '48px', fontSize: '18px', borderRadius: '12px' }}>
              {displayName ? displayName.slice(0, 1) : '?'}
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600 }}>{displayName || '（未入力）'}</div>
              <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>{email || '—'}</div>
            </div>
          </div>

          <div className="ep-settings-group" style={{ marginBottom: 0 }}>
            <label className="ep-settings-label">氏名 *</label>
            <input
              className="ep-settings-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="田中 太郎"
            />
            {nameErr && <span style={{ color: 'var(--danger, #ef4444)', fontSize: '11px' }}>{nameErr}</span>}
          </div>

          <div className="ep-settings-group" style={{ marginBottom: 0 }}>
            <label className="ep-settings-label">メールアドレス *</label>
            <input
              className="ep-settings-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              disabled={isEdit}
              style={isEdit ? { opacity: 0.6, cursor: 'not-allowed' } : undefined}
            />
            {emailErr && <span style={{ color: 'var(--danger, #ef4444)', fontSize: '11px' }}>{emailErr}</span>}
            {isEdit && <span className="ep-settings-hint">メールアドレスは変更できません。</span>}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div className="ep-settings-group" style={{ marginBottom: 0 }}>
              <label className="ep-settings-label">ロール</label>
              <select
                className="ep-settings-select"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                {(Object.keys(ROLE_LABELS) as UserRole[]).map((r) => (
                  <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                ))}
              </select>
            </div>

            <div className="ep-settings-group" style={{ marginBottom: 0 }}>
              <label className="ep-settings-label">ステータス</label>
              <select
                className="ep-settings-select"
                value={status}
                onChange={(e) => setStatus(e.target.value as UserStatus)}
              >
                {(Object.keys(STATUS_LABELS) as UserStatus[]).map((s) => (
                  <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="ep-settings-group" style={{ marginBottom: 0 }}>
            <label className="ep-settings-label">認証方式</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              {(['password', 'm365'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setAuthMethod(m)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    border: `1.5px solid ${authMethod === m ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: '6px',
                    background: authMethod === m ? 'var(--accent-soft)' : 'var(--surface)',
                    color: authMethod === m ? 'var(--accent)' : 'var(--fg-2)',
                    fontSize: '12px',
                    fontWeight: authMethod === m ? 600 : 400,
                    cursor: 'pointer',
                    transition: 'all .12s',
                  }}
                >
                  {m === 'password' ? '🔑 パスワード' : '☁️ Microsoft 365'}
                </button>
              ))}
            </div>
            {authMethod === 'm365' && (
              <span className="ep-settings-hint">
                M365 メールアドレスでの非対話式認証。ロールはこのシステムで決定されます。
              </span>
            )}
          </div>
        </div>

        <div className="ep-modal-footer">
          <button className="ep-btn ep-btn-secondary" onClick={onClose}>キャンセル</button>
          <button className="ep-btn ep-btn-primary" onClick={handleSave}>
            {isEdit ? '更新' : 'ユーザーを追加'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── DeleteConfirm ───────────────────────────────────────────── */
interface DeleteConfirmProps {
  user: UserRecord
  onConfirm: () => void
  onClose: () => void
}

function DeleteConfirm({ user, onConfirm, onClose }: DeleteConfirmProps) {
  return (
    <div className="ep-modal-backdrop" onClick={onClose}>
      <div className="ep-modal" style={{ maxWidth: '400px' }} onClick={(e) => e.stopPropagation()}>
        <div className="ep-modal-header">
          <h2 className="ep-modal-title">ユーザーを削除</h2>
          <button className="ep-modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="ep-modal-body">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <div className="ep-user-avatar">{user.displayName.slice(0, 1)}</div>
            <div>
              <div style={{ fontWeight: 600 }}>{user.displayName}</div>
              <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{user.email}</div>
            </div>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--fg-2)' }}>
            このユーザーを削除しますか？この操作は取り消せません。
            削除後はログインできなくなります。
          </p>
        </div>
        <div className="ep-modal-footer">
          <button className="ep-btn ep-btn-secondary" onClick={onClose}>キャンセル</button>
          <button
            className="ep-btn"
            style={{ background: 'var(--danger, #ef4444)', color: '#fff' }}
            onClick={onConfirm}
          >
            削除する
          </button>
        </div>
      </div>
    </div>
  )
}

function mapApiUser(u: UserResponse): UserRecord {
  return {
    id: u.id,
    displayName: u.full_name,
    email: u.email,
    role: u.role,
    status: u.status,
    authMethod: 'password',
    lastLogin: u.last_login ? u.last_login.replace('T', ' ').slice(0, 16) : null,
    createdAt: u.created_at.slice(0, 10),
  }
}

/* ── UsersSection ────────────────────────────────────────────── */
function UsersSection({ onShowToast }: Pick<ViewProps, 'onShowToast'>) {
  const [users, setUsers] = useState<UserRecord[]>(INITIAL_USERS)
  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState<UserRole | 'all'>('all')
  const [editTarget, setEditTarget] = useState<UserRecord | null | 'new'>(null)
  const [deleteTarget, setDeleteTarget] = useState<UserRecord | null>(null)

  useEffect(() => {
    listUsers()
      .then((data) => { setUsers(data.map(mapApiUser)) })
      .catch(() => { /* fallback to static INITIAL_USERS */ })
  }, [])

  const filtered = users.filter((u) => {
    const matchQuery =
      !searchQuery ||
      u.displayName.includes(searchQuery) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchRole = roleFilter === 'all' || u.role === roleFilter
    return matchQuery && matchRole
  })

  function handleSave(data: Omit<UserRecord, 'id' | 'createdAt' | 'lastLogin'>) {
    if (editTarget === 'new') {
      const username = data.email.split('@')[0]
      createUser({
        email: data.email,
        username,
        full_name: data.displayName,
        password: 'TempPass123!',
        role: data.role,
      })
        .then((created) => {
          setUsers((prev) => [mapApiUser(created), ...prev])
          onShowToast(`${data.displayName} を追加しました`, 'ok')
        })
        .catch(() => {
          const newUser: UserRecord = {
            ...data,
            id: `u${++_userSeq}`,
            createdAt: new Date().toISOString().slice(0, 10),
            lastLogin: null,
          }
          setUsers((prev) => [newUser, ...prev])
          onShowToast(`${data.displayName} を追加しました（オフライン）`, 'warn')
        })
    } else if (editTarget) {
      updateUser(editTarget.id, { full_name: data.displayName, role: data.role, status: data.status })
        .then((updated) => {
          setUsers((prev) => prev.map((u) => u.id === editTarget.id ? mapApiUser(updated) : u))
          onShowToast(`${data.displayName} の情報を更新しました`, 'ok')
        })
        .catch(() => {
          setUsers((prev) => prev.map((u) => u.id === editTarget.id ? { ...u, ...data } : u))
          onShowToast(`${data.displayName} の情報を更新しました（オフライン）`, 'warn')
        })
    }
    setEditTarget(null)
  }

  function handleDelete() {
    if (!deleteTarget) return
    const target = deleteTarget
    deleteUser(target.id)
      .then(() => {
        setUsers((prev) => prev.filter((u) => u.id !== target.id))
        onShowToast(`${target.displayName} を削除しました`, 'warn')
      })
      .catch(() => {
        setUsers((prev) => prev.filter((u) => u.id !== target.id))
        onShowToast(`${target.displayName} を削除しました（オフライン）`, 'warn')
      })
    setDeleteTarget(null)
  }

  const activeCnt = users.filter((u) => u.status === 'active').length
  const m365Cnt = users.filter((u) => u.authMethod === 'm365').length

  return (
    <>
      <div className="ep-settings-content">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '4px' }}>
          <div>
            <h2>ユーザー管理</h2>
            <p className="ep-settings-desc">
              全 {users.length} ユーザー（有効 {activeCnt} / M365認証 {m365Cnt}）
            </p>
          </div>
          <button
            className="ep-btn ep-btn-primary"
            style={{ marginTop: '4px', flexShrink: 0 }}
            onClick={() => setEditTarget('new')}
          >
            + 新規ユーザー
          </button>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
          <input
            className="ep-settings-input"
            style={{ flex: '1', minWidth: '160px' }}
            placeholder="名前・メールで検索…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <select
            className="ep-settings-select"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value as UserRole | 'all')}
          >
            <option value="all">全ロール</option>
            {(Object.keys(ROLE_LABELS) as UserRole[]).map((r) => (
              <option key={r} value={r}>{ROLE_LABELS[r]}</option>
            ))}
          </select>
        </div>

        {/* User table */}
        <div style={{ border: '1px solid var(--border)', borderRadius: '8px', overflow: 'hidden' }}>
          <table className="ep-user-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }} />
                <th>氏名</th>
                <th>メールアドレス</th>
                <th>ロール</th>
                <th>認証</th>
                <th>ステータス</th>
                <th>最終ログイン</th>
                <th style={{ width: '72px' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '12px', padding: '24px' }}>
                    該当するユーザーが見つかりません
                  </td>
                </tr>
              ) : (
                filtered.map((u) => (
                  <tr key={u.id} className={u.status !== 'active' ? 'ep-user-row-inactive' : ''}>
                    <td>
                      <div className="ep-user-avatar">{u.displayName.slice(0, 1)}</div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 500, fontSize: '13px' }}>{u.displayName}</div>
                      <div style={{ fontSize: '10px', color: 'var(--muted)' }}>登録: {u.createdAt}</div>
                    </td>
                    <td style={{ fontSize: '12px', fontFamily: 'var(--font-mono)' }}>{u.email}</td>
                    <td>
                      <span
                        className="ep-user-role-badge"
                        style={{ background: ROLE_COLORS[u.role] + '22', color: ROLE_COLORS[u.role], borderColor: ROLE_COLORS[u.role] + '55' }}
                      >
                        {ROLE_LABELS[u.role]}
                      </span>
                    </td>
                    <td>
                      {u.authMethod === 'm365' ? (
                        <span className="ep-user-auth-badge ep-user-auth-m365">M365</span>
                      ) : (
                        <span className="ep-user-auth-badge ep-user-auth-pw">PW</span>
                      )}
                    </td>
                    <td>
                      <span className={`ep-user-status ep-user-status-${u.status}`}>
                        {STATUS_LABELS[u.status]}
                      </span>
                    </td>
                    <td style={{ fontSize: '11px', color: 'var(--muted)' }}>
                      {u.lastLogin ?? '未ログイン'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                        <button
                          className="ep-user-icon-btn"
                          title="編集"
                          onClick={() => setEditTarget(u)}
                        >
                          ✏️
                        </button>
                        <button
                          className="ep-user-icon-btn ep-user-icon-delete"
                          title="削除"
                          onClick={() => setDeleteTarget(u)}
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      {editTarget !== null && (
        <UserModal
          user={editTarget === 'new' ? {} : editTarget}
          onSave={handleSave}
          onClose={() => setEditTarget(null)}
        />
      )}
      {deleteTarget && (
        <DeleteConfirm
          user={deleteTarget}
          onConfirm={handleDelete}
          onClose={() => setDeleteTarget(null)}
        />
      )}
    </>
  )
}

/* ── General ─────────────────────────────────────────────────── */
function GeneralSection({ onShowToast }: Pick<ViewProps, 'onShowToast'>) {
  const [siteName, setSiteName] = useState('CivilPDF-DX 本社')
  const [lang, setLang] = useState('ja')
  const [tz, setTz] = useState('Asia/Tokyo')
  const [dateFormat, setDateFormat] = useState('YYYY/MM/DD')
  const [sessionTimeout, setSessionTimeout] = useState(60)

  return (
    <div className="ep-settings-content">
      <h2>一般設定</h2>
      <p className="ep-settings-desc">組織・表示・セッションに関する基本設定です。</p>

      <div className="ep-settings-group">
        <label className="ep-settings-label">サイト名称</label>
        <input className="ep-settings-input" value={siteName} onChange={(e) => setSiteName(e.target.value)} />
        <span className="ep-settings-hint">ヘッダーおよびメール件名に表示されます。</span>
      </div>

      <div className="ep-settings-group">
        <label className="ep-settings-label">表示言語</label>
        <select className="ep-settings-select" value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="ja">日本語</option>
          <option value="en">English</option>
        </select>
      </div>

      <div className="ep-settings-row2">
        <div className="ep-settings-group">
          <label className="ep-settings-label">タイムゾーン</label>
          <select className="ep-settings-select" value={tz} onChange={(e) => setTz(e.target.value)}>
            <option value="Asia/Tokyo">Asia/Tokyo (JST+9)</option>
            <option value="UTC">UTC</option>
          </select>
        </div>
        <div className="ep-settings-group">
          <label className="ep-settings-label">日付フォーマット</label>
          <select className="ep-settings-select" value={dateFormat} onChange={(e) => setDateFormat(e.target.value)}>
            <option value="YYYY/MM/DD">YYYY/MM/DD</option>
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="MM-DD-YYYY">MM-DD-YYYY</option>
          </select>
        </div>
      </div>

      <div className="ep-settings-group">
        <label className="ep-settings-label">セッションタイムアウト（分）</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input type="range" min={15} max={480} step={15} value={sessionTimeout}
            onChange={(e) => setSessionTimeout(Number(e.target.value))} className="ep-slider" style={{ flex: 1 }} />
          <span style={{ minWidth: '48px', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{sessionTimeout}分</span>
        </div>
      </div>

      <div className="ep-settings-footer">
        <button className="ep-btn ep-btn-primary" onClick={() => onShowToast('一般設定を保存しました', 'ok')}>保存</button>
      </div>
    </div>
  )
}

/* ── Security ────────────────────────────────────────────────── */
function SecuritySection({ onShowToast }: Pick<ViewProps, 'onShowToast'>) {
  const [ipWhitelist, setIpWhitelist] = useState('192.168.1.0/24\n10.0.0.0/8')
  const [dlpEnabled, setDlpEnabled] = useState(true)
  const [watermark, setWatermark] = useState(true)
  const [watermarkText, setWatermarkText] = useState('{user} {date}')
  const [encryptAtRest, setEncryptAtRest] = useState(true)
  const [loginAttempts, setLoginAttempts] = useState(5)

  return (
    <div className="ep-settings-content">
      <h2>セキュリティポリシー</h2>
      <p className="ep-settings-desc">アクセス制御・DLP・暗号化ポリシーを設定します。</p>

      <div className="ep-settings-group">
        <label className="ep-settings-label">IP ホワイトリスト（CIDR、1行1エントリ）</label>
        <textarea className="ep-settings-textarea" value={ipWhitelist} onChange={(e) => setIpWhitelist(e.target.value)} rows={4} />
        <span className="ep-settings-hint">空白の場合は全 IP を許可します。</span>
      </div>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">DLP（データ損失防止）</div>
          <div className="ep-settings-hint">機密キーワードを含むファイルのダウンロードをブロックします。</div>
        </div>
        <button className={`ep-toggle${dlpEnabled ? ' on' : ''}`} onClick={() => setDlpEnabled((v) => !v)} />
      </div>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">透かし（ウォーターマーク）</div>
          <div className="ep-settings-hint">PDF ダウンロード時に透かしを自動付与します。</div>
        </div>
        <button className={`ep-toggle${watermark ? ' on' : ''}`} onClick={() => setWatermark((v) => !v)} />
      </div>

      {watermark && (
        <div className="ep-settings-group" style={{ marginLeft: '16px' }}>
          <label className="ep-settings-label">透かしテキストテンプレート</label>
          <input className="ep-settings-input" value={watermarkText} onChange={(e) => setWatermarkText(e.target.value)} />
          <span className="ep-settings-hint">使用可能変数: {'{user}'} {'{date}'} {'{ip}'} {'{org}'}</span>
        </div>
      )}

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">保存時暗号化（AES-256）</div>
          <div className="ep-settings-hint">ストレージ上の全ファイルを暗号化します。</div>
        </div>
        <button className={`ep-toggle${encryptAtRest ? ' on' : ''}`} onClick={() => setEncryptAtRest((v) => !v)} />
      </div>

      <div className="ep-settings-group">
        <label className="ep-settings-label">ログイン失敗ロックアウト（回数）</label>
        <input type="number" className="ep-settings-input" value={loginAttempts}
          onChange={(e) => setLoginAttempts(Number(e.target.value))} min={3} max={20} style={{ width: '100px' }} />
      </div>

      <div className="ep-settings-footer">
        <button className="ep-btn ep-btn-primary" onClick={() => onShowToast('セキュリティポリシーを保存しました', 'ok')}>保存</button>
      </div>
    </div>
  )
}

/* ── Notifications ───────────────────────────────────────────── */
function NotificationsSection({ onShowToast }: Pick<ViewProps, 'onShowToast'>) {
  const [emailEnabled, setEmailEnabled] = useState(true)
  const [teamsEnabled, setTeamsEnabled] = useState(true)
  const [slackEnabled, setSlackEnabled] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState('')

  const EVENTS = [
    { id: 'approve', label: '承認完了', defaultOn: true },
    { id: 'ng', label: 'NG検出', defaultOn: true },
    { id: 'upload', label: 'アップロード完了', defaultOn: false },
    { id: 'login', label: '管理者ログイン', defaultOn: true },
    { id: 'expire', label: 'ライセンス期限警告', defaultOn: true },
    { id: 'storage', label: 'ストレージ残量警告', defaultOn: true },
  ]
  const [events, setEvents] = useState<Record<string, boolean>>(
    Object.fromEntries(EVENTS.map((e) => [e.id, e.defaultOn]))
  )

  return (
    <div className="ep-settings-content">
      <h2>通知設定</h2>
      <p className="ep-settings-desc">イベント発生時の通知チャネルとトリガーを設定します。</p>

      <div className="ep-settings-subheading">通知チャネル</div>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">メール通知</div>
          <div className="ep-settings-hint">登録メールアドレスに送信します。</div>
        </div>
        <button className={`ep-toggle${emailEnabled ? ' on' : ''}`} onClick={() => setEmailEnabled((v) => !v)} />
      </div>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">Microsoft Teams</div>
          <div className="ep-settings-hint">Teams チャンネル Webhook 経由で送信します。</div>
        </div>
        <button className={`ep-toggle${teamsEnabled ? ' on' : ''}`} onClick={() => setTeamsEnabled((v) => !v)} />
      </div>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">Slack</div>
          <div className="ep-settings-hint">Slack Incoming Webhook 経由で送信します。</div>
        </div>
        <button className={`ep-toggle${slackEnabled ? ' on' : ''}`} onClick={() => setSlackEnabled((v) => !v)} />
      </div>

      {slackEnabled && (
        <div className="ep-settings-group" style={{ marginLeft: '16px' }}>
          <label className="ep-settings-label">Slack Webhook URL</label>
          <input className="ep-settings-input" value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/..." />
        </div>
      )}

      <div className="ep-settings-subheading" style={{ marginTop: '20px' }}>通知トリガー</div>
      <div className="ep-settings-events-grid">
        {EVENTS.map((ev) => (
          <label key={ev.id} className="ep-settings-event-row">
            <input type="checkbox" checked={events[ev.id]} onChange={() => setEvents((prev) => ({ ...prev, [ev.id]: !prev[ev.id] }))}
              className="ep-settings-checkbox" />
            <span>{ev.label}</span>
          </label>
        ))}
      </div>

      <div className="ep-settings-footer">
        <button className="ep-btn ep-btn-primary" onClick={() => onShowToast('通知設定を保存しました', 'ok')}>保存</button>
      </div>
    </div>
  )
}

/* ── Integrations (with M365 non-interactive auth config) ───── */
function IntegrationsSection({ onShowToast }: Pick<ViewProps, 'onShowToast'>) {
  const [spUrl, setSpUrl] = useState('https://contoso.sharepoint.com/sites/civil')
  const [spSync, setSpSync] = useState(true)
  const [siemEndpoint, setSiemEndpoint] = useState('')

  // M365 App Registration (3 required values)
  const [m365Enabled, setM365Enabled] = useState(false)
  const [tenantId, setTenantId] = useState('')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [secretVisible, setSecretVisible] = useState(false)
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'ok' | 'fail'>('idle')

  const m365Configured = tenantId.length > 0 && clientId.length > 0 && clientSecret.length > 0

  async function handleTestConnection() {
    setTestStatus('testing')
    // Simulated async test (replace with real API call when backend ready)
    await new Promise((r) => setTimeout(r, 1200))
    if (m365Configured) {
      setTestStatus('ok')
      onShowToast('M365 接続テスト成功', 'ok')
    } else {
      setTestStatus('fail')
      onShowToast('接続に失敗しました。設定値を確認してください。', 'error')
    }
  }

  return (
    <div className="ep-settings-content">
      <h2>外部連携</h2>
      <p className="ep-settings-desc">Microsoft 365・SIEM・外部 API との接続設定です。</p>

      {/* M365 Non-interactive Auth */}
      <div style={{
        border: '1.5px solid var(--accent)',
        borderRadius: '10px',
        padding: '16px',
        marginBottom: '20px',
        background: 'var(--accent-soft)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: '#0078d4', display: 'grid', placeItems: 'center',
            }}>
              <M365GridIcon />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13px' }}>Microsoft 365 非対話式認証</div>
              <div style={{ fontSize: '11px', color: 'var(--muted)' }}>Client Credentials Flow（サービスプリンシパル認証）</div>
            </div>
          </div>
          <button className={`ep-toggle${m365Enabled ? ' on' : ''}`} onClick={() => setM365Enabled((v) => !v)} />
        </div>

        {m365Enabled && (
          <>
            <div style={{
              background: 'oklch(95% 0.02 250)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '10px 12px',
              fontSize: '11px',
              lineHeight: '1.6',
              marginBottom: '14px',
              color: 'var(--fg-2)',
            }}>
              <strong>認証フロー:</strong> ユーザーがメールアドレスを入力 → バックエンドが Microsoft Graph に client_credentials でトークン取得 →
              テナント内ユーザー存在確認 → このシステムのロールで JWT 発行。パスワード入力・ブラウザポップアップ不要。
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="ep-settings-group" style={{ marginBottom: 0 }}>
                <label className="ep-settings-label">
                  ① Tenant ID <span style={{ color: 'var(--danger, #ef4444)' }}>*</span>
                  <span className="ep-settings-hint" style={{ marginLeft: '6px', textTransform: 'none', fontWeight: 400 }}>（後日提示）</span>
                </label>
                <input
                  className="ep-settings-input ep-settings-mono"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
              </div>

              <div className="ep-settings-group" style={{ marginBottom: 0 }}>
                <label className="ep-settings-label">
                  ② Client ID（Application ID）<span style={{ color: 'var(--danger, #ef4444)' }}>*</span>
                  <span className="ep-settings-hint" style={{ marginLeft: '6px', textTransform: 'none', fontWeight: 400 }}>（後日提示）</span>
                </label>
                <input
                  className="ep-settings-input ep-settings-mono"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
              </div>

              <div className="ep-settings-group" style={{ marginBottom: 0 }}>
                <label className="ep-settings-label">
                  ③ Client Secret <span style={{ color: 'var(--danger, #ef4444)' }}>*</span>
                  <span className="ep-settings-hint" style={{ marginLeft: '6px', textTransform: 'none', fontWeight: 400 }}>（後日提示）</span>
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    className="ep-settings-input ep-settings-mono"
                    type={secretVisible ? 'text' : 'password'}
                    value={clientSecret}
                    onChange={(e) => setClientSecret(e.target.value)}
                    placeholder="••••••••••••••••••••••••••••••••"
                    style={{ paddingRight: '36px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setSecretVisible((v) => !v)}
                    style={{
                      position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)',
                      fontSize: '13px', padding: '2px',
                    }}
                    title={secretVisible ? '非表示' : '表示'}
                  >
                    {secretVisible ? '🙈' : '👁️'}
                  </button>
                </div>
                <span className="ep-settings-hint">
                  Azure Portal → アプリ登録 → 証明書とシークレット で生成した値。バックエンドで暗号化保存されます。
                </span>
              </div>

              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  className="ep-btn ep-btn-secondary"
                  onClick={handleTestConnection}
                  disabled={testStatus === 'testing' || !m365Configured}
                >
                  {testStatus === 'testing' ? '接続テスト中…' : '接続テスト'}
                </button>
                {testStatus === 'ok' && <span style={{ fontSize: '12px', color: 'oklch(50% 0.15 145)' }}>✓ 接続成功</span>}
                {testStatus === 'fail' && <span style={{ fontSize: '12px', color: 'var(--danger, #ef4444)' }}>✕ 接続失敗</span>}
                {!m365Configured && (
                  <span style={{ fontSize: '11px', color: 'var(--muted)' }}>3つの必須値をすべて入力してください</span>
                )}
              </div>

              <div style={{
                background: 'oklch(97% 0.01 250)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                padding: '10px 12px',
                fontSize: '11px',
                color: 'var(--muted)',
              }}>
                <strong>必要な API アクセス許可（Azure AD アプリ登録）:</strong>
                <ul style={{ margin: '6px 0 0 14px', lineHeight: '1.8' }}>
                  <li><code>User.Read.All</code> — ユーザー情報・テナント所属確認</li>
                  <li><code>Directory.Read.All</code> — ディレクトリ検索</li>
                  <li>権限タイプ: <strong>アプリケーション権限</strong>（委任ではなく）</li>
                  <li>管理者の同意: <strong>必須</strong></li>
                </ul>
              </div>
            </div>
          </>
        )}
      </div>

      {/* SharePoint */}
      <div className="ep-settings-subheading">SharePoint / OneDrive</div>
      <div className="ep-settings-group">
        <label className="ep-settings-label">SharePoint サイト URL</label>
        <input className="ep-settings-input" value={spUrl} onChange={(e) => setSpUrl(e.target.value)} />
      </div>
      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">双方向リアルタイム同期</div>
          <div className="ep-settings-hint">変更を即時に SharePoint へ反映します。</div>
        </div>
        <button className={`ep-toggle${spSync ? ' on' : ''}`} onClick={() => setSpSync((v) => !v)} />
      </div>

      {/* SIEM */}
      <div className="ep-settings-subheading" style={{ marginTop: '20px' }}>SIEM 連携</div>
      <div className="ep-settings-group">
        <label className="ep-settings-label">Syslog エンドポイント</label>
        <input className="ep-settings-input ep-settings-mono" value={siemEndpoint}
          onChange={(e) => setSiemEndpoint(e.target.value)} placeholder="syslog://10.0.0.50:514" />
        <span className="ep-settings-hint">空白の場合 SIEM 転送は無効です。</span>
      </div>

      <div className="ep-settings-footer">
        <button className="ep-btn ep-btn-primary" onClick={() => onShowToast('連携設定を保存しました', 'ok')}>保存</button>
      </div>
    </div>
  )
}

function M365GridIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 23 23" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="10" height="10" fill="white" opacity="0.9" />
      <rect x="12" y="1" width="10" height="10" fill="white" opacity="0.7" />
      <rect x="1" y="12" width="10" height="10" fill="white" opacity="0.7" />
      <rect x="12" y="12" width="10" height="10" fill="white" opacity="0.9" />
    </svg>
  )
}

/* ── Storage ─────────────────────────────────────────────────── */
function StorageSection({ onShowToast }: Pick<ViewProps, 'onShowToast'>) {
  const used = 847, total = 2000
  const pct = Math.round((used / total) * 100)
  const [retentionDays, setRetentionDays] = useState(365)
  const [autoArchive, setAutoArchive] = useState(true)
  const [archiveAfter, setArchiveAfter] = useState(180)

  return (
    <div className="ep-settings-content">
      <h2>ストレージ</h2>
      <p className="ep-settings-desc">使用量・保持ポリシー・自動アーカイブを管理します。</p>

      <div className="ep-settings-storage-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
          <span>使用量</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{used} GB / {total} GB</span>
        </div>
        <div className="ep-settings-storage-bar">
          <div className="ep-settings-storage-fill" style={{ width: `${pct}%`, background: pct > 80 ? 'var(--danger)' : 'var(--accent)' }} />
        </div>
        <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '6px' }}>{pct}% 使用中 — 残り {total - used} GB</div>
      </div>

      <div className="ep-settings-group" style={{ marginTop: '20px' }}>
        <label className="ep-settings-label">ファイル保持期間（日）</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input type="range" min={90} max={3650} step={90} value={retentionDays}
            onChange={(e) => setRetentionDays(Number(e.target.value))} className="ep-slider" style={{ flex: 1 }} />
          <span style={{ minWidth: '56px', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{retentionDays}日</span>
        </div>
      </div>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">自動アーカイブ</div>
          <div className="ep-settings-hint">一定期間アクセスのないファイルを低コストストレージへ移動します。</div>
        </div>
        <button className={`ep-toggle${autoArchive ? ' on' : ''}`} onClick={() => setAutoArchive((v) => !v)} />
      </div>

      {autoArchive && (
        <div className="ep-settings-group" style={{ marginLeft: '16px' }}>
          <label className="ep-settings-label">アーカイブ開始（最終アクセスから何日後）</label>
          <input type="number" className="ep-settings-input" value={archiveAfter}
            onChange={(e) => setArchiveAfter(Number(e.target.value))} min={30} max={720} style={{ width: '100px' }} />
        </div>
      )}

      <div className="ep-settings-footer">
        <button className="ep-btn ep-btn-primary" onClick={() => onShowToast('ストレージ設定を保存しました', 'ok')}>保存</button>
        <button className="ep-btn ep-btn-secondary" onClick={() => onShowToast('クリーンアップを開始しました', 'ok')}>今すぐクリーンアップ</button>
      </div>
    </div>
  )
}

/* ── Audit Settings ──────────────────────────────────────────── */
function AuditSection({ onShowToast }: Pick<ViewProps, 'onShowToast'>) {
  const [hashChain, setHashChain] = useState(true)
  const [logLevel, setLogLevel] = useState('all')
  const [exportFormat, setExportFormat] = useState('json')
  const [autoExport, setAutoExport] = useState(false)
  const [exportSchedule, setExportSchedule] = useState('monthly')

  return (
    <div className="ep-settings-content">
      <h2>監査設定</h2>
      <p className="ep-settings-desc">監査ログの記録レベル・エクスポート・改ざん防止設定です。</p>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">ハッシュチェーン改ざん防止</div>
          <div className="ep-settings-hint">各ログエントリに前エントリの SHA-256 を連結します。</div>
        </div>
        <button className={`ep-toggle${hashChain ? ' on' : ''}`} onClick={() => setHashChain((v) => !v)} />
      </div>

      <div className="ep-settings-group">
        <label className="ep-settings-label">記録レベル</label>
        <select className="ep-settings-select" value={logLevel} onChange={(e) => setLogLevel(e.target.value)}>
          <option value="all">全操作（推奨）</option>
          <option value="write">書き込みのみ</option>
          <option value="admin">管理操作のみ</option>
        </select>
      </div>

      <div className="ep-settings-group">
        <label className="ep-settings-label">エクスポート形式</label>
        <select className="ep-settings-select" value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="syslog">Syslog (RFC 5424)</option>
        </select>
      </div>

      <div className="ep-settings-toggle-row">
        <div>
          <div className="ep-settings-label">自動エクスポート</div>
          <div className="ep-settings-hint">定期的にログを外部ストレージへエクスポートします。</div>
        </div>
        <button className={`ep-toggle${autoExport ? ' on' : ''}`} onClick={() => setAutoExport((v) => !v)} />
      </div>

      {autoExport && (
        <div className="ep-settings-group" style={{ marginLeft: '16px' }}>
          <label className="ep-settings-label">スケジュール</label>
          <select className="ep-settings-select" value={exportSchedule} onChange={(e) => setExportSchedule(e.target.value)}>
            <option value="daily">毎日</option>
            <option value="weekly">毎週</option>
            <option value="monthly">毎月</option>
          </select>
        </div>
      )}

      <div className="ep-settings-footer">
        <button className="ep-btn ep-btn-primary" onClick={() => onShowToast('監査設定を保存しました', 'ok')}>保存</button>
        <button className="ep-btn ep-btn-secondary" onClick={() => onShowToast('監査ログをエクスポートしました', 'ok')}>今すぐエクスポート</button>
      </div>
    </div>
  )
}

/* ── License ─────────────────────────────────────────────────── */
function LicenseSection({ onShowModal }: Pick<ViewProps, 'onShowModal'>) {
  return (
    <div className="ep-settings-content">
      <h2>ライセンス情報</h2>
      <p className="ep-settings-desc">現在のライセンスプランと有効期限を確認します。</p>

      <div className="ep-settings-license-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '16px' }}>Enterprise Plan</div>
            <div style={{ color: 'var(--muted)', fontSize: '12px', marginTop: '4px' }}>建設・土木業向け 全機能プラン</div>
          </div>
          <span className="ep-badge ep-badge-ok">有効</span>
        </div>

        <div className="ep-settings-license-grid">
          {[
            { label: 'ライセンスキー', value: 'CPDF-ENT-2026-XXXX-XXXX', mono: true },
            { label: '契約組織', value: '株式会社 〇〇建設', mono: false },
            { label: 'ユーザー上限', value: '500ユーザー', mono: false },
            { label: '有効期限', value: '2027年3月31日', mono: false },
            { label: 'バージョン', value: 'v0.4.2-enterprise', mono: true },
            { label: 'サポート', value: 'Enterprise SLA (24h)', mono: false },
          ].map((item) => (
            <div key={item.label} className="ep-settings-license-row">
              <span className="ep-settings-license-key">{item.label}</span>
              <span className="ep-settings-license-val"
                style={item.mono ? { fontFamily: 'var(--font-mono)', fontSize: '12px' } : undefined}>
                {item.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="ep-settings-footer">
        <button className="ep-btn ep-btn-secondary" onClick={() =>
          onShowModal({ title: 'ライセンス更新', body: '更新の手続きはサポートポータルから行ってください。\nhttps://support.civilpdf-dx.example.com\n\n担当営業にご連絡いただくと更新手続きをご案内します。' })
        }>ライセンス更新</button>
      </div>
    </div>
  )
}

/* ── Main view ───────────────────────────────────────────────── */
export const SettingsView: FC<ViewProps> = ({ onShowModal, onShowToast }) => {
  const [active, setActive] = useState<SettingsSection>('general')

  function renderSection() {
    switch (active) {
      case 'general': return <GeneralSection onShowToast={onShowToast} />
      case 'users': return <UsersSection onShowToast={onShowToast} />
      case 'security': return <SecuritySection onShowToast={onShowToast} />
      case 'notifications': return <NotificationsSection onShowToast={onShowToast} />
      case 'integrations': return <IntegrationsSection onShowToast={onShowToast} />
      case 'storage': return <StorageSection onShowToast={onShowToast} />
      case 'audit': return <AuditSection onShowToast={onShowToast} />
      case 'license': return <LicenseSection onShowModal={onShowModal} />
    }
  }

  return (
    <div className="ep ep-settings-root">
      <aside className="ep-settings-sidebar">
        <div className="ep-settings-sidebar-title">システム設定</div>
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            className={`ep-settings-nav-item${active === s.id ? ' active' : ''}`}
            onClick={() => setActive(s.id)}
          >
            <span className="ep-settings-nav-icon">{s.icon}</span>
            {s.label}
          </button>
        ))}
      </aside>
      <main className="ep-settings-main">{renderSection()}</main>
    </div>
  )
}
