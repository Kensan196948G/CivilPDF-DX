import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listWorkflows, decideStep } from '../api/workflows'
import { useAuthStore } from '../store/auth'

const statusLabel: Record<string, { label: string; cls: string }> = {
  pending: { label: '待機中', cls: 'bg-gray-100 text-gray-600' },
  in_progress: { label: '審査中', cls: 'bg-orange-100 text-orange-700' },
  approved: { label: '承認済', cls: 'bg-green-100 text-green-700' },
  rejected: { label: '却下', cls: 'bg-red-100 text-red-700' },
}

interface DecideState {
  workflowId: string
  stepId: string
  action: 'approve' | 'reject'
}

export function Workflows() {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const { data: workflows = [], isLoading } = useQuery({ queryKey: ['workflows'], queryFn: listWorkflows })

  const [deciding, setDeciding] = useState<DecideState | null>(null)
  const [comment, setComment] = useState('')

  const decide = useMutation({
    mutationFn: () =>
      decideStep(deciding!.workflowId, deciding!.stepId, deciding!.action, comment || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflows'] })
      setDeciding(null)
      setComment('')
    },
  })

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">承認ワークフロー</h1>

      {deciding && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-md">
            <h2 className="font-semibold text-gray-800 mb-3">
              {deciding.action === 'approve' ? '承認確認' : '却下確認'}
            </h2>
            <p className="text-sm text-gray-600 mb-3">
              コメント（任意{deciding.action === 'reject' ? '・却下理由を推奨' : ''}）
            </p>
            <textarea
              className="w-full border rounded px-3 py-2 text-sm"
              rows={3}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={deciding.action === 'reject' ? '却下理由を入力...' : 'コメントを入力...'}
            />
            {decide.error && (
              <p className="text-red-600 text-sm mt-2">{String(decide.error)}</p>
            )}
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => decide.mutate()}
                disabled={decide.isPending}
                className={`px-4 py-2 rounded text-sm text-white disabled:opacity-50 ${
                  deciding.action === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {decide.isPending ? '処理中...' : deciding.action === 'approve' ? '承認する' : '却下する'}
              </button>
              <button
                onClick={() => { setDeciding(null); setComment('') }}
                className="text-gray-600 px-4 py-2 rounded text-sm border"
              >
                キャンセル
              </button>
            </div>
          </div>
        </div>
      )}

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
                  const isMyPendingStep =
                    step.approver_id === currentUser?.id && step.status === 'pending'
                  return (
                    <div key={step.id} className="flex-1 border rounded p-3 text-sm">
                      <p className="font-medium text-gray-700">
                        ステップ {step.step_number}: {step.step_name}
                      </p>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs ${ss.cls}`}>
                        {ss.label}
                      </span>
                      {step.comment && (
                        <p className="text-gray-500 mt-1 text-xs">{step.comment}</p>
                      )}
                      {isMyPendingStep && (
                        <div className="flex gap-2 mt-2">
                          <button
                            onClick={() =>
                              setDeciding({ workflowId: wf.id, stepId: step.id, action: 'approve' })
                            }
                            className="text-xs px-2 py-1 rounded bg-green-600 text-white hover:bg-green-700"
                          >
                            承認
                          </button>
                          <button
                            onClick={() =>
                              setDeciding({ workflowId: wf.id, stepId: step.id, action: 'reject' })
                            }
                            className="text-xs px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700"
                          >
                            却下
                          </button>
                        </div>
                      )}
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
