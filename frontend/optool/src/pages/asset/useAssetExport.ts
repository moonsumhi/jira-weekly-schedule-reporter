// 자산 Export / 템플릿 다운로드 (읽기 전용). ServerAssetPage 에서 분리.
import { ref, type Ref } from 'vue'
import * as XLSX from 'xlsx'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { getErrorMessage } from 'src/utils/http/error'
import { formatKst } from 'src/utils/time/kst'
import type { ServerAsset } from 'src/types/assets'
import { CATEGORY_TEMPLATE_COLS, type TemplateCol } from './assetTemplateColumns'

interface AssetExportOptions {
  filteredRows: Ref<ServerAsset[]>
  category: Ref<string>
  colOptions: { key: string }[]
  columnDisplayOrder: readonly string[]
  fieldLabel: (k: string) => string
}

export function useAssetExport(opts: AssetExportOptions) {
  const $q = useQuasar()
  const exportLoading = ref(false)

  async function doExport() {
    exportLoading.value = true
    try {
      const sourceRows = opts.filteredRows.value
      const colOrder = opts.colOptions.map((o) => o.key)
      // 전체 탭일 때 맨 앞에 자산 종류 추가
      const finalCols = !opts.category.value ? ['__assetType__', ...colOrder] : colOrder

      const header = finalCols.map((k) => {
        if (k === '__asset_id__') return 'Asset ID'
        if (k === '__ip__') return 'IP'
        if (k === '__name__') return 'HostName'
        if (k === '__assetType__') return '자산 종류'
        if (k === 'createdAt') return '작성일'
        return opts.fieldLabel(k)
      })

      const dataRows = sourceRows.map((row) =>
        finalCols.map((k) => {
          if (k === '__asset_id__') return row.assetId ?? ''
          if (k === '__ip__') return row.ip
          if (k === '__name__') return row.name
          if (k === '__assetType__') return (row.fields?.['자산유형'] as string) || '서버'
          if (k === 'createdAt') return row.createdAt ? formatKst(row.createdAt) : ''
          const v = row.fields?.[k]
          if (v === null || v === undefined) return ''
          if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return String(v)
          return JSON.stringify(v)
        }),
      )

      const ws = XLSX.utils.aoa_to_sheet([header, ...dataRows])
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, '서버자산')

      const filename = `서버자산_${new Date().toISOString().slice(0, 10)}.xlsx`
      const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' }) as ArrayBuffer
      const form = new FormData()
      form.append('file', new Blob([buf]), filename)

      const res = await api.post<Blob>('/assets/encrypt-xlsx', form, {
        params: { filename },
        responseType: 'blob',
      })

      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: unknown) {
      $q.notify({ type: 'negative', message: getErrorMessage(err, 'Export 실패') })
    } finally {
      exportLoading.value = false
    }
  }

  function downloadTemplate() {
    const cat = opts.category.value

    // 전체 탭용 — 모든 컬럼
    const defaultCols: TemplateCol[] = [
      { key: 'asset_id', label: 'Asset ID (고유키, 재import 시 매칭용)', sample: '' },
      { key: 'ip', label: 'IP' },
      { key: 'name', label: 'HostName' },
      { key: '자산유형', label: '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)', sample: '' },
      ...opts.columnDisplayOrder
        .filter((k) => k !== '__ip__' && k !== '__name__')
        .map((k) => {
          if (k === '운영체제') return { key: k, label: '운영체제 / 배포판 / 기종 / DB종류' }
          if (k === '서버명') return { key: k, label: '서버명 / 자산명' }
          return { key: k, label: opts.fieldLabel(k) }
        }),
    ]

    const baseCols = CATEGORY_TEMPLATE_COLS[cat] ?? defaultCols

    // 페이지와 동일한 순서로 정렬
    const displayOrder = ['asset_id', 'ip', 'name', '자산유형', ...opts.columnDisplayOrder.map((k) =>
      k === '__ip__' ? 'ip' : k === '__name__' ? 'name' : k,
    )]
    const sorted = [...baseCols].sort((a, b) => {
      const ai = displayOrder.indexOf(a.key)
      const bi = displayOrder.indexOf(b.key)
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
    })

    const headers = sorted.map((c) => {
      if (c.key === 'asset_id') return 'Asset ID'
      if (c.key === 'ip') return 'IP'
      if (c.key === 'name') return 'HostName'
      return c.label ?? opts.fieldLabel(c.key)
    })

    const sample = sorted.map((c) => c.sample ?? '')
    const ws = XLSX.utils.aoa_to_sheet([headers, sample])
    const wb = XLSX.utils.book_new()
    const sheetName = cat || '전체자산'
    XLSX.utils.book_append_sheet(wb, ws, sheetName)
    XLSX.writeFile(wb, `${sheetName}_템플릿.xlsx`)
  }

  return { exportLoading, doExport, downloadTemplate }
}
