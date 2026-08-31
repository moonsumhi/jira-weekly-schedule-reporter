<template>
  <div class="rack-mgmt">
    <!-- 헤더 -->
    <div class="rk-head">
      <div>
        <div class="rk-head-title">랙 배치 관리</div>
        <div class="rk-head-sub">랙 {{ racks.length }}대 · 배치 자산 {{ totalAssets }}대 · 미배치 {{ unplaced.length }}대</div>
      </div>
      <q-space />
      <div class="rk-head-search">
        <q-input
          v-model="searchQ"
          dense outlined bg-color="white"
          placeholder="자산명 · 자산번호 · IP · 호스트명"
          @keyup.enter="doSearch"
        >
          <template #prepend><q-icon name="search" /></template>
          <template #append>
            <q-icon v-if="searchQ" name="close" class="cursor-pointer" @click="clearSearch" />
          </template>
          <q-menu v-model="searchMenu" fit no-focus no-parent-event anchor="bottom left" self="top left" max-height="360px">
            <q-list style="min-width: 340px">
              <q-item
                v-for="r in searchResults"
                :key="`${r.assetCategory}-${r.assetId}`"
                clickable v-close-popup
                @click="goToResult(r)"
              >
                <q-item-section avatar>
                  <q-avatar size="30px" :color="r.placement ? 'blue-1' : 'orange-1'" :text-color="r.placement ? 'primary' : 'orange'">
                    <q-icon :name="r.placement ? 'my_location' : 'help_outline'" size="16px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ r.name }} <span class="text-caption text-grey">· {{ r.assetCategory }}</span></q-item-label>
                  <q-item-label caption>
                    {{ r.assetCode || '-' }} · {{ r.ip || 'IP 없음' }}
                    <template v-if="r.placement">· {{ r.placement.rackName }} / U{{ r.placement.startU }}~U{{ r.placement.endU }}</template>
                    <template v-else>· <span class="text-orange">미배치</span></template>
                  </q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="!searchResults.length">
                <q-item-section class="text-grey">검색 결과가 없습니다.</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-input>
      </div>
      <q-btn v-if="selectedRackId" flat round icon="history" color="blue-grey-7" @click="openHistory">
        <q-tooltip>배치 이력</q-tooltip>
      </q-btn>
      <q-btn v-if="isAdmin && integrityIssueCount > 0" flat no-caps icon="warning" color="warning"
        :label="`정합성 이상 ${integrityIssueCount}`" @click="integrityDialog = true">
        <q-tooltip>랙 배치 정합성에 문제가 발견되었습니다. 클릭해 확인하세요.</q-tooltip>
      </q-btn>
      <q-btn v-if="isAdmin" flat round icon="cloud_download" color="blue-grey-7" :loading="loadingMigrate" @click="runMigration">
        <q-tooltip>레거시 RackNo 가져오기</q-tooltip>
      </q-btn>
      <q-btn unelevated color="primary" icon="add" label="랙 추가" @click="openRackCreate" />
    </div>

    <div class="row q-col-gutter-md">
      <!-- 랙 목록 -->
      <div class="col-12 col-md-3">
        <div class="rk-panel-label">랙 목록</div>
        <q-card flat bordered class="rk-list-card">
          <q-scroll-area style="height: calc(100vh - 240px); min-height: 320px">
            <div
              v-for="rk in racks"
              :key="rk.rackId"
              class="rk-list-item"
              :class="{ 'is-active': rk.rackId === selectedRackId }"
              @click="selectRack(rk.rackId)"
            >
              <div class="row items-center no-wrap">
                <q-icon name="dns" size="18px" class="q-mr-sm" :color="rk.rackId === selectedRackId ? 'primary' : 'blue-grey-4'" />
                <div class="col ellipsis">
                  <div class="rk-list-name">{{ rk.name }}</div>
                  <div class="rk-list-room">{{ rk.serverRoom || '서버실 미지정' }}</div>
                </div>
                <div class="rk-list-pct" :class="`text-${usageColor(rk.usageRate)}`">{{ Math.round(rk.usageRate) }}%</div>
              </div>
              <q-linear-progress
                :value="(rk.usageRate || 0) / 100" size="6px" rounded class="q-mt-xs"
                :color="usageColor(rk.usageRate)" track-color="blue-grey-1"
              />
              <div class="rk-list-meta">
                <span>{{ rk.usedU }}/{{ rk.totalU }}U</span>
                <span>빈 {{ rk.maxContiguousFreeU }}U · {{ rk.assetCount }}대</span>
              </div>
            </div>
            <div v-if="!racks.length && !loading" class="rk-empty">
              <q-icon name="dns" size="32px" color="blue-grey-2" />
              <div>등록된 랙이 없습니다.</div>
              <q-btn flat dense color="primary" label="랙 추가" @click="openRackCreate" />
            </div>
          </q-scroll-area>
        </q-card>
      </div>

      <!-- 배치도 -->
      <div class="col-12 col-md-6">
        <div class="rk-panel-label">배치도</div>
        <q-card flat bordered class="q-pa-md rk-elev-card">
          <RackElevation
            v-if="layout"
            :layout="layout"
            :highlight-asset-id="highlightAssetId"
            :side="side"
            @select="onSelectAsset"
            @click-empty="onClickEmpty"
            @move-drop="onMoveDrop"
            @update:side="side = $event"
          />
          <div v-else class="rk-empty rk-empty--big">
            <q-icon name="grid_view" size="40px" color="blue-grey-2" />
            <div>좌측에서 랙을 선택하세요.</div>
          </div>
        </q-card>
      </div>

      <!-- 우측 -->
      <div class="col-12 col-md-3">
        <div class="rk-panel-label">{{ selectedAsset ? '자산 상세' : '랙 정보' }}</div>
        <!-- 상세 / 랙 정보 -->
        <q-card flat bordered class="q-mb-md rk-detail-card">
          <template v-if="selectedAsset">
            <div class="rk-detail-head" :style="{ '--accent': catColor(selectedAsset.assetCategory) }">
              <q-avatar size="34px" square rounded :style="{ background: catColor(selectedAsset.assetCategory) }" text-color="white">
                <q-icon :name="catIcon(selectedAsset.assetCategory)" size="18px" />
              </q-avatar>
              <div class="col ellipsis">
                <div class="rk-detail-name">{{ selectedAsset.name }}</div>
                <div class="rk-detail-cat">{{ selectedAsset.assetCategory }}</div>
              </div>
              <q-btn flat round dense size="sm" icon="info" :loading="loadingAssetInfo" @click="openAssetInfo">
                <q-tooltip>자산 상세 정보</q-tooltip>
              </q-btn>
              <q-btn flat round dense size="sm" icon="close" @click="selectedAsset = null; highlightAssetId = null" />
            </div>
            <q-separator />
            <div class="rk-kv">
              <div class="rk-kv-row"><span>자산번호</span><b>{{ selectedAsset.assetCode || '—' }}</b></div>
              <div class="rk-kv-row"><span>IP</span><b>{{ selectedAsset.ip || '—' }}</b></div>
              <div class="rk-kv-row"><span>랙 위치</span><b>{{ layout?.rack.name }} / U{{ selectedAsset.startU }}~U{{ selectedAsset.endU }}</b></div>
              <div class="rk-kv-row"><span>크기 / 면</span><b>{{ selectedAsset.heightU }}U · {{ mountLabel(selectedAsset.mountSide) }}</b></div>
            </div>
            <q-separator />
            <div class="rk-detail-actions">
              <q-btn unelevated color="primary" icon="edit_location_alt" label="수정" class="col" @click="openMove" />
              <q-btn outline color="negative" icon="logout" label="반출" class="col" :loading="removing" @click="confirmRemove" />
            </div>
          </template>
          <template v-else-if="layout">
            <div class="rk-detail-head" style="--accent: #607d8b">
              <q-avatar size="34px" square rounded color="blue-grey-6" text-color="white"><q-icon name="dns" size="18px" /></q-avatar>
              <div class="col ellipsis">
                <div class="rk-detail-name">{{ layout.rack.name }}</div>
                <div class="rk-detail-cat">{{ layout.rack.serverRoom || '서버실 미지정' }}</div>
              </div>
              <q-badge :color="statusColor(layout.rack.status)" class="q-pa-xs">{{ layout.rack.status || '-' }}</q-badge>
            </div>
            <q-separator />
            <div v-if="rackEditing" class="rk-edit-form">
              <label class="rk-edit-label">랙 이름 <em>*</em></label>
              <q-input v-model="rackEditForm.name" dense outlined autofocus hide-bottom-space />

              <label class="rk-edit-label">랙 코드</label>
              <q-input v-model="rackEditForm.assetId" dense outlined hide-bottom-space />

              <label class="rk-edit-label">서버실(위치)</label>
              <div class="rk-edit-control">
                <q-select
                  v-model="rackEditRoomSelect"
                  :options="[...locationOptions, '기타']"
                  dense outlined clearable hide-bottom-space
                  @update:model-value="onRackEditRoomChange"
                />
                <q-input
                  v-if="rackEditRoomSelect === '기타'"
                  v-model="rackEditForm.serverRoom"
                  dense outlined hide-bottom-space
                  placeholder="서버실 직접 입력"
                  class="q-mt-sm"
                />
              </div>

              <label class="rk-edit-label">전체 U <em>*</em></label>
              <q-input v-model.number="rackEditForm.totalU" type="number" min="1" dense outlined hide-bottom-space />

              <label class="rk-edit-label">상태</label>
              <q-select v-model="rackEditForm.status" :options="STATUS_OPTIONS" dense outlined hide-bottom-space />

              <label class="rk-edit-label">최대 하중(kg)</label>
              <q-input v-model.number="rackEditForm.maxLoadKg" type="number" min="0" dense outlined hide-bottom-space />

              <label class="rk-edit-label">최대 전력(W)</label>
              <q-input v-model.number="rackEditForm.maxPowerW" type="number" min="0" dense outlined hide-bottom-space />
            </div>
            <div v-else class="rk-kv">
              <div class="rk-kv-row"><span>랙 코드</span><b>{{ layout.rack.assetCode || '—' }}</b></div>
              <div class="rk-kv-row"><span>사용</span><b>{{ layout.rack.usedU }}/{{ layout.rack.totalU }}U ({{ layout.rack.usageRate }}%)</b></div>
              <div class="rk-kv-row"><span>최대 연속 빈</span><b>{{ layout.rack.maxContiguousFreeU }}U</b></div>
              <div class="rk-kv-row"><span>최대 허용 하중</span><b>{{ layout.rack.maxLoadKg != null ? layout.rack.maxLoadKg + ' kg' : '—' }}</b></div>
              <div class="rk-kv-row"><span>최대 허용 전력</span><b>{{ layout.rack.maxPowerW != null ? layout.rack.maxPowerW + ' W' : '—' }}</b></div>
            </div>
            <q-separator />
            <div v-if="rackEditing" class="rk-detail-actions">
              <q-btn flat color="blue-grey-7" label="취소" class="col" :disable="savingRackEdit" @click="cancelRackEdit" />
              <q-btn
                unelevated color="primary" icon="save" label="저장" class="col"
                :loading="savingRackEdit"
                :disable="!rackEditForm.name.trim() || rackEditForm.totalU < 1"
                @click="saveRackEdit"
              />
            </div>
            <div v-else class="rk-detail-actions">
              <q-btn unelevated color="primary" icon="edit" label="수정" class="col" :loading="loadingRackEdit" @click="openRackEdit" />
              <q-btn outline color="negative" icon="delete" label="삭제" class="col" :loading="deletingRack" @click="confirmDeleteRack" />
            </div>
          </template>
          <div v-else class="rk-empty"><q-icon name="touch_app" size="28px" color="blue-grey-2" /><div>자산 또는 랙을 선택하세요.</div></div>
        </q-card>

        <!-- 미배치 자산 -->
        <div class="rk-panel-label">미배치 자산 <q-badge color="orange" class="q-ml-xs">{{ unplaced.length }}</q-badge></div>
        <q-card flat bordered class="rk-unplaced-card">
          <div v-if="pendingAsset" class="rk-pending">
            <q-icon name="place" size="16px" class="q-mr-xs" />
            <span class="col ellipsis"><b>{{ pendingAsset.name }}</b> — 빈 U 클릭</span>
            <q-btn flat dense size="sm" round icon="close" @click="pendingAsset = null" />
          </div>
          <q-scroll-area style="height: 240px">
            <q-list dense>
              <q-item
                v-for="a in unplaced"
                :key="`${a.assetCategory}-${a.assetId}`"
                clickable
                :active="pendingAsset?.assetId === a.assetId"
                active-class="rk-pending-active"
                @click="selectPending(a)"
              >
                <q-item-section avatar>
                  <span class="rk-unplaced-dot" :style="{ background: catColor(a.assetCategory) }" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="ellipsis">{{ a.name }}</q-item-label>
                  <q-item-label caption>{{ a.assetCategory }} · {{ a.assetCode || a.ip || '—' }}</q-item-label>
                </q-item-section>
                <q-item-section side><q-icon name="add_location_alt" size="18px" color="blue-grey-4" /></q-item-section>
              </q-item>
              <div v-if="!unplaced.length" class="rk-empty rk-empty--sm">
                <q-icon name="check_circle" size="24px" color="green-3" /><div>모든 자산이 배치되었습니다.</div>
              </div>
            </q-list>
          </q-scroll-area>
        </q-card>
      </div>
    </div>

    <RackPlacementDialog
      v-model="dialogOpen"
      :mode="dialogMode"
      :rack-id="selectedRackId"
      :racks="racks"
      :preset-start-u="presetStartU"
      :preset-height="presetHeight"
      :preset-mount-side="presetMountSide"
      :asset="dialogMode === 'move' ? selectedAsset : null"
      :placement-id="selectedAsset?.placementId ?? null"
      :preset-asset="dialogMode === 'place' && pendingAsset
        ? { assetCategory: pendingAsset.assetCategory, assetId: pendingAsset.assetId, name: pendingAsset.name }
        : null"
      @saved="onSaved"
    />

    <!-- 자산 상세 정보 -->
    <q-dialog v-model="assetInfoDialog">
      <q-card style="width: 520px; max-width: 95vw">
        <q-card-section class="row items-center q-pb-sm" :style="{ borderTop: `3px solid ${catColor(assetInfo?.fields?.['자산유형'] as string || selectedAsset?.assetCategory || '')}` }">
          <q-avatar size="34px" square rounded :style="{ background: catColor(selectedAsset?.assetCategory || '') }" text-color="white">
            <q-icon :name="catIcon(selectedAsset?.assetCategory || '')" size="18px" />
          </q-avatar>
          <div class="col q-ml-sm ellipsis">
            <div class="text-h6 ellipsis">{{ assetInfo?.name }}</div>
            <div class="text-caption text-grey-6">{{ selectedAsset?.assetCategory }}</div>
          </div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow-y: auto">
          <div class="rk-info-grid">
            <template v-if="assetInfo">
              <div class="rk-info-row"><span>자산번호</span><b>{{ assetInfo.assetNo || '—' }}</b></div>
              <div class="rk-info-row"><span>Asset ID</span><b>{{ assetInfo.assetId || '—' }}</b></div>
              <div class="rk-info-row"><span>IP</span><b>{{ assetInfo.ip || '—' }}</b></div>
              <div v-for="e in assetInfoEntries" :key="e.label" class="rk-info-row"><span>{{ e.label }}</span><b>{{ e.value }}</b></div>
            </template>
          </div>
        </q-card-section>
        <q-card-actions align="right"><q-btn flat label="닫기" v-close-popup /></q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 랙 추가 -->
    <q-dialog v-model="rackDialog">
      <q-card style="width: 460px; max-width: 95vw">
        <q-card-section class="row items-center q-pb-none">
          <q-avatar size="30px" square rounded color="primary" text-color="white"><q-icon name="add" size="18px" /></q-avatar>
          <span class="text-h6 q-ml-sm">랙 추가</span>
        </q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-sm">
            <div class="col-12">
              <q-input v-model="rackForm.name" label="랙 이름 *" outlined dense autofocus />
            </div>
            <div class="col-6">
              <q-input v-model="rackForm.assetId" label="랙 코드 (선택)" outlined dense />
            </div>
            <div class="col-6">
              <q-select
                v-model="rackRoomSelect"
                :options="[...locationOptions, '기타']"
                label="서버실(위치)" outlined dense clearable
                @update:model-value="(v: string) => { rackForm.serverRoom = v && v !== '기타' ? v : '' }"
              />
            </div>
            <div v-if="rackRoomSelect === '기타'" class="col-12">
              <q-input v-model="rackForm.serverRoom" label="서버실 직접 입력" outlined dense />
            </div>
            <div class="col-6">
              <q-input v-model.number="rackForm.totalU" type="number" label="전체 U *" outlined dense min="1" />
            </div>
            <div class="col-6">
              <q-select v-model="rackForm.status" :options="STATUS_OPTIONS" label="상태" outlined dense />
            </div>
            <div class="col-6">
              <q-input v-model.number="rackForm.maxLoadKg" type="number" label="최대 하중(kg)" outlined dense />
            </div>
            <div class="col-6">
              <q-input v-model.number="rackForm.maxPowerW" type="number" label="최대 전력(W)" outlined dense />
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn unelevated color="primary" label="추가" :loading="savingRack" :disable="!rackForm.name || rackForm.totalU < 1" @click="createRack" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 배치 이력 -->
    <q-dialog v-model="historyDialog">
      <q-card style="width: 640px; max-width: 95vw">
        <q-card-section class="row items-center q-pb-sm">
          <q-icon name="history" size="22px" class="q-mr-sm text-blue-grey-7" />
          <span class="text-h6">배치 이력</span>
          <span class="text-grey q-ml-sm">· {{ layout?.rack.name }}</span>
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow-y: auto">
          <q-timeline v-if="history.length" color="blue-grey-4">
            <q-timeline-entry
              v-for="h in history"
              :key="h.id"
              :icon="actionIcon(h.action)"
              :color="actionColor(h.action)"
            >
              <template #title>
                <span class="text-body2 text-weight-medium">{{ actionLabel(h.action) }} · {{ h.assetName || h.assetId }}</span>
              </template>
              <template #subtitle>{{ fmtDate(h.changedAt) }} · {{ h.changedBy || '' }}</template>
              <div class="text-caption text-grey-8">
                <template v-if="h.before"><q-icon name="arrow_back" size="12px" /> {{ posLabel(h.before) }}<br /></template>
                <template v-if="h.after"><q-icon name="arrow_forward" size="12px" /> {{ posLabel(h.after) }}</template>
              </div>
            </q-timeline-entry>
          </q-timeline>
          <div v-else class="rk-empty"><q-icon name="inbox" size="28px" color="blue-grey-2" /><div>이력이 없습니다.</div></div>
        </q-card-section>
        <q-card-actions align="right"><q-btn flat label="닫기" v-close-popup /></q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 정합성 점검 -->
    <q-dialog v-model="integrityDialog">
      <q-card style="width: 640px; max-width: 95vw">
        <q-card-section class="row items-center q-pb-sm">
          <q-icon name="fact_check" size="22px" class="q-mr-sm text-blue-grey-7" />
          <span class="text-h6">정합성 점검</span>
          <q-space />
          <q-badge :color="integrity?.status === 'OK' ? 'positive' : 'warning'" class="q-pa-xs">
            {{ integrity?.status }} · {{ integrity?.issueCount ?? 0 }}건
          </q-badge>
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow-y: auto">
          <q-list v-if="integrity && integrity.issues.length" separator>
            <q-item v-for="(iss, i) in integrity.issues" :key="i">
              <q-item-section avatar><q-icon name="warning" color="warning" /></q-item-section>
              <q-item-section>
                <q-item-label>{{ iss.type }}</q-item-label>
                <q-item-label caption>{{ iss.detail }} <span v-if="iss.assetId">· {{ iss.assetCategory }}/{{ iss.assetId }}</span></q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
          <div v-else class="rk-empty"><q-icon name="verified" size="30px" color="green-4" /><div>문제가 발견되지 않았습니다.</div></div>
        </q-card-section>
        <q-card-actions align="right"><q-btn flat label="닫기" v-close-popup /></q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'
