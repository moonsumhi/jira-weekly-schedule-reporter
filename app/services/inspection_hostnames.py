"""Review IP-based hostname corrections before applying them to server assets."""
from collections import Counter, defaultdict
import hashlib
import ipaddress
import json

from fastapi import HTTPException
from pymongo import ReturnDocument

from app.db.mongo import MongoClientManager as M
from app.services import monthly_inspection_reports as reports
from app.services.assets_service import _write_history
from app.utils.mongo import to_out


def usable_ip(value):
    address = ipaddress.ip_address(value)
    return not (address.is_loopback or address.is_link_local or address.is_unspecified or address.is_multicast)


def candidates(records, assets):
    by_ip, by_name, ip_rows = defaultdict(set), defaultdict(set), defaultdict(set)
    by_id = {str(asset['_id']): asset for asset in assets}
    for aid, asset in by_id.items():
        for ip in reports.ips(asset.get('ip')):
            by_ip[ip].add(aid)
        if reports.host(asset.get('name')):
            by_name[reports.host(asset['name'])].add(aid)
    names = Counter(reports.host(row['host_name']) for row in records if not row['hostname_missing'])
    for row in records:
        for ip in reports.ips(row['ip']):
            ip_rows[ip].add(row['key'])

    result, proposed = [], defaultdict(list)
    for record in records:
        name = record['host_name'].strip() if not record['hostname_missing'] else ''
        all_ips = set(reports.ips(record['ip']))
        ignored = {ip for ip in all_ips if not usable_ip(ip) or len(ip_rows[ip]) > 1}
        matched = set().union(*(by_ip[ip] for ip in all_ips - ignored)) if all_ips - ignored else set()
        row = {'key': record['key'], 'hostname': name, 'source_ip': record['ip'],
               'ignored_ips': sorted(ignored), 'matched_ips': [], 'asset_id': None,
               'asset_name': '', 'current_hostname': '', 'asset_ip': '',
               'status': 'review', 'reason': ''}
        if len(matched) == 1:
            aid = next(iter(matched))
            asset = by_id[aid]
            row.update(asset_id=aid, asset_name=str((asset.get('fields') or {}).get('자산명') or asset.get('asset_no') or ''),
                       current_hostname=asset.get('name') or '', asset_ip=asset.get('ip') or '',
                       matched_ips=sorted((all_ips - ignored).intersection(reports.ips(asset.get('ip')))))
            proposed[aid].append(row)

        if not name or name.lower() in ('-', 'n/a', 'none', 'null', 'unknown') or any(c.isspace() for c in name):
            row['reason'] = '점검 데이터에 올바른 호스트명이 없습니다.'
        elif not all_ips:
            row['reason'] = '점검 데이터에 유효한 IP가 없습니다.'
        elif not all_ips - ignored:
            row['reason'] = '공통 IP 또는 서버 식별에 사용할 수 없는 IP만 있습니다.'
        elif not matched:
            row['reason'] = 'IP가 일치하는 서버 자산이 없습니다.'
        elif len(matched) > 1:
            row['reason'] = f'IP가 서로 다른 자산 {len(matched)}개와 일치합니다.'
        elif names[reports.host(name)] > 1:
            row['reason'] = '점검 데이터에 같은 호스트명의 서버가 여러 개 있습니다.'
        elif by_name[reports.host(name)] - matched:
            row['reason'] = '변경할 호스트명을 다른 자산에서 사용하고 있습니다.'
        elif row['current_hostname'] == name:
            row.update(status='unchanged', reason='호스트명이 이미 일치합니다.')
        else:
            row.update(status='ready')
        result.append(row)

    # A server with several interfaces still corresponds to one asset. Never let
    # different measurement rows compete to rename that same asset.
    for rows in proposed.values():
        if len(rows) > 1:
            for row in rows:
                row.update(status='review', reason='여러 점검 항목이 같은 자산과 일치합니다.')
    return result


async def preview(source_id):
    source = await reports.source_doc(source_id)
    assets = await M.get_assets_servers_collection().find({'is_deleted': {'$ne': True}}).sort('_id', 1).to_list(None)
    rows = candidates(reports.resource_rows(source), assets)
    # Bind approval to the reviewed source and inventory, including versions.
    # The client sends IDs, never arbitrary replacement hostnames.
    basis = {'source': reports.source_info(source), 'rows': rows,
             'assets': [{key: asset.get(key) for key in ('_id', 'name', 'ip', 'version', 'updated_at')} for asset in assets]}
    revision = hashlib.sha256(json.dumps(reports.clean(basis), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {'source': reports.source_info(source), 'rows': rows, 'revision': revision}, assets


async def apply(source_id, revision, asset_ids, user):
    data, assets = await preview(source_id)
    if data['revision'] != revision:
        raise HTTPException(409, '점검 데이터 또는 자산 정보가 바뀌었습니다. 목록을 다시 불러와 확인해 주세요.')
    available = {row['asset_id']: row for row in data['rows'] if row['status'] == 'ready'}
    if any(aid not in available for aid in asset_ids):
        raise HTTPException(422, '변경 가능한 자산만 선택해 주세요.')
    by_id = {str(asset['_id']): asset for asset in assets}
    col = M.get_assets_servers_collection()
    updated, skipped = [], []
    for aid in asset_ids:
        before, row = by_id[aid], available[aid]
        query = {'_id': before['_id'], 'is_deleted': {'$ne': True}}
        for key in ('name', 'ip', 'version', 'updated_at'):
            query[key] = before[key] if key in before else {'$exists': False}
        values = {'name': row['hostname'], 'updated_at': reports.now(), 'updated_by': user.email,
                  'version': int(before.get('version') or 1) + 1}
        after = await col.find_one_and_update(query, {'$set': values}, return_document=ReturnDocument.AFTER)
        if after is None:
            skipped.append({'asset_id': aid, 'reason': '적용 중 자산 정보가 변경되어 제외했습니다.'})
            continue
        await _write_history(asset_id=aid, action='UPDATE', changed_by=user.email,
                             before=to_out(before), after=to_out(after),
                             patch={'$set': {'name': row['hostname']}, 'inspection_source_id': source_id,
                                    'inspection_date': data['source']['report_date'], 'matched_ips': row['matched_ips']},
                             source='inspection_hostname', history_col=M.get_assets_server_history_collection())
        updated.append(aid)
    return {'updated_ids': updated, 'skipped': skipped}
