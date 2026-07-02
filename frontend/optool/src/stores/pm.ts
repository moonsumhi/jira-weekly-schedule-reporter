import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Organization } from 'src/services/pm/organization'
import type { Project } from 'src/services/pm/project'
import type { Sprint } from 'src/services/pm/sprint'

export const usePmStore = defineStore('pm', () => {
  const currentOrg = ref<Organization | null>(null)
  const currentProject = ref<Project | null>(null)
  const activeSprint = ref<Sprint | null>(null)

  function setOrg(org: Organization | null) {
    currentOrg.value = org
    if (!org) {
      currentProject.value = null
      activeSprint.value = null
    }
  }

  function setProject(project: Project | null) {
    currentProject.value = project
    activeSprint.value = null
  }

  function setActiveSprint(sprint: Sprint | null) {
    activeSprint.value = sprint
  }

  return {
    currentOrg,
    currentProject,
    activeSprint,
    setOrg,
    setProject,
    setActiveSprint,
  }
})