import RackElevation from './RackElevation.vue'
import RackPlacementDialog from './RackPlacementDialog.vue'
import {
  getRackHistory, getRackLayout, integrityCheck, listRacks, listUnplacedAssets,
  migrateRackFromFields, movePlacement, removePlacement, searchRackAssets,
} from 'src/services/racks'
import { createServer, deleteServer, getServer, patchServer } from 'src/services/assets'
import { envCategoryService } from 'src/services/envCategory'
import type { ServerAsset } from 'src/types/assets'
import type {
  AssetSearchResult, IntegrityReport, MountSide, PlacementHistory, PlacementHistoryPos,
  RackLayout, RackPlacementAsset, RackSummary, UnplacedAsset,
} from 'src/types/racks'

const $q = useQuasar()
const auth = useAuthStore()
const isAdmin = computed(() => !!auth.me?.isAdmin)

const racks = ref<RackSummary[]>([])
const selectedRackId = ref('')
const layout = ref<RackLayout | null>(null)
const selectedAsset = ref<RackPlacementAsset | null>(null)
const highlightAssetId = ref<string | null>(null)
const loading = ref(false)
const removing = ref(false)
const side = ref<'ALL' | 'FRONT' | 'REAR'>('ALL')

const searchQ = ref('')
const searchResults = ref<AssetSearchResult[]>([])
const searchMenu = ref(false)

