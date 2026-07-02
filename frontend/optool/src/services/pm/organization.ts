import { api } from 'src/boot/axios'
import type { Project } from 'src/services/pm/project'

export type Organization = {
  id: string
  name: string
  slug: string
  createdAt: string
  updatedAt: string
}

export type PmUser = {
  id: string
  email: string
  name: string
}

export type OrgMember = {
  id: string
  orgId: string
  userId: string
  userEmail: string
  userName: string
  role: 'ADMIN' | 'MEMBER'
  joinedAt: string
}

export async function listOrganizations() {
  const { data } = await api.get<Organization[]>('/pm/organizations')
  return data
}

export async function createOrganization(payload: { name: string; slug: string }) {
  const { data } = await api.post<Organization>('/pm/organizations', payload)
  return data
}

export async function getOrganization(orgId: string) {
  const { data } = await api.get<Organization>(`/pm/organizations/${orgId}`)
  return data
}

export async function deleteOrganization(orgId: string) {
  await api.delete(`/pm/organizations/${orgId}`)
}

export async function patchOrganization(orgId: string, payload: { name: string }) {
  const { data } = await api.patch<Organization>(`/pm/organizations/${orgId}`, payload)
  return data
}

export async function listOrgProjects(orgId: string) {
  const { data } = await api.get<Project[]>(`/pm/organizations/${orgId}/projects`)
  return data
}

export async function listPmUsers() {
  const { data } = await api.get<PmUser[]>('/pm/users')
  return data
}

export async function listOrgMembers(orgId: string) {
  const { data } = await api.get<OrgMember[]>(`/pm/organizations/${orgId}/members`)
  return data
}

export async function addOrgMember(orgId: string, userId: string, role: 'ADMIN' | 'MEMBER' = 'MEMBER') {
  const { data } = await api.post<OrgMember>(`/pm/organizations/${orgId}/members`, { user_id: userId, role })
  return data
}

export async function patchOrgMemberRole(orgId: string, userId: string, role: 'ADMIN' | 'MEMBER') {
  const { data } = await api.patch<OrgMember>(`/pm/organizations/${orgId}/members/${userId}`, { role })
  return data
}

export async function removeOrgMember(orgId: string, userId: string) {
  await api.delete(`/pm/organizations/${orgId}/members/${userId}`)
}
