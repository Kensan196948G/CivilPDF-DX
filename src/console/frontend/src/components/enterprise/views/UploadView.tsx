import { useState, useCallback } from 'react'

interface ViewProps {
  onNavigate: (view: string) => void
  onShowModal: (content: { title: string; body: string }) => void
  onShowToast: (message: string, type?: 'ok' | 'warn' | 'error') => void
}

interface UploadFile {
  id: string
  name: string
  subLabel: string
  type: string
  size: string
  progress: number
  status: 'done' | 'uploading' | 'warn'
}

interface ProcessingOption {
  id: string
  label: string
  description: string
  value: boolean
}

interface StandardChip {
  id: string
  name: string
  version: string
  enabled: boolean
}

const INITIAL_FILES: UploadFile[] = [
  { id: 'f1', name: '特記仕様書_R6-04_rev2.pdf', subLabel: 'PDF · 3.1MB', type: 'PDF', size: '3.1MB', progress: 100, status: 'done' },
  { id: 'f2', name: '数量計算書_R6-04.xlsx', subLabel: 'XLSX · 22MB', type: 'XLS', size: '22MB', progress: 100, status: 'done' },
  { id: 'f3', name: '県道○○号_詳細図_Rev04.dwg', subLabel: 'DWG · 218MB', type: 'DWG', size: '218MB', progress: 64, status: 'uploading' },
  { id: 'f4', name: 'グリーンファイル一式.zip', subLabel: 'ZIP · 8.4MB', type: 'ZIP', size: '8.4MB', progress: 100, status: 'done' },
]

const INITIAL_OPTIONS: ProcessingOption[] = [
  { id: 'ocr', label: 'OCR テキスト抽出', description: 'Tesseract (jpn) で全ページをOCR処理', value: true },
  { id: 'table', label: '表データ抽出', description: '図面・仕様書内の表を構造化データに変換', value: true },
  { id: 'standard', label: '基準突合チェック', description: '国交省基準・設計図書と自動照合', value: true },
  { id: 'pdfa', label: 'PDF/A 変換', description: '電子納品用 PDF/A-1b へ変換', value: false },
  { id: 'stamp', label: '電子印鑑 検出', description: '承認印・確認印の有無を検出', value: true },
  { id: 'meta', label: 'メタデータ埋込み', description: '工事番号・作成者情報をメタデータに付与', value: true },
  { id: 'thumb', label: 'サムネイル生成', description: '各ページのプレビュー画像を生成', value: false },
]

const INITIAL_STANDARDS: StandardChip[] = [
  { id: 's1', name: '国交省電子納品要領', version: 'R5版', enabled: true },
  { id: 's2', name: '道路設計要領', version: '2023年', enabled: true },
  { id: 's3', name: '橋梁設計標準', version: 'H29版', enabled: false },
]

function fileIconBg(type: string): { bg: string; color: string } {
  switch (type) {
    case 'PDF': return { bg: 'var(--danger-soft)', color: 'var(--danger)' }
    case 'XLS': return { bg: 'var(--success-soft)', color: 'var(--success)' }
    case 'DWG': return { bg: 'var(--info-soft)', color: 'var(--info)' }
    default: return { bg: 'var(--surface-2)', color: 'var(--muted)' }
  }
}

