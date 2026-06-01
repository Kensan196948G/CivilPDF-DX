import { useState, useRef, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listDocuments,
  uploadDocument,
  deleteDocument,
  type DocumentResponse,
} from '../api/documents'
import { listProjects } from '../api/projects'
import { DocumentPreviewModal } from '../components/DocumentPreviewModal'
import { classifyDocument, type ClassifyResponse } from '../api/ai'

const DOC_TYPE_LABELS: Record<string, string> = {
  drawing: '図面',
  specification: '仕様書',
  report: '報告書',
  contract: '契約書',
  other: 'その他',
}

const STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  draft: { label: '下書き', cls: 'bg-gray-100 text-gray-600' },
  pending_review: { label: 'レビュー待ち', cls: 'bg-yellow-100 text-yellow-700' },
  approved: { label: '承認済', cls: 'bg-green-100 text-green-700' },
  rejected: { label: '却下', cls: 'bg-red-100 text-red-700' },
}

export function Documents() {
  const qc = useQueryClient()
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => listDocuments(),
  })
  const { data: projects = [] } = useQuery({ queryKey: ['projects'], queryFn: listProjects })

  // Upload form state
  const [showUpload, setShowUpload] = useState(false)
  const [title, setTitle] = useState('')
  const [projectId, setProjectId] = useState('')
  const [docType, setDocType] = useState('drawing')
  const [previewDoc, setPreviewDoc] = useState<DocumentResponse | null>(null)
  const [aiResult, setAiResult] = useState<ClassifyResponse | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  // Search / filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch =
        searchQuery === '' ||
        doc.title.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesType = filterType === '' || doc.document_type === filterType
      const matchesStatus = filterStatus === '' || doc.status === filterStatus
      return matchesSearch && matchesType && matchesStatus
    })
  }, [documents, searchQuery, filterType, filterStatus])

  const upload = useMutation({
    mutationFn: () => {
      const file = fileRef.current?.files?.[0]
      if (!file) throw new Error('ファイルを選択してください')
      return uploadDocument(projectId, title, docType, file)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      setShowUpload(false)
      setTitle('')
    },
  })

  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })

  const classify = useMutation({
    mutationFn: classifyDocument,
    onSuccess: (result) => {
      setAiResult(result)
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">ドキュメント</h1>
        <button
          onClick={() => setShowUpload(true)}
          className="bg-blue-700 hover:bg-blue-800 text-white text-sm px-4 py-2 rounded-lg transition-colors"
        >
          + アップロード
        </button>
      </div>

      {showUpload && (
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">ドキュメントのアップロード</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="doc-title" className="block text-sm text-gray-600 mb-1">タイトル</label>
              <input
                id="doc-title"
                className="w-full border rounded px-3 py-2 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="doc-project" className="block text-sm text-gray-600 mb-1">プロジェクト</label>
              <select
                id="doc-project"
                className="w-full border rounded px-3 py-2 text-sm"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
              >
                <option value="">選択してください</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="doc-type" className="block text-sm text-gray-600 mb-1">種別</label>
              <select
                id="doc-type"
                className="w-full border rounded px-3 py-2 text-sm"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
              >
                <option value="drawing">図面</option>
                <option value="specification">仕様書</option>
                <option value="report">報告書</option>
                <option value="contract">契約書</option>
                <option value="other">その他</option>
              </select>
            </div>
            <div>
              <label htmlFor="doc-file" className="block text-sm text-gray-600 mb-1">PDFファイル</label>
              <input id="doc-file" type="file" accept=".pdf" ref={fileRef} className="text-sm" />
            </div>
          </div>
          {upload.error && (
            <p className="text-red-600 text-sm mt-2">{String(upload.error)}</p>
          )}
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => upload.mutate()}
              disabled={upload.isPending}
              className="bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
            >
              {upload.isPending ? 'アップロード中...' : 'アップロード'}
            </button>
            <button
              onClick={() => setShowUpload(false)}
              className="text-gray-600 px-4 py-2 rounded text-sm border"
            >
              キャンセル
            </button>
          </div>
        </div>
      )}

      {/* Search & Filter bar */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="search"
          placeholder="タイトルで検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm flex-1 min-w-[200px]"
          aria-label="タイトルで検索"
        />
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
          aria-label="種別フィルター"
        >
          <option value="">すべての種別</option>
          {Object.entries(DOC_TYPE_LABELS).map(([val, lbl]) => (
            <option key={val} value={val}>{lbl}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
          aria-label="ステータスフィルター"
        >
          <option value="">すべてのステータス</option>
          {Object.entries(STATUS_LABELS).map(([val, { label }]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>
        {(searchQuery || filterType || filterStatus) && (
          <button
            onClick={() => { setSearchQuery(''); setFilterType(''); setFilterStatus('') }}
            className="text-xs text-gray-500 underline px-2"
          >
            クリア
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow">
        {isLoading ? (
          <p className="p-6 text-gray-400 text-sm">読み込み中...</p>
        ) : filteredDocuments.length === 0 ? (
          <p className="p-6 text-gray-400 text-sm">
            {documents.length > 0 ? '条件に一致するドキュメントがありません' : 'ドキュメントがありません'}
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3">タイトル</th>
                <th className="px-4 py-3">種別</th>
                <th className="px-4 py-3">ステータス</th>
                <th className="px-4 py-3">AI タグ</th>
                <th className="px-4 py-3">サイズ</th>
                <th className="px-4 py-3">登録日</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filteredDocuments.map((doc) => {
                const s = STATUS_LABELS[doc.status] ?? { label: doc.status, cls: 'bg-blue-100 text-blue-700' }
                return (
                  <tr key={doc.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{doc.title}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${s.cls}`}>
                        {s.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(doc.tags ?? []).filter(t => t.startsWith('図面:') || t.startsWith('種別:')).map((tag) => (
                          <span
                            key={tag}
                            className="px-1.5 py-0.5 rounded text-xs bg-purple-100 text-purple-700"
                          >
                            {tag}
                          </span>
                        ))}
                        {(doc.tags ?? []).includes('ai分類済') && (
                          <span className="px-1.5 py-0.5 rounded text-xs bg-indigo-100 text-indigo-600">
                            ✦AI
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {(doc.file_size / 1024).toFixed(0)} KB
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(doc.created_at).toLocaleDateString('ja-JP')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-3">
                        <button
                          onClick={() => setPreviewDoc(doc)}
                          className="text-blue-600 hover:text-blue-800 text-xs"
                        >
                          プレビュー
                        </button>
                        <button
                          onClick={() => classify.mutate(doc.id)}
                          disabled={classify.isPending && classify.variables === doc.id}
                          className="text-purple-600 hover:text-purple-800 text-xs disabled:opacity-50"
                          title="Claude AIで文書を分類"
                        >
                          {classify.isPending && classify.variables === doc.id ? '分類中...' : 'AI分類'}
                        </button>
                        <button
                          onClick={() => remove.mutate(doc.id)}
                          className="text-red-500 hover:text-red-700 text-xs"
                        >
                          削除
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <DocumentPreviewModal
        documentId={previewDoc?.id ?? null}
        filename={previewDoc?.filename}
        title={previewDoc?.title}
        onClose={() => setPreviewDoc(null)}
      />

      {/* AI Classification Result Modal */}
      {aiResult && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setAiResult(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-800">✦ AI 分類結果</h2>
              <button onClick={() => setAiResult(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">図面種別</dt>
                <dd className="font-medium">{aiResult.drawing_type ?? '—'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">プロジェクト種別</dt>
                <dd className="font-medium">{aiResult.project_type ?? '—'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">信頼度</dt>
                <dd className="font-medium">{(aiResult.confidence * 100).toFixed(0)}%</dd>
              </div>
              <div>
                <dt className="text-gray-500 mb-1">付与タグ</dt>
                <dd className="flex flex-wrap gap-1">
                  {aiResult.tags.map((tag) => (
                    <span key={tag} className="px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-700">
                      {tag}
                    </span>
                  ))}
                </dd>
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <dt>モデル</dt>
                <dd>{aiResult.model}</dd>
              </div>
            </dl>
            <button
              onClick={() => setAiResult(null)}
              className="mt-4 w-full bg-blue-700 text-white py-2 rounded-lg text-sm"
            >
              閉じる
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
