import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function loadTypescriptModule(relativePath) {
  const source = fs.readFileSync(path.join(projectRoot, relativePath), 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
  const module = { exports: {} }
  new Function('module', 'exports', 'require', compiled)(module, module.exports, () => {
    throw new Error(`${relativePath}에서 외부 모듈을 불러올 수 없습니다.`)
  })
  return module.exports
}

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(projectRoot, relativePath), 'utf8'))
}

const { OS_TREE } = loadTypescriptModule('src/constants/osVersions.ts')
const { DBMS_TREE } = loadTypescriptModule('src/constants/dbmsVersions.ts')
const audit = readJson('../../app/data/lifecycle_audit.json')
if (JSON.stringify(audit) !== JSON.stringify(readJson('src/data/lifecycle_audit.json'))) throw new Error('Lifecycle audit mirrors differ')

function evidenceFor(section, dist, version) {
  const key = `${dist}|${version}`
  return audit[section][key] ?? audit[section][audit.softwareAliases[key]]
}
function hasEos(dist, version) {
  return Boolean(evidenceFor('software', dist, version))
}
function hasEol(dist, version) {
  return Boolean(evidenceFor('eol', dist, version))
}

const combinations = []
for (const [family, distributions] of Object.entries(OS_TREE)) {
  for (const [dist, majors] of Object.entries(distributions)) {
    for (const [major, minors] of Object.entries(majors)) {
      // VMware는 마이너마다 지원 주기가 달라 메이저만으로 종료일을 확정하지 않는다.
      const versions = family === 'VMware' && minors.length ? minors : [major, ...minors]
      for (const version of new Set(versions)) combinations.push([dist, version])
    }
  }
}
for (const [dist, seriesMap] of Object.entries(DBMS_TREE)) {
  for (const [series, patches] of Object.entries(seriesMap)) {
    for (const version of patches.length ? patches : [series]) combinations.push([dist, version])
  }
}

const missingEos = combinations.filter(([dist, version]) => !hasEos(dist, version))
const missingEol = combinations.filter(([dist, version]) => !['ESXi', 'vCenter'].includes(dist) && !hasEol(dist, version))

if (missingEos.length || missingEol.length) {
  if (missingEos.length) console.error('EoS 누락:', missingEos.map(v => v.join('|')).join(', '))
  if (missingEol.length) console.error('EoL 누락:', missingEol.map(v => v.join('|')).join(', '))
  process.exit(1)
}

console.log(`EoS 처리 범위(근거 확인 필요 포함)/EoL 매핑 검증 완료: 드롭다운 ${combinations.length}개 조합, 누락 0건`)

for (const [section, kind] of [['software', 'service_end'], ['eol', 'life_end']]) {
  for (const [key, entry] of Object.entries(audit[section])) {
    if (entry.date && entry.dateKind !== kind) throw new Error(`${section} ${key}: 잘못된 종료일 의미`)
  }
}
