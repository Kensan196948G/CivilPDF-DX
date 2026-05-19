import { useQuery } from '@tanstack/react-query'
import { getStats } from '../api/stats'
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
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    staleTime: 60_000,
    enabled: isAdmin,
  })

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">設定</h1>
      <p className="text-sm text-gray-500 mb-8">システム設定とプロフィール情報</p>

      {/* プロフィール */}
      <div className="bg-white rounded-xl shadow p-6 mb-6">
        <h2 className="text-base font-semibold text-gray-700 mb-4">プロフィール</h2>
        <InfoRow label="氏名" value={user?.full_name || '—'} />
        <InfoRow label="メールアドレス" value={user?.email || '—'} />
        <InfoRow label="ユーザー名" value={user?.username || '—'} />
        <InfoRow label="ロール" value={ROLE_LABELS[user?.role ?? ''] ?? '—'} />
        <InfoRow label="ステータス" value={user?.status === 'active' ? '有効' : '無効'} />
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
