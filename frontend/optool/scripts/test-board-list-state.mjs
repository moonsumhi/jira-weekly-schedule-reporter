import assert from 'node:assert/strict'
import { defaultBoardListState, readBoardListState, writeBoardListState } from '../src/utils/boardListState.ts'

const values = new Map()
const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) }
const filtered = { search: '배포', category: '공지', pagination: { page: 3, rowsPerPage: 30, sortBy: 'createdAt', descending: true } }
writeBoardListState('first', filtered, storage)
assert.deepEqual(readBoardListState('first', storage), filtered)
assert.deepEqual(readBoardListState('second', storage), defaultBoardListState())
writeBoardListState('first', { ...filtered, search: '', category: null }, storage)
assert.equal(readBoardListState('first', storage).search, '')
assert.equal(readBoardListState('first', storage).category, null)
storage.setItem('board-list:broken', '{')
assert.deepEqual(readBoardListState('broken', storage), defaultBoardListState())
storage.setItem('board-list:invalid', JSON.stringify({ search: null, pagination: { page: -1, rowsPerPage: 999, sortBy: 'unknown' } }))
assert.deepEqual(readBoardListState('invalid', storage), defaultBoardListState())
assert.deepEqual(readBoardListState('private', { getItem() { throw Error('disabled') } }), defaultBoardListState())
assert.doesNotThrow(() => writeBoardListState('private', filtered, { setItem() { throw Error('disabled') } }))
console.log('Board list state: filter, pagination, sorting, board isolation, clearing and invalid storage checks passed.')
