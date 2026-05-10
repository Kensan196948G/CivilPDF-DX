import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { UserResponse } from '../api/auth'
import { useAuthStore } from '../store/auth'

async function listUsers(): Promise<UserResponse[]> {
  const res = await api.get<UserResponse[]>('/users/')
  return res.data
}

async function createUser(body: {
  email: string
  username: string
  full_name: string
  password: string
  role: string
}): Promise<UserResponse> {
  const res = await api.post<UserResponse>('/users/', body)
  return res.data
}

async function updateUserStatus(id: string, status: string): Promise<UserResponse> {
  const res = await api.patch<UserResponse>(`/users/${id}`, { status })
  return res.data
}

const roleLabel: Record<string, string> = {
  admin: '管理者',
  manager: 'マネージャー',
  engineer: 'エンジニア',
  viewer: '閲覧者',
}

const initialForm = { email: '', username: '', full_name: '', password: '', role: 'engineer' }

export function Users() {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const { data: users = [], isLoading } = useQuery({ queryKey: ['users'], queryFn: listUsers })

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(initialForm)

  const create = useMutation({
    mutationFn: () => createUser(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setForm(initialForm)
    },
  })

  const toggleStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateUserStatus(id, status === 'active' ? 'inactive' : 'active'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  if (currentUser?.role !== 'admin' && currentUser?.role !== 'manager') {
    return (
      <div className="p-8">
        <p className="text-gray-500">この画面へのアクセス権限がありません</p>
      </div>
    )
  }

  const isAdmin = currentUser?.role === 'admin'

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">ユーザー管理</h1>
        {isAdmin && (
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-700 hover:bg-blue-800 text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            + ユーザー追加
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">新規ユーザー作成</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">メールアドレス</label>
              <input
                type="email"
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">ユーザー名</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">氏名</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">パスワード（8文字以上）</label>
              <input
                type="password"
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">ロール</label>
              <select
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                {Object.entries(roleLabel).map(([val, lbl]) => (
                  <option key={val} value={val}>{lbl}</option>
                ))}
              </select>
            </div>
          </div>
          {create.error && (
            <p className="text-red-600 text-sm mt-2">{String(create.error)}</p>
          )}
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => create.mutate()}
              disabled={create.isPending}
              className="bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
            >
              {create.isPending ? '作成中...' : '作成'}
            </button>
            <button
              onClick={() => { setShowForm(false); setForm(initialForm) }}
              className="text-gray-600 px-4 py-2 rounded text-sm border"
            >
              キャンセル
            </button>
          </div>
        </div>
      )}

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
                {isAdmin && <th className="px-4 py-3"></th>}
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
                  {isAdmin && (
                    <td className="px-4 py-3">
                      {u.id !== currentUser?.id && (
                        <button
                          onClick={() => toggleStatus.mutate({ id: u.id, status: u.status })}
                          className={`text-xs px-2 py-1 rounded border transition-colors ${
                            u.status === 'active'
                              ? 'border-red-300 text-red-600 hover:bg-red-50'
                              : 'border-green-300 text-green-600 hover:bg-green-50'
                          }`}
                        >
                          {u.status === 'active' ? '無効化' : '有効化'}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
