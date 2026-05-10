import { useQuery } from '@tanstack/react-query'
import { listDocuments } from '../api/documents'
import { listProjects } from '../api/projects'
import { listWorkflows } from '../api/workflows'
import { useAuthStore } from '../store/auth'

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`bg-white rounded-xl shadow p-6 border-l-4 ${color}`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold text-gray-800 mt-1">{value}</p>
    </div>
  )
}

export function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const { data: documents = [] } = useQuery({ queryKey: ['documents'], queryFn: () => listDocuments() })
  const { data: projects = [] } = useQuery({ queryKey: ['projects'], queryFn: listProjects })
  const { data: workflows = [] } = useQuery({ queryKey: ['workflows'], queryFn: listWorkflows })

  const pendingWorkflows = workflows.filter((w) => w.status === 'in_progress').length

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">ダッシュボード</h1>
      <p className="text-sm text-gray-500 mb-8">
        ようこそ、{user?.full_name ?? user?.email} さん
      </p>
      <div className="grid grid-cols-2 gap-6 mb-8 lg:grid-cols-4">
        <StatCard label="ドキュメント" value={documents.length} color="border-blue-500" />
        <StatCard label="プロジェクト" value={projects.length} color="border-green-500" />
        <StatCard label="ワークフロー" value={workflows.length} color="border-purple-500" />
        <StatCard label="承認待ち" value={pendingWorkflows} color="border-orange-500" />
      </div>
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">最近のドキュメント</h2>
        {documents.length === 0 ? (
          <p className="text-gray-400 text-sm">ドキュメントがありません</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2">タイトル</th>
                <th className="pb-2">種別</th>
                <th className="pb-2">ステータス</th>
                <th className="pb-2">登録日</th>
              </tr>
            </thead>
            <tbody>
              {documents.slice(0, 5).map((doc) => (
                <tr key={doc.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="py-2 font-medium">{doc.title}</td>
                  <td className="py-2 text-gray-500">{doc.document_type}</td>
                  <td className="py-2">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">
                      {doc.status}
                    </span>
                  </td>
                  <td className="py-2 text-gray-400">
                    {new Date(doc.created_at).toLocaleDateString('ja-JP')}
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
