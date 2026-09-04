// 查询相关类型
export interface QueryRequest {
  query: string
  session_id?: string
  is_stream: boolean
}

export interface QuerySubmitResponse {
  message: string
  session_id: string
}

export interface HistoryItem {
  role: string
  text: string
  rewritten_query: string
  item_names: string[]
  ts?: number
}

export interface HistoryResponse {
  session_id: string
  items: HistoryItem[]
}

// SSE 事件类型
export interface SSEReadyEvent {
  type: 'ready'
}

export interface SSEProgressEvent {
  type: 'progress'
  done_list: string[]
  running_list: string[]
}

export interface SSEDeltaEvent {
  type: 'delta'
  delta: string
}

export interface SourceItem {
  idx: number
  source: string
  chunk_id?: string
  title?: string
  url?: string
  score?: number
}

export interface SSEFinalEvent {
  type: 'final'
  answer: string
  sources?: SourceItem[]
}

export type SSEEvent = SSEReadyEvent | SSEProgressEvent | SSEDeltaEvent | SSEFinalEvent

// 上传相关
export interface UploadResponse {
  message: string
  task_ids: string[]
}

export interface TaskStatusResponse {
  status: string
  done_list: string[]
  running_list: string[]
}

// 前端消息模型
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: number
  isStreaming?: boolean
  doneList?: string[]
  runningList?: string[]
  sources?: SourceItem[]
}

// 导入文件状态
export type ImportFileStatus = 'uploading' | 'processing' | 'completed' | 'error'

export interface ImportFileItem {
  id: string
  name: string
  size: number
  status: ImportFileStatus
  doneList: string[]
  runningList: string[]
  error?: string
}

// Toast 消息
export interface Toast {
  id: string
  type: 'success' | 'error' | 'info'
  message: string
}
