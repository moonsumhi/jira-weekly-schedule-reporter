import { api } from 'src/boot/axios'

export interface DocFolder {
  id: string
  name: string
  parent_id: string | null
  created_at: string | null
}

export interface DocFile {
  id: string
  name: string
  folder_id: string | null
  extension: string
  mime_type: string
  size: number
  created_at: string | null
  created_by: string | null
  snippet?: string
  text_content?: string
}

export const documentService = {
  async getFolders(): Promise<DocFolder[]> {
    const { data } = await api.get<DocFolder[]>('/documents/folders')
    return data
  },

  async getFilesInFolder(folderId: string): Promise<DocFile[]> {
    const { data } = await api.get<DocFile[]>(`/documents/folders/${folderId}/files`)
    return data
  },

  async getRootFiles(): Promise<DocFile[]> {
    const { data } = await api.get<DocFile[]>('/documents/root-files')
    return data
  },

  async getFileMeta(fileId: string): Promise<DocFile> {
    const { data } = await api.get<DocFile>(`/documents/files/${fileId}`)
    return data
  },

  async uploadFiles(files: File[], paths: string[]): Promise<{ uploaded: number }> {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))
    paths.forEach((p) => formData.append('paths', p))
    const { data } = await api.post<{ uploaded: number }>('/documents/upload', formData)
    return data
  },

  async search(q: string): Promise<DocFile[]> {
    const { data } = await api.get<DocFile[]>('/documents/search', { params: { q } })
    return data
  },

  async updateFile(fileId: string, payload: { name?: string; folder_id?: string | null }): Promise<DocFile> {
    const { data } = await api.patch<DocFile>(`/documents/files/${fileId}`, payload)
    return data
  },

  async deleteFile(fileId: string): Promise<void> {
    await api.delete(`/documents/files/${fileId}`)
  },

  async deleteFolder(folderId: string): Promise<void> {
    await api.delete(`/documents/folders/${folderId}`)
  },

  async getFileBlob(fileId: string): Promise<string> {
    const resp = await api.get(`/documents/files/${fileId}/content`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(resp.data as Blob)
  },

  getDownloadUrl(fileId: string): string {
    const base = (api.defaults.baseURL ?? '/api').replace(/\/$/, '')
    return `${base}/documents/files/${fileId}/content`
  },
}
