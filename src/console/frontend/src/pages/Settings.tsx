import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getStats } from '../api/stats'
import { updateMe, changePassword } from '../api/auth'
import { useAuthStore } from '../store/auth'

const ROLE_LABELS: Record<string, string> = {
  admin: '管理者',
  manager: 'マネージャー',
  engineer: '技術担当',
  viewer: '閲覧のみ',
}

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center py-2 border-b last:border-0">
      <span className="text-sm text-gray-500 w-40 flex-shrink-0">{label}</span>
      <span className="text-sm font-medium text-gray-800">{value}</span>
    </div>
  )
}

export function Settings() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const isAdmin = user?.role === 'admin'

  const [editName, setEditName] = useState(false)
  const [newName, setNewName] = useState('')
  const [editPass, setEditPass] = useState(false)
  const [currentPass, setCurrentPass] = useState('')
  const [newPass, setNewPass] = useState('')

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    staleTime: 60_000,
    enabled: isAdmin,
  })

  const updateNameMutation = useMutation({
    mutationFn: () => updateMe(newName),
    onSuccess: (updated) => {
      setUser(updated)
      qc.invalidateQueries({ queryKey: ['me'] })
      setEditName(false)
      setNewName('')
    },
  })

  const changePassMutation = useMutation({
    mutationFn: () => changePassword(currentPass, newPass),
    onSuccess: () => {
      setEditPass(false)
      setCurrentPass('')
      setNewPass('')
    },
  })

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">設定</h1>
      <p className="text-sm text-gray-500 mb-8">システム設定とプロフィール情報</p>

      {/* プロフィール */}
      <div className="bg-white rounded-xl shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-700">プロフィール</h2>
          {!editName && (
            <button
              onClick={() => { setEditName(true); setNewName(user?.full_name || '') }}
              className="text-xs text-blue-600 hover:underline"
            >
              編集
            </button>
          )}
        </div>

        {editName ? (
          <div className="space-y-3">
            <div>
              <label htmlFor="edit-name" className="block text-sm text-gray-600 mb-1">氏名</label>
              <input
                id="edit-name"
                className="w-full border rounded px-3 py-2 text-sm max-w-sm"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            {updateNameMutation.error && (
              <p className="text-red-600 text-xs">{String(updateNameMutation.error)}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => updateNameMutation.mutate()}
                disabled={updateNameMutation.isPending || !newName.trim()}
                className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded disabled:opacity-50"
              >
                {updateNameMutation.isPending ? '保存中...' : '保存'}
              </button>
              <button
                onClick={() => setEditName(false)}
                className="text-gray-600 text-sm px-4 py-1.5 rounded border"
              >
                キャンセル
              </button>
            </div>
          </div>
        ) : (
          <>
            <InfoRow label="氏名" value={user?.full_name || '—'} />
            <InfoRow label="メールアドレス" value={user?.email || '—'} />
            <InfoRow label="ユーザー名" value={user?.username || '—'} />
            <InfoRow label="ロール" value={ROLE_LABELS[user?.role ?? ''] ?? '—'} />
            <InfoRow label="ステータス" value={user?.status === 'active' ? '有効' : '無効'} />
          </>
        )}
      </div>

      {/* パスワード変更 */}
      <div className="bg-white rounded-xl shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-700">パスワード変更</h2>
          {!editPass && (
            <button
              onClick={() => setEditPass(true)}
              className="text-xs text-blue-600 hover:underline"
            >
              変更
            </button>
          )}
        </div>
        {editPass ? (
          <div className="space-y-3 max-w-sm">
            <div>
              <label htmlFor="current-pass" className="block text-sm text-gray-600 mb-1">現在のパスワード</label>
              <input
                id="current-pass"
                type="password"
                className="w-full border rounded px-3 py-2 text-sm"
                value={currentPass}
                onChange={(e) => setCurrentPass(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="new-pass" className="block text-sm text-gray-600 mb-1">新しいパスワード（8文字以上）</label>
              <input
                id="new-pass"
                type="password"
                className="w-full border rounded px-3 py-2 text-sm"
                value={newPass}
                onChange={(e) => setNewPass(e.target.value)}
              />
            </div>
            {changePassMutation.error && (
              <p className="text-red-600 text-xs">{String(changePassMutation.error)}</p>
            )}
            {changePassMutation.isSuccess && (
              <p className="text-green-600 text-xs">パスワードを変更しました</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => changePassMutation.mutate()}
                disabled={changePassMutation.isPending || !currentPass || !newPass}
                className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded disabled:opacity-50"
              >
                {changePassMutation.isPending ? '変更中...' : '変更する'}
              </button>
              <button
                onClick={() => { setEditPass(false); setCurrentPass(''); setNewPass('') }}
                className="text-gray-600 text-sm px-4 py-1.5 rounded border"
              >
                キャンセル
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">「変更」ボタンからパスワードを更新できます。</p>
        )}
      </div>

      {/* システム情報（管理者のみ） */}
      {isAdmin && (
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="text-base font-semibold text-gray-700 mb-4">システム情報</h2>
          {stats ? (
            <>
              <InfoRow label="総ドキュメント数" value={stats.total_documents} />
              <InfoRow label="アクティブユーザー" value={stats.active_users} />
              <InfoRow label="承認待ち" value={stats.pending_approvals} />
              <InfoRow label="今月承認済み" value={stats.approved_this_month} />
            </>
          ) : (
            <p className="text-sm text-gray-400">読み込み中...</p>
          )}
        </div>
      )}

      {/* セキュリティ設定（表示のみ） */}
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-base font-semibold text-gray-700 mb-4">セキュリティポリシー</h2>
        <InfoRow label="パスワード有効期限" value="90日" />
        <InfoRow label="セッションタイムアウト" value="8時間" />
        <InfoRow label="MFA" value="無効（予定）" />
        <p className="text-xs text-gray-400 mt-3">
          セキュリティポリシーの変更は管理者にお問い合わせください。
        </p>
      </div>
    </div>
  )
}
