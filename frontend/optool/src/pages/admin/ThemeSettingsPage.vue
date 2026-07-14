<template>
  <q-page padding>
    <div class="text-subtitle1 text-weight-bold q-mb-md">스킨 설정</div>

    <q-card flat bordered style="max-width: 480px">
      <q-card-section class="q-gutter-md">
        <div>
          <div class="text-caption text-grey-7 q-mb-sm">테마 색상</div>
          <div class="row q-gutter-sm">
            <div
              v-for="(theme, key) in THEME_COLORS"
              :key="key"
              class="color-swatch"
              :class="{ 'color-swatch--active': selectedColor === key }"
              :style="{ background: theme.primary }"
              @click="selectedColor = key"
            >
              <q-icon v-if="selectedColor === key" name="check" color="white" size="18px" />
            </div>
          </div>
          <div class="text-caption text-grey-6 q-mt-xs">{{ THEME_COLORS[selectedColor].label }} 선택됨</div>
        </div>

        <q-input
          v-model="appName"
          label="앱 이름 (헤더에 표시되는 글자)"
          outlined
          dense
          maxlength="20"
          counter
        />
      </q-card-section>

      <q-card-section class="text-caption text-grey">
        <q-icon name="fa-solid fa-info-circle" size="xs" class="q-mr-xs" />
        저장하면 모든 사용자 화면에 재접속 없이 바로 반영됩니다.
      </q-card-section>

      <q-card-actions align="right">
        <q-btn color="primary" label="저장" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { settingsService } from 'src/services/settings'
import { useThemeStore, THEME_COLORS, type ThemeColorKey } from 'stores/theme'

const $q = useQuasar()
const themeStore = useThemeStore()

const appName = ref('OPTOOL')
const selectedColor = ref<ThemeColorKey>('blue')
const saving = ref(false)

async function load() {
  const [nameRes, colorRes] = await Promise.all([
    settingsService.get('app_name'),
    settingsService.get('app_theme_color'),
  ])
  appName.value = nameRes.value || 'OPTOOL'
  const key = (colorRes.value || 'blue') as ThemeColorKey
  selectedColor.value = THEME_COLORS[key] ? key : 'blue'
}

async function save() {
  if (!appName.value.trim()) {
    $q.notify({ type: 'warning', message: '앱 이름을 입력해주세요' })
    return
  }
  saving.value = true
  try {
    await Promise.all([
      settingsService.put('app_name', appName.value.trim()),
      settingsService.put('app_theme_color', selectedColor.value),
    ])
    themeStore.setLocal(appName.value.trim(), selectedColor.value)
    $q.notify({ type: 'positive', message: '저장되었습니다' })
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.color-swatch {
  width: 36px;
  height: 36px;
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
</style>
