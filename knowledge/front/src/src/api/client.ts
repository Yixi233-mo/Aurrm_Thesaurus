import type { QuerySubmitResponse, HistoryItem, HistoryResponse, TaskStatusResponse, UploadResponse, SSEProgressEvent, SSEDeltaEvent, SSEFinalEvent, SourceItem } from '../types'

// 自动检测 API 基址：同源时为空字符串
function getApiBase(): string {
  if (location.protocol === 'http:' || location.protocol === 'https:') {
    return ''
  }
  return 'http://127.0.0.1:8001'
}

export const API_BASE = getApiBase()

// 导入服务基址：将查询服务的 8001 替换为 8000
export function getImportBase(): string {
  const base = API_BASE
  if (base.includes(':8001')) {
    return base.replace(':8001', ':8000')
  }
  if (base === '') {
    return '' // 同源时两个服务都在同一域名下
  }
  return base
}

// ==================== SSE Hook ====================

import { useEffect, useRef } from 'react'

// Re-export types for convenience
export type { HistoryItem, SSEProgressEvent, SSEDeltaEvent, SSEFinalEvent } from '../types'

type SSECallbacks = {
  onProgress: (data: SSEProgressEvent) => void
  onDelta: (data: SSEDeltaEvent) => void
  onFinal: (data: SSEFinalEvent & { sources?: SourceItem[] }) => void
  onError: (message: string) => void
}

export function useSSE(taskId: string | null, callbacks: SSECallbacks) {
  const callbacksRef = useRef(callbacks)
  const retryCountRef = useRef(0)
  callbacksRef.current = callbacks

  useEffect(() => {
    if (!taskId) return

    const baseUrl = API_BASE || window.location.origin
    const es = new EventSource(`${baseUrl}/stream/${taskId}`)

    es.addEventListener('ready', () => {
      retryCountRef.current = 0
    })

    es.addEventListener('progress', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as SSEProgressEvent
        callbacksRef.current.onProgress(data)
      } catch {
        // 忽略无法解析的事件
      }
    })

    es.addEventListener('delta', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as SSEDeltaEvent
        callbacksRef.current.onDelta(data)
      } catch {
        // 忽略
      }
    })

    es.addEventListener('final', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as SSEFinalEvent
        callbacksRef.current.onFinal(data)
      } catch {
        // 忽略
      }
      es.close()
    })

    es.onerror = () => {
      retryCountRef.current += 1
      if (retryCountRef.current >= 5) {
        callbacksRef.current.onError('SSE 连接中断，请刷新页面重试')
        es.close()
      }
      // 否则不主动关闭，交由 EventSource 内置重连机制自动恢复
    }

    return () => {
      es.close()
    }
  }, [taskId])
}

// ==================== HTTP 请求 ====================

export async function submitQuery(
  query: string,
  sessionId: string,
  isStream: boolean,
): Promise<QuerySubmitResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId, is_stream: isStream }),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => `请求失败 (HTTP ${res.status})`)
    throw new Error(text)
  }
  return res.json()
}

export function getQueryBase(): string {
  return API_BASE
}

export async function fetchHistory(sessionId: string): Promise<HistoryItem[]> {
  try {
    const res = await fetch(`${API_BASE}/history/${sessionId}`)
    if (!res.ok) return []
    const data = await res.json() as HistoryResponse
    return data.items || []
  } catch {
    return []
  }
}

export async function clearHistoryApi(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/history/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(`清空历史失败 (HTTP ${res.status})`)
  }
}

// ==================== 导入 API ====================

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))

  const res = await fetch(`${getImportBase()}/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => `上传失败 (HTTP ${res.status})`)
    throw new Error(text)
  }
  return res.json()
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await fetch(`${getImportBase()}/status/${taskId}`)
  if (!res.ok) {
    throw new Error(`状态查询失败 (HTTP ${res.status})`)
  }
  return res.json()
}

// Re-export showToast from Toast component
export { showToast } from '../components/Toast'
