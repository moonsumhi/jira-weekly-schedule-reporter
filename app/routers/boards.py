"""Board & post CRUD. Boards belong to a menu."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.mongo import MongoClientManager
from app.models.board import BoardCreate, BoardOut, BoardPatch, PostCreate, PostOut
from app.models.user import UserPublic
from app.routers.admin import require_admin
from app.routers.auth import get_current_user
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()


# ─── Boards ───────────────────────────────────────────────


def _board_to_out(doc: dict, post_count: int = 0) -> BoardOut:
    return BoardOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        description=doc.get("description", ""),
        menu_id=doc.get("menu_id", ""),
        icon=doc.get("icon"),
        post_count=post_count,
        link=doc.get("link"),
        sort_order=doc.get("sort_order"),
        created_at=fmt_dt(doc.get("created_at")),
    )


@router.get("", response_model=list[BoardOut])
async def list_boards(menu_id: str | None = Query(default=None)):
    col = MongoClientManager.get_boards_collection()
    posts_col = MongoClientManager.get_board_posts_collection()

    query = {}
    if menu_id is not None:
        query["menu_id"] = menu_id
    docs = [doc async for doc in col.find(query)]
    docs.sort(key=lambda d: (d.get("sort_order") is None, d.get("sort_order") or 0))

    # 게시글 수를 단일 aggregation으로 조회 (N+1 방지)
    board_ids = [str(d["_id"]) for d in docs]
    count_map: dict[str, int] = {}
    if board_ids:
        pipeline = [
            {"$match": {"board_id": {"$in": board_ids}}},
            {"$group": {"_id": "$board_id", "count": {"$sum": 1}}},
        ]
        async for row in posts_col.aggregate(pipeline):
            count_map[row["_id"]] = row["count"]

    return [_board_to_out(doc, count_map.get(str(doc["_id"]), 0)) for doc in docs]


@router.post("", response_model=BoardOut, status_code=201)
async def create_board(payload: BoardCreate, _=Depends(require_admin)):
    # menu 존재 확인
    menus_col = MongoClientManager.get_menus_collection()
    menu_oid = parse_oid(payload.menu_id, "Invalid menu id")
    menu = await menus_col.find_one({"_id": menu_oid})
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    col = MongoClientManager.get_boards_collection()
    doc = {
        "title": payload.title,
        "description": payload.description,
        "menu_id": payload.menu_id,
        "icon": payload.icon,
        "link": payload.link,
        "sort_order": payload.sort_order,
        "created_at": datetime.now(timezone.utc),
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _board_to_out(doc)


@router.patch("/{board_id}", response_model=BoardOut)
async def patch_board(board_id: str, payload: BoardPatch, _=Depends(require_admin)):
    col = MongoClientManager.get_boards_collection()
    _oid = parse_oid(board_id, "Invalid board id")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")

    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Board not found")
    return _board_to_out(doc)


@router.delete("/{board_id}", status_code=204)
async def delete_board(board_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_boards_collection()
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(board_id, "Invalid board id")
    result = await col.delete_one({"_id": _oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Board not found")
    await posts_col.delete_many({"board_id": board_id})


# ─── Posts ────────────────────────────────────────────────


def _post_to_out(doc: dict) -> PostOut:
    return PostOut(
        id=str(doc["_id"]),
        board_id=doc.get("board_id", ""),
        title=doc.get("title", ""),
        content=doc.get("content", ""),
        author_id=doc.get("author_id", ""),
        author_name=doc.get("author_name", ""),
        created_at=fmt_dt(doc.get("created_at")),
    )


@router.get("/{board_id}/posts", response_model=list[PostOut])
async def list_posts(board_id: str, _=Depends(get_current_user)):
    posts_col = MongoClientManager.get_board_posts_collection()
    docs = [doc async for doc in posts_col.find({"board_id": board_id}).sort("created_at", -1)]
    return [_post_to_out(doc) for doc in docs]


@router.post("/{board_id}/posts", response_model=PostOut, status_code=201)
async def create_post(
    board_id: str,
    payload: PostCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    boards_col = MongoClientManager.get_boards_collection()
    _oid = parse_oid(board_id, "Invalid board id")
    board = await boards_col.find_one({"_id": _oid})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    posts_col = MongoClientManager.get_board_posts_collection()
    doc = {
        "board_id": board_id,
        "title": payload.title,
        "content": payload.content,
        "author_id": current_user.id,
        "author_name": current_user.full_name or current_user.email,
        "created_at": datetime.now(timezone.utc),
    }
    result = await posts_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _post_to_out(doc)


@router.patch("/{board_id}/posts/{post_id}", response_model=PostOut)
async def patch_post(
    board_id: str,
    post_id: str,
    payload: PostCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(post_id, "Invalid post id")
    doc = await posts_col.find_one({"_id": _oid, "board_id": board_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Post not found")
    if doc.get("author_id") != current_user.id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await posts_col.find_one_and_update(
        {"_id": _oid},
        {"$set": {"title": payload.title, "content": payload.content}},
        return_document=True,
    )
    return _post_to_out(doc)


@router.delete("/{board_id}/posts/{post_id}", status_code=204)
async def delete_post(
    board_id: str,
    post_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(post_id, "Invalid post id")
    doc = await posts_col.find_one({"_id": _oid, "board_id": board_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Post not found")
    if doc.get("author_id") != current_user.id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")
    await posts_col.delete_one({"_id": _oid})
