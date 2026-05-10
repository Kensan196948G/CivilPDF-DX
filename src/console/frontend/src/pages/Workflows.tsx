import { useQuery } from '@tanstack/react-query'
import { listWorkflows } from '../api/workflows'

const statusLabel: Record<string, { label: string; cls: string }> = {
  pending: { label: '待機中', cls: 'bg-gray-100 text-gray-600' },
  in_progress: { label: '審査中', cls: 'bg-orange-100 text-orange-700' },
  approved: { label: '承認済', cls: 'bg-green-100 text-green-700' },
  rejected: { label: '却下', cls: 'bg-red-100 text-red-700' },
}

export function Workflows() {
  const { data: workflows = [], isLoading } = useQuery({ queryKey: ['workflows'], queryFn: listWorkflows })

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">承認ワークフロー</h1>
      <div className="space-y-4">
        {isLoading && <p className="text-gray-400 text-sm">読み込み中...</p>}
        {!isLoading && workflows.length === 0 && (
          <p className="text-gray-400 text-sm">ワークフローがありません</p>
        )}
        {workflows.map((wf) => {
          const s = statusLabel[wf.status] ?? { label: wf.status, cls: 'bg-gray-100 text-gray-600' }
          return (
            <div key={wf.id} className="bg-white rounded-xl shadow p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-gray-800">{wf.title}</h2>
                <span className={`px-2 py-0.5 rounded-full text-xs ${s.cls}`}>{s.label}</span>
              </div>
              <div className="flex gap-2">
                {wf.steps.map((step) => {
                  const ss = statusLabel[step.status] ?? { label: step.status, cls: 'bg-gray-100 text-gray-600' }
                  return (
                    <div key={step.id} className="flex-1 border rounded p-3 text-sm">
                      <p className="font-medium text-gray-700">ステップ {step.step_number}: {step.step_name}</p>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs ${ss.cls}`}>{ss.label}</span>
                      {step.comment && <p className="text-gray-500 mt-1 text-xs">{step.comment}</p>}
                    </div>
                  )
                })}
              </div>
              <p className="text-gray-400 text-xs mt-3">
                作成: {new Date(wf.created_at).toLocaleDateString('ja-JP')}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
