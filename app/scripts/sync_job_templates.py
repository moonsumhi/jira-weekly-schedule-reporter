"""Synchronize duplicate job templates to the newest canonical section schema.

Usage:
    python -m app.scripts.sync_job_templates          # dry-run
    python -m app.scripts.sync_job_templates --apply  # write changes
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
from copy import deepcopy

from motor.motor_asyncio import AsyncIOMotorClient

try:
    from app.core.config import settings
    MONGO_URI = settings.MONGO_URI
    DB_NAME = settings.APP_DB_NAME
except Exception:
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("APP_DB_NAME", "optool")


def norm(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def is_job_template(doc: dict) -> bool:
    return doc.get("menu") in ("job", None) and "작업" in str(doc.get("title", ""))


async def main(apply: bool) -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    collection = client[DB_NAME]["form_templates"]
    docs = [d async for d in collection.find({"is_deleted": {"$ne": True}})]
    docs = [d for d in docs if is_job_template(d)]

    groups: dict[str, list[dict]] = {}
    for doc in docs:
        groups.setdefault(norm(doc.get("title")), []).append(doc)

    for title_key, group in groups.items():
        canonical = next(
            (d for d in group if {"작업 개요", "작업 대상", "세부 작업 절차"}
             <= {s.get("title") for s in d.get("sections", []) if isinstance(s, dict)}),
            None,
        )
        if canonical is None or len(group) < 2:
            continue
        source_sections = deepcopy(canonical.get("sections", []))
        print(f"[canonical] {canonical['_id']} {canonical.get('title')!r}")
        for target in group:
            if target["_id"] == canonical["_id"]:
                continue
            if target.get("sections") == source_sections:
                print(f"[skip] {target['_id']} already matches")
                continue
            print(f"[update] {target['_id']} {target.get('title')!r}")
            if apply:
                await collection.update_one(
                    {"_id": target["_id"]},
                    {"$set": {"sections": deepcopy(source_sections)}},
                )
    client.close()
    print("Applied." if apply else "Dry-run only. Re-run with --apply to write changes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.apply))
