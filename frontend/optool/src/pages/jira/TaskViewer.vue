<template>
  <div class="q-pa-md">
    <!-- Filter Card -->
    <q-card flat bordered>
      <q-card-section>
        <div class="row q-col-gutter-md">

          <!-- Start Date -->
          <div class="col-12 col-md-3">
            <q-input v-model="startDate" label="Start Date" readonly>
              <template v-slot:append>
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                    <q-date v-model="startDate" mask="YYYY-MM-DD"/>
                  </q-popup-proxy>
                </q-icon>
              </template>
            </q-input>
          </div>

          <!-- End Date -->
          <div class="col-12 col-md-3">
            <q-input v-model="endDate" label="End Date" readonly>
              <template v-slot:append>
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                    <q-date v-model="endDate" mask="YYYY-MM-DD"/>
                  </q-popup-proxy>
                </q-icon>
              </template>
            </q-input>
          </div>

          <!-- Assignees -->
          <div class="col-12 col-md-3">
            <q-input
              v-model="assigneesInput"
              label="Assignees (comma-separated)"
              placeholder="문수미,김세현"
            />
          </div>

          <!-- Status -->
          <div class="col-12 col-md-3">
            <q-select
              v-model="selectedStatuses"
              :options="statusOptions"
              multiple
              label="Status"
              emit-value
              map-options
            />
          </div>
        </div>

        <div class="q-mt-md">
          <q-btn label="검색" color="primary" @click="fetchTasks"/>
        </div>
      </q-card-section>
    </q-card>

    <!-- Assignee Buttons -->
    <div v-if="showAssigneeButtons" class="q-mt-md row q-gutter-sm q-wrap">
      <q-btn
        outline
        color="primary"
        size="md"
        rounded
        :flat="selectedAssigneeFilter === 'all'"
        @click="selectedAssigneeFilter = 'all'"
        class="q-mb-sm q-mr-sm"
      >
        All
      </q-btn>

      <q-btn
        v-for="assignee in assigneeList"
        :key="assignee"
        outline
        color="secondary"
        size="md"
        rounded
        :flat="selectedAssigneeFilter === assignee"
        @click="selectedAssigneeFilter = assignee"
        class="q-mb-sm q-mr-sm"
      >
        {{ assignee }}
      </q-btn>
    </div>


    <!-- Task List -->
    <div class="q-mt-lg">
      <div v-for="group in filteredTasks" :key="group.assignee" class="q-mb-md">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6">{{ group.assignee }} · {{ group.count }} tasks</div>
            <q-separator spaced/>
            <div v-for="issue in group.issues" :key="issue.key">
              <div>
                <a :href="issue.url" target="_blank">{{ issue.key }}</a>
                {{ issue.summary }}
                <q-badge :color="statusColor(issue.status)" class="q-ml-sm">{{ issue.status }}</q-badge>
              </div>
              <div class="text-subtitle2 text-grey">
                Created: {{ issue.created }} · Due: {{ issue.duedate }}
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {ref, computed} from 'vue'
import qs from 'qs'
import {api} from 'boot/axios'
import type {AssigneeGroup} from 'src/types/jira'

const startDate = ref('')
const endDate = ref('')
const assigneesInput = ref('')
const selectedStatuses = ref<string[]>([])
const tasks = ref<AssigneeGroup[]>([])

// Assignee filter & visibility
const selectedAssigneeFilter = ref('all')
const showAssigneeButtons = ref(false)

// Computed assignee list from input
const assigneeList = computed(() => {
  return assigneesInput.value
    ? assigneesInput.value.split(',').map(a => a.trim()).filter(a => a)
    : []
})

// Filtered tasks based on selected assignee
const filteredTasks = computed(() => {
  if (selectedAssigneeFilter.value === 'all') return tasks.value
  return tasks.value.filter(group => group.assignee === selectedAssigneeFilter.value)
})

const statusOptions = ["To Do", "In Progress", "Done", "Blocked"]

function statusColor(status: string) {
  switch (status) {
    case "To Do":
      return "amber"
    case "In Progress":
      return "blue"
    case "Done":
      return "green"
    case "Blocked":
      return "red"
    default:
      return "grey"
  }
}

async function fetchTasks() {
  if (!startDate.value || !endDate.value) {
    alert("Please select start and end dates")
    return
  }

  const assignees = assigneesInput.value
    ? assigneesInput.value.split(",").map(a => a.trim()).filter(a => a)
    : undefined

  const res = await api.get("/issues/today-tasks", {
    params: {
      start: startDate.value,
      end: endDate.value,
      assignees,
      status: selectedStatuses.value
    },
    paramsSerializer: params => qs.stringify(params, {arrayFormat: 'repeat'})
  })

  tasks.value = res.data.groups
  showAssigneeButtons.value = true  // Show buttons after fetch
  selectedAssigneeFilter.value = 'all' // Reset filter
}
</script>
<style scoped>
.q-btn:hover {
  transform: scale(1.05);
  transition: transform 0.1s ease-in-out;
}
</style>
