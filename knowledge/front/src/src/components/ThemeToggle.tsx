import { useEffect, useState } from 'react'

type Skin = 'skin-gambit-dark' | 'skin-gambit-light' | 'skin-xuanji'

const SKINS: { value: Skin; label: string; icon: string }[] = [
  { value: 'skin-gambit-dark', label: '砂金暗', icon: '🌙' },
  { value: 'skin-gambit-light', label: '砂金亮', icon: '☀️' },
  { value: 'skin-xuanji', label: '璇玑亮星', icon: '⭐' },
]

export function ThemeToggle() {
  const [skin, setSkin] = useState<Skin>(() => {
    return (localStorage.getItem('skin') as Skin) || 'skin-gambit-dark'
  })

  useEffect(() => {
    const root = document.documentElement
    root.removeAttribute('data-skin')
    root.classList.remove('light')

    if (skin === 'skin-gambit-light') {
      root.classList.add('light')
    } else if (skin === 'skin-xuanji') {
      root.setAttribute('data-skin', 'xuanji')
    }
    // skin-gambit-dark is the default: no class, no attribute
  }, [skin])

  const select = (next: Skin) => {
    setSkin(next)
    localStorage.setItem('skin', next)
    window.dispatchEvent(new CustomEvent('skin-changed'))
  }

  return (
    <div className="flex items-center gap-1 bg-[var(--skin-bg-card)]/80 rounded-lg p-0.5 border border-[var(--skin-border)]">
      {SKINS.map((s) => (
        <button
          key={s.value}
          onClick={() => select(s.value)}
          className={`px-2 py-1 rounded text-xs transition-all duration-200 ${
            skin === s.value
              ? 'bg-[var(--skin-accent-warm)]/20 text-[var(--skin-accent-warm)]'
              : 'text-[var(--skin-text-secondary)] hover:text-[var(--skin-text-primary)] hover:bg-[var(--skin-accent)]/10'
          }`}
          title={s.label}
        >
          <span className="mr-1">{s.icon}</span>
          {s.label}
        </button>
      ))}
    </div>
  )
}
