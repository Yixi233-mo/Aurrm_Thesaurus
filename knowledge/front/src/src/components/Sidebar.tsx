import { NavLink, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'

export function Sidebar() {
  const { pathname } = useLocation()
  const isChatActive = pathname === '/chat' || pathname === '/'
  const isImportActive = pathname === '/import'

  const [skin, setSkin] = useState<string>(() => localStorage.getItem('skin') || 'skin-gambit-dark')
  useEffect(() => {
    const handler = () => setSkin(localStorage.getItem('skin') || 'skin-gambit-dark')
    window.addEventListener('skin-changed', handler)
    return () => window.removeEventListener('skin-changed', handler)
  }, [])

  const isXuanji = skin === 'skin-xuanji'

  return (
    <nav className="w-64 h-screen bg-[var(--sidebar-bg)] border-r border-[var(--skin-border)] flex flex-col shrink-0 relative overflow-hidden text-[var(--sidebar-text)]">
      {/* 皮肤专属装饰：砂金博弈保留扑克花色，璇玑金策移除 */}
      {!isXuanji && (
        <>
          <span className="pointer-events-none absolute bottom-6 right-4 text-[var(--skin-accent)]/10 text-6xl leading-none select-none">♠</span>
          <span className="pointer-events-none absolute bottom-16 right-14 text-[var(--skin-accent)]/10 text-4xl leading-none select-none">♥</span>
        </>
      )}

      {/* 品牌 Logo */}
      <div className="p-5 flex items-center gap-3">
        {/* 璇玑仪同心圆环 */}
        <div className="relative w-9 h-9">
          <div className="absolute inset-0 rounded-full border-2 border-[var(--skin-accent-warm)]/40" />
          <div className="absolute inset-1 rounded-full border border-[var(--skin-accent-warm)]/20" />
          {/* 璇玑专属：星轨弧线装饰 */}
          {isXuanji && (
            <svg className="absolute inset-0 w-full h-full text-[var(--skin-accent)]/30" viewBox="0 0 36 36" fill="none">
              <path d="M18 2 A16 16 0 0 1 34 18" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
              <path d="M2 18 A16 16 0 0 1 18 34" stroke="currentColor" strokeWidth="0.75" strokeLinecap="round" opacity="0.6" />
            </svg>
          )}
          <div className="absolute inset-0 flex items-center justify-center">
            <svg className="w-4 h-4 text-[var(--skin-accent-warm)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 4.168 6.253v13C4.168 19.223 5.754 19 7.5 19s3.332.477 3.332 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 3.332 1.253v13C19.832 19.223 18.247 19 16.5 19s-3.332.477-3.332 1.253" />
            </svg>
          </div>
        </div>
        <div>
          <h1 className="text-sm font-bold text-[var(--skin-accent-warm)] tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>
            璇玑金策
          </h1>
          <p className="text-[11px] text-[var(--skin-text-secondary)]">金融知识库智能问答</p>
        </div>
      </div>

      {/* 金色分割线 */}
      <div className="mx-5 h-px bg-gradient-to-r from-transparent via-[var(--skin-accent-warm)]/30 to-transparent" />

      {/* 导航链接 */}
      <div className="px-3 space-y-0.5 mt-4">
        <NavLink
          to="/chat"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 relative ${
              isActive
                ? 'bg-[var(--skin-accent)]/10 text-[var(--skin-accent-warm)] shadow-sm'
                : 'text-[var(--skin-text-secondary)] hover:text-[var(--skin-text-primary)] hover:bg-[var(--skin-accent)]/10'
            }`
          }
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-4.272C3.512 14.261 3 13.068 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="font-medium">智能问答</span>
          {isChatActive && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-[var(--skin-accent-warm)] rounded-r" />
          )}
        </NavLink>

        <NavLink
          to="/import"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 relative ${
              isActive
                ? 'bg-[var(--skin-accent)]/10 text-[var(--skin-accent-warm)] shadow-sm'
                : 'text-[var(--skin-text-secondary)] hover:text-[var(--skin-text-primary)] hover:bg-[var(--skin-accent)]/10'
            }`
          }
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <span className="font-medium">文档导入</span>
          {isImportActive && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-[var(--skin-accent-warm)] rounded-r" />
          )}
        </NavLink>
      </div>

      {/* 底部品牌标语 */}
      <div className="mt-auto p-5 border-t border-[var(--skin-border)]">
        <p className="text-[11px] text-[var(--skin-text-secondary)] text-center tracking-wide" style={{ fontFamily: 'var(--font-display)' }}>
          {isXuanji ? '璇玑转，金策出，万变归真知。' : '砂金筹码落，检索万变归真知'}
        </p>
      </div>
    </nav>
  )
}
