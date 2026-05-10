import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { UserResponse } from '../api/auth'
import { useAuthStore } from '../store/auth'

async function listUsers(): Promise<UserResponse[]> {
  const res = await api.get<UserResponse[]>('/users/')
  return res.data
}

const roleLabel: Record<string, string> = {
  admin: '管理者',
  manager: 'マネージャー',
  engineer: 'エンジニア',
  viewer: '閲覧者',
}

export function Users() {
  const currentUser = useAuthStore((s) => s.user)
  const { data: users = [], isLoading } = useQuery({ queryKey: ['users'], queryFn: listUsers })

  if (currentUser?.role !== 'admin' && currentUser?.role !== 'manager') {
    return (
      <div className="p-8">
        <p className="text-gray-500">この画面へのアクセス権限がありません</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">ユーザー管理</h1>
      <div className="bg-white rounded-xl shadow">
        {isLoading ? (
          <p className="p-6 text-gray-400 text-sm">読み込み中...</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3">名前</th>
                <th className="px-4 py-3">メールアドレス</th>
                <th className="px-4 py-3">ロール</th>
                <th className="px-4 py-3">ステータス</th>
                <th className="px-4 py-3">最終ログイン</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{u.full_name}</td>
                  <td className="px-4 py-3 text-gray-500">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-700">
                      {roleLabel[u.role] ?? u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      u.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {u.status === 'active' ? '有効' : '無効'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {u.last_login ? new Date(u.last_login).toLocaleDateString('ja-JP') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
