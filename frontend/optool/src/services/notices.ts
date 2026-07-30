import { api } from 'boot/axios'

// camelcaseKeys 인터셉터로 인해 응답은 camelCase로 변환됨
export interface NoticeOut {
  id: string
  title: string
  content: string
  startDate: string
  endDate: string
  isActive: boolean
  createdBy: string
  createdAt: string | null
}

export const noticeService = {
  list(): Promise<NoticeOut[]> {
    return api.get('/notices').then((r) => r.data)
  },
  listActive(): Promise<NoticeOut[]> {
    return api.get('/notices/active').then((r) => r.data)
  },
  create(payload: { title: string; content: string; start_date: string; end_date: string; is_active?: boolean }): Promise<NoticeOut> {
    return api.post('/notices', payload).then((r) => r.data)
  },
  patch(id: string, payload: { title?: string; content?: string; start_date?: string; end_date?: string; is_active?: boolean }): Promise<NoticeOut> {
    return api.patch(`/notices/${id}`, payload).then((r) => r.data)
  },
  remove(id: string): Promise<void> {
    return api.delete(`/notices/${id}`)
  },
}
