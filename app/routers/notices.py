"""공지사항 CRUD 및 활성 공지 조회 (관리자 > 공지사항)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db.mongo import MongoClientManager
from app.models.notice import NoticeCreate, NoticeOut, NoticePatch
from app.models.user import UserPublic
from app.routers.admin import require_admin
from app.routers.auth import get_current_user
from app.utils.mongo import fmt_dt, oid as parse_oid
from app.utils.time import KST

router = APIRouter()


def _notice_to_out(doc: dict) -> NoticeOut:
    return NoticeOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        content=doc.get("content", ""),
        start_date=doc.get("start_date", ""),
        end_date=doc.get("end_date", ""),
        is_active=doc.get("is_active", True),
        created_by=doc.get("created_by", ""),
        created_at=fmt_dt(doc.get("created_at")),
    )


@router.get("", response_model=list[NoticeOut])
async def list_notices(_=Depends(require_admin)):
    col = MongoClientManager.get_notices_collection()
    docs = [doc async for doc in col.find({}).sort("start_date", -1)]
    return [_notice_to_out(d) for d in docs]


@router.get("/active", response_model=list[NoticeOut])
async def list_active_notices(_=Depends(get_current_user)):
    """오늘(KST) 날짜가 게시 기간에 포함되는 활성 공지사항 목록."""
    today = datetime.now(timezone.utc).astimezone(KST).strftime("%Y-%m-%d")
    col = MongoClientManager.get_notices_collection()
    docs = [
        doc async for doc in col.find({
            "is_active": True,
            "start_date": {"$lte": today},
            "end_date": {"$gte": today},
        }).sort("start_date", 1)
    ]
    return [_notice_to_out(d) for d in docs]


@router.post("", response_model=NoticeOut, status_code=201)
async def create_notice(payload: NoticeCreate, current_user: UserPublic = Depends(require_admin)):
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=400, detail="시작일이 종료일보다 늦을 수 없습니다.")
    col = MongoClientManager.get_notices_collection()
    doc = {
        "title": payload.title,
        "content": payload.content,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "is_active": payload.is_active,
        "created_by": current_user.full_name or current_user.email,
        "created_at": datetime.now(timezone.utc),
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _notice_to_out(doc)


@router.patch("/{notice_id}", response_model=NoticeOut)
async def patch_notice(notice_id: str, payload: NoticePatch, _=Depends(require_admin)):
    col = MongoClientManager.get_notices_collection()
    _oid = parse_oid(notice_id, "잘못된 공지사항 ID입니다.")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다.")

    doc = await col.find_one({"_id": _oid})
    if not doc:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")
    start_date = update.get("start_date", doc.get("start_date", ""))
    end_date = update.get("end_date", doc.get("end_date", ""))
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="시작일이 종료일보다 늦을 수 없습니다.")

    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    return _notice_to_out(doc)


@router.delete("/{notice_id}", status_code=204)
async def delete_notice(notice_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_notices_collection()
    _oid = parse_oid(notice_id, "잘못된 공지사항 ID입니다.")
    result = await col.delete_one({"_id": _oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")
