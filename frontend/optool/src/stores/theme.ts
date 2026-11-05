import { defineStore } from 'pinia'
import { ref } from 'vue'
import { Dark } from 'quasar'
import { api } from 'boot/axios'
import { settingsService } from 'src/services/settings'

export type ThemeColorKey =
  | 'blue'
  | 'indigo'
  | 'purple'
  | 'red'
  | 'orange'
  | 'yellow'
  | 'green'
  | 'teal'
  | 'cyan'
  | 'black'
  | 'gray'

export const THEME_COLORS: Record<ThemeColorKey, { label: string; primary: string; textColor: string }> = {
  blue:   { label: '파란색', primary: '#1976d2', textColor: 'white' },
  indigo: { label: '남색', primary: '#3949ab', textColor: 'white' },
  purple: { label: '보라색', primary: '#7b1fa2', textColor: 'white' },
  red:    { label: '빨간색', primary: '#c62828', textColor: 'white' },
  orange: { label: '주황색', primary: '#ef6c00', textColor: 'white' },
  yellow: { label: '노란색', primary: '#f9a825', textColor: 'black' },
  green:  { label: '초록색', primary: '#2e7d32', textColor: 'white' },
  teal:   { label: '청록색', primary: '#00897b', textColor: 'white' },
  cyan:   { label: '하늘색', primary: '#00acc1', textColor: 'black' },
  black:  { label: '검정색', primary: '#212121', textColor: 'white' },
  gray:   { label: '회색',   primary: '#616161', textColor: 'white' },
}

const DEFAULT_APP_NAME = 'OPTOOL'
const DEFAULT_COLOR_KEY: ThemeColorKey = 'blue'
const APPEARANCE_MODE_STORAGE_PREFIX = 'user-appearance-mode:'
const HEX_COLOR_PATTERN = /^#[\da-f]{6}$/i

export type AppearanceMode = 'light' | 'dark'

function readableTextColor(hex: string): 'black' | 'white' {
  const red = Number.parseInt(hex.slice(1, 3), 16)
  const green = Number.parseInt(hex.slice(3, 5), 16)
  const blue = Number.parseInt(hex.slice(5, 7), 16)
  const brightness = (red * 299 + green * 587 + blue * 114) / 1000
  return brightness >= 150 ? 'black' : 'white'
}

function normalizeThemeColor(value: string): string {
  if (THEME_COLORS[value as ThemeColorKey]) return value
  return HEX_COLOR_PATTERN.test(value) ? value.toLowerCase() : DEFAULT_COLOR_KEY
}

export const useThemeStore = defineStore('theme', () => {
  const appName = ref(DEFAULT_APP_NAME)
  const tabTitle = ref(DEFAULT_APP_NAME)
  const colorKey = ref<string>(DEFAULT_COLOR_KEY)
  const sidebarBackgroundColor = ref('#ffffff')
  const appearanceMode = ref<AppearanceMode>('light')

  function applyAppearanceMode(mode: AppearanceMode) {
    appearanceMode.value = mode
    Dark.set(mode === 'dark')
  }

  function loadAppearanceMode(userId: string | number | null | undefined) {
    if (userId === null || userId === undefined || userId === '') {
      applyAppearanceMode('light')
      return
    }

    const savedMode = localStorage.getItem(`${APPEARANCE_MODE_STORAGE_PREFIX}${userId}`)
    applyAppearanceMode(savedMode === 'dark' ? 'dark' : 'light')
  }

  function setAppearanceMode(mode: AppearanceMode, userId: string | number | null | undefined) {
    applyAppearanceMode(mode)
    if (userId !== null && userId !== undefined && userId !== '') {
      localStorage.setItem(`${APPEARANCE_MODE_STORAGE_PREFIX}${userId}`, mode)
    }
  }

  function applyColor(key: string) {
    const theme = THEME_COLORS[key as ThemeColorKey]
    const primary = theme?.primary ?? (HEX_COLOR_PATTERN.test(key) ? key : THEME_COLORS[DEFAULT_COLOR_KEY].primary)
    // Quasar 2는 팔레트 색상을 :root의 CSS 변수(--q-primary)로 참조하므로,
    // 인라인 스타일로 덮어쓰면 리빌드 없이 런타임에 테마 색이 바뀐다.
    document.documentElement.style.setProperty('--q-primary', primary)
  }

  function currentTextColor() {
    const theme = THEME_COLORS[colorKey.value as ThemeColorKey]
    if (theme) return theme.textColor
    return HEX_COLOR_PATTERN.test(colorKey.value) ? readableTextColor(colorKey.value) : 'white'
  }

  function applyAppName(name: string) {
    appName.value = name || DEFAULT_APP_NAME
  }

  // 브라우저 탭 제목은 앱 이름(헤더 표시용)과 별개로 관리 — 서로 다른 값으로 설정 가능
  function applyTabTitle(title: string) {
    tabTitle.value = title || DEFAULT_APP_NAME
    document.title = tabTitle.value
  }

  /** 로그인 여부와 무관하게 호출 가능한 공개 브랜딩 조회 (인증 불필요) */
  async function load() {
    try {
      const { data } = await api.get<{
        appName?: string; app_name?: string
        themeColor?: string; theme_color?: string
        tabTitle?: string; tab_title?: string
      }>('/branding')
      const name = data.appName ?? data.app_name ?? DEFAULT_APP_NAME
      applyAppName(name)
      applyTabTitle(data.tabTitle ?? data.tab_title ?? name)
      colorKey.value = normalizeThemeColor(data.themeColor ?? data.theme_color ?? DEFAULT_COLOR_KEY)
    } catch {
      applyAppName(DEFAULT_APP_NAME)
      applyTabTitle(DEFAULT_APP_NAME)
      colorKey.value = DEFAULT_COLOR_KEY
    }
    applyColor(colorKey.value)
  }

  /** 관리자 스킨 설정의 사이드바 전체 배경색을 불러온다. */
  async function loadSidebarTheme() {
    try {
      const setting = await settingsService.get('app_sidebar_background_color')
      sidebarBackgroundColor.value = HEX_COLOR_PATTERN.test(setting.value ?? '')
        ? setting.value!.toLowerCase()
        : '#ffffff'
    } catch {
      sidebarBackgroundColor.value = '#ffffff'
    }
  }

  /** 관리자가 설정 저장 직후, 재조회 없이 즉시 반영할 때 사용 */
  function setLocal(name: string, title: string, key: string, sidebarColor?: string) {
    applyAppName(name)
    applyTabTitle(title)
    colorKey.value = key
    if (sidebarColor !== undefined) sidebarBackgroundColor.value = sidebarColor
    applyColor(key)
  }

  return {
    appName, tabTitle, colorKey, sidebarBackgroundColor, appearanceMode,
    load, loadSidebarTheme, loadAppearanceMode, setAppearanceMode, applyColor, currentTextColor, setLocal,
  }
})
