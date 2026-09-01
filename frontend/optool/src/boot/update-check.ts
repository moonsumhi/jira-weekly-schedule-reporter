import { defineBoot } from '#q-app/wrappers'
import { Notify } from 'quasar'

const CHECK_INTERVAL_MS = 5 * 60 * 1000
const CHECK_THROTTLE_MS = 10 * 1000

const getEntryAssetPath = (documentToInspect: Document): string | null => {
  const entryScript = documentToInspect.querySelector<HTMLScriptElement>(
    'script[type="module"][src*="/assets/"]'
  )

  if (!entryScript?.src) {
    return null
  }

  try {
    return new URL(entryScript.src, window.location.href).pathname
  } catch {
    return null
  }
}

export default defineBoot(() => {
  const currentEntryAsset = getEntryAssetPath(document)

  // 개발 서버는 해시가 적용된 /assets/ 진입 파일을 사용하지 않는다.
  if (!currentEntryAsset) {
    return
  }

  let checking = false
  let updateDetected = false
  let lastCheckedAt = 0

  const checkForUpdate = async () => {
    const now = Date.now()

    if (checking || updateDetected || now - lastCheckedAt < CHECK_THROTTLE_MS) {
      return
    }

    checking = true
    lastCheckedAt = now

    try {
      const response = await fetch(`/index.html?t=${now}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
        },
      })

      if (!response.ok) {
        return
      }

      const latestDocument = new DOMParser().parseFromString(await response.text(), 'text/html')
      const latestEntryAsset = getEntryAssetPath(latestDocument)

      if (!latestEntryAsset || latestEntryAsset === currentEntryAsset) {
        return
      }

      updateDetected = true
      Notify.create({
        type: 'info',
        icon: 'system_update_alt',
        message: '새 버전이 배포되었습니다.',
        caption: '작성 중인 내용을 저장한 뒤 최신 화면으로 새로고침해 주세요.',
        position: 'top',
        timeout: 0,
        actions: [
          {
            label: '새로고침',
            color: 'white',
            handler: () => window.location.reload(),
          },
        ],
      })
    } catch {
      // 내부망 연결 상태 등으로 확인에 실패하면 다음 주기에 다시 시도한다.
    } finally {
      checking = false
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      void checkForUpdate()
    }
  })
  window.addEventListener('focus', () => void checkForUpdate())
  window.setInterval(() => void checkForUpdate(), CHECK_INTERVAL_MS)

  void checkForUpdate()
})
