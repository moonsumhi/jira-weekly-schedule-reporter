import { onBeforeUnmount, watch, type Ref } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { createDialogHistory } from 'src/utils/dialogHistory'

/** Back closes this dialog; explicit navigation first removes its temporary entry. */
export function useDialogHistory(open: Ref<boolean>) {
  const history = createDialogHistory(window, () => { open.value = false })
  watch(open, (value) => { void history.setOpen(value) }, { immediate: true })
  async function closeBeforeNavigation() {
    open.value = false
    await history.close()
  }
  onBeforeRouteLeave(closeBeforeNavigation)
  onBeforeRouteUpdate(closeBeforeNavigation)
  onBeforeUnmount(() => history.dispose())
}
