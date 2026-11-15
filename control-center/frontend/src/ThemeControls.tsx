import { useEffect, useState } from 'react'

type Theme = 'dark' | 'slate' | 'light'
type ColorKey = 'bg' | 'sidebar' | 'panel'

type Colors = Record<ColorKey, string>

const presets: Record<Theme, Colors> = {
  dark: {
    bg: '#0b1220',
    sidebar: '#101b2e',
    panel: '#121f33',
  },
  slate: {
    bg: '#1e293b',
    sidebar: '#273449',
    panel: '#394555',
  },
  light: {
    bg: '#f8fafc',
    sidebar: '#ffffff',
    panel: '#ffffff',
  },
}

const fields: { key: ColorKey; label: string }[] = [
  { key: 'bg', label: 'Main background' },
  { key: 'sidebar', label: 'Sidebar background' },
  { key: 'panel', label: 'Panel background' },
]

function readTheme(): Theme {
  try {
    const value = localStorage.getItem('titan-theme')
    if (value === 'dark' || value === 'slate' || value === 'light') {
      return value
    }
  } catch {
    // Storage is optional.
  }
  return 'dark'
}

function readColors(): Partial<Colors> {
  try {
    const value = localStorage.getItem('titan-custom-colors')
    if (!value) return {}

    const parsed: unknown = JSON.parse(value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {}
    }

    const record = parsed as Record<string, unknown>
    const result: Partial<Colors> = {}

    for (const { key } of fields) {
      const color = record[key]
      if (typeof color === 'string' && /^#[0-9a-fA-F]{6}$/.test(color)) {
        result[key] = color
      }
    }
    return result
  } catch {
    return {}
  }
}

export default function ThemeControls() {
  const [theme, setTheme] = useState<Theme>(readTheme)
  const [custom, setCustom] = useState<Partial<Colors>>(readColors)

  const colors = { ...presets[theme], ...custom }

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-titan-theme', theme)

    root.style.setProperty('--titan-bg', colors.bg)
    root.style.setProperty('--titan-sidebar', colors.sidebar)
    root.style.setProperty('--titan-panel', colors.panel)

    try {
      localStorage.setItem('titan-theme', theme)
      localStorage.setItem('titan-custom-colors', JSON.stringify(custom))
    } catch {
      // Storage is optional.
    }
  }, [theme, custom, colors.bg, colors.sidebar, colors.panel])

  function selectTheme(value: Theme) {
    setTheme(value)
    setCustom({})
  }

  function resetColors() {
    setCustom({})
  }

  return (
    <details className="titan-appearance">
      <summary>Appearance</summary>

      <div className="titan-appearance-options">
        <label htmlFor="titan-theme-select">Theme</label>
        <select
          id="titan-theme-select"
          value={theme}
          onChange={event => selectTheme(event.target.value as Theme)}
        >
          <option value="dark">Dark</option>
          <option value="slate">Slate</option>
          <option value="light">Light</option>
        </select>

        {fields.map(({ key, label }) => (
          <label key={key}>
            <span>{label}</span>
            <input
              type="color"
              value={colors[key]}
              aria-label={label}
              onChange={event =>
                setCustom(current => ({
                  ...current,
                  [key]: event.target.value,
                }))
              }
            />
          </label>
        ))}

        <button type="button" onClick={resetColors}>
          Reset colors
        </button>
      </div>
    </details>
  )
}
