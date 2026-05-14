import { api } from 'boot/axios'

// camelcaseKeys 인터셉터로 인해 응답은 camelCase로 변환됨
export interface BoardOut {
  id: string
  title: string
  description: string
  menuId: string
  icon: string | null
  postCount: number
  link: string | null
  sortOrder: number | null
  createdAt: string | null
}

export interface PostOut {
  id: string
  boardId: string
  title: string
  content: string
  authorId: string
  authorName: string
  createdAt: string | null
}

export const boardService = {
  listBoards(menuId?: string): Promise<BoardOut[]> {
    return api.get('/boards', { params: menuId ? { menu_id: menuId } : {} }).then((r) => r.data)
  },
  createBoard(payload: { title: string; description?: string; menu_id: string; icon?: string | null }): Promise<BoardOut> {
    return api.post('/boards', payload).then((r) => r.data)
  },
  patchBoard(id: string, payload: { title?: string; description?: string; icon?: string | null; link?: string | null; sort_order?: number | null }): Promise<BoardOut> {
    return api.patch(`/boards/${id}`, payload).then((r) => r.data)
  },
  deleteBoard(id: string): Promise<void> {
    return api.delete(`/boards/${id}`)
  },

  listPosts(boardId: string): Promise<PostOut[]> {
    return api.get(`/boards/${boardId}/posts`).then((r) => r.data)
  },
  createPost(boardId: string, payload: { title: string; content: string }): Promise<PostOut> {
    return api.post(`/boards/${boardId}/posts`, payload).then((r) => r.data)
  },
  patchPost(boardId: string, postId: string, payload: { title: string; content: string }): Promise<PostOut> {
    return api.patch(`/boards/${boardId}/posts/${postId}`, payload).then((r) => r.data)
  },
  deletePost(boardId: string, postId: string): Promise<void> {
    return api.delete(`/boards/${boardId}/posts/${postId}`)
  },
}
