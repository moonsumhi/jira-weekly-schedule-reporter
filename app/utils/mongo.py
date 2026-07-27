# app/utils/mongo.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException


def oid(s: str, detail: str = "잘못된 ID입니다.") -> ObjectId:
    """ObjectId 변환. 실패 시 HTTP 400."""
    try:
        return ObjectId(s)
    except InvalidId:
        raise HTTPException(status_code=400, detail=detail)


def fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    """datetime → 'YYYY-MM-DDTHH:MM:SSZ' 문자열. None 이면 None 반환."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def to_out(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d.setdefault("fields", {})
    return d
