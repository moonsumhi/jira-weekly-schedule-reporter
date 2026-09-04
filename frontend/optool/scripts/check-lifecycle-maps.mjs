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
const eosMap = readJson('../../app/data/eos_map_snapshot.json').data
const eolMap = readJson('src/data/eol_map_snapshot.json')

function dbSeries(dist, version) {
  return Object.entries(DBMS_TREE[dist] ?? {}).find(([, patches]) => patches.includes(version))?.[0]
}

function hasEos(dist, version) {
  if (eosMap[`${dist}|${version}`]) return true
  if (version.includes('.')) {
    const parent = version.slice(0, version.lastIndexOf('.'))
    if (eosMap[`${dist}|${parent}`]) return true
  }
  return false
}

function hasEol(dist, version) {
  if (eolMap[`${dist}|${version}`]) return true
  if (version.includes('.')) {
    const lastDot = version.lastIndexOf('.')
    if (eolMap[`${dist}|${version.slice(0, lastDot)}`]) return true
    const firstDot = version.indexOf('.')
    if (firstDot !== lastDot && eolMap[`${dist}|${version.slice(0, firstDot)}`]) return true
  }
  const series = dbSeries(dist, version)
  return Boolean(series && eolMap[`${dist}|${series}`])
}

const combinations = []
for (const distributions of Object.values(OS_TREE)) {
  for (const [dist, majors] of Object.entries(distributions)) {
    for (const [major, minors] of Object.entries(majors)) {
      // 마이너 버전은 선택 사항이므로 메이저 버전만 저장하는 경우도 반드시 검증한다.
      for (const version of new Set([major, ...minors])) combinations.push([dist, version])
    }
  }
}
for (const [dist, seriesMap] of Object.entries(DBMS_TREE)) {
  for (const [series, patches] of Object.entries(seriesMap)) {
    for (const version of patches.length ? patches : [series]) combinations.push([dist, version])
  }
}

const missingEos = combinations.filter(([dist, version]) => !hasEos(dist, version))
const missingEol = combinations.filter(([dist, version]) => !hasEol(dist, version))

if (missingEos.length || missingEol.length) {
  if (missingEos.length) console.error('EoS 누락:', missingEos.map(v => v.join('|')).join(', '))
  if (missingEol.length) console.error('EoL 누락:', missingEol.map(v => v.join('|')).join(', '))
  process.exit(1)
}

console.log(`EoS/EoL 매핑 검증 완료: 드롭다운 ${combinations.length}개 조합, 누락 0건`)
