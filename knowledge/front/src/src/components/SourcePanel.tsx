import { useState } from 'react'
import type { SourceItem } from '../types'

interface SourcePanelProps {
  sources: SourceItem[]
}

export function SourcePanel({ sources }: SourcePanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!sources.length) return null

  return (
    <div className="mt-3 w-full">
      <button
        type="button"
        onClick={() => setIsExpanded((v) => !v)}
        className="text-[11px] text-[var(--skin-accent-warm)] hover:text-[var(--skin-accent)] flex items-center gap-1 select-none"
      >
        <svg
          className={`w-3 h-3 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        引用来源 ({sources.length})
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {sources.map((item) => (
            <div
              key={item.idx}
              className="rounded-lg border border-[var(--theme-border)] bg-[var(--theme-bg-card)] px-3 py-2 text-[11px] text-[var(--theme-text-secondary)]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-[var(--skin-accent-warm)]">[{item.idx}] {item.title || item.source}</span>
                {item.score != null && (
                  <span className="text-[var(--theme-text-secondary)]">相关度 {item.score.toFixed(4)}</span>
                )}
              </div>

              <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-[var(--theme-text-secondary)]">
                {item.source && <span>来源：{item.source}</span>}
                {item.chunk_id && <span>片段：{item.chunk_id}</span>}
              </div>

              {item.url && (
                <div className="mt-1">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[var(--skin-accent)] hover:text-[var(--skin-accent-warm)] hover:underline break-all"
                  >
                    {item.url}
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