const unplaced = ref<UnplacedAsset[]>([])
const pendingAsset = ref<UnplacedAsset | null>(null)

const dialogOpen = ref(false)
const dialogMode = ref<'place' | 'move'>('place')
const presetStartU = ref<number | null>(null)
const presetHeight = ref<number | null>(null)
const presetMountSide = ref<'FULL' | 'FRONT' | 'REAR'>('FULL')

const STATUS_OPTIONS = ['ACTIVE', '점검', '폐기']
const rackDialog = ref(false)
const savingRack = ref(false)
const deletingRack = ref(false)
const rackEditing = ref(false)
const loadingRackEdit = ref(false)
const savingRackEdit = ref(false)
const rackEditAsset = ref<ServerAsset | null>(null)
const locationOptions = ref<string[]>([])
const rackRoomSelect = ref('')
const rackEditRoomSelect = ref('')
const rackForm = reactive({
  name: '', assetId: '', serverRoom: '', totalU: 42, status: 'ACTIVE',
  maxLoadKg: null as number | null, maxPowerW: null as number | null,
})
const rackEditForm = reactive({
  name: '', assetId: '', serverRoom: '', totalU: 42, status: 'ACTIVE',
  maxLoadKg: null as number | null, maxPowerW: null as number | null,
})

const assetInfoDialog = ref(false)
const assetInfo = ref<ServerAsset | null>(null)
const loadingAssetInfo = ref(false)

