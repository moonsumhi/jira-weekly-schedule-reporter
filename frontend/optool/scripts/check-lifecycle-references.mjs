import fs from 'node:fs'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const audit = JSON.parse(fs.readFileSync(path.join(root, 'src/data/lifecycle_audit.json'), 'utf8'))
const documents = JSON.parse(fs.readFileSync(path.join(root, 'src/data/lifecycle_references.json'), 'utf8'))
const sources = new Set()
function collect(value) {
  if (!value || typeof value !== 'object') return
  for (const [key, child] of Object.entries(value)) {
    if (key === 'source' && typeof child === 'string' && /^https?:/.test(child)) sources.add(child)
    else collect(child)
  }
}
collect(audit)
for (const source of sources) {
  const entry = documents[source]
  if (!entry) throw new Error(`내부망 근거 등록 누락: ${source}`)
  if (entry.unavailableReason) {
    if (entry.path || !entry.checkedAt) throw new Error(`잘못된 미확보 근거: ${source}`)
    continue
  }
  if (!/^\/reference\/[a-zA-Z0-9_/-]+\.pdf$/.test(entry.path)) throw new Error(`외부/잘못된 PDF 경로: ${source}`)
  const buffer = fs.readFileSync(path.join(root, 'public', entry.path))
  if (buffer.subarray(0, 5).toString() !== '%PDF-' || !buffer.subarray(-1024).includes('%%EOF')) throw new Error(`유효하지 않은 PDF: ${entry.path}`)
  if (createHash('sha256').update(buffer).digest('hex') !== entry.sha256) throw new Error(`PDF 해시 불일치: ${entry.path}`)
  if (!entry.title || !entry.capturedAt || !entry.retrievedUrl) throw new Error(`출처 메타데이터 누락: ${source}`)
}
const unavailable = [...sources].filter(source => documents[source].unavailableReason).length
console.log(`내부망 근거 검증: ${sources.size - unavailable}개 PDF 연결, 미확보 ${unavailable}개 명시, 누락 0건`)
