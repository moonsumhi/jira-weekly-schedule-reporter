import { defineStore } from 'pinia'
import { ref } from 'vue'
import { menuService, type MenuOut } from 'src/services/menus'
import { boardService, type BoardOut } from 'src/services/boards'
import { formTemplateService } from 'src/services/formTemplates'

export const useMenuStore = defineStore('menus', () => {
  const sidebarMenus = ref<MenuOut[]>([])
  const sidebarBoards = ref<BoardOut[]>([])
  const templateItems = ref<{ title: string; icon: string; link: string; menu: string }[]>([])

  async function loadMenus() {
    try {
      ;[sidebarMenus.value, sidebarBoards.value] = await Promise.all([
        menuService.list(false),
        boardService.listBoards(),
      ])
    } catch (e) {
      console.error('[menuStore] loadMenus failed:', e)
    }
  }

  async function loadTemplates() {
    try {
      const templates = await formTemplateService.list()
      if (!Array.isArray(templates)) return
      templateItems.value = templates
        .filter((t) => !!t.menu)
        .map((t) => ({
          title: t.title,
          icon: 'fa-solid fa-file-alt',
          link: `/job/forms/${t.id}`,
          menu: t.menu as string,
        }))
    } catch (e) {
      console.error('[menuStore] loadTemplates failed:', e)
    }
  }

  async function refresh() {
    await Promise.all([loadMenus(), loadTemplates()])
  }

  return { sidebarMenus, sidebarBoards, templateItems, loadMenus, loadTemplates, refresh }
})
