import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listProjects, createProject, deleteProject } from '../api/projects'
import { useAuthStore } from '../store/auth'

export function Projects() {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const isAdmin = currentUser?.role === 'admin'

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
  })

  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [description, setDescription] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredProjects = useMemo(() => {
    if (searchQuery === '') return projects
    return projects.filter((p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [projects, searchQuery])

  const create = useMutation({
    mutationFn: () => createProject({ name, code, description }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      setShowForm(false)
      setName('')
      setCode('')
      setDescription('')
    },
  })

  const remove = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">プロジェクト</h1>
        {isAdmin && (
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-700 hover:bg-blue-800 text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            + 新規作成
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">プロジェクト作成</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="proj-name" className="block text-sm text-gray-600 mb-1">プロジェクト名</label>
              <input
                id="proj-name"
                className="w-full border rounded px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="proj-code" className="block text-sm text-gray-600 mb-1">コード</label>
              <input
                id="proj-code"
                className="w-full border rounded px-3 py-2 text-sm"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>
            <div className="col-span-2">
              <label htmlFor="proj-description" className="block text-sm text-gray-600 mb-1">説明</label>
              <textarea
                id="proj-description"
                className="w-full border rounded px-3 py-2 text-sm"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
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
              onClick={() => setShowForm(false)}
              className="text-gray-600 px-4 py-2 rounded text-sm border"
            >
              キャンセル
            </button>
          </div>
        </div>
      )}

      {/* Search bar */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="search"
          placeholder="プロジェクト名で検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm flex-1 min-w-[200px]"
          aria-label="プロジェクト名で検索"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="text-xs text-gray-500 underline px-2"
          >
            クリア
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow">
        {isLoading ? (
          <p className="p-6 text-gray-400 text-sm">読み込み中...</p>
        ) : filteredProjects.length === 0 ? (
          <p className="p-6 text-gray-400 text-sm">
            {projects.length > 0
              ? '条件に一致するプロジェクトがありません'
              : 'プロジェクトがありません'}
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3">プロジェクト名</th>
                <th className="px-4 py-3">コード</th>
                <th className="px-4 py-3">ステータス</th>
                <th className="px-4 py-3">作成日</th>
                {isAdmin && <th className="px-4 py-3"></th>}
              </tr>
            </thead>
            <tbody>
              {filteredProjects.map((p) => (
                <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{p.name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{p.code}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}>
                      {p.is_active ? '有効' : '無効'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(p.created_at).toLocaleDateString('ja-JP')}
                  </td>
                  {isAdmin && (
                    <td className="px-4 py-3">
                      <button
                        onClick={() => remove.mutate(p.id)}
                        className="text-red-500 hover:text-red-700 text-xs"
                      >
                        削除
                      </button>
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
