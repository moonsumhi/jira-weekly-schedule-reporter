import { api } from 'src/boot/axios'

export interface DocFolder {
  id: string
  name: string
  parentId: string | null
  createdAt: string | null
}

export interface DocFile {
  id: string
  name: string
  folderId: string | null
  extension: string
  mimeType: string
  size: number
  createdAt: string | null
  createdBy: string | null
  snippet?: string
  textContent?: string
  convertedFrom?: string | null
}

export const documentService = {
  async createFolder(name: string, parentId?: string | null): Promise<DocFolder> {
    const formData = new FormData()
    formData.append('name', name)
    if (parentId) formData.append('parent_id', parentId)
    const { data } = await api.post<DocFolder>('/documents/folders', formData)
    return data
  },

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

  async replaceFile(fileId: string, file: File): Promise<DocFile> {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post<DocFile>(`/documents/files/${fileId}/replace`, formData)
    return data
  },

  async deleteFile(fileId: string): Promise<void> {
    await api.delete(`/documents/files/${fileId}`)
  },

  async updateFolder(folderId: string, name: string): Promise<DocFolder> {
    const formData = new FormData()
    formData.append('name', name)
    const { data } = await api.patch<DocFolder>(`/documents/folders/${folderId}`, formData)
    return data
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

  getContentUrl(fileId: string, token: string): string {
    const base = (api.defaults.baseURL ?? '/api').replace(/\/$/, '')
    return `${base}/documents/files/${fileId}/content?token=${encodeURIComponent(token)}`
  },

  getHwpPreviewUrl(fileId: string, token: string): string {
    const base = (api.defaults.baseURL ?? '/api').replace(/\/$/, '')
    return `${base}/documents/files/${fileId}/hwp-preview?token=${encodeURIComponent(token)}`
  },

  async convertToDocx(fileId: string): Promise<DocFile> {
    const { data } = await api.post<DocFile>(`/documents/files/${fileId}/convert-to-docx`)
    return data
  },

  async getEditContent(fileId: string): Promise<{ contentType: string; content: string }> {
    const { data } = await api.get<{ content_type: string; content: string }>(`/documents/files/${fileId}/edit-content`)
    return { contentType: data.content_type, content: data.content }
  },

  async saveEditContent(fileId: string, contentType: string, content: string): Promise<DocFile> {
    const formData = new FormData()
    formData.append('content_type', contentType)
    formData.append('content', content)
    const { data } = await api.put<DocFile>(`/documents/files/${fileId}/edit-content`, formData)
    return data
  },
}
