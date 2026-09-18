<template>
  <button
    type="button"
    class="resource-status-help"
    aria-label="자원 점검 상태 표시 기준"
    :aria-describedby="visible ? tooltipId : undefined"
    @click.stop="visible = true"
    @focus="visible = true"
    @blur="visible = false"
    @keydown.stop
    @keydown.esc="visible = false"
  >
    <q-icon name="info_outline" size="15px" />
    <q-tooltip
      v-model="visible"
      :id="tooltipId"
      class="resource-status-tooltip"
      :no-parent-event="$q.platform.is.mobile === true"
      anchor="bottom middle"
      self="top middle"
      :offset="[0, 8]"
      max-width="min(380px, calc(100vw - 32px))"
    >
      <strong>상태 표시 기준</strong>
      <dl>
        <dt class="status-danger">위험</dt>
        <dd>CPU·RAM 사용률 또는 디스크 최대 사용률이 90% 이상이거나, 하드웨어 점검에서 이상(NG)으로 표시된 항목이 있는 경우</dd>
        <dt class="status-warning">주의</dt>
        <dd>사용량이 80% 이상 90% 미만이거나, 보안·서비스·로그에 이상이 표시된 경우</dd>
        <dt>확인 필요<br />측정값 없음</dt>
        <dd>위험·주의 항목은 없지만 조치 사항, 자산 중복 연결 또는 누락된 측정값을 확인해야 하는 경우</dd>
        <dt>사용량 양호</dt>
        <dd>사용량이 모두 80% 미만이고 다른 확인 항목이 없는 경우</dd>
      </dl>
      <p>하드웨어 점검의 빈칸이나 미선택 항목은 ‘미기록’으로 표시하며, 위험·주의 판정에 포함하지 않습니다.</p>
      <p>여러 조건에 해당하면 위험 → 주의 순으로 표시합니다.</p>
      <p>디스크는 파일시스템별 사용량 중 최댓값을 사용합니다. 상세 값이 없으면 업로드한 요약 값 또는 Total 값을 사용합니다.</p>
    </q-tooltip>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { uid } from 'quasar';

// Criteria follow resource_rows (backend) and buildResourceResults (frontend).
const visible = ref(false);
const tooltipId = `resource-status-${uid()}`;
</script>

<style scoped>
.resource-status-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #7a899c;
  cursor: help;
  vertical-align: middle;
  flex-shrink: 0;
}
.resource-status-help:hover,
.resource-status-help:focus-visible {
  color: #315f8b;
  background: #eaf0f7;
}
.resource-status-help:focus-visible {
  outline: 2px solid #315f8b;
  outline-offset: 1px;
}
:global(.q-tooltip.resource-status-tooltip) {
  padding: 15px 16px;
  background: #fff;
  color: #46566b;
  border: 1px solid #dfe6ef;
  border-radius: 9px;
  box-shadow: 0 5px 20px #233b5829;
  font-size: 12px;
  line-height: 1.65;
}
.resource-status-tooltip strong { display: block; color: #2f435b; font-size: 13px; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 10px 12px; margin: 12px 0; }
dt { font-weight: 600; }
dd { margin: 0; }
.status-danger { color: #b42318; }
.status-warning { color: #9a6014; }
p { margin: 8px 0 0; font-size: 11px; color: #718096; }
</style>
