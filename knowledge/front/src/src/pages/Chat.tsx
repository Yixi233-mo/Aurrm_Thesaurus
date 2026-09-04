import { useState, useRef, useEffect, useCallback } from 'react'
import { useChatStore } from '../store'
import { ChatMessage } from '../components/ChatMessage'
import { ThemeToggle } from '../components/ThemeToggle'
import { useSSE, submitQuery, fetchHistory, showToast } from '../api/client'
import type { HistoryItem, SSEProgressEvent, SSEDeltaEvent, SSEFinalEvent } from '../api/client'
import { useAutoResize } from '../hooks/useAutoResize'

export function ChatPage() {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 皮肤状态检测（用于璇玑专属装饰）
  const [skin, setSkin] = useState<string>(() => localStorage.getItem('skin') || 'skin-gambit-dark')
  useEffect(() => {
    const handler = () => setSkin(localStorage.getItem('skin') || 'skin-gambit-dark')
    window.addEventListener('skin-changed', handler)
    return () => window.removeEventListener('skin-changed', handler)
  }, [])
  const isXuanji = skin === 'skin-xuanji'

  const {
    sessionId,
    messages,
    isLoading,
    streamingText,
    currentTaskId,
    addMessage,
    updateLastAssistantMessage,
    setIsLoading,
    setStreamingText,
    setCurrentTaskId,
    setProgress,
    clearMessages,
    resetSessionId,
    lastSources,
    setLastSources,
  } = useChatStore()

  useAutoResize(textareaRef, input)

  // 加载历史记录
  useEffect(() => {
    fetchHistory(sessionId).then((items: HistoryItem[]) => {
      if (items.length > 0) {
        items.forEach((item: HistoryItem) => {
          addMessage({
            id: crypto.randomUUID(),
            role: item.role as 'user' | 'assistant',
            text: item.text,
            timestamp: item.ts || Date.now(),
          })
        })
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  // SSE 流式处理
  useSSE(currentTaskId, {
    onProgress: (data: SSEProgressEvent) => {
      setProgress(data.done_list, data.running_list)
      updateLastAssistantMessage({
        doneList: data.done_list,
        runningList: data.running_list,
      })
    },
    onDelta: (data: SSEDeltaEvent) => {
      const newText = streamingText + data.delta
      setStreamingText(newText)
      updateLastAssistantMessage({ text: newText })
    },
    onFinal: (data: SSEFinalEvent) => {
      updateLastAssistantMessage({
        text: data.answer,
        isStreaming: false,
        doneList: [],
        runningList: [],
        sources: data.sources || [],
      })
      setStreamingText('')
      setIsLoading(false)
      setCurrentTaskId(null)
      setProgress([], [])
      setLastSources(data.sources || [])
    },
    onError: (msg: string) => {
      showToast('error', msg)
      updateLastAssistantMessage({ isStreaming: false, text: '抱歉，连接中断，请稍后重试。' })
      setStreamingText('')
      setIsLoading(false)
      setCurrentTaskId(null)
      setProgress([], [])
    },
  })

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isLoading) return

    setInput('')
    addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      text,
      timestamp: Date.now(),
    })

    // 创建 AI 占位消息
    addMessage({
      id: crypto.randomUUID(),
      role: 'assistant',
      text: '',
      timestamp: Date.now(),
      isStreaming: true,
      doneList: [],
      runningList: [],
    })
    setIsLoading(true)
    setStreamingText('')

    try {
      const response = await submitQuery(text, sessionId, true)
      setCurrentTaskId(response.session_id)
    } catch (err) {
      const message = err instanceof Error ? err.message : '请求失败'
      showToast('error', message)
      updateLastAssistantMessage({ isStreaming: false, text: `抱歉，请求失败：${message}` })
      setStreamingText('')
      setIsLoading(false)
    }
  }, [input, isLoading, sessionId, addMessage, updateLastAssistantMessage, setIsLoading, setStreamingText, setCurrentTaskId])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleStop = () => {
    setIsLoading(false)
    setStreamingText('')
    setCurrentTaskId(null)
    setProgress([], [])
    updateLastAssistantMessage({ isStreaming: false, text: streamingText || '已停止生成。' })
  }

  const handleNewSession = () => {
    resetSessionId()
    clearMessages()
    showToast('info', '已创建新对话')
  }

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden">
      {/* 顶部 Header */}
      <header className="shrink-0 bg-[var(--theme-bg-card)]/70 backdrop-blur-sm border-b border-[var(--theme-border)] px-6 py-3.5 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="w-8 h-8 rounded-lg border border-[var(--skin-accent-warm)]/30 flex items-center justify-center relative">
            <div className="absolute inset-0 rounded-lg bg-[var(--skin-accent-warm)]/5" />
            <svg className="w-4 h-4 text-[var(--skin-accent-warm)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 4.168 6.253v13C4.168 19.223 5.754 19 7.5 19s3.332.477 3.332 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 3.332 1.253v13C19.832 19.223 18.247 19 16.5 19s-3.332.477-3.332 1.253" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-[var(--skin-accent-warm)]" style={{ fontFamily: 'var(--font-display)' }}>
              智能问答
            </h1>
            <p className="text-[11px] text-[var(--theme-text-secondary)]">输入问题，获取知识库精准回答</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            onClick={handleNewSession}
            className="text-xs text-[var(--theme-text-secondary)] hover:text-[var(--skin-accent)] px-3 py-1.5 rounded-lg hover:bg-[var(--skin-accent)]/10 transition-all duration-200"
          >
            新建对话
          </button>
        </div>
      </header>

      {/* 消息流 */}
      <main className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center animate-fade-in-up">
              {/* 筹码/宝石装饰 */}
              <div className="w-16 h-16 rounded-2xl border border-[var(--skin-accent-warm)]/20 flex items-center justify-center mb-4 relative bg-[var(--skin-accent-warm)]/5">
                <div className="absolute inset-2 rounded-xl border border-[var(--skin-accent-warm)]/10" />
                <svg className="w-8 h-8 text-[var(--skin-accent-warm)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.002 4.002 0 01-3.09-3.09L2.25 12l2.846-.813a4.002 4.002 0 013.09-3.09L9 5.25l.813 2.846a4.002 4.002 0 013.09 3.09L15.75 12l-2.846.813a4.002 4.002 0 01-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-[var(--theme-text-primary)]" style={{ fontFamily: 'var(--font-display)' }}>
                欢迎使用璇玑金策
              </h2>
              {/* 璇玑专属：星轨分隔线 */}
              {isXuanji && (
                <div className="relative flex items-center gap-3 my-4 w-full max-w-xs mx-auto">
                  <div className="flex-1 h-[1px] bg-gradient-to-r from-transparent via-[var(--skin-accent)]/30 to-transparent" />
                  <span className="text-[var(--skin-accent)] text-xs tracking-[0.2em]">✦ 璇玑策 ✦</span>
                  <div className="flex-1 h-[1px] bg-gradient-to-r from-transparent via-[var(--skin-accent)]/30 to-transparent" />
                </div>
              )}
              <p className="text-sm text-[var(--theme-text-secondary)] mt-2 max-w-md">
                请输入您的问题，系统将从金融知识库中检索相关内容并生成结构化回答
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['华夏债券基金的基本情况', '什么是ETF基金？', '理财产品的风险等级有哪些？'].map((q) => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="text-xs px-3 py-1.5 rounded-full bg-[var(--theme-bg-card)] border border-[var(--theme-border)] text-[var(--theme-text-secondary)] hover:border-[var(--skin-accent-warm)]/40 hover:text-[var(--skin-accent-warm)] transition-all duration-200"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg: import('../types').ChatMessage) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isStreaming={msg.isStreaming}
                sources={msg.role === 'assistant' ? lastSources : undefined}
              />
            ))
          )}
          <div className="h-4" />
        </div>
      </main>

      {/* 底部输入区 */}
      <footer className="shrink-0 bg-[var(--theme-bg-card)]/80 backdrop-blur-sm border-t border-[var(--theme-border)] px-4 py-3">
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="请输入您的问题...（Enter 发送，Shift+Enter 换行）"
              className="w-full resize-none rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-input)] px-4 py-3 text-sm text-[var(--theme-text-primary)] placeholder:text-[var(--theme-text-secondary)] focus:outline-none focus:border-[var(--skin-accent)]/60 focus:ring-1 focus:ring-[var(--skin-accent)]/20 transition-all duration-200"
              rows={1}
              disabled={isLoading}
            />
          </div>
          <button
            onClick={isLoading ? handleStop : handleSend}
            disabled={!input.trim() && !isLoading}
            className={`
              shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
              transition-all duration-200
              ${
                isLoading
                  ? 'bg-red-500/90 hover:bg-red-500 text-white'
                  : 'bg-gradient-to-br from-[var(--skin-accent-warm)] to-[var(--skin-accent-warm-hover)] text-[var(--skin-bg-card)] hover:shadow-lg hover:shadow-[var(--skin-accent-warm)]/20 disabled:opacity-40 disabled:cursor-not-allowed'
              }
            `}
            aria-label={isLoading ? '停止生成' : '发送'}
          >
            {isLoading ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 7.5A2.25 2.25 0 017.5 5.25h9a2.25 2.25 0 012.25 2.25v9a2.25 2.25 0 01-2.25 2.25h-9a2.25 2.25 0 01-2.25-2.25v-9z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12z" />
              </svg>
            )}
          </button>
        </div>
        <p className="text-[10px] text-[var(--theme-text-secondary)] text-center mt-2">
          璇玑金策仅提供信息参考，不构成投资建议
        </p>
      </footer>
    </div>
  )
}
