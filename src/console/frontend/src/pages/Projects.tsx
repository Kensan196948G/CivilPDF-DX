import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listProjects, createProject } from '../api/projects'

export function Projects() {
  const qc = useQueryClient()
  const { data: projects = [], isLoading } = useQuery({ queryKey: ['projects'], queryFn: listProjects })
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [description, setDescription] = useState('')

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

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">プロジェクト</h1>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-700 hover:bg-blue-800 text-white text-sm px-4 py-2 rounded-lg"
        >
          + 新規作成
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">プロジェクト作成</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">プロジェクト名</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">コード</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={code} onChange={(e) => setCode(e.target.value)} />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-gray-600 mb-1">説明</label>
              <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>
          {create.error && <p className="text-red-600 text-sm mt-2">{String(create.error)}</p>}
          <div className="flex gap-3 mt-4">
            <button onClick={() => create.mutate()} disabled={create.isPending} className="bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50">
              {create.isPending ? '作成中...' : '作成'}
            </button>
            <button onClick={() => setShowForm(false)} className="text-gray-600 px-4 py-2 rounded text-sm border">キャンセル</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow">
        {isLoading ? (
          <p className="p-6 text-gray-400 text-sm">読み込み中...</p>
        ) : projects.length === 0 ? (
          <p className="p-6 text-gray-400 text-sm">プロジェクトがありません</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3">プロジェクト名</th>
                <th className="px-4 py-3">コード</th>
                <th className="px-4 py-3">ステータス</th>
                <th className="px-4 py-3">作成日</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{p.name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono">{p.code}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">{p.status}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{new Date(p.created_at).toLocaleDateString('ja-JP')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
