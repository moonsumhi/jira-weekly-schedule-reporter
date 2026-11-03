import type { RackPlacementForm, RackSummary } from 'src/types/racks'

export function placementRangeError(form: RackPlacementForm, racks: RackSummary[]): string {
  const rack = racks.find(item => item.rackId === form.rackId)
  if (!rack) return '랙을 선택해 주세요.'
  if (!Number.isInteger(form.startU) || !Number.isInteger(form.heightU) || form.startU < 1 || form.heightU < 1) {
    return '시작 U와 높이는 1 이상의 정수로 입력해 주세요.'
  }
  if (form.startU + form.heightU - 1 > rack.totalU) return `선택한 랙의 전체 ${rack.totalU}U를 초과할 수 없습니다.`
  if (form.mountSide !== 'FRONT' && form.mountSide !== 'REAR') return '장착면을 선택해 주세요.'
  return ''
}
