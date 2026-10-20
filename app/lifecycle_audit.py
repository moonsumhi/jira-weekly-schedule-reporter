"""Reviewed lifecycle facts. Imported feeds are candidates, not verified support promises."""
import json
import re
from datetime import date
from pathlib import Path

AUDIT = json.loads((Path(__file__).parent / 'data/lifecycle_audit.json').read_text())


def reviewed_eos_map(candidate: dict[str, str]) -> dict[str, str]:
    # No external feed field (including Technical Guidance) can override reviewed facts.
    result = {k: v['date'] for k, v in AUDIT.get('technicalGuidance', {}).items()
              if v['date'] and v['source']}
    for key, entry in AUDIT['software'].items():
        if entry['date'] and entry['source']:
            result[key] = entry['date'][:7]
            if key.startswith(('ESXi|', 'vCenter|')):
                result[key + '|generalSupport'] = entry['date']
    return result


def normalize_model(model: str) -> str:
    return re.sub(r'[^a-z0-9]', '', model.lower()).removeprefix('cisco').removeprefix('nexus')


def network_entry(model: str) -> dict | None:
    normalized = normalize_model(model)
    return next((row for row in [*AUDIT['network'], *AUDIT.get('additionalNetwork', [])] if normalized in row['aliases']), None)


def support_status(end: str, today: date | None = None) -> str:
    if not end:
        return 'REVIEW_REQUIRED'
    now = (today or date.today()).isoformat()
    # A month-only source does not establish which day of that month support ends.
    if len(end) == 7 and now[:7] == end:
        return 'REVIEW_REQUIRED'
    return 'EOS' if end < now[:len(end)] else 'ACTIVE'


def asset_eos(fields: dict, category: str, today: date | None = None) -> dict | None:
    product = str(fields.get('운영체제') or '').strip()
    version = str(fields.get('version') or '').strip()
    if not product:
        return None
    vmware = re.fullmatch(r'(?:VMware\s+)?(ESXi|ESX|vCenter(?:\s+Server)?)(?:\s+(.+))?', product, re.I)
    if vmware:
        product = 'ESXi' if vmware[1].lower().startswith('esx') else 'vCenter'
        raw = version or vmware[2] or ''
        cycle = re.match(r'^v?(\d+)(?:\.(\d+|x))?(?=$|[\s.uU(-])', raw, re.I)
        version = (cycle[1] + ('.' + cycle[2] if cycle[2] and cycle[2].lower() != 'x' else '')) if cycle else raw
    key = product + '|' + version
    entry = AUDIT['software'].get(key) or AUDIT['software'].get(AUDIT['softwareAliases'].get(key, ''))
    if entry is None and any(k.startswith(product + '|') for k in AUDIT['software']):
        entry = {'date': ''}
    if entry is None and category in ('네트워크', '정보보호시스템'):
        entry = network_entry(product)
        # Nonempty models without an exact verified match must not retain guessed dates.
        entry = entry or {'date': '', 'source': '', 'basis': '', 'note': '정확한 모델 및 제조사 공지 확인 필요'}
    if entry is None:
        return None
    end = entry['date']
    status = support_status(end, today)
    if status == 'ACTIVE' and product in ('Rocky Linux', 'RHEL') and version in ('8', '9', '10'):
        status = 'VERSION_REQUIRED'
    elif status == 'ACTIVE' and product == 'Rocky Linux' and version == '8.10':
        status = 'MAINTENANCE'
    return {'eos_date': end[:7], 'eos_action_status': status}
