import { useCallback, useEffect, useRef } from 'react'
import { useImportStore } from '../store'
import { FileUploader, ImportFileCard } from '../components/FileUploader'
import { ThemeToggle } from '../components/ThemeToggle'
import type { ImportFileItem } from '../types'
import { uploadFiles, fetchTaskStatus, showToast } from '../api/client'

export function ImportPage() {
  const { files, addFile, updateFile } = useImportStore()
  const pollingRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())

  // 组件卸载时清理所有轮询
  useEffect(() => {
    return () => {
      pollingRef.current.forEach((interval) => clearInterval(interval))
      pollingRef.current.clear()
    }
  }, [])

  const handleUpload = useCallback(
    async (file: File) => {
      const id = crypto.randomUUID()

      // 创建文件记录
      addFile({
        id,
        name: file.name,
        size: file.size,
        status: 'uploading',
        doneList: [],
        runningList: [],
      })

      try {
        // 更新为上传完成，开始处理
        updateFile(id, { status: 'processing' })

        const response = await uploadFiles([file])
        const taskId = response.task_ids[0]

        if (!taskId) {
          updateFile(id, { status: 'error', error: '未获取到任务 ID' })
          return
        }

        // 轮询任务状态
        const interval = setInterval(async () => {
          try {
            const data = await fetchTaskStatus(taskId)

            if (data.status === 'success') {
              updateFile(id, {
                status: 'completed',
                doneList: data.done_list,
                runningList: [],
              })
              clearInterval(interval)
              pollingRef.current.delete(taskId)
              showToast('success', `"${file.name}" 导入成功`)
            } else if (data.status === 'failed') {
              updateFile(id, {
                status: 'error',
                doneList: data.done_list,
                runningList: data.running_list,
                error: '导入失败，请检查文件格式',
              })
              clearInterval(interval)
              pollingRef.current.delete(taskId)
              showToast('error', `"${file.name}" 导入失败`)
            } else {
              updateFile(id, {
                status: 'processing',
                doneList: data.done_list,
                runningList: data.running_list,
              })
            }
          } catch {
            // 网络错误，静默重试
          }
        }, 1500)

        pollingRef.current.set(taskId, interval)
      } catch (err) {
        updateFile(id, {
          status: 'error',
          error: err instanceof Error ? err.message : '上传失败',
        })
        showToast('error', `"${file.name}" 上传失败`)
      }
    },
    [addFile, updateFile],
  )

  // 统计
  const stats = {
    total: files.length,
    uploading: files.filter((f: ImportFileItem) => f.status === 'uploading').length,
    processing: files.filter((f: ImportFileItem) => f.status === 'processing').length,
    completed: files.filter((f: ImportFileItem) => f.status === 'completed').length,
    error: files.filter((f: ImportFileItem) => f.status === 'error').length,
  }

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden">
      {/* 顶部 Header */}
      <header className="shrink-0 bg-[var(--theme-bg-card)]/70 backdrop-blur-sm border-b border-[var(--theme-border)] px-6 py-3.5 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--skin-accent-warm)] to-[var(--skin-accent-warm-hover)] flex items-center justify-center shadow-md shadow-[var(--skin-accent-warm)]/15">
            <svg className="w-4 h-4 text-[var(--skin-bg-card)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-[var(--skin-accent-warm)]" style={{ fontFamily: 'var(--font-display)' }}>文档导入</h1>
            <p className="text-[11px] text-[var(--theme-text-secondary)]">上传 PDF / Markdown 文件，自动解析并入库</p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      {/* 主内容 */}
      <main className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {/* 上传区域 */}
          <FileUploader onUpload={handleUpload} />

          {/* 统计卡片 */}
          {files.length > 0 && (
            <div className="grid grid-cols-5 gap-3">
              <StatCard label="总计" value={stats.total} color="bone" />
              <StatCard label="上传中" value={stats.uploading} color="gold" />
              <StatCard label="处理中" value={stats.processing} color="peacock" />
              <StatCard label="已完成" value={stats.completed} color="gold" />
              <StatCard label="失败" value={stats.error} color="red" />
            </div>
          )}

          {/* 文件列表 */}
          {files.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-[var(--theme-text-secondary)] uppercase tracking-wider px-1">
                导入记录 ({files.length})
              </h3>
              {files.map((file: ImportFileItem) => (
                <ImportFileCard key={file.id} file={file} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

// ==================== 统计卡片 ==================

interface StatCardProps {
  label: string
  value: number
  color: 'bone' | 'gold' | 'peacock' | 'red'
}

function StatCard({ label, value, color }: StatCardProps) {
  const colorMap = {
    bone: 'bg-[var(--theme-bg-card)] text-[var(--theme-text-primary)] border-[var(--theme-border)]',
    gold: 'bg-[var(--skin-accent-warm)]/10 text-[var(--skin-accent-warm)] border-[var(--skin-accent-warm)]/20',
    peacock: 'bg-[var(--skin-accent)]/10 text-[var(--skin-accent)] border-[var(--skin-accent)]/30',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
  }

  return (
    <div className={`rounded-xl border ${colorMap[color]} px-4 py-3 transition-all duration-200`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs mt-0.5 opacity-80">{label}</p>
    </div>
  )
}
