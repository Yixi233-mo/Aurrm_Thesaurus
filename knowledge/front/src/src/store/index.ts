import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ChatMessage, Toast, ImportFileItem, SourceItem } from '../types'

// ==================== Chat Store ====================

interface ChatState {
  // 会话 ID：持久化到 localStorage
  sessionId: string
  setSessionId: (id: string) => void
  resetSessionId: () => void

  // 消息列表
  messages: ChatMessage[]
  addMessage: (msg: ChatMessage) => void
  updateLastAssistantMessage: (updates: Partial<ChatMessage>) => void
  clearMessages: () => void

  // 流式状态
  streamingText: string
  setStreamingText: (text: string) => void

  // 加载状态
  isLoading: boolean
  setIsLoading: (v: boolean) => void

  // 当前任务 ID（用于 SSE）
  currentTaskId: string | null
  setCurrentTaskId: (id: string | null) => void

  // 进度信息
  progressDoneList: string[]
  progressRunningList: string[]
  setProgress: (done: string[], running: string[]) => void

  // 最近回答的来源
  lastSources: SourceItem[]
  setLastSources: (sources: SourceItem[]) => void

  // Toast 通知
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, _get) => ({
      // 会话 ID
      sessionId: crypto.randomUUID(),
      setSessionId: (id) => set({ sessionId: id }),
      resetSessionId: () => set({ sessionId: crypto.randomUUID() }),

      // 消息
      messages: [],
      addMessage: (msg) =>
        set((s) => ({ messages: [...s.messages, msg] })),
      updateLastAssistantMessage: (updates) =>
        set((s) => {
          const msgs = [...s.messages]
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].role === 'assistant') {
              msgs[i] = { ...msgs[i], ...updates }
              break
            }
          }
          return { messages: msgs }
        }),
      clearMessages: () => set({ messages: [] }),

      // 流式
      streamingText: '',
      setStreamingText: (text) => set({ streamingText: text }),

      // 加载
      isLoading: false,
      setIsLoading: (v) => set({ isLoading: v }),

      // 任务 ID
      currentTaskId: null,
      setCurrentTaskId: (id) => set({ currentTaskId: id }),

      // 进度
      progressDoneList: [],
      progressRunningList: [],
      setProgress: (done, running) => set({ progressDoneList: done, progressRunningList: running }),

      // 来源
      lastSources: [],
      setLastSources: (sources) => set({ lastSources: sources }),

      // Toast
      toasts: [],
      addToast: (toast) => {
        const id = crypto.randomUUID()
        set((s) => ({
          toasts: [...s.toasts, { ...toast, id }],
        }))
        // 自动移除
        setTimeout(() => {
          set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
        }, toast.type === 'error' ? 5000 : 3000)
      },
      removeToast: (id) =>
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
    }),
    {
      name: 'kb-session-storage',
      partialize: (state) => ({ sessionId: state.sessionId }),
    },
  ),
)

// ==================== Import Store ====================

interface ImportState {
  files: ImportFileItem[]
  setFiles: (files: ImportFileItem[]) => void
  addFile: (file: ImportFileItem) => void
  updateFile: (id: string, updates: Partial<ImportFileItem>) => void
}

export const useImportStore = create<ImportState>()((set, _get) => ({
  files: [],
  setFiles: (files) => set({ files }),
  addFile: (file) =>
    set((s) => ({ files: [file, ...s.files] })),
  updateFile: (id, updates) =>
    set((s) => ({
      files: s.files.map((f) => (f.id === id ? { ...f, ...updates } : f)),
    })),
}))
