import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/types/assetSystemInfo.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const {
  systemInfoSections, copySystemInformation, systemInfoFieldValue, updateSystemInfoField,
  systemInfoFieldError, systemInformationError, systemInformationPayload, formatHardwareBytes,
} = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

const section = key => systemInfoSections.find(item => item.key === key)
const field = (key, name) => section(key).fields.find(item => item.key === name)
const diskSize = field('disks', 'sizeBytes')

test('unit capacities retain the source string without inventing exact bytes', () => {
  for (const value of ['446.1G', '500 GB', '1.5 TiB', '32G', '1 TB (SSD)', 'N/A']) {
    const row = updateSystemInfoField(diskSize, { sizeBytes: 123, capacity: 'old' }, value)
    assert.equal(row.sizeBytes, null)
    assert.equal(row.capacity, value)
    assert.equal(systemInfoFieldValue(diskSize, row), value)
    assert.equal(systemInfoFieldError(diskSize, value), '')
    const data = copySystemInformation()
    data.disks.push(row)
    assert.equal(systemInformationPayload(data).disks[0].capacity, value)
  }
})

test('exact byte input and clearing remove a stale capacity string', () => {
  const exact = updateSystemInfoField(diskSize, { capacity: '446.1G' }, '34559738368')
  assert.equal(exact.sizeBytes, 34559738368)
  assert.equal(exact.capacity, '')
  assert.equal(systemInfoFieldValue(diskSize, exact), 34559738368)
  const cleared = updateSystemInfoField(diskSize, exact, '')
  assert.equal(cleared.sizeBytes, null)
  assert.equal(cleared.capacity, '')
  const data = copySystemInformation()
  data.disks.push(cleared)
  assert.deepEqual(systemInformationPayload(data).disks, [])
})

test('invalid and unsafe capacity inputs block saving', () => {
  for (const value of ['-1', '1.5', '9007199254740992', 'a'.repeat(257)]) {
    const data = copySystemInformation()
    data.disks.push(updateSystemInfoField(diskSize, {}, value))
    assert.notEqual(systemInformationError(data), '', value)
  }
  for (const value of [NaN, Infinity, -1, 1.5]) assert.notEqual(systemInfoFieldError(diskSize, value), '')
  assert.equal(systemInfoFieldError(diskSize, Number.MAX_SAFE_INTEGER), '')
  assert.equal(formatHardwareBytes(1024 ** 3), '1 GiB')
})

test('old exact bytes and capacity survive editing another field', () => {
  const data = copySystemInformation({ disks: [{ sizeBytes: 1000, capacity: '1 TB', type: '디스크' }] })
  data.disks[0] = updateSystemInfoField(field('disks', 'model'), data.disks[0], 'RAID 930-8i-2GB')
  assert.equal(systemInformationPayload(data).disks[0].sizeBytes, 1000)
  assert.equal(systemInformationPayload(data).disks[0].capacity, '1 TB')
  const legacyText = copySystemInformation({ disks: [{ capacity: '1 TB (SSD)' }] })
  legacyText.cpu.model = 'Updated CPU'
  assert.equal(systemInformationError(legacyText), '')
  assert.equal(systemInformationPayload(legacyText).disks[0].capacity, '1 TB (SSD)')
})

test('identifiers, revisions and speed keep text including leading zeros', () => {
  for (const [key, name, value] of [
    ['hardware', 'boardSerial', '0053520357'],
    ['hardware', 'boardVersion', 'S26361-D3289-B13 WGS04 GS02'],
    ['cpu', 'threadList', '0-15,32-47'],
    ['memoryModules', 'speed', '2400 MT/s'],
    ['memoryModules', 'serial', '2D2254AF'],
  ]) {
    const item = field(key, name)
    assert.equal(updateSystemInfoField(item, {}, value)[name], value)
    assert.equal(systemInfoFieldError(item, value), '')
  }
  const revision = systemInfoSections.find(item => item.title === 'BIOS 상세').fields.find(item => item.key === 'biosRevision')
  assert.equal(updateSystemInfoField(revision, {}, '1.150').biosRevision, '1.150')
})

test('counts stay integers, decimal quantities and percentages enforce their ranges', () => {
  assert.notEqual(systemInfoFieldError(field('cpu', 'sockets'), 1.5), '')
  assert.notEqual(systemInfoFieldError(field('cpu', 'sockets'), 0), '')
  assert.equal(systemInfoFieldError(field('memory', 'installedSlots'), 0), '')
  assert.equal(updateSystemInfoField(field('memory', 'totalGb'), {}, '').totalGb, null)
  assert.equal(systemInfoFieldError(field('memory', 'totalGb'), 32.5), '')
  assert.equal(systemInfoFieldError(field('partitions', 'usedPercent'), 6.5), '')
  assert.notEqual(systemInfoFieldError(field('partitions', 'usedPercent'), 100.1), '')
})

test('dates are real calendar dates and installation states are selected values', () => {
  const date = systemInfoSections.find(item => item.title === 'BIOS 상세').fields.find(item => item.key === 'biosDate')
  for (const value of ['2017-02-24', '2028-02-29']) assert.equal(systemInfoFieldError(date, value), '')
  for (const value of ['02/24/2017', '2026-02-29', '0000-01-01', 'invalid']) assert.notEqual(systemInfoFieldError(date, value), '')
  assert.notEqual(systemInfoFieldError(field('memoryModules', 'status'), 'disk'), '')
  assert.equal(systemInfoFieldError(field('disks', 'type'), 'raid10'), '')
})

test('long text remains bounded and original field order is retained', () => {
  assert.notEqual(systemInfoFieldError(field('cpu', 'model'), 'a'.repeat(257)), '')
  assert.equal(systemInfoFieldError(field('hardware', 'boardFeatures'), 'a'.repeat(4000)), '')
  for (const item of systemInfoSections) {
    assert.deepEqual([...item.rows.flat()].sort(), item.fields.map(item => item.key).sort())
  }
  assert.deepEqual(section('cpu').rows[0], ['manufacturer', 'model'])
  assert.deepEqual(section('memoryModules').rows[2], ['model', 'specification'])
})
