import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage, SourceItem } from '../types'
import { SourcePanel } from './SourcePanel'

interface ChatMessageProps {
  message: ChatMessage
  isStreaming?: boolean
  sources?: SourceItem[]
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export function ChatMessage({ message, isStreaming, sources }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const resolvedSources = sources ?? message.sources

  return (
    <div
      className={`flex gap-3 mb-5 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* AI 头像 */}
      {!isUser && (
        <div className="w-8 h-8 rounded-lg border border-[var(--skin-accent-warm)]/30 flex items-center justify-center shrink-0 mt-1 bg-[var(--skin-accent-warm)]/10">
          <svg className="w-4 h-4 text-[var(--skin-accent-warm)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.002 4.002 0 01-3.09-3.09L2.25 12l2.846-.813a4.002 4.002 0 013.09-3.09L9 5.25l.813 2.846a4.002 4.002 0 013.09 3.09L15.75 12l-2.846.813a4.002 4.002 0 01-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
        </div>
      )}

      <div className={`max-w-[78%] min-w-0 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* 气泡 */}
        <div
          className={`
            rounded-xl px-4 py-3 text-sm leading-relaxed
            transition-all duration-200
            ${
              isUser
                ? 'bg-gradient-to-br from-[var(--skin-accent-warm)] to-[var(--skin-accent-warm-hover)] text-[var(--skin-bg-card)] rounded-br-md shadow-lg shadow-[var(--skin-accent-warm)]/20'
                : 'bg-[var(--theme-bg-card)] border-l-2 border-[var(--skin-accent-warm)]/60 text-[var(--theme-text-primary)] rounded-bl-md shadow-sm hover:shadow-md'
            }
          `}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.text}</p>
          ) : (
            <div className={`markdown-body ${isStreaming ? 'typing-cursor' : ''}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.text || '​'}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* 时间戳 + 进度 */}
        <span className="text-[11px] text-[var(--theme-text-secondary)] mt-1.5 px-1">
          {formatTime(message.timestamp)}
          {!isUser && isStreaming && (
            <span className="ml-1.5 text-[var(--skin-accent-warm)] font-medium">生成中...</span>
          )}
        </span>

        {/* 阶段进度 */}
        {!isUser && (message.doneList?.length || message.runningList?.length) && (
          <div className="mt-1.5 w-full">
            <ProgressTracker
              doneList={message.doneList || []}
              runningList={message.runningList || []}
            />
          </div>
        )}

        {/* 引用来源 */}
        {!isUser && resolvedSources?.length ? (
          <div className="mt-2 w-full">
            <SourcePanel sources={resolvedSources} />
          </div>
        ) : null}
      </div>
    </div>
  )
}

// ==================== Progress Tracker ====================

interface ProgressTrackerProps {
  doneList: string[]
  runningList: string[]
}

function ProgressTracker({ doneList, runningList }: ProgressTrackerProps) {
  return (
    <details open className="border border-dashed border-[var(--theme-border)] rounded-lg p-2.5 bg-[var(--theme-bg-card)]/60 transition-all duration-200">
      <summary className="text-[11px] text-[var(--skin-text-secondary)] cursor-pointer select-none font-medium">
        阶段进度 ({doneList.length} 完成, {runningList.length} 进行中)
      </summary>
      <div className="mt-2 ml-5 space-y-1">
        {doneList.map((item) => (
          <div key={item} className="text-[11px] text-[var(--skin-accent-warm)] flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            {item}
          </div>
        ))}
        {runningList.map((item) => (
          <div key={item} className="text-[11px] text-[var(--skin-accent)] flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {item}
          </div>
        ))}
      </div>
    </details>
  )
}