const historyDialog = ref(false)
const history = ref<PlacementHistory[]>([])
const integrityDialog = ref(false)
const integrity = ref<IntegrityReport | null>(null)
const integrityIssueCount = ref(0)
const loadingMigrate = ref(false)

const totalAssets = computed(() => racks.value.reduce((s, r) => s + (r.assetCount || 0), 0))

const CAT_COLOR: Record<string, string> = {
  서버: '#1976d2', 네트워크: '#009688', 정보보호시스템: '#9c27b0', DBMS: '#f57c00', VMware: '#43a047',
}
const CAT_ICON: Record<string, string> = {
  서버: 'dns', 네트워크: 'lan', 정보보호시스템: 'shield', DBMS: 'storage', VMware: 'cloud',
}
function catColor(c: string): string { return CAT_COLOR[c] || '#64748b' }
function catIcon(c: string): string { return CAT_ICON[c] || 'memory' }
function usageColor(r: number): string { return r >= 90 ? 'negative' : r >= 70 ? 'orange' : 'primary' }
function statusColor(s?: string | null): string { return s === '폐기' ? 'negative' : s === '점검' ? 'orange' : 'positive' }
function mountLabel(s: MountSide): string { return s === 'FULL' ? '전체(전·후면)' : s === 'FRONT' ? '전면' : '후면' }

