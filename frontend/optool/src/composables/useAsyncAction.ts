import { ref } from 'vue'
import { useQuasar } from 'quasar'

interface AsyncActionOptions {
  success?: string
  error?: string
  onError?: (e: unknown) => void
}

export function useAsyncAction() {
  const $q = useQuasar()
  const loading = ref(false)

  async function run<T>(
    action: () => Promise<T>,
    options: AsyncActionOptions = {}
  ): Promise<T | undefined> {
    loading.value = true
    try {
      const result = await action()
      if (options.success) {
        $q.notify({ type: 'positive', message: options.success })
      }
      return result
    } catch (e) {
      if (options.onError) {
        options.onError(e)
      } else if (options.error) {
        $q.notify({ type: 'negative', message: options.error })
      }
      return undefined
    } finally {
      loading.value = false
    }
  }

  return { run, loading }
}