export function UploadView({ onNavigate, onShowToast }: ViewProps) {
  const [files, setFiles] = useState<UploadFile[]>(INITIAL_FILES)
  const [options, setOptions] = useState<ProcessingOption[]>(INITIAL_OPTIONS)
  const [standards, setStandards] = useState<StandardChip[]>(INITIAL_STANDARDS)
  const [isDragging, setIsDragging] = useState(false)

  const handleDropzoneClick = useCallback(() => {
    onShowToast('ファイルを選択してください')
  }, [onShowToast])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    onShowToast('ファイルを選択してください')
  }, [onShowToast])

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }, [])

  const toggleOption = useCallback((id: string) => {
    setOptions((prev) =>
      prev.map((o) => (o.id === id ? { ...o, value: !o.value } : o))
    )
  }, [])

  const toggleStandard = useCallback((id: string) => {
    setStandards((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s))
    )
  }, [])

  const enabledCount = options.filter((o) => o.value).length
  const doneCount = files.filter((f) => f.status === 'done').length

  return (
    <div className="ep-upload-grid">
      {/* Left: dropzone + file list */}
      <div>
        {/* Dropzone */}
        <div
          className={`ep-dropzone${isDragging ? ' drag' : ''}`}
          onClick={handleDropzoneClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleDropzoneClick() }}
          aria-label="ファイルをドロップまたはクリックして選択"
        >
          <div className="ic">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 16V8m0 0-3 3m3-3 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M20 16.7A4 4 0 0 0 18 9h-1.26A7 7 0 1 0 4 15.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h3>ファイルをドロップ</h3>
          <p>PDF・DWG・XLSX・画像ファイルをドラッグ&ドロップ<br />または<strong>クリックしてファイルを選択</strong></p>
          <div className="file-types">対応形式: PDF · DWG · DXF · XLSX · CSV · JPG · PNG · TIFF · ZIP</div>
        </div>

        {/* File list */}
        <div className="ep-upload-list">
          <div className="ep-ul-head">
            <span />
            <span>ファイル名</span>
            <span>状態</span>
            <span>進捗</span>
            <span>サイズ</span>
            <span>処理</span>
            <span />
          </div>
          {files.map((file) => {
            const { bg, color } = fileIconBg(file.type)
            const progressClass = file.status === 'done'
              ? 'ep-progress done'
              : file.status === 'warn'
              ? 'ep-progress warn'
              : 'ep-progress'
            return (
              <div key={file.id} className="ep-ul-row">
                <div
                  className="ep-file-ic"
                  style={{ background: bg, color }}
                >
                  {file.type.slice(0, 3)}
                </div>
                <div>
                  <div className="ep-fname">{file.name}</div>
                  <div className="ep-fsub">{file.subLabel}</div>
                </div>
                <div>
                  {file.status === 'done' ? (
                    <span className="ep-pill ep-pill-ok">完了</span>
                  ) : file.status === 'warn' ? (
                    <span className="ep-pill ep-pill-warn">警告</span>
                  ) : (
                    <span className="ep-pill ep-pill-info-2">転送中</span>
                  )}
                </div>
                <div className={progressClass}>
                  <div style={{ width: `${file.progress}%` }} />
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--muted)' }}>
                  {file.size}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--muted)' }}>
                  {file.progress}%
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(file.id)}
                  aria-label={`${file.name}を削除`}
                  style={{ width: '18px', height: '18px', display: 'grid', placeItems: 'center', color: 'var(--muted)', borderRadius: '3px', cursor: 'pointer', background: 'none', border: 'none' }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--danger)' }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--muted)' }}
                >
                  ✕
                </button>
              </div>
            )
          })}
        </div>

        {/* Run bar */}
        <div className="ep-run-bar">
          <div className="summary">
            <strong>{files.length}</strong> ファイル ·{' '}
            <strong>{doneCount}</strong> 転送完了 ·{' '}
            <strong>{enabledCount}</strong> 処理オプション有効
          </div>
          <button
            className="ep-btn ep-btn-primary"
            type="button"
            onClick={() => onNavigate('viewer')}
          >
            処理を実行 →
          </button>
        </div>
      </div>

      {/* Right: processing options */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>処理オプション</h3>
            <span className="meta">{enabledCount}/{options.length} 有効</span>
          </div>
          <div className="ep-panel-body">
            {options.map((opt) => (
              <div key={opt.id} className="ep-opt-row">
                <div className="lbl">
                  {opt.label}
                  <small>{opt.description}</small>
                </div>
                <div
                  className={`ep-toggle${opt.value ? ' on' : ''}`}
                  role="switch"
                  aria-checked={opt.value}
                  tabIndex={0}
                  onClick={() => toggleOption(opt.id)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleOption(opt.id) }}
                  aria-label={opt.label}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>適用基準</h3>
            <span className="meta">{standards.filter((s) => s.enabled).length} 選択中</span>
          </div>
          <div className="ep-panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {standards.map((std) => (
              <div
                key={std.id}
                className="ep-std-chip"
                onClick={() => toggleStandard(std.id)}
                role="checkbox"
                aria-checked={std.enabled}
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleStandard(std.id) }}
              >
                <div>
                  <span className="name">{std.name}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                  <span className="ver">{std.version}</span>
                  <div
                    className={`ep-toggle${std.enabled ? ' on' : ''}`}
                    style={{ pointerEvents: 'none' }}
                    aria-hidden="true"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="ep-panel">
          <div className="ep-panel-head">
            <h3>出力設定</h3>
          </div>
          <div className="ep-panel-body">
            <div className="ep-opt-row">
              <div className="lbl">
                出力フォルダー
                <small>処理済みファイルの保存先</small>
              </div>
              <select className="ep-select" aria-label="出力フォルダー">
                <option>2024-038/図書</option>
                <option>2024-041/図書</option>
                <option>一時フォルダー</option>
              </select>
            </div>
            <div className="ep-opt-row">
              <div className="lbl">
                命名規則
                <small>ファイル名の自動整形ルール</small>
              </div>
              <select className="ep-select" aria-label="命名規則">
                <option>国交省標準</option>
                <option>社内標準</option>
                <option>元ファイル名</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
