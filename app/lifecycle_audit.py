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
        if entry.get('dateKind') == 'service_end' and entry['date'] and entry['source']:
            result[key] = entry['date'][:7]
        if key.startswith(('ESXi|', 'vCenter|')) and entry.get('milestone', {}).get('date'):
            result[key + '|generalSupport'] = entry['milestone']['date']
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



def normalize_cisco_software(product: str, version: str) -> tuple[str, str]:
    names = {'apic': 'Cisco APIC', 'ciscoapic': 'Cisco APIC', 'aciswitch': 'Cisco ACI Switch', 'ciscoaciswitch': 'Cisco ACI Switch'}
    dist = names.get(re.sub(r'[\s_-]', '', product.lower()))
    if not dist:
        return product, version
    match = re.fullmatch(r'(\d+\.\d+)(?:\(\d+[a-z]?\)|\.\d+[a-z]?)?', version.strip(), re.I)
    return dist, match[1] if match else version.strip()


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
    product, version = normalize_cisco_software(product, version)
    key = product + '|' + version
    entry = AUDIT['software'].get(key) or AUDIT['software'].get(AUDIT['softwareAliases'].get(key, ''))
    if entry is None and any(k.startswith(product + '|') for k in AUDIT['software']):
        entry = {'date': ''}
    if entry is None:
        entry = network_entry(product)
    if entry is None and category in ('네트워크', '정보보호시스템'):
        entry = network_entry(product)
        # Nonempty models without an exact verified match must not retain guessed dates.
        entry = entry or {'date': '', 'source': '', 'basis': '', 'note': '정확한 모델 및 제조사 공지 확인 필요'}
    if entry is None:
        return None
    end = entry['date'] if entry.get('dateKind') == 'service_end' else ''
    status = support_status(end, today)
    if status == 'ACTIVE' and product in ('Rocky Linux', 'RHEL') and version in ('8', '9', '10'):
        status = 'VERSION_REQUIRED'
    elif status == 'ACTIVE' and product == 'Rocky Linux' and version == '8.10':
        status = 'MAINTENANCE'
    return {'eos_date': end[:7], 'eos_action_status': status}


def software_entry(fields: dict, section: str = 'software') -> dict | None:
    product = str(fields.get('운영체제') or '').strip()
    version = str(fields.get('version') or '').strip()
    vmware = re.fullmatch(r'(?:VMware\s+)?(ESXi|ESX|vCenter(?:\s+Server)?)(?:\s+(.+))?', product, re.I)
    if vmware:
        product = 'ESXi' if vmware[1].lower().startswith('esx') else 'vCenter'
        cycle = re.match(r'^v?(\d+)(?:\.(\d+|x))?(?=$|[\s.uU(-])', version or vmware[2] or '', re.I)
        if cycle:
            version = cycle[1] + ('.' + cycle[2] if cycle[2] and cycle[2].lower() != 'x' else '')
    product, version = normalize_cisco_software(product, version)
    key = product + '|' + version
    return AUDIT[section].get(key) or AUDIT[section].get(AUDIT['softwareAliases'].get(key, ''))


def asset_eol(fields: dict) -> dict | None:
    entry = software_entry(fields, 'eol')
    if entry is None:
        hardware = network_entry(str(fields.get('운영체제') or ''))
        if hardware and 'eolNote' in hardware:
            return {'eol_date': '', 'eol_status': 'REVIEW_REQUIRED'}
        return None
    end = entry['date'] if entry.get('dateKind') == 'life_end' else ''
    status = support_status(end)
    return {'eol_date': end[:7], 'eol_status': 'O' if status == 'EOS' else 'X' if status == 'ACTIVE' else 'REVIEW_REQUIRED'}
