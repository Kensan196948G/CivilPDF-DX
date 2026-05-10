import { useQuery } from '@tanstack/react-query'
import { listWorkflows } from '../api/workflows'

const statusLabel: Record<string, { label: string; cls: string }> = {
  in_progress: { label: '審査中', cls: 'bg-orange-100 text-orange-700' },
  approved: { label: '承認済', cls: 'bg-green-100 text-green-700' },
  rejected: { label: '却下', cls: 'bg-red-100 text-red-700' },
}

export function Workflows() {
  const { data: workflows = [], isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: listWorkflows,
  })

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">承認ワークフロー</h1>

      <div className="bg-white rounded-xl shadow">
        {isLoading ? (
          <p className="p-6 text-gray-400 text-sm">読み込み中...</p>
        ) : workflows.length === 0 ? (
          <p className="p-6 text-gray-400 text-sm">ワークフローがありません</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3">ドキュメント</th>
                <th className="px-4 py-3">ステータス</th>
                <th className="px-4 py-3">ステップ数</th>
                <th className="px-4 py-3">承認待ち</th>
                <th className="px-4 py-3">作成日</th>
                <th className="px-4 py-3">完了日</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((wf) => {
                const s = statusLabel[wf.status] ?? { label: wf.status, cls: 'bg-gray-100 text-gray-600' }
                return (
                  <tr key={wf.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{wf.document_title}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${s.cls}`}>{s.label}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-center">{wf.step_count}</td>
                    <td className="px-4 py-3 text-center">
                      {wf.pending_step_count > 0 ? (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700">
                          {wf.pending_step_count}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(wf.created_at).toLocaleDateString('ja-JP')}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {wf.completed_at ? new Date(wf.completed_at).toLocaleDateString('ja-JP') : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
