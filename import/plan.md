# 三皮肤 · 实际色值（同步自 index.css）

> 以下为项目当前实际使用的色值，同步自 `front/src/src/index.css`，仅作记录参考。


## 📊 总览对比表

| 维度       | 🌙 砂金暗（暖棕调） | ☀️ 砂金亮 | ⭐ 璇玑亮星（薰衣草紫） |
| -------- | ---------- | ---------- | --------------- |
| **核心情绪** | 沉稳·暖金·醇厚   | 温暖·典雅·松弛   | 通透·浪漫·智慧        |
| **色彩性格** | 暖棕底 × 柔金 | 暖白纸色 × 琥珀金 | 薰衣草紫 × 流金 × 极光青 |
| **符号语言** | ♠♥♦♣ 扑克·筹码 | 纸牌·筹码·暖光   | ★✦✧ 星轨·璇玑       |
| **视觉温度** | 暖          | 暖          | 暖（紫调）           |


## 🌙 砂金博弈（暗色）

> 心智：*"暖棕夜色，金砂流转。"*

### CSS 变量块（实际代码）

```css
:root {
  --skin-bg-base: #2C2420;
  --skin-bg-card: #3D322C;
  --skin-bg-input: #1F1916;
  --skin-text-primary: #EDE6DB;
  --skin-text-secondary: #A89A8C;
  --skin-text-muted: #6B6058;
  --skin-border: rgba(196, 168, 106, 0.25);
  --skin-accent: #C4A86A;
  --skin-accent-hover: #D9BF8A;
  --skin-accent-warm: #C4A86A;
  --skin-accent-warm-hover: #D9BF8A;
  --skin-sidebar-bg: #1F1916;
  --skin-sidebar-text: #CCC1B2;
  --skin-shimmer: rgba(196, 168, 106, 0.08);
}
```


## ☀️ 砂金博弈（亮色）

> 心智：*"午后暖光，纸牌轻展。"*

### CSS 变量块（实际代码）

```css
html.light {
  --skin-bg-base: #F7F3EE;
  --skin-bg-card: #FFFFFF;
  --skin-bg-input: #FFFFFF;
  --skin-text-primary: #1A1A1A;
  --skin-text-secondary: #6B6B6B;
  --skin-text-muted: #A8A09A;
  --skin-border: #E8E0D6;
  --skin-accent: #C49A6C;
  --skin-accent-hover: #DCAE7A;
  --skin-accent-warm: #C49A6C;
  --skin-accent-warm-hover: #DCAE7A;
  --skin-sidebar-bg: #1A4A50;
  --skin-sidebar-text: #E8E4D9;
  --skin-shimmer: rgba(196, 154, 108, 0.12);
}
```


## ⭐ 璇玑金策（亮星 · 薰衣草紫）

> 心智：*"薰衣草夜，星光落于策卷。"*

### CSS 变量块（实际代码）

```css
html[data-skin="xuanji"] {
  --skin-bg-base: #9A90AD;
  --skin-bg-card: #ADA3C0;
  --skin-bg-input: #7C728D;
  --skin-text-primary: #1A1626;
  --skin-text-secondary: #4A4460;
  --skin-text-muted: #6E6880;
  --skin-border: rgba(26, 22, 38, 0.10);
  --skin-accent: #6A6380;
  --skin-accent-hover: #8A83A0;
  --skin-accent-warm: #C9A96E;
  --skin-accent-warm-hover: #DDC08A;
  --skin-sidebar-bg: #7D738A;
  --skin-sidebar-text: #201C2E;
  --skin-shimmer: rgba(220, 215, 235, 0.12);
}
```


## 🔄 切换逻辑

```tsx
// ThemeToggle.tsx
type Skin = 'skin-gambit-dark' | 'skin-gambit-light' | 'skin-xuanji'

// skin-gambit-dark → 默认 :root，无需任何 class/attribute
// skin-gambit-light → html.light
// skin-xuanji → html[data-skin="xuanji"]
```


## ✅ 数据来源

| 来源 | 路径 |
|------|------|
| CSS 变量 | `front/src/src/index.css` |
| 切换组件 | `front/src/src/components/ThemeToggle.tsx` |
| 最后同步 | 2026-09-04 |