const FIELD_LABELS: Record<string, string> = {
  rack_no: 'RackNo.', rack_unit_no: 'Rack Unit No.', asset_id: 'Asset ID',
}
const assetInfoEntries = computed(() => {
  const f = assetInfo.value?.fields ?? {}
  return Object.entries(f)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => ({
      label: FIELD_LABELS[k] ?? k,
      value: Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v),
    }))
})

async function openAssetInfo() {
  if (!selectedAsset.value) return
  loadingAssetInfo.value = true
  try {
    assetInfo.value = await getServer(selectedAsset.value.assetId, selectedAsset.value.assetCategory)
    assetInfoDialog.value = true
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErr(e, '자산 정보를 불러오지 못했습니다.') })
  } finally {
    loadingAssetInfo.value = false
  }
}

const SELECTED_RACK_KEY = 'rackMgmt:selectedRackId'

async function loadRacks() {
  loading.value = true
  try {
    racks.value = await listRacks()
    if (!selectedRackId.value && racks.value.length) {
      // 새로고침 시 마지막으로 보던 랙 복원(없으면 첫 번째)
      const saved = localStorage.getItem(SELECTED_RACK_KEY)
      const target = racks.value.find((r) => r.rackId === saved) ?? racks.value[0]!
      await selectRack(target.rackId)
    }
  } finally {
    loading.value = false
  }
}

