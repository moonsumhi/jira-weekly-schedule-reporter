import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getIssue, type Issue } from 'src/services/pm/issue'

// 알림(멘션 등)을 클릭했을 때 프로젝트 보드 페이지로 이동하지 않고
// 현재 화면 위에 바로 이슈 상세를 띄우기 위한 전역 다이얼로그 상태.
export const useIssueDialogStore = defineStore('issueDialog', () => {
  const open = ref(false)
  const issue = ref<Issue | null>(null)
  const initialCommentId = ref<string | null>(null)

  async function openIssue(projectId: string, issueId: string, commentId: string | null = null) {
    try {
      issue.value = await getIssue(projectId, issueId)
      initialCommentId.value = commentId
      open.value = true
    } catch { /* 이슈 조회 실패 시 조용히 무시 */ }
  }

  function close() {
    open.value = false
  }

  return { open, issue, initialCommentId, openIssue, close }
})
