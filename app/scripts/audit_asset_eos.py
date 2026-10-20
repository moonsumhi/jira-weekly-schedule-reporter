"""Audit stored asset lifecycle fields. Default: dry-run. Apply: python -m app.scripts.audit_asset_eos --apply.

Uses the application's Mongo configuration. Backups precede compare-and-set writes;
no names, IP addresses, credentials or full documents are printed.
"""
import argparse
import asyncio
from datetime import datetime, timezone

from app.db.mongo import MongoClientManager
from app.lifecycle_audit import AUDIT, asset_eos, normalize_model


async def run(apply: bool = False) -> dict:
    db = MongoClientManager.get_db()
    counts = {'scanned': 0, 'changes': 0, 'applied': 0, 'conflicts': 0, 'manual_review': 0}
    for category, (collection, _) in MongoClientManager.CATEGORY_COLLECTIONS.items():
        if category == '랙':
            continue
        async for doc in db[collection].find({'is_deleted': {'$ne': True}}):
            counts['scanned'] += 1
            fields = doc.get('fields') or {}
            proposed = asset_eos(fields, category)
            if not proposed or all(fields.get(k, '') == v for k, v in proposed.items()):
                continue
            # Only replace recognizable legacy automatic values. Preserve custom values for review.
            product = str(fields.get('운영체제') or '')
            version = str(fields.get('version') or '')
            old_date = fields.get('eos_date') or ''
            legacy = AUDIT['software'].get(product + '|' + version, {}).get('previousDate')
            if category in ('네트워크', '정보보호시스템'):
                normalized = normalize_model(product)
                matches = sorted((r for r in AUDIT['network'] if r['pattern'] in normalized), key=lambda r: -len(r['pattern']))
                legacy = matches[0]['previousDate'] if matches else ''
            if old_date and old_date != legacy:
                counts['manual_review'] += 1
                continue
            counts['changes'] += 1
            if not apply:
                continue
            before = {k: fields.get(k) for k in proposed}
            backup = await db['asset_lifecycle_audit'].insert_one({
                'collection': collection, 'asset_id': doc['_id'], 'before': before,
                'missing_fields': [k for k in proposed if k not in fields], 'after': proposed,
                'reviewed_at': AUDIT['reviewedAt'], 'created_at': datetime.now(timezone.utc), 'applied': False,
            })
            # Match the entire fields object so simultaneous model/date edits cannot be overwritten.
            result = await db[collection].update_one({'_id': doc['_id'], 'fields': fields},
                {'$set': {f'fields.{k}': v for k, v in proposed.items()}})
            applied = result.modified_count == 1
            await db['asset_lifecycle_audit'].update_one({'_id': backup.inserted_id}, {'$set': {'applied': applied}})
            counts['applied' if applied else 'conflicts'] += 1
    print({'mode': 'apply' if apply else 'dry-run', **counts})
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Back up and correct recognized legacy automatic values')
    args = parser.parse_args()
    asyncio.run(run(args.apply))


if __name__ == '__main__':
    main()