async function selectRack(rackId: string) {
  cancelRackEdit()
  selectedRackId.value = rackId
  selectedAsset.value = null
  highlightAssetId.value = null
  localStorage.setItem(SELECTED_RACK_KEY, rackId)
  layout.value = await getRackLayout(rackId)
}

async function loadUnplaced() { unplaced.value = await listUnplacedAssets() }

async function reloadAll() {
  await loadRacks()
  if (selectedRackId.value) await selectRack(selectedRackId.value)
  await loadUnplaced()
  await checkIntegrity()
}

function onSelectAsset(p: RackPlacementAsset) {
  cancelRackEdit()
  selectedAsset.value = p
  highlightAssetId.value = p.assetId
}

function selectPending(a: UnplacedAsset) {
  pendingAsset.value = a
  $q.notify({ type: 'info', message: '배치할 빈 U 를 클릭하세요.', timeout: 1500, position: 'top' })
}

function onClickEmpty(u: number, s: 'FULL' | 'FRONT' | 'REAR') {
  if (!selectedRackId.value) return
  dialogMode.value = 'place'
  presetStartU.value = u
  presetHeight.value = 1
  presetMountSide.value = s
  dialogOpen.value = true
}

function openMove() {
  if (!selectedAsset.value) return
  dialogMode.value = 'move'
  presetStartU.value = selectedAsset.value.startU
  presetHeight.value = selectedAsset.value.heightU
  dialogOpen.value = true
}

function confirmRemove() {
  if (!selectedAsset.value) return
  const p = selectedAsset.value
  $q.dialog({
    title: '자산 반출',
    message: `${p.name} 을(를) 랙에서 반출합니다. 해당 U 는 비게 됩니다.`,
    cancel: true,
    ok: { label: '반출', color: 'negative', unelevated: true },
  }).onOk(() => { void doRemove(p) })
}

async function doRemove(p: RackPlacementAsset) {
  removing.value = true
  try {
    await removePlacement(p.placementId)
    $q.notify({ type: 'positive', message: '반출했습니다.' })
    selectedAsset.value = null
    await reloadAll()
  } catch {
    $q.notify({ type: 'negative', message: '반출에 실패했습니다.' })
  } finally {
    removing.value = false
  }
}

async function onMoveDrop(payload: { placement: RackPlacementAsset; startU: number; targetSide: 'FRONT' | 'REAR' }) {
  const p = payload.placement
  // 깊이 전체(FULL) 장비는 그대로 유지, 전면/후면 장비는 드롭한 레인의 면으로 변경
  const mountSide: MountSide = p.mountSide === 'FULL' ? 'FULL' : payload.targetSide
  try {
    await movePlacement(p.placementId, {
      rackId: selectedRackId.value, startU: payload.startU,
      heightU: p.heightU, mountSide, expectedVersion: p.version,
    })
    $q.notify({ type: 'positive', message: '이동했습니다.' })
    await reloadAll()
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErr(e, '이동에 실패했습니다.') })
  }
}

async function onSaved() {
  pendingAsset.value = null
  await reloadAll()
}

async function doSearch() {
  const q = searchQ.value.trim()
  if (!q) { searchResults.value = []; searchMenu.value = false; return }
  searchResults.value = await searchRackAssets(q)
  searchMenu.value = true
}

function clearSearch() {
  searchQ.value = ''
  searchResults.value = []
  searchMenu.value = false
}

async function goToResult(r: AssetSearchResult) {
  if (!r.placement) { $q.notify({ type: 'info', message: '미배치 자산입니다.' }); return }
  await selectRack(r.placement.rackId)
  highlightAssetId.value = r.assetId
  const found = layout.value?.placements.find((p) => p.assetId === r.assetId)
  if (found) selectedAsset.value = found
}

function openRackCreate() {
  Object.assign(rackForm, {
    name: '', assetId: '', serverRoom: '', totalU: 42, status: 'ACTIVE', maxLoadKg: null, maxPowerW: null,
  })
  rackRoomSelect.value = ''
  rackDialog.value = true
}

function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function textOr(value: unknown, fallback = ''): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : fallback
}

function onRackEditRoomChange(value: string | null) {
  rackEditForm.serverRoom = value && value !== '기타' ? value : ''
}

async function openRackEdit() {
  const rackId = selectedRackId.value
  if (!rackId || !layout.value) return
  loadingRackEdit.value = true
  try {
    const rack = await getServer(rackId, '랙')
    const fields = rack.fields ?? {}
    const serverRoom = textOr(fields.server_room, layout.value.rack.serverRoom ?? '')
    rackEditAsset.value = rack
    Object.assign(rackEditForm, {
      name: rack.name,
      assetId: rack.assetId ?? '',
      serverRoom,
      totalU: Number(fields.total_u ?? layout.value.rack.totalU ?? 42),
      status: textOr(fields.status, layout.value.rack.status ?? 'ACTIVE'),
      maxLoadKg: numberOrNull(fields.max_load_kg),
      maxPowerW: numberOrNull(fields.max_power_w),
    })
    rackEditRoomSelect.value = !serverRoom
      ? ''
      : locationOptions.value.includes(serverRoom) ? serverRoom : '기타'
    rackEditing.value = true
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErr(e, '랙 정보를 불러오지 못했습니다.') })
  } finally {
    loadingRackEdit.value = false
  }
}

