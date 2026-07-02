<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <div class="text-h5">조직 관리</div>
      <q-space />
      <q-btn color="primary" icon="add" label="조직 만들기" @click="openCreate" />
    </div>

    <q-inner-loading :showing="loading" />

    <div v-if="!loading && orgs.length === 0" class="column items-center q-mt-xl text-grey-6">
      <q-icon name="fa-solid fa-building" size="48px" class="q-mb-md" />
      <div class="text-body1">조직이 없습니다.</div>
      <div class="text-caption q-mt-xs">새 조직을 만들어 프로젝트를 관리하세요.</div>
    </div>

    <div class="row q-col-gutter-md">
      <div v-for="org in orgs" :key="org.id" class="col-12 col-sm-6 col-md-4">
        <q-card flat bordered class="org-card">
          <q-card-section class="cursor-pointer" @click="goDetail(org.id)">
            <div class="row items-center q-gutter-sm q-mb-xs">
              <q-avatar color="primary" text-color="white" size="36px">
                {{ org.name[0]?.toUpperCase() ?? '' }}
              </q-avatar>
              <div>
                <div class="text-subtitle1 text-weight-medium">{{ org.name }}</div>
                <div class="text-caption text-grey-6">{{ org.slug }}</div>
              </div>
            </div>
          </q-card-section>
          <q-separator />
          <q-card-section class="q-py-xs row items-center">
            <div class="text-caption text-grey-6">생성일: {{ fmtDate(org.createdAt) }}</div>
            <q-space />
            <q-btn
              v-if="auth.me?.isAdmin"
              flat dense round icon="delete" color="negative" size="sm"
              @click.stop="confirmDelete(org)"
            />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- 조직 생성 다이얼로그 -->
    <q-dialog v-model="createDialog.open" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">새 조직 만들기</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model="createDialog.name"
            label="조직 이름 *"
            dense outlined
            :rules="[v => !!v || '필수 항목입니다.']"
            @update:model-value="autoSlug"
          />
          <q-input
            v-model="createDialog.slug"
            label="Slug *"
            dense outlined
            hint="영문 소문자, 숫자, 하이픈만 사용 가능"
            :rules="[
              v => !!v || '필수 항목입니다.',
              v => /^[a-z0-9-]+$/.test(v) || '영문 소문자, 숫자, 하이픈만 허용됩니다.',
            ]"
          />
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" @click="createDialog.open = false" />
          <q-btn
            color="primary" label="생성"
            :loading="createDialog.loading"
            :disable="!createDialog.name || !createDialog.slug"
            @click="submitCreate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Dialog, Notify } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import { listOrganizations, createOrganization, deleteOrganization, type Organization } from 'src/services/pm/organization'
import { getErrorMessage } from 'src/utils/http/error'

const router = useRouter()
const auth = useAuthStore()

const orgs = ref<Organization[]>([])
const loading = ref(false)

const createDialog = ref({
  open: false,
  name: '',
  slug: '',
  loading: false,
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    orgs.value = await listOrganizations()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '조직 목록 로드 실패') })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createDialog.value = { open: true, name: '', slug: '', loading: false }
}

function autoSlug(name: string | number | null) {
  if (!name || typeof name !== 'string') return
  createDialog.value.slug = name
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .slice(0, 50)
}

async function submitCreate() {
  createDialog.value.loading = true
  try {
    const org = await createOrganization({
      name: createDialog.value.name,
      slug: createDialog.value.slug,
    })
    orgs.value.unshift(org)
    createDialog.value.open = false
    Notify.create({ type: 'positive', message: '조직이 생성되었습니다.' })
    void router.push(`/pm/organizations/${org.id}`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '조직 생성 실패') })
  } finally {
    createDialog.value.loading = false
  }
}

function goDetail(orgId: string) {
  void router.push(`/pm/organizations/${orgId}`)
}

function confirmDelete(org: Organization) {
  Dialog.create({
    title: '조직 삭제',
    message: `"${org.name}" 조직을 삭제하시겠습니까? 조직 멤버 정보도 함께 삭제됩니다.`,
    cancel: true,
    persistent: true,
    ok: { color: 'negative', label: '삭제' },
  }).onOk(() => {
    void (async () => {
      try {
        await deleteOrganization(org.id)
        orgs.value = orgs.value.filter(o => o.id !== org.id)
        Notify.create({ type: 'positive', message: '조직이 삭제되었습니다.' })
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' })
}
</script>

<style scoped>
.org-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
</style>
