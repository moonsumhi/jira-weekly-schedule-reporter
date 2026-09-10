export type BoardListState = {
  search: string
  category: string | null
  pagination: { page: number; rowsPerPage: number; sortBy: string | null; descending: boolean }
}

export function defaultBoardListState(): BoardListState {
  return { search: '', category: null, pagination: { page: 1, rowsPerPage: 15, sortBy: null, descending: false } }
}

export function readBoardListState(boardId: string, storage: Pick<Storage, 'getItem'>): BoardListState {
  const state = defaultBoardListState()
  try {
    const saved = JSON.parse(storage.getItem(`board-list:${boardId}`) ?? 'null') as Partial<BoardListState> | null
    if (!saved || typeof saved !== 'object') return state
    if (typeof saved.search === 'string') state.search = saved.search
    if (typeof saved.category === 'string') state.category = saved.category
    const p = saved.pagination
    if (p && typeof p === 'object') {
      if (Number.isSafeInteger(p.page) && p.page > 0) state.pagination.page = p.page
      if ([15, 30, 50, 100, 0].includes(p.rowsPerPage)) state.pagination.rowsPerPage = p.rowsPerPage
      if (p.sortBy && ['title', 'part', 'authorName', 'createdAt'].includes(p.sortBy)) state.pagination.sortBy = p.sortBy
      state.pagination.descending = p.descending === true
    }
  } catch { /* Unavailable storage or an old value should not block the board. */ }
  return state
}

export function writeBoardListState(boardId: string, state: BoardListState, storage: Pick<Storage, 'setItem'>) {
  try { storage.setItem(`board-list:${boardId}`, JSON.stringify(state)) } catch { /* Storage may be disabled. */ }
}
