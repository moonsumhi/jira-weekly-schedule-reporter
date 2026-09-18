"""Shared asset selection and minimal snapshots for work documents and issues."""

from fastapi import HTTPException

from app.services import asset_catalog


def link_snapshot(asset):
    return {key: asset[key] for key in ('id', 'category', 'name', 'ip', 'asset_name', 'is_deleted')}


async def selected_assets(asset_ids, previous=None):
    old = {a['id']: a for a in (previous or {}).get('linked_assets', [])}
    by_id = await asset_catalog.asset_map(asset_ids)
    result = []
    for asset_id in asset_ids:
        doc = by_id.get(asset_id)
        if not doc or doc.get('is_deleted'):
            # 기존 삭제된 자산 연결은 유지할 수 있지만 새로 연결하지는 않는다.
            if asset_id not in old:
                raise HTTPException(422, '선택한 자산이 삭제되었거나 존재하지 않습니다. 다시 선택해 주세요.')
            result.append({**old[asset_id], 'is_deleted': True})
        else:
            result.append(link_snapshot(doc))
    return result


async def hydrate(entries):
    ids = {a['id'] for entry in entries for a in entry.get('linked_assets', [])}
    if not ids:
        return
    current = {identifier: link_snapshot(asset) for identifier, asset in (await asset_catalog.asset_map(ids)).items()}
    for entry in entries:
        entry['linked_assets'] = [current.get(a['id'], {**a, 'is_deleted': True}) for a in entry.get('linked_assets', [])]


async def search_assets(search, category=None):
    return [link_snapshot(asset) for asset in await asset_catalog.search_assets(search, category=category)]
