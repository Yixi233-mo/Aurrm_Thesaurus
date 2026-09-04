import { useEffect, useState } from 'react'
import React from 'react'
import { createPortal } from 'react-dom'
import type { Toast as ToastType } from '../types'

// 全局 Toast 容器（在 App 层渲染一次）

const TOAST_ICONS: Record<ToastType['type'], React.ReactNode> = {
  success: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  ),
  info: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
    </svg>
  ),
}

const TOAST_COLORS: Record<ToastType['type'], { bg: string; border: string; icon: string }> = {
  success: { bg: 'bg-[var(--skin-accent-warm)]', border: 'border-[var(--skin-accent-warm-hover)]', icon: 'text-[var(--skin-bg-card)]' },
  error: { bg: 'bg-red-500/90', border: 'border-red-400/60', icon: 'text-white' },
  info: { bg: 'bg-[var(--skin-accent)]', border: 'border-[var(--skin-accent-hover)]', icon: 'text-[var(--skin-bg-card)]' },
}

function ToastItem({ toast, onRemove }: { toast: ToastType; onRemove: () => void }) {
  const [isExiting, setIsExiting] = useState(false)

  const handleRemove = () => {
    setIsExiting(true)
    setTimeout(onRemove, 200)
  }

  const colors = TOAST_COLORS[toast.type]

  return (
    <div
      className={`
        flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-white text-sm
        border ${colors.bg} ${colors.border}
        transition-all duration-200
        ${isExiting ? 'opacity-0 translate-x-4' : 'opacity-100 translate-x-0'}
      `}
    >
      <div className={`shrink-0 ${colors.icon}`}>{TOAST_ICONS[toast.type]}</div>
      <p className="flex-1 min-w-0">{toast.message}</p>
      <button
        onClick={handleRemove}
        className="shrink-0 opacity-70 hover:opacity-100 transition-opacity"
        aria-label="关闭通知"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastType[]>([])

  // 通过自定义事件与 store 通信
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.toast) {
        setToasts((prev) => [...prev, detail.toast])
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== detail.toast.id))
        }, detail.toast.type === 'error' ? 5000 : 3000)
      }
    }
    window.addEventListener('kb-toast', handler as EventListener)
    return () => window.removeEventListener('kb-toast', handler as EventListener)
  }, [])

  if (toasts.length === 0) return null

  return createPortal(
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={() => setToasts((p) => p.filter((t) => t.id !== toast.id))} />
      ))}
    </div>,
    document.body,
  )
}

// 便捷函数：全局发送 toast
export function showToast(type: ToastType['type'], message: string) {
  const toast: ToastType = {
    id: crypto.randomUUID(),
    type,
    message,
  }
  window.dispatchEvent(new CustomEvent('kb-toast', { detail: { toast } }))
}
