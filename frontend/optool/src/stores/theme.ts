import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export type ThemeColorKey = 'blue' | 'red' | 'yellow' | 'green' | 'black' | 'gray'

export const THEME_COLORS: Record<ThemeColorKey, { label: string; primary: string; textColor: string }> = {
  blue:   { label: '파란색', primary: '#1976d2', textColor: 'white' },
  red:    { label: '빨간색', primary: '#c62828', textColor: 'white' },
  yellow: { label: '노란색', primary: '#f9a825', textColor: 'black' },
  green:  { label: '초록색', primary: '#2e7d32', textColor: 'white' },
  black:  { label: '검정색', primary: '#212121', textColor: 'white' },
  gray:   { label: '회색',   primary: '#616161', textColor: 'white' },
}

const DEFAULT_APP_NAME = 'OPTOOL'
const DEFAULT_COLOR_KEY: ThemeColorKey = 'blue'

export const useThemeStore = defineStore('theme', () => {
  const appName = ref(DEFAULT_APP_NAME)
  const colorKey = ref<ThemeColorKey>(DEFAULT_COLOR_KEY)

  function applyColor(key: string) {
    const theme = THEME_COLORS[key as ThemeColorKey] ?? THEME_COLORS[DEFAULT_COLOR_KEY]
    // Quasar 2는 팔레트 색상을 :root의 CSS 변수(--q-primary)로 참조하므로,
    // 인라인 스타일로 덮어쓰면 리빌드 없이 런타임에 테마 색이 바뀐다.
    document.documentElement.style.setProperty('--q-primary', theme.primary)
  }

  function currentTextColor() {
    return (THEME_COLORS[colorKey.value] ?? THEME_COLORS[DEFAULT_COLOR_KEY]).textColor
  }

  /** 로그인 여부와 무관하게 호출 가능한 공개 브랜딩 조회 (인증 불필요) */
  async function load() {
    try {
      const { data } = await api.get<{ appName?: string; app_name?: string; themeColor?: string; theme_color?: string }>('/branding')
      appName.value = data.appName ?? data.app_name ?? DEFAULT_APP_NAME
      const key = (data.themeColor ?? data.theme_color ?? DEFAULT_COLOR_KEY) as ThemeColorKey
      colorKey.value = THEME_COLORS[key] ? key : DEFAULT_COLOR_KEY
    } catch {
      appName.value = DEFAULT_APP_NAME
      colorKey.value = DEFAULT_COLOR_KEY
    }
    applyColor(colorKey.value)
  }

  /** 관리자가 설정 저장 직후, 재조회 없이 즉시 반영할 때 사용 */
  function setLocal(name: string, key: ThemeColorKey) {
    appName.value = name || DEFAULT_APP_NAME
    colorKey.value = key
    applyColor(key)
  }

  return { appName, colorKey, load, applyColor, currentTextColor, setLocal }
})
