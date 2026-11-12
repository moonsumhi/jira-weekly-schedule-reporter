<template>
  <q-page class="bo-page theme-settings-page" padding>
    <div role="heading" aria-level="1" class="text-subtitle1 text-weight-bold q-mb-md bo-page-title bo-page-title--standalone">스킨 설정</div>

    <q-card flat bordered class="settings-card q-mb-md">
      <q-card-section class="q-gutter-md">
        <div>
          <div class="text-caption text-grey-7 q-mb-sm">테마 색상</div>
          <div class="row q-gutter-sm">
            <button
              v-for="(themeColor, key) in THEME_COLORS"
              :key="key"
              type="button"
              class="color-swatch"
              :class="{ 'color-swatch--active': selectedColor === key }"
              :style="{ background: themeColor.primary }"
              :aria-label="`${themeColor.label} 테마 선택`"
              :title="themeColor.label"
              @click="selectedColor = key"
            >
              <q-icon v-if="selectedColor === key" name="check" color="white" size="18px" />
            </button>
          </div>
          <div class="text-caption text-grey-6 q-mt-xs">{{ selectedThemeLabel }} 선택됨</div>
          <label class="theme-color-picker q-mt-md">
            <span class="text-caption text-grey-7">직접 색상 선택</span>
            <input
              type="color"
              :value="selectedThemeHex"
              aria-label="테마 색상 직접 선택"
              @input="setCustomThemeColor"
            />
            <span class="text-caption text-grey-6">{{ selectedThemeHex.toUpperCase() }}</span>
          </label>
        </div>

        <q-input
          v-model="appName"
          label="앱 이름 (헤더에 표시되는 글자)"
          outlined
          dense
          maxlength="20"
          counter
        />

        <q-input
          v-model="tabTitle"
          label="브라우저 탭 제목"
          hint="비워두면 앱 이름과 동일하게 표시됩니다"
          outlined
          dense
          maxlength="30"
          counter
        />
      </q-card-section>
    </q-card>

    <q-card flat bordered class="settings-card">
      <q-card-section>
        <div class="text-subtitle2 text-weight-bold">사이드바 색상</div>
        <div class="text-caption text-grey-7 q-mt-xs">
          선택한 배경색을 상위 메뉴와 하위 메뉴를 포함한 사이드바 전체에 적용합니다.
        </div>
        <label class="sidebar-color-picker q-mt-md">
          <span class="text-caption text-grey-7">사이드바 배경색</span>
          <input
            v-model="sidebarBackgroundColor"
            type="color"
            aria-label="사이드바 배경색"
          />
          <span class="text-caption text-grey-6">{{ sidebarBackgroundColor.toUpperCase() }}</span>
        </label>
      </q-card-section>

      <q-separator />
      <q-card-section class="text-caption text-grey">
        <q-icon name="fa-solid fa-info-circle" size="xs" class="q-mr-xs" />
        저장하면 모든 사용자의 사이드바 전체 배경에 반영됩니다.
      </q-card-section>
      <q-card-actions align="right">
        <q-btn color="primary" label="저장" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { settingsService } from 'src/services/settings'
import { useThemeStore, THEME_COLORS, DEFAULT_APP_NAME, type ThemeColorKey } from 'stores/theme'

const $q = useQuasar()
const themeStore = useThemeStore()

const appName = ref(DEFAULT_APP_NAME)
const tabTitle = ref('')
const selectedColor = ref<string>('blue')
const sidebarBackgroundColor = ref('#ffffff')
const saving = ref(false)
const selectedThemeHex = computed(() => {
  const preset = THEME_COLORS[selectedColor.value as ThemeColorKey]
  return preset?.primary ?? selectedColor.value
})
const selectedThemeLabel = computed(() =>
  THEME_COLORS[selectedColor.value as ThemeColorKey]?.label ?? '사용자 지정 색상',
)

function setCustomThemeColor(event: Event) {
  selectedColor.value = (event.target as HTMLInputElement).value.toLowerCase()
}

async function load() {
  try {
    const [nameRes, tabTitleRes, colorRes, sidebarColorRes] = await Promise.all([
      settingsService.get('app_name'),
      settingsService.get('tab_title'),
      settingsService.get('app_theme_color'),
      settingsService.get('app_sidebar_background_color'),
    ])
    appName.value = nameRes.value || DEFAULT_APP_NAME
    tabTitle.value = tabTitleRes.value || ''
    const color = colorRes.value || 'blue'
    selectedColor.value = THEME_COLORS[color as ThemeColorKey] || /^#[\da-f]{6}$/i.test(color)
      ? color
      : 'blue'
    sidebarBackgroundColor.value = /^#[\da-f]{6}$/i.test(sidebarColorRes.value || '')
      ? sidebarColorRes.value!
      : '#ffffff'
  } catch {
    $q.notify({ type: 'negative', message: '스킨 설정을 불러오지 못했습니다.' })
  }
}

async function save() {
  if (!appName.value.trim()) {
    $q.notify({ type: 'warning', message: '앱 이름을 입력해 주세요.' })
    return
  }
  saving.value = true
  try {
    const trimmedName = appName.value.trim()
    const trimmedTitle = tabTitle.value.trim()
    await Promise.all([
      settingsService.put('app_name', trimmedName),
      settingsService.put('tab_title', trimmedTitle),
      settingsService.put('app_theme_color', selectedColor.value),
      settingsService.put('app_sidebar_background_color', sidebarBackgroundColor.value),
    ])
    themeStore.setLocal(
      trimmedName,
      trimmedTitle || trimmedName,
      selectedColor.value,
      sidebarBackgroundColor.value,
    )
    $q.notify({ type: 'positive', message: '저장되었습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다.' })
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.settings-card {
  max-width: 960px;
}

.color-swatch {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid transparent;
  transition: transform 0.1s;
}

.color-swatch:hover {
  transform: scale(1.08);
}

.color-swatch--active {
  border-color: #333;
}

.theme-color-picker {
  display: flex;
  width: fit-content;
  align-items: center;
  gap: 10px;
}

.theme-color-picker input,
.sidebar-color-picker input {
  width: 42px;
  height: 34px;
  padding: 2px;
  border: 1px solid #c7cbd1;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.sidebar-color-picker {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px 32px;
  min-height: 36px;
  color: #424242;
  font-size: 13px;
}
</style>
