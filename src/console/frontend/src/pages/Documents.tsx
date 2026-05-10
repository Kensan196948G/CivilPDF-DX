import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listDocuments, uploadDocument, deleteDocument } from '../api/documents'
import { listProjects } from '../api/projects'

export function Documents() {
  const qc = useQueryClient()
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => listDocuments(),
  })
  const { data: projects = [] } = useQuery({ queryKey: ['projects'], queryFn: listProjects })

  const [showUpload, setShowUpload] = useState(false)
  const [title, setTitle] = useState('')
  const [projectId, setProjectId] = useState('')
  const [docType, setDocType] = useState('drawing')
  const fileRef = useRef<HTMLInputElement>(null)

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
              <label className="block text-sm text-gray-600 mb-1">タイトル</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">プロジェクト</label>
              <select
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
              <label className="block text-sm text-gray-600 mb-1">種別</label>
              <select
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
              <label className="block text-sm text-gray-600 mb-1">PDFファイル</label>
              <input type="file" accept=".pdf" ref={fileRef} className="text-sm" />
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

      <div className="bg-white rounded-xl shadow">
        {isLoading ? (
          <p className="p-6 text-gray-400 text-sm">読み込み中...</p>
        ) : documents.length === 0 ? (
          <p className="p-6 text-gray-400 text-sm">ドキュメントがありません</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3">タイトル</th>
                <th className="px-4 py-3">種別</th>
                <th className="px-4 py-3">ステータス</th>
                <th className="px-4 py-3">サイズ</th>
                <th className="px-4 py-3">登録日</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{doc.title}</td>
                  <td className="px-4 py-3 text-gray-500">{doc.document_type}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {(doc.file_size / 1024).toFixed(0)} KB
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(doc.created_at).toLocaleDateString('ja-JP')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => remove.mutate(doc.id)}
                      className="text-red-500 hover:text-red-700 text-xs"
                    >
                      削除
                    </button>
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
