# app/utils/mongo.py
from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from typing import Any, Dict


def oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id")


def to_out(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d.setdefault("fields", {})
    return d