function cancelRackEdit() {
  rackEditing.value = false
  rackEditAsset.value = null
}

async function saveRackEdit() {
  const rack = rackEditAsset.value
  const rackId = selectedRackId.value
  if (!rack || !rackId) return
  savingRackEdit.value = true
  try {
    await patchServer(rackId, {
      name: rackEditForm.name.trim(),
      asset_id: rackEditForm.assetId.trim() || null,
      fields: {
        ...rack.fields,
        server_room: rackEditForm.serverRoom.trim(),
        total_u: Number(rackEditForm.totalU),
        status: rackEditForm.status,
        u_direction: rack.fields.u_direction ?? 'BOTTOM_UP',
        max_load_kg: rackEditForm.maxLoadKg,
        max_power_w: rackEditForm.maxPowerW,
      },
      ...(rack.version != null ? { version: rack.version } : {}),
    }, '랙')
    $q.notify({ type: 'positive', message: '랙 정보를 수정했습니다.' })
    cancelRackEdit()
    await reloadAll()
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErr(e, '랙 수정에 실패했습니다.') })
  } finally {
    savingRackEdit.value = false
  }
}

async function createRack() {
  savingRack.value = true
  try {
    await createServer(
      '', rackForm.name.trim(),
      {
        server_room: rackForm.serverRoom.trim(), total_u: rackForm.totalU, status: rackForm.status,
        u_direction: 'BOTTOM_UP', max_load_kg: rackForm.maxLoadKg, max_power_w: rackForm.maxPowerW,
      },
      null, '랙', rackForm.assetId.trim() || null,
    )
    $q.notify({ type: 'positive', message: '랙을 추가했습니다.' })
    rackDialog.value = false
    await loadRacks()
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErr(e, '랙 추가에 실패했습니다.') })
  } finally {
    savingRack.value = false
  }
}

function apiErr(e: unknown, fallback: string): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) return String(detail.message)
  return fallback
}

function confirmDeleteRack() {
  if (!layout.value) return
  const name = layout.value.rack.name
  $q.dialog({
    title: '랙 삭제',
    message: `랙 "${name}" 을(를) 삭제합니다. 배치된 자산이 있으면 삭제할 수 없습니다.`,
    cancel: true,
    ok: { label: '삭제', color: 'negative', unelevated: true },
  }).onOk(() => { void doDeleteRack() })
}

async function doDeleteRack() {
  const rackId = selectedRackId.value
  if (!rackId) return
  deletingRack.value = true
  try {
    await deleteServer(rackId, undefined, '랙')
    $q.notify({ type: 'positive', message: '랙을 삭제했습니다.' })
    selectedRackId.value = ''
    layout.value = null
    await reloadAll()
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErr(e, '랙 삭제에 실패했습니다.') })
  } finally {
    deletingRack.value = false
  }
}

async function openHistory() {
  if (!selectedRackId.value) return
  history.value = await getRackHistory(selectedRackId.value)
  historyDialog.value = true
}

// 백그라운드 정합성 점검: 문제가 있을 때만 툴바에 경고 노출 (평소엔 숨김)
async function checkIntegrity() {
  if (!isAdmin.value) return
  try {
    integrity.value = await integrityCheck()
    integrityIssueCount.value = integrity.value.issueCount
  } catch {
    integrityIssueCount.value = 0
  }
}

async function runMigration() {
  loadingMigrate.value = true
  try {
    const dry = await migrateRackFromFields(true)
    const racks = dry.racksToCreate ?? []
    const rackList = racks.length
      ? `<div style="margin:4px 0 8px; padding:6px 8px; background:#f5f5f5; border-radius:4px; font-size:12px">${racks.map((r) => `• ${r}`).join('<br>')}</div>`
      : ''
    $q.dialog({
      title: '레거시 RackNo 가져오기',
      message:
        `기존 자산의 RackNo/Rack Unit No 를 랙 배치로 이관합니다.<br><br>`
        + `· 새로 만들 랙: <b>${racks.length}</b>개 (42U)`
        + rackList
        + `· 배치 예정: <b>${dry.placementsCreated}</b>건<br>`
        + `· U 정보 없어 건너뜀: ${dry.skippedNoUnit}건<br>`
        + `· 이미 배치됨: ${dry.skippedAlreadyPlaced}건<br><br>`
        + `진행할까요?`,
      html: true,
      cancel: true,
      ok: { label: '이관 실행', color: 'primary', unelevated: true },
    }).onOk(() => { void doMigrate() })
  } catch {
    $q.notify({ type: 'negative', message: '이관 미리보기에 실패했습니다.' })
  } finally {
    loadingMigrate.value = false
  }
}

