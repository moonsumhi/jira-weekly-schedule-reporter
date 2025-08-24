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

    <!-- Calendar -->
    <div class="q-mt-lg">
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
import {toKSTPlusOneDay, toKSTDay} from 'src/utils/time'

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

const assigneeList = computed(() => {
  return tasks.value.map(group => group.assignee)
})

const filteredTasks = computed(() => {
  if (selectedAssigneeFilter.value === 'all') return tasks.value
  return tasks.value.filter(group => group.assignee === selectedAssigneeFilter.value)
})

const statusOptions = ["To Do", "In Progress", "Done", "Blocked"]


// Calendar Config
const calendarRef = ref()
const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek'
  },
  displayEventTime: false,
  events: []
})

function statusColor(status: string) {
  switch (status) {
    case "To Do":
      return "#FFC107" // amber
    case "In Progress":
      return "#2196F3" // blue
    case "Done":
      return "#4CAF50" // green
    case "Blocked":
      return "#F44336" // red
    default:
      return "#9E9E9E"
  }
}

// Refresh calendar events dynamically
function refreshCalendar() {
  const calendarApi = calendarRef.value.getApi()
  calendarApi.removeAllEvents()


  const events: EventInput[] = []
  filteredTasks.value.forEach(group => {
    group.issues.forEach(issue => {
      const event: EventInput = {
        title: `${group.assignee}: ${issue.summary} (${issue.key})`,
        url: issue.url,
        color: statusColor(issue.status)
      }

      const startVal = toKSTDay(issue.start)
      if (startVal) event.start = startVal

      const endVal = toKSTPlusOneDay(issue.duedate) || toKSTDay(issue.start)
      if (endVal) event.end = endVal

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
  showAssigneeButtons.value = true
  selectedAssigneeFilter.value = 'all'
  loading.value = false;
  refreshCalendar()
}
</script>

<style scoped>
.q-btn:hover {
  transform: scale(1.05);
  transition: transform 0.1s ease-in-out;
}
</style>
