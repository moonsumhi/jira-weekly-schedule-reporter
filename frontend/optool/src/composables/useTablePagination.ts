import { ref } from 'vue'

interface PaginationOptions {
  rowsPerPage?: number
  sortBy?: string
  descending?: boolean
}

export function useTablePagination(options: PaginationOptions = {}) {
  const pagination = ref({
    rowsPerPage: options.rowsPerPage ?? 20,
    sortBy: options.sortBy ?? '',
    descending: options.descending ?? false,
    page: 1,
    rowsNumber: 0,
  })

  function resetPage() {
    pagination.value.page = 1
  }

  return { pagination, resetPage }
}
