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

export interface PostAttachment {
  fileId: string
  originalName: string
  url: string
  size: number
  contentType: string
}

// 백엔드 전송용 snake_case 첨부파일 타입
export interface PostAttachmentInput {
  file_id: string
  original_name: string
  url: string
  size: number
  content_type: string
}

export interface PostOut {
  id: string
  boardId: string
  title: string
  part: string
  category: string
  content: string
  authorId: string
  authorName: string
  attachments: PostAttachment[]
  createdAt: string | null
  parentId: string | null
  version: number
  updatedAt: string | null
  editorIds: string[]
  ownerId: string
  ownerName: string
  adoptedBy: string | null
  adoptedName: string | null
  adoptedAt: string | null
  adoptedVersion: number | null
  followerCount: number
  mentionedUsers: MentionedUser[]
}

export interface MentionedUser {
  userId: string
  displayName: string
}

export interface BoardCommentReactionUser {
  userId: string
  displayName: string
}

export interface BoardCommentReaction {
  emoji: string
  users: BoardCommentReactionUser[]
}

export interface BoardComment {
  id: string
  boardId: string
  postId: string
  authorId: string
  authorName: string
  content: string
  mentionedUsers: MentionedUser[]
  reactions: BoardCommentReaction[]
  createdAt: string
  updatedAt: string
}

export interface PostHistoryDiff {
  key: string | null
  field: string
  before: string | null
  after: string | null
}

export interface PostVersionSnapshot {
  title: string
  part: string
  category: string
  content: string
  attachments: PostAttachment[]
  parentId: string | null
}

export interface PostHistoryOut {
  id: string
  postId: string
  diff: PostHistoryDiff[]
  changedBy: string
  changedAt: string | null
  version: number | null
  snapshot: PostVersionSnapshot | null
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
  getPost(boardId: string, postId: string): Promise<PostOut> {
    return api.get(`/boards/${boardId}/posts/${postId}`).then((r) => r.data)
  },
  createPost(boardId: string, payload: { title: string; part?: string; category?: string; content: string; attachments?: PostAttachmentInput[]; parent_id?: string | null; editor_ids?: string[]; mentioned_user_ids?: string[] }): Promise<PostOut> {
    return api.post(`/boards/${boardId}/posts`, payload).then((r) => r.data)
  },
  patchPost(boardId: string, postId: string, payload: { title: string; part?: string; category?: string; content: string; attachments?: PostAttachmentInput[]; parent_id?: string | null; editor_ids?: string[]; owner_id?: string; expected_version?: number; mentioned_user_ids?: string[] }): Promise<PostOut> {
    return api.patch(`/boards/${boardId}/posts/${postId}`, payload).then((r) => r.data)
  },
  deletePost(boardId: string, postId: string): Promise<void> {
    return api.delete(`/boards/${boardId}/posts/${postId}`)
  },
  getPostHistory(boardId: string, postId: string): Promise<PostHistoryOut[]> {
    return api.get(`/boards/${boardId}/posts/${postId}/history`).then((r) => r.data)
  },
  async getFollowStatus(boardId: string, postId: string): Promise<boolean> {
    const { data } = await api.get<{ following: boolean }>(`/boards/${boardId}/posts/${postId}/follow`)
    return data.following
  },
  async followPost(boardId: string, postId: string): Promise<void> {
    await api.post(`/boards/${boardId}/posts/${postId}/follow`)
  },
  async unfollowPost(boardId: string, postId: string): Promise<void> {
    await api.delete(`/boards/${boardId}/posts/${postId}/follow`)
  },
  adoptPost(boardId: string, postId: string, version: number): Promise<PostOut> {
    return api.post(`/boards/${boardId}/posts/${postId}/adopt`, { version }).then((r) => r.data)
  },
  clearAdoption(boardId: string, postId: string): Promise<PostOut> {
    return api.delete(`/boards/${boardId}/posts/${postId}/adopt`).then((r) => r.data)
  },
  listComments(boardId: string, postId: string): Promise<BoardComment[]> {
    return api.get(`/boards/${boardId}/posts/${postId}/comments`).then((r) => r.data)
  },
  createComment(boardId: string, postId: string, content: string, mentionedUserIds: string[]): Promise<BoardComment> {
    return api.post(`/boards/${boardId}/posts/${postId}/comments`, {
      content,
      mentioned_user_ids: mentionedUserIds,
    }).then((r) => r.data)
  },
  deleteComment(boardId: string, postId: string, commentId: string): Promise<void> {
    return api.delete(`/boards/${boardId}/posts/${postId}/comments/${commentId}`)
  },
  toggleCommentReaction(boardId: string, postId: string, commentId: string, emoji: string): Promise<BoardComment> {
    return api.post(`/boards/${boardId}/posts/${postId}/comments/${commentId}/reactions`, { emoji }).then((r) => r.data)
  },
}
