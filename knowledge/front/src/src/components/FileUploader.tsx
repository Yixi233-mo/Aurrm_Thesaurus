import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import type { ImportFileItem } from '../types'

interface FileUploaderProps {
  onUpload: (file: File) => void
}

export function FileUploader({ onUpload }: FileUploaderProps) {
  const onDrop = useCallback(
    (files: File[]) => {
      files.forEach((f) => onUpload(f))
    },
    [onUpload],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/markdown': ['.md', '.markdown'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB
  })

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-xl p-10 text-center cursor-pointer
        transition-all duration-200 select-none
        ${isDragActive
          ? 'border-[var(--skin-accent-warm)] bg-[var(--skin-accent-warm)]/10 scale-[1.01] shadow-inner'
          : 'border-[var(--theme-border)] bg-[var(--theme-bg-card)] hover:border-[var(--skin-accent-warm)]/60 hover:bg-[var(--skin-accent-warm)]/5'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div className={`
          w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-200
          ${isDragActive ? 'bg-[var(--skin-accent-warm)]/20 scale-110' : 'bg-[var(--skin-accent-warm)]/10'}
        `}>
          <svg className={`w-7 h-7 transition-colors duration-200 ${isDragActive ? 'text-[var(--skin-accent)]' : 'text-[var(--skin-accent-warm)]'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--skin-text-primary)]">
            {isDragActive ? '释放文件以上传' : '点击或拖拽文件到此处'}
          </p>
          <p className="text-xs text-[var(--theme-text-secondary)] mt-1">支持 PDF、Markdown 格式，单文件最大 100MB</p>
        </div>
      </div>
    </div>
  )
}

// ==================== Import File Card ==================

interface ImportFileCardProps {
  file: ImportFileItem
}

export function ImportFileCard({ file }: ImportFileCardProps) {
  type StatusKey = ImportFileItem['status']

  const statusMap: Record<StatusKey, { label: string; bg: string; text: string }> = {
    uploading: { label: '上传中', bg: 'bg-[var(--skin-accent-warm)]/10', text: 'text-[var(--skin-accent)]' },
    processing: { label: '处理中', bg: 'bg-[var(--skin-accent)]/10', text: 'text-[var(--skin-accent)]' },
    completed: { label: '已完成', bg: 'bg-[var(--skin-accent-warm)]/10', text: 'text-[var(--skin-accent-warm)]' },
    error: { label: '失败', bg: 'bg-red-500/10', text: 'text-red-400' },
  }

  const s = statusMap[file.status]
  const totalNodes = 8
  const progress = file.doneList.length > 0
    ? Math.round((file.doneList.length / totalNodes) * 100)
    : 0

  return (
    <div className={`
      bg-[var(--theme-bg-card)] rounded-xl border border-[var(--theme-border)] shadow-sm hover:shadow-md hover:border-[var(--skin-accent-warm)]/25
      transition-all duration-200 p-4
    `}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-10 h-10 rounded-lg ${s.bg} flex items-center justify-center shrink-0`}>
            <svg className={`w-5 h-5 ${s.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-[var(--theme-text-primary)] truncate">{file.name}</p>
            <p className="text-xs text-[var(--theme-text-secondary)] mt-0.5">
              {(file.size / 1024).toFixed(1)} KB &middot; {s.label}
            </p>
          </div>
        </div>

        <span className={`
          px-2.5 py-1 rounded-md text-xs font-medium ${s.bg} ${s.text}
        `}>
          {s.label}
        </span>
      </div>

      {/* 进度条 */}
      {(file.status === 'uploading' || file.status === 'processing') && (
        <div className="mt-3">
          <div className="h-1.5 bg-[var(--theme-border)] rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                (file.status as string) === 'completed' ? 'bg-[var(--skin-accent-warm)]' :
                (file.status as string) === 'error' ? 'bg-red-500' : 'bg-[var(--skin-accent)]'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* 阶段步骤 */}
      {(file.doneList.length > 0 || file.runningList.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {file.doneList.map((step: string) => (
            <span key={step} className="text-[11px] px-2 py-0.5 rounded bg-[var(--skin-accent-warm)]/10 text-[var(--skin-accent-warm)] font-medium flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              {step}
            </span>
          ))}
          {file.runningList.map((step: string) => (
            <span key={step} className="text-[11px] px-2 py-0.5 rounded bg-[var(--skin-accent)]/10 text-[var(--skin-accent)] font-medium animate-pulse">
              {step}
            </span>
          ))}
        </div>
      )}

      {/* 错误信息 */}
      {file.status === 'error' && file.error && (
        <p className="mt-2 text-xs text-red-400">{file.error}</p>
      )}
    </div>
  )
}