async function doMigrate() {
  loadingMigrate.value = true
  try {
    const r = await migrateRackFromFields(false)
    $q.notify({
      type: 'positive',
      message: `랙 ${(r.racksCreated ?? []).length}개 생성 · 배치 ${r.placementsCreated}건`
        + (r.skippedConflict ? ` · 충돌 ${r.skippedConflict}건 건너뜀` : ''),
      timeout: 4000,
    })
    await reloadAll()
  } catch {
    $q.notify({ type: 'negative', message: '이관에 실패했습니다.' })
  } finally {
    loadingMigrate.value = false
  }
}

function actionLabel(a: string): string { return a === 'PLACE' ? '배치' : a === 'MOVE' ? '이동' : a === 'REMOVE' ? '반출' : a }
function actionColor(a: string): string { return a === 'PLACE' ? 'primary' : a === 'MOVE' ? 'orange' : a === 'REMOVE' ? 'negative' : 'grey' }
function actionIcon(a: string): string { return a === 'PLACE' ? 'add_location_alt' : a === 'MOVE' ? 'open_with' : a === 'REMOVE' ? 'logout' : 'circle' }
function posLabel(pos: PlacementHistoryPos): string {
  if (!pos.rackName && pos.startU == null) return '-'
  const s = pos.mountSide && pos.mountSide !== 'FULL' ? ` (${pos.mountSide === 'FRONT' ? '전면' : '후면'})` : ''
  return `${pos.rackName || pos.rackId || ''} / U${pos.startU}~U${pos.endU}${s}`
}
function fmtDate(s: string): string { return new Date(s).toLocaleString('ko-KR') }

async function loadLocationOptions() {
  try {
    const items = await envCategoryService.itemsByKey('asset_location')
    locationOptions.value = items.map((i) => i.value || i.label)
  } catch { /* 무시 */ }
}

onMounted(() => { void loadRacks(); void loadUnplaced(); void checkIntegrity(); void loadLocationOptions() })
</script>

<style scoped>
.rack-mgmt { padding-bottom: 8px; }

/* 헤더 */
.rk-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
}
.rk-head-title {
  font-size: 20px;
  font-weight: 700;
  color: #263238;
}
.rk-head-sub {
  font-size: 12px;
  color: #90a4ae;
  margin-top: 2px;
}
.rk-head-search { width: 320px; max-width: 40vw; }

/* 패널 라벨 */
.rk-panel-label {
  font-size: 12px;
  font-weight: 700;
  color: #78909c;
  letter-spacing: 0.3px;
  margin-bottom: 6px;
  padding-left: 2px;
}

/* 랙 목록 */
.rk-list-card { border-radius: 10px; overflow: hidden; }
.rk-list-item {
  padding: 10px 12px;
  border-bottom: 1px solid #eceff1;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background 0.12s, border-color 0.12s;
}
.rk-list-item:hover { background: #f5f7f9; }
.rk-list-item.is-active {
  background: #e8f2fe;
  border-left-color: #1976d2;
}
.rk-list-name { font-size: 13px; font-weight: 600; color: #37474f; }
.rk-list-room { font-size: 11px; color: #b0bec5; }
.rk-list-pct { font-size: 13px; font-weight: 700; }
.rk-list-meta {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #b0bec5;
  margin-top: 4px;
}

/* 배치도 카드 */
.rk-elev-card { border-radius: 10px; }

/* 상세 */
.rk-detail-card { border-radius: 10px; overflow: hidden; }
.rk-detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: linear-gradient(180deg, #fafbfc, #f1f4f6);
  border-top: 3px solid var(--accent, #607d8b);
}
.rk-detail-name { font-size: 14px; font-weight: 700; color: #263238; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rk-detail-cat { font-size: 11px; color: #90a4ae; }
.rk-kv { padding: 6px 12px; }
.rk-kv-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  font-size: 12px;
}
.rk-kv-row span { color: #90a4ae; flex: 0 0 auto; }
.rk-kv-row b { color: #37474f; font-weight: 600; text-align: right; min-width: 0; }
.rk-edit-form {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  align-items: center;
  gap: 10px 8px;
  padding: 12px;
}
.rk-edit-label {
  color: #78909c;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.3;
  text-align: right;
}
.rk-edit-label em { color: #d32f2f; font-style: normal; }
.rk-edit-control { min-width: 0; }
.rk-detail-actions { display: flex; gap: 8px; padding: 12px; }

/* 미배치 */
.rk-unplaced-card { border-radius: 10px; overflow: hidden; }
.rk-pending {
  display: flex;
  align-items: center;
  padding: 6px 10px;
  background: #e8f2fe;
  color: #1565c0;
  font-size: 12px;
  border-bottom: 1px solid #d6e6fb;
}
.rk-pending-active { background: #e8f2fe; }
.rk-unplaced-dot { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

/* 자산 상세 정보 */
.rk-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 20px;
}
.rk-info-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 2px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
  min-width: 0;
}
.rk-info-row span { color: #9e9e9e; flex: 0 0 auto; }
.rk-info-row b { color: #37474f; font-weight: 600; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 빈 상태 */
.rk-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 28px 16px;
  color: #b0bec5;
  font-size: 13px;
  text-align: center;
}
.rk-empty--big { padding: 80px 16px; }
.rk-empty--sm { padding: 24px 12px; }
</style>
