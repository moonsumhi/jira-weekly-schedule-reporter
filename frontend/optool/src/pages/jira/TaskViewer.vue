<template>
  <div class="q-pa-md">
    <!-- Filters -->
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
          <q-btn label="검색" color="primary" :loading="loading" @click="fetchTasks"/>
        </div>
      </q-card-section>
    </q-card>

    <!-- Assignee Filter -->
    <div v-if="showAssigneeButtons" class="q-mt-md row q-gutter-sm q-wrap">
      <q-btn
        outline
        color="primary"
        size="md"
        rounded
        :flat="selectedAssigneeFilter === 'all'"
        @click="selectedAssigneeFilter = 'all'; refreshCalendar()"
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
        @click="selectedAssigneeFilter = assignee; refreshCalendar()"
      >
        {{ assignee }}
      </q-btn>
    </div>

    <!-- Calendar & Download -->
    <div class="q-mt-lg">
      <div class="row justify-end q-mb-sm">
        <q-btn
          label="JSON 다운로드"
          color="secondary"
          @click="downloadJSON"
          :disable="!filteredTasks.length"
        />
      </div>
      <FullCalendar
        ref="calendarRef"
        :options="calendarOptions"
        style="max-width: 100%; margin: auto;"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import {ref, computed} from 'vue'
import qs from 'qs'
import {api} from 'boot/axios'
import type {AssigneeGroup} from 'src/types/jira'
import {toKSTPlusOneDay, toKSTDay} from 'src/utils/time/kst'

// FullCalendar imports
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import type {EventInput} from '@fullcalendar/core'

const startDate = ref('')
const endDate = ref('')
const assigneesInput = ref('')
const selectedStatuses = ref<string[]>([])
const tasks = ref<AssigneeGroup[]>([])

const loading = ref(false)

const selectedAssigneeFilter = ref('all')
const showAssigneeButtons = ref(false)

const statusOptions = ["To Do", "In Progress", "Done", "Blocked"]

const assigneeList = computed(() => tasks.value.map(group => group.assignee))

const filteredTasks = computed(() => {
  if (selectedAssigneeFilter.value === 'all') return tasks.value
  return tasks.value.filter(group => group.assignee === selectedAssigneeFilter.value)
})

// Calendar Config
const calendarRef = ref<InstanceType<typeof FullCalendar> | null>(null)
const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek' },
  displayEventTime: false,
  events: []
})

function statusColor(status: string) {
  switch (status) {
    case "To Do": return "#FFC107"
    case "In Progress": return "#2196F3"
    case "Done": return "#4CAF50"
    case "Blocked": return "#F44336"
    default: return "#9E9E9E"
  }
}

function refreshCalendar() {
  if (!calendarRef.value) return
  const calendarApi = calendarRef.value.getApi()
  calendarApi.removeAllEvents()

  const events: EventInput[] = []
  filteredTasks.value.forEach(group => {
    group.issues.forEach(issue => {
      const event: EventInput = {
        title: `${group.assignee}: ${issue.summary} (${issue.key})`,
        url: issue.url,
        color: statusColor(issue.status),
        start: toKSTDay(issue.start),
        end: toKSTPlusOneDay(issue.duedate) || toKSTDay(issue.start)
      }
      events.push(event)
    })
  })

  calendarApi.addEventSource(events)
}

async function fetchTasks() {
  if (!startDate.value || !endDate.value) {
    alert("Please select start and end dates")
    return
  }

  loading.value = true
  try {
    const assignees = assigneesInput.value
      ? assigneesInput.value.split(",").map(a => a.trim()).filter(a => a)
      : undefined

    const res = await api.get("/issues/today-tasks", {
      params: { start: startDate.value, end: endDate.value, assignees, status: selectedStatuses.value },
      paramsSerializer: params => qs.stringify(params, { arrayFormat: 'repeat' })
    })

    tasks.value = res.data.groups
    showAssigneeButtons.value = true
    selectedAssigneeFilter.value = 'all'
    refreshCalendar()
  } finally {
    loading.value = false
  }
}

// --- Download filtered tasks as JSON ---
function downloadJSON() {
  const dataStr = JSON.stringify(filteredTasks.value, null, 2)
  const blob = new Blob([dataStr], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = `tasks_${selectedAssigneeFilter.value}_${new Date().toISOString().slice(0,10)}.json`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.q-btn:hover {
  transform: scale(1.05);
  transition: transform 0.1s ease-in-out;
}
</style>
