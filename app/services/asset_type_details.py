"""Optional storage/software fields shared by manual, MCP and Excel writes."""
import json
import math
import re
from datetime import date

from bson import ObjectId

from app.services import asset_catalog

LINK_KEY = '연결자산'
PERIOD_LICENSES = {'구독', '기간제', '평가판'}
CAPACITY_UNITS = {'GB': 10**9, 'TB': 10**12, 'PB': 10**15,
                  'GiB': 2**30, 'TiB': 2**40, 'PiB': 2**50}


def list_value(value):
    if value is None or value == '':
        return []
    if isinstance(value, str):
        if value.strip().startswith('['):
            try:
                value = json.loads(value)
            except ValueError:
                raise ValueError('목록은 JSON 배열 또는 쉼표로 구분한 값으로 입력해 주세요.')
        else:
            value = re.split(r'[,;\n]', value)
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError('목록에는 문자열만 입력할 수 있습니다.')
    return list(dict.fromkeys(v.strip() for v in value if v.strip()))


def normalize_details(fields, category):
    result = dict(fields)
    if category not in ('스토리지', '소프트웨어'):
        return result
    numeric = ('총물리용량', '사용가능용량', '디스크수량', '디스크개별용량') if category == '스토리지' else ('라이선스수량',)
    for key in numeric:
        value = result.get(key)
        if value in (None, ''):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f'{key}: 0 이상의 숫자를 입력해 주세요.')
        if isinstance(value, bool) or not math.isfinite(number) or number < 0:
            raise ValueError(f'{key}: 0 이상의 숫자를 입력해 주세요.')
        if key == '디스크수량' and not number.is_integer():
            raise ValueError('디스크 수량은 정수로 입력해 주세요.')
        result[key] = int(number) if number.is_integer() else number
    if category == '스토리지':
        for key in ('총물리용량', '사용가능용량', '디스크개별용량'):
            if result.get(key) not in (None, '') and result.get(key + '단위') not in CAPACITY_UNITS:
                raise ValueError(f'{key}의 용량 단위를 선택해 주세요.')
        if all(result.get(key) not in (None, '') for key in ('총물리용량', '사용가능용량')):
            raw = result['총물리용량'] * CAPACITY_UNITS[result['총물리용량단위']]
            usable = result['사용가능용량'] * CAPACITY_UNITS[result['사용가능용량단위']]
            if usable > raw:
                raise ValueError('사용 가능 용량은 총 물리 용량보다 클 수 없습니다. 단위를 확인해 주세요.')
        if '연결방식' in result:
            result['연결방식'] = list_value(result['연결방식'])
    else:
        if result.get('사용권형태') and result['사용권형태'] not in PERIOD_LICENSES:
            result['사용권만료일'] = None
        for key in ('사용시작일', '사용권만료일'):
            if result.get(key):
                try:
                    result[key] = date.fromisoformat(str(result[key])).isoformat()
                except ValueError:
                    raise ValueError(f'{key}: YYYY-MM-DD 형식의 올바른 날짜를 입력해 주세요.')
        if result.get('사용시작일') and result.get('사용권만료일') and result['사용시작일'] > result['사용권만료일']:
            raise ValueError('사용권 만료일은 사용 시작일보다 빠를 수 없습니다.')
        if result.get('라이선스수량') not in (None, '') and not result.get('라이선스기준'):
            raise ValueError('보유 수량의 라이선스 기준을 선택해 주세요.')
    if LINK_KEY in result:
        result[LINK_KEY] = list_value(result[LINK_KEY])
        if len(result[LINK_KEY]) > 100 or any(not ObjectId.is_valid(v) for v in result[LINK_KEY]):
            raise ValueError('연결 자산은 유효한 자산 ID로 최대 100개까지 선택해 주세요.')
    return result


async def prepare_details(fields, category, previous=None, own_id=None):
    result = normalize_details(fields, category)
    if category not in ('스토리지', '소프트웨어') or LINK_KEY not in result:
        return result
    ids = result[LINK_KEY]
    if own_id is not None and str(own_id) in ids:
        raise ValueError('자기 자신을 연결 자산으로 선택할 수 없습니다.')
    old = set(list_value((previous or {}).get(LINK_KEY)))
    found = await asset_catalog.asset_map(ids)
    if any((identifier not in found or found[identifier]['is_deleted']) and identifier not in old for identifier in ids):
        raise ValueError('연결할 자산이 삭제되었거나 존재하지 않습니다. 다시 선택해 주세요.')
    return result
