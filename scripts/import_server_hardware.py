"""Preview and apply server hardware updates from the matching Excel template.

Run with the project's Python 3.12 environment (openpyxl, pydantic).
The script never creates assets and never changes general asset fields.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from openpyxl import load_workbook
from pydantic import ValidationError

from app.models.asset_system_info import SystemInformation


SHEETS = {
    'Servers': ('hardware', 'cpu', 'memory'),
    'MemorySlots': ('memoryModules',),
    'Disks': ('disks',),
    'Partitions': ('partitions',),
    'Networks': ('networkInterfaces',),
    'GPUs': ('gpus',),
}
KEY_FIELDS = {
    'MemorySlots': ('slot',),
    'Disks': ('name',),
    'Partitions': ('mountPoint', 'source'),
    'Networks': ('name',),
    'GPUs': ('manufacturer', 'productName'),
}
MODEL_FIELDS = {
    key: set(model.model_fields)
    for key, model in (
        ('hardware', SystemInformation.model_fields['hardware'].annotation),
        ('cpu', SystemInformation.model_fields['cpu'].annotation),
        ('memory', SystemInformation.model_fields['memory'].annotation),
    )
}
LIST_MODELS = {
    'MemorySlots': SystemInformation.model_fields['memory_modules'].annotation,
    'Disks': SystemInformation.model_fields['disks'].annotation,
    'Partitions': SystemInformation.model_fields['partitions'].annotation,
    'Networks': SystemInformation.model_fields['network_interfaces'].annotation,
    'GPUs': SystemInformation.model_fields['gpus'].annotation,
}
LIST_SECTION = {name: SHEETS[name][0] for name in KEY_FIELDS}
NUMERIC_TYPES = {
    'cpu': {'sockets', 'coresPerSocket', 'threadsPerCore', 'logicalCpus', 'numaNodes', 'frequencyMhz'},
    'memory': {'totalGb', 'maxCapacityGb', 'installedSlots', 'totalSlots'},
    'MemorySlots': {'capacityGb', 'sizeBytes'},
    'Disks': {'sizeBytes'},
    'Partitions': {'sizeBytes', 'usedBytes', 'availableBytes', 'usedPercent'},
    'Networks': {'mtu'},
}

# Excel headers mirror the labels in frontend/optool/src/types/assetSystemInfo.ts.
# The Servers sheet repeats labels such as 제조사, so it includes the section title.
HEADER_LABELS = {
    'Servers': {
        'hostName': 'HostName',
        'hardware.boardManufacturer': '메인보드 상세 · 제조사',
        'hardware.boardModel': '메인보드 상세 · 제품명',
        'hardware.boardVersion': '메인보드 상세 · 버전',
        'hardware.boardSerial': '메인보드 상세 · 시리얼',
        'hardware.boardFeatures': '메인보드 상세 · 특징',
        'hardware.biosManufacturer': 'BIOS 상세 · 제조사',
        'hardware.biosRevision': 'BIOS 상세 · BIOS 리비전',
        'hardware.biosVersion': 'BIOS 상세 · 버전',
        'hardware.biosDate': 'BIOS 상세 · 릴리즈 일자',
        'hardware.biosFeatures': 'BIOS 상세 · 특징',
        'cpu.manufacturer': 'CPU 상세 · 제조사',
        'cpu.model': 'CPU 상세 · 모델명',
        'cpu.architecture': 'CPU 상세 · 아키텍처',
        'cpu.frequencyMhz': 'CPU 상세 · 동작 주파수 (MHz)',
        'cpu.virtualization': 'CPU 상세 · 가상화 기술 지원',
        'cpu.sockets': 'CPU 상세 · 소켓 수',
        'cpu.coresPerSocket': 'CPU 상세 · 소켓당 코어 수',
        'cpu.threadsPerCore': 'CPU 상세 · 코어당 스레드 수',
        'cpu.logicalCpus': 'CPU 상세 · 논리 CPU 수',
        'cpu.threadList': 'CPU 상세 · 스레드 목록',
        'cpu.numaNodes': 'CPU 상세 · NUMA 노드 수',
        'memory.totalGb': '메모리 정보 · 총 용량 (GB)',
        'memory.maxCapacityGb': '메모리 정보 · 최대 지원 용량 (GB)',
        'memory.installedSlots': '메모리 정보 · 장착 슬롯 수',
        'memory.totalSlots': '메모리 정보 · 전체 슬롯 수',
    },
    'MemorySlots': {
        'hostName': 'HostName', 'slot': '메모리 슬롯', 'status': '장착 상태',
        'manufacturer': '제조사', 'partNumber': 'Part Number',
        'model': '모델명', 'specification': '사양', 'type': '메모리 타입',
        'formFactor': 'Form Factor', 'speed': 'Speed',
        'sizeBytes': 'Size (byte)', 'capacityGb': 'Size (GB)', 'serial': 'Serial',
    },
    'Disks': {
        'hostName': 'HostName', 'name': '장치명', 'kernelName': '커널명',
        'parent': '부모 커널명', 'type': '장치 종류', 'filesystem': '파일시스템 종류',
        'uuid': 'UUID', 'mountPoint': '마운트 경로', 'sizeBytes': 'Size',
        'partitionLabel': '파티션 라벨', 'filesystemLabel': '파일시스템 라벨',
        'revision': 'REV', 'manufacturer': '제조사', 'model': '모델명',
        'serial': 'Serial', 'capacity': '용량 원문',
    },
    'Partitions': {
        'hostName': 'HostName', 'mountPoint': '마운트 경로', 'source': '마운트 소스',
        'sizeBytes': 'Size (byte)', 'usedBytes': 'Used (byte)',
        'availableBytes': 'Avail (byte)', 'usedPercent': 'Used (%)',
        'filesystem': '파일시스템 타입',
    },
    'Networks': {
        'hostName': 'HostName', 'name': '네트워크 인터페이스', 'ipv4': 'IP',
        'netmask': 'netmask', 'gateway': 'gateway',
        'bondingOptions': 'bonding 옵션',
    },
    'GPUs': {
        'hostName': 'HostName', 'manufacturer': 'GPU 제조사',
        'productName': 'GPU 제품명', 'coreCodename': 'GPU 코어 코드네임',
    },
}


def header_key(sheet: str, label: str) -> str:
    mapping = HEADER_LABELS[sheet]
    return next((key for key, name in mapping.items() if label in (key, name)), label)


def camel(name: str) -> str:
    parts = name.split('_')
    return parts[0] + ''.join(part.title() for part in parts[1:])


def allowed_columns(sheet: str) -> set[str]:
    if sheet == 'Servers':
        return {'hostName'} | {
            section + '.' + camel(field)
            for section in SHEETS['Servers'] for field in MODEL_FIELDS[section]
        }
    model = LIST_MODELS[sheet].__args__[0]
    return {'hostName'} | {camel(field) for field in model.model_fields}


def cell_value(value: Any, column: str, sheet: str) -> Any:
    if value is None or value == '':
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.startswith('='):
            raise ValueError(f'{column}: 수식은 입력할 수 없습니다')
    if column == 'hardware.biosDate':
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError as exc:
            raise ValueError(f'{column}: YYYY-MM-DD 날짜가 필요합니다') from exc
    section, _, field = column.partition('.')
    numeric_group = section if field else sheet
    numeric_field = field or section
    if numeric_field in NUMERIC_TYPES.get(numeric_group, set()):
        try:
            number = float(value)
            if not number.is_integer() and numeric_field not in {
                'frequencyMhz', 'totalGb', 'maxCapacityGb', 'capacityGb', 'usedPercent'
            }:
                raise ValueError()
            return number if not number.is_integer() else int(number)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f'{column}: 숫자가 필요합니다') from exc
    return str(value).strip()


def read_rows(path: Path) -> dict[str, list[dict[str, Any]]]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    try:
        missing = set(SHEETS) - set(workbook.sheetnames)
        if missing:
            raise ValueError('필수 시트 누락: ' + ', '.join(sorted(missing)))
        result: dict[str, list[dict[str, Any]]] = {}
        for name in SHEETS:
            rows = workbook[name].iter_rows(values_only=True)
            header = next(rows, None)
            if not header:
                raise ValueError(f'{name}: 헤더가 없습니다')
            columns = [header_key(name, str(item).strip()) if item is not None else '' for item in header]
            columns = columns[:max((i + 1 for i, col in enumerate(columns) if col), default=0)]
            if not columns or columns[0] != 'hostName' or len(columns) != len(set(columns)):
                raise ValueError(f'{name}: 첫 열은 HostName이어야 하고 헤더는 중복될 수 없습니다')
            unknown = set(columns) - allowed_columns(name)
            if unknown:
                raise ValueError(f'{name}: 알 수 없는 열: {", ".join(sorted(unknown))}')
            result[name] = []
            for row_number, values in enumerate(rows, 2):
                if not any(value is not None and str(value).strip() for value in values):
                    continue
                if any(value is not None and str(value).strip() for value in values[len(columns):]):
                    raise ValueError(f'{name} {row_number}행: 헤더 밖에 값이 있습니다')
                try:
                    item = {col: cell_value(values[i] if i < len(values) else None, col, name)
                            for i, col in enumerate(columns)}
                except ValueError as exc:
                    raise ValueError(f'{name} {row_number}행: {exc}') from exc
                if not item.get('hostName'):
                    raise ValueError(f'{name} {row_number}행: HostName이 없습니다')
                item['hostName'] = str(item['hostName']).strip().casefold()
                item['_row'] = row_number
                result[name].append(item)
        return result
    finally:
        workbook.close()


def identity(sheet: str, item: dict[str, Any]) -> tuple[str, ...]:
    fields = KEY_FIELDS[sheet]
    values = tuple(str(item.get(key) or '').strip() for key in fields)
    if not all(values):
        raise ValueError(f'{sheet} {item["_row"]}행: 식별 열 {", ".join(fields)}이 필요합니다')
    return values


def merge_system_info(existing: dict[str, Any] | None, rows: dict[str, list[dict[str, Any]]],
                      host_name: str) -> dict[str, Any]:
    info = SystemInformation.model_validate(existing or {}).model_dump(mode='json', by_alias=True)
    single = [row for row in rows['Servers'] if row['hostName'] == host_name]
    if len(single) > 1:
        raise ValueError(f'{host_name}: Servers 시트에 중복 행이 있습니다')
    if single:
        for column, value in single[0].items():
            if value is None or '.' not in column:
                continue
            section, field = column.split('.', 1)
            info[section][field] = value
    for sheet, section in LIST_SECTION.items():
        incoming = [row for row in rows[sheet] if row['hostName'] == host_name]
        seen: set[tuple[str, ...]] = set()
        for row in incoming:
            key = identity(sheet, row)
            if key in seen:
                raise ValueError(f'{host_name}: {sheet} 시트에 중복 항목 {key}가 있습니다')
            seen.add(key)
            current = next((entry for entry in info[section]
                            if tuple(str(entry.get(field) or '').strip() for field in KEY_FIELDS[sheet]) == key), None)
            if current is None:
                current = {field: value for field, value in zip(KEY_FIELDS[sheet], key)}
                info[section].append(current)
            for field, value in row.items():
                if field not in ('hostName', '_row') and value is not None:
                    current[field] = value
    return SystemInformation.model_validate(info).model_dump(mode='json', by_alias=True)


def request_json(token: str, method: str, url: str, *, params: dict[str, str] | None = None,
                 payload: dict[str, Any] | None = None) -> Any:
    if params:
        url += '?' + urlencode(params)
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as exc:
        detail = exc.read(500).decode('utf-8', errors='replace')
        raise RuntimeError(f'{method} {url}: HTTP {exc.code} {detail}') from exc


def api_token() -> str:
    token = os.environ.get('ASSET_IMPORT_TOKEN', '').strip()
    if not token:
        raise ValueError('ASSET_IMPORT_TOKEN 환경 변수가 필요합니다')
    return token


def api_url(base_url: str, asset_id: str | None = None) -> str:
    url = base_url.rstrip('/') + '/assets'
    return url + '/' + quote(asset_id, safe='') if asset_id else url


def changed_values(before: Any, after: Any, path: str = '') -> list[tuple[str, Any, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        return [item for key in sorted(set(before) | set(after))
                for item in changed_values(before.get(key), after.get(key), f'{path}.{key}' if path else key)]
    if isinstance(before, list) and isinstance(after, list):
        return [item for index in range(max(len(before), len(after)))
                for item in changed_values(before[index] if index < len(before) else None,
                                           after[index] if index < len(after) else None,
                                           f'{path}[{index + 1}]')]
    return [(path, before, after)] if before != after else []


def preview(args: argparse.Namespace) -> None:
    rows = read_rows(args.workbook)
    targets = {str(row['hostName']) for sheet_rows in rows.values() for row in sheet_rows}
    if not targets:
        raise ValueError('입력된 자산이 없습니다')
    token = api_token()
    assets = request_json(token, 'GET', api_url(args.base_url), params={'category': '서버'})
    by_name: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        if not asset.get('is_deleted') and asset.get('name'):
            by_name.setdefault(str(asset['name']).strip().casefold(), []).append(asset)
    missing = sorted(name for name in targets if len(by_name.get(name, [])) != 1)
    if missing:
        raise ValueError('HostName에 해당하는 서버가 없거나 중복됩니다: ' + ', '.join(missing))
    changes = []
    backups = []
    for host_name in sorted(targets):
        asset = by_name[host_name][0]
        updated = merge_system_info(asset.get('system_info'), rows, host_name)
        current = SystemInformation.model_validate(asset.get('system_info') or {}).model_dump(mode='json', by_alias=True)
        if updated == current:
            continue
        backups.append(asset)
        changes.append({'hostName': host_name, 'assetId': asset.get('asset_id'), 'id': asset['id'], 'name': asset['name'],
                        'version': asset.get('version') or 1, 'before': current, 'after': updated})
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    plan = {'createdAt': datetime.now(timezone.utc).isoformat(), 'baseUrl': args.base_url.rstrip('/'),
            'workbook': str(args.workbook.resolve()), 'changes': changes}
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    output.with_name(output.stem + '.backup.json').write_text(
        json.dumps(backups, ensure_ascii=False, indent=2), encoding='utf-8')
    report_path = output.with_name(output.stem + '.changes.csv')
    with report_path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['HostName', 'field', 'before', 'after'])
        for change in changes:
            for field, before, after in changed_values(change['before'], change['after']):
                writer.writerow([change['hostName'], field,
                                 json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False)])
    print(f'미리보기: 대상 {len(targets)}건, 변경 {len(changes)}건, 변경 없음 {len(targets) - len(changes)}건')
    print(f'계획: {output}\n변경표: {report_path}\n자산 백업: {output.with_name(output.stem + ".backup.json")}')
    for change in changes:
        print(f'  {change["hostName"]} | {change["name"]} | version {change["version"]}')


def apply(args: argparse.Namespace) -> None:
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    if not args.confirm:
        raise ValueError('적용하려면 --confirm이 필요합니다')
    base_url = args.base_url.rstrip('/')
    if base_url != plan['baseUrl']:
        raise ValueError('적용 서버 주소가 미리보기의 서버 주소와 다릅니다')
    token = api_token()
    changes = plan['changes']
    if any('hostName' not in change or 'assetId' not in change for change in changes):
        raise ValueError('이전 양식의 계획입니다. HostName 템플릿으로 미리보기를 다시 생성하세요')
    # Preflight all assets before the first write. Version is checked again by the API.
    active_assets = request_json(token, 'GET', api_url(base_url), params={'category': '서버'})
    for change in changes:
        matches = [asset for asset in active_assets
                   if not asset.get('is_deleted') and str(asset.get('name') or '').strip().casefold() == change['hostName']]
        if len(matches) != 1 or matches[0]['id'] != change['id']:
            raise ValueError(f'{change["hostName"]}: HostName 매칭이 미리보기 이후 변경되어 적용을 중단합니다')
    for change in changes:
        current = request_json(token, 'GET', api_url(base_url, change['id']), params={'category': '서버'})
        if (str(current.get('name') or '').strip().casefold() != change['hostName']
                or current.get('asset_id') != change['assetId']
                or current.get('version') != change['version']):
            raise ValueError(f'{change["hostName"]}: HostName, 자산 ID 또는 버전이 변경되어 적용을 중단합니다')
        actual_info = SystemInformation.model_validate(current.get('system_info') or {}).model_dump(mode='json', by_alias=True)
        if actual_info != change['before']:
            raise ValueError(f'{change["hostName"]}: 하드웨어 정보가 변경되어 적용을 중단합니다')
    for index, change in enumerate(changes, 1):
        request_json(token, 'PATCH', api_url(base_url, change['id']), params={'category': '서버'},
                     payload={'version': change['version'], 'system_info': change['after']})
        print(f'적용 {index}/{len(changes)}: {change["hostName"]} | {change["name"]}')
    print(f'완료: {len(changes)}건')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('preview', help='변경 계획과 자산 백업 생성 (쓰기 없음)')
    p.add_argument('workbook', type=Path)
    p.add_argument('--base-url', required=True, help='예: http://localhost:9000/api')
    p.add_argument('--output', type=Path, default=Path('hardware-import-plan.json'))
    p = sub.add_parser('apply', help='검토한 계획을 서버에 적용')
    p.add_argument('plan', type=Path)
    p.add_argument('--base-url', required=True, help='미리보기에서 사용한 주소와 같아야 합니다')
    p.add_argument('--confirm', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'preview':
            preview(args)
        else:
            apply(args)
    except (ValueError, ValidationError, RuntimeError, OSError, URLError) as exc:
        print(f'오류: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
