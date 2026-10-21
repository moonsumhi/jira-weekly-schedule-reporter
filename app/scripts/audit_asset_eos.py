"""Audit stored asset lifecycle fields. Default: dry-run. Apply: python -m app.scripts.audit_asset_eos --apply.

Uses the application's Mongo configuration. Backups precede compare-and-set writes;
no names, IP addresses, credentials or full documents are printed.
"""
import argparse
import asyncio
from datetime import datetime, timezone

from app.db.mongo import MongoClientManager
from app.lifecycle_audit import AUDIT, asset_eos, asset_eol, software_entry, network_entry


async def run(apply: bool = False) -> dict:
    db = MongoClientManager.get_db()
    counts = {'scanned': 0, 'changes': 0, 'applied': 0, 'conflicts': 0, 'manual_review': 0}
    for category, (collection, _) in MongoClientManager.CATEGORY_COLLECTIONS.items():
        if category == '랙':
            continue
        async for doc in db[collection].find({'is_deleted': {'$ne': True}}):
            counts['scanned'] += 1
            fields = doc.get('fields') or {}
            proposed = {}
            for section, date_key, result in (
                ('software', 'eos_date', asset_eos(fields, category)),
                ('eol', 'eol_date', asset_eol(fields)),
            ):
                if not result or all(fields.get(k, '') == v for k, v in result.items()):
                    continue
                entry = software_entry(fields, section)
                if section == 'software' and category in ('네트워크', '정보보호시스템'):
                    entry = network_entry(str(fields.get('운영체제') or ''))
                old_date = fields.get(date_key) or ''
                legacy = (entry or {}).get('legacyDates', [])
                if old_date and old_date not in legacy:
                    counts['manual_review'] += 1
                    continue
                proposed.update(result)
            if not proposed:
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
