"""Menu CRUD — admin manages sidebar menus (groups that contain boards)."""

from datetime import datetime, timezone  # datetime: create_menu의 created_at에 사용

from fastapi import APIRouter, Depends, HTTPException

from app.db.mongo import MongoClientManager
from app.models.menu import MenuCreate, MenuOut, MenuPatch, SubMenuItem
from app.routers.admin import require_admin
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()


def _to_out(doc: dict) -> MenuOut:
    raw_submenus = doc.get("submenus", [])
    submenus = [SubMenuItem(**s) for s in raw_submenus if isinstance(s, dict)]
    return MenuOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        icon=doc.get("icon", "fa-solid fa-folder"),
        sort_order=doc.get("sort_order"),
        is_visible=bool(doc.get("is_visible", True)),
        is_external_visible=bool(doc.get("is_external_visible", False)),
        is_internal_visible=bool(doc.get("is_internal_visible", True)),
        is_system=bool(doc.get("is_system", False)),
        slug=doc.get("slug"),
        sub_icons=doc.get("sub_icons"),
        sub_order=doc.get("sub_order"),
        link=doc.get("link"),
        submenus=submenus,
        visible_teams=doc.get("visible_teams") or [],
        created_at=fmt_dt(doc.get("created_at")),
    )


@router.get("", response_model=list[MenuOut])
async def list_menus(visible_only: bool = True):
    col = MongoClientManager.get_menus_collection()
    query = {"is_visible": True} if visible_only else {}
    docs = [doc async for doc in col.find(query)]
    docs.sort(key=lambda d: (d.get("sort_order") is None, d.get("sort_order") or 0))
    return [_to_out(doc) for doc in docs]


@router.post("", response_model=MenuOut, status_code=201)
async def create_menu(payload: MenuCreate, _=Depends(require_admin)):
    col = MongoClientManager.get_menus_collection()
    doc = {
        "title": payload.title,
        "icon": payload.icon,
        "sort_order": payload.sort_order,
        "is_visible": payload.is_visible,
        "link": payload.link,
        "visible_teams": payload.visible_teams,
        "created_at": datetime.now(timezone.utc),
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{menu_id}", response_model=MenuOut)
async def patch_menu(menu_id: str, payload: MenuPatch, _=Depends(require_admin)):
    col = MongoClientManager.get_menus_collection()
    _oid = parse_oid(menu_id, "잘못된 메뉴 ID입니다.")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다.")

    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다.")
    return _to_out(doc)


@router.delete("/{menu_id}", status_code=204)
async def delete_menu(menu_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_menus_collection()
    boards_col = MongoClientManager.get_boards_collection()
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(menu_id, "잘못된 메뉴 ID입니다.")
    doc = await col.find_one({"_id": _oid})
    if not doc:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다.")
    if doc.get("is_system"):
        raise HTTPException(status_code=400, detail="시스템 메뉴는 삭제할 수 없습니다.")
    result = await col.delete_one({"_id": _oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다.")
    # 해당 메뉴의 게시판 및 게시글도 함께 삭제
    boards = [doc async for doc in boards_col.find({"menu_id": menu_id})]
    board_ids = [str(b["_id"]) for b in boards]
    if board_ids:
        await posts_col.delete_many({"board_id": {"$in": board_ids}})
    await boards_col.delete_many({"menu_id": menu_id})
