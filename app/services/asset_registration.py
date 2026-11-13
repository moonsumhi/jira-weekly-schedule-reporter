"""MCP registration rules use the backoffice asset and lifecycle services."""
from __future__ import annotations

import re

from fastapi import HTTPException

from app.lifecycle_audit import AUDIT, asset_eol, asset_eos, network_entry, software_entry
from app.models.assets import McpAssetCreate


def _canonical_product(product: str) -> str:
    # The UI normalizes capitalization, spaces and hyphens in known OS names.
    normalize = lambda value: re.sub(r'[\s_-]', '', value).lower()
    needle = normalize(product)
    for key in (*AUDIT['software'], *AUDIT['eol'], *AUDIT['softwareAliases']):
        candidate = key.split('|', 1)[0]
        if normalize(candidate) == needle:
            return candidate
    return product


def evaluate_lifecycle(fields: dict, category: str, series: str | None = None) -> tuple[dict, dict]:
    product = _canonical_product(str(fields.get('운영체제') or '').strip())
    if not product:
        return {}, {'eos': {}, 'eol': {}}
    lookup = {**fields, '운영체제': product}
    eos = asset_eos(lookup, category)
    if eos is None and series:
        eos = asset_eos({**lookup, 'version': series}, category)
    eos = eos or {'eos_date': '', 'eos_action_status': 'REVIEW_REQUIRED'}
    is_vmware = bool(re.fullmatch(r'(?:VMware\s+)?(?:ESXi|ESX|vCenter(?:\s+Server)?)(?:\s+.+)?', product, re.I))
    eol = None if is_vmware else asset_eol(lookup)
    if eol is None and series and not is_vmware:
        eol = asset_eol({**lookup, 'version': series})
    if eol is None and not is_vmware:
        eol = {'eol_date': '', 'eol_status': 'REVIEW_REQUIRED'}
    lifecycle = {**eos, **(eol or {})}
    evidence = software_entry(lookup) or network_entry(product)
    eol_evidence = software_entry(lookup, 'eol')
    return lifecycle, {
        'eos': {**eos, 'source': (evidence or {}).get('source', ''), 'note': (evidence or {}).get('note', '')},
        'eol': {**(eol or {}), 'source': (eol_evidence or {}).get('source', ''), 'note': (eol_evidence or {}).get('note', '')},
    }


def prepare_mcp_asset(body: McpAssetCreate) -> tuple[dict, dict]:
    missing = []
    for key, label in [('구분', '구분'), ('서버명', '자산명'), ('설명', '설명'), ('운영체제', '운영체제/기종')]:
        if not isinstance(body.fields.get(key), str) or not body.fields[key].strip():
            missing.append(label)
    if not body.name.strip():
        missing.append('호스트명')
    if not body.ip.strip() and body.category != '소프트웨어':
        missing.append('IP')
    if not body.asset_no.strip():
        missing.append('자산번호')
    if body.category == '정보보호시스템' and (not isinstance(body.fields.get('제조사'), str) or not body.fields['제조사'].strip()):
        missing.append('제조사')
    if body.category == 'DBMS' and not str(body.fields.get('version') or body.db_series or '').strip():
        missing.append('DBMS 시리즈 또는 버전')
    if missing:
        raise HTTPException(422, detail={'message': '필수 항목을 입력해 주세요.', 'missing': missing})
    if body.system_info is not None and body.category != '서버':
        raise HTTPException(422, detail='시스템 정보는 서버 자산에만 입력할 수 있습니다.')
    if body.fields.get('자산유형') and body.fields['자산유형'] != body.category:
        raise HTTPException(422, detail='자산유형과 category가 일치하지 않습니다.')
    fields = dict(body.fields)
    fields['자산유형'] = body.category
    fields.setdefault('상태', '운영')
    if body.category == 'DBMS' and not fields.get('version'):
        fields['version'] = body.db_series
    lifecycle, evidence = evaluate_lifecycle(fields, body.category, body.db_series)
    for key, value in lifecycle.items():
        if fields.get(key) not in (None, '', value):
            raise HTTPException(422, detail={'message': '입력한 EoS/EoL 값이 확인된 자동 계산 결과와 다릅니다.', 'field': key, 'calculated': value})
        fields[key] = value
    return fields, evidence
