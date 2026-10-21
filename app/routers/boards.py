"""Board & post CRUD. Boards belong to a menu."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.mongo import MongoClientManager
from app.models.board import (
    AdoptPostVersion, BoardCommentCreate, BoardCommentOut, BoardCreate, BoardOut, BoardPatch,
    PostCreate, PostHistoryOut, PostOut,
)
from app.models.user import UserPublic
from app.models.comment_reaction import CommentReactionToggle
from app.routers.admin import require_admin
from app.routers.auth import get_current_user
from app.services.mention_service import notify_mentions, resolve_mentions
from app.services.notification_service import create_notification, notify_users
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


async def _validate_post_parent(posts_col, board_id: str, parent_id: str | None, post_id: str | None = None) -> str | None:
    if not parent_id:
        return None
    if parent_id == post_id:
        raise HTTPException(status_code=400, detail="문서를 자기 자신의 하위 문서로 지정할 수 없습니다.")
    parent = await posts_col.find_one({"_id": parse_oid(parent_id, "잘못된 상위 문서 ID입니다."), "board_id": board_id})
    if not parent:
        raise HTTPException(status_code=400, detail="같은 게시판의 문서를 상위 문서로 선택해 주세요.")
    seen = {post_id}
    cursor = parent
    while cursor.get("parent_id"):
        ancestor_id = cursor["parent_id"]
        if ancestor_id in seen:
            raise HTTPException(status_code=400, detail="문서 계층에 순환이 생길 수 없습니다.")
        seen.add(ancestor_id)
        cursor = await posts_col.find_one({"_id": parse_oid(ancestor_id, "잘못된 상위 문서 ID입니다."), "board_id": board_id})
        if not cursor:
            break
    return parent.get("category") or ""


async def _validate_editors(editor_ids: list[str]):
    if len(editor_ids) != len(set(editor_ids)):
        raise HTTPException(status_code=400, detail="편집자를 중복 지정할 수 없습니다.")
    if not editor_ids:
        return
    user_oids = [parse_oid(user_id, "잘못된 편집자 ID입니다.") for user_id in editor_ids]
    users_col = MongoClientManager.get_users_collection()
    count = await users_col.count_documents({"_id": {"$in": user_oids}, "is_blocked": {"$ne": True}})
    if count != len(user_oids):
        raise HTTPException(status_code=400, detail="선택한 편집자 중 사용할 수 없는 계정이 있습니다.")


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
    menu_oid = parse_oid(payload.menu_id, "잘못된 메뉴 ID입니다.")
    menu = await menus_col.find_one({"_id": menu_oid})
    if not menu:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다.")

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
    _oid = parse_oid(board_id, "잘못된 게시판 ID입니다.")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다.")

    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다.")
    return _board_to_out(doc)


@router.delete("/{board_id}", status_code=204)
async def delete_board(board_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_boards_collection()
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(board_id, "잘못된 게시판 ID입니다.")
    result = await col.delete_one({"_id": _oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다.")
    await posts_col.delete_many({"board_id": board_id})


# ─── Posts ────────────────────────────────────────────────


def _post_to_out(doc: dict) -> PostOut:
    return PostOut(
        id=str(doc["_id"]),
        board_id=doc.get("board_id", ""),
        title=doc.get("title", ""),
        part=doc.get("part", ""),
        category=doc.get("category", ""),
        content=doc.get("content", ""),
        author_id=doc.get("author_id", ""),
        author_name=doc.get("author_name", ""),
        attachments=doc.get("attachments", []),
        created_at=fmt_dt(doc.get("created_at")),
        parent_id=doc.get("parent_id"),
        version=doc.get("version", 1),
        updated_at=fmt_dt(doc.get("updated_at")),
        editor_ids=doc.get("editor_ids") or [],
        owner_id=doc.get("owner_id") or doc.get("author_id", ""),
        owner_name=doc.get("owner_name") or doc.get("author_name", ""),
        adopted_by=doc.get("adopted_by"),
        adopted_name=doc.get("adopted_name"),
        adopted_at=fmt_dt(doc.get("adopted_at")),
        adopted_version=doc.get("adopted_version"),
        follower_count=len(doc.get("follower_ids") or []),
        mentioned_users=doc.get("mentioned_users") or [],
    )


def _post_version_snapshot(doc: dict) -> dict:
    return {
        "title": doc.get("title", ""),
        "part": doc.get("part", ""),
        "category": doc.get("category", ""),
        "content": doc.get("content", ""),
        "attachments": doc.get("attachments") or [],
        "parent_id": doc.get("parent_id"),
    }


@router.get("/{board_id}/posts", response_model=list[PostOut])
async def list_posts(board_id: str, _=Depends(get_current_user)):
    posts_col = MongoClientManager.get_board_posts_collection()
    docs = [doc async for doc in posts_col.find({"board_id": board_id}).sort("created_at", -1)]
    return [_post_to_out(doc) for doc in docs]


@router.get("/{board_id}/posts/{post_id}", response_model=PostOut)
async def get_post(board_id: str, post_id: str, _=Depends(get_current_user)):
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(post_id, "잘못된 게시글 ID입니다.")
    doc = await posts_col.find_one({"_id": _oid, "board_id": board_id})
    if not doc:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    return _post_to_out(doc)


@router.post("/{board_id}/posts", response_model=PostOut, status_code=201)
async def create_post(
    board_id: str,
    payload: PostCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    boards_col = MongoClientManager.get_boards_collection()
    _oid = parse_oid(board_id, "잘못된 게시판 ID입니다.")
    board = await boards_col.find_one({"_id": _oid})
    if not board:
        raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다.")

    posts_col = MongoClientManager.get_board_posts_collection()
    parent_category = await _validate_post_parent(posts_col, board_id, payload.parent_id)
    await _validate_editors(payload.editor_ids)
    mentioned = await resolve_mentions(payload.mentioned_user_ids, actor_id=str(current_user.id))
    now = datetime.now(timezone.utc)
    doc = {
        "board_id": board_id,
        "title": payload.title,
        "part": payload.part,
        "category": parent_category if payload.parent_id else payload.category,
        "content": payload.content,
        "author_id": current_user.id,
        "author_name": current_user.full_name or current_user.email,
        "attachments": [a.model_dump() for a in payload.attachments],
        "parent_id": payload.parent_id,
        "version": 1,
        "editor_ids": payload.editor_ids,
        "owner_id": current_user.id,
        "owner_name": current_user.full_name or current_user.email,
        "mentioned_users": [m.model_dump() for m in mentioned],
        "follower_ids": [],
        "created_at": now,
        "updated_at": now,
    }
    result = await posts_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    await MongoClientManager.get_board_post_histories_collection().insert_one({
        "post_id": str(result.inserted_id),
        "version": 1,
        "snapshot": _post_version_snapshot(doc),
        "diff": [],
        "changed_by": current_user.full_name or current_user.email,
        "changed_at": now,
    })
    if mentioned:
        await notify_mentions(
            mentioned_users=mentioned,
            comment_id=str(result.inserted_id),
            target_type="BOARD",
            target_id=str(result.inserted_id),
            target_title=payload.title,
            actor_id=str(current_user.id),
            actor_name=current_user.full_name or current_user.email,
            target_url=f"/board/{board_id}/post/{result.inserted_id}",
        )
    return _post_to_out(doc)


@router.patch("/{board_id}/posts/{post_id}", response_model=PostOut)
async def patch_post(
    board_id: str,
    post_id: str,
    payload: PostCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(post_id, "잘못된 게시글 ID입니다.")
    doc = await posts_col.find_one({"_id": _oid, "board_id": board_id})
    if not doc:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    current_owner_id = doc.get("owner_id") or doc.get("author_id")
    is_admin = getattr(current_user, "is_admin", False)
    is_owner = current_owner_id == current_user.id or is_admin
    if not is_owner and current_user.id not in (doc.get("editor_ids") or []):
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    if not is_owner and payload.editor_ids != (doc.get("editor_ids") or []):
        raise HTTPException(status_code=403, detail="편집자는 작성자 또는 관리자만 변경할 수 있습니다.")
    if is_owner:
        await _validate_editors(payload.editor_ids)
    if payload.owner_id and payload.owner_id != current_owner_id and not is_admin:
        raise HTTPException(status_code=403, detail="문서 책임자는 관리자만 변경할 수 있습니다.")
    next_owner_id = payload.owner_id or current_owner_id
    next_owner_name = doc.get("owner_name") or doc.get("author_name", "")
    if next_owner_id != current_owner_id:
        users_col = MongoClientManager.get_users_collection()
        next_owner = await users_col.find_one({
            "_id": parse_oid(next_owner_id, "잘못된 문서 책임자 ID입니다."),
            "is_blocked": {"$ne": True},
        })
        if not next_owner:
            raise HTTPException(status_code=400, detail="선택한 문서 책임자를 찾을 수 없습니다.")
        next_owner_name = next_owner.get("full_name") or next_owner.get("email", "")
    if payload.expected_version is not None and doc.get("version", 1) != payload.expected_version:
        raise HTTPException(status_code=409, detail="다른 사용자가 문서를 수정했습니다. 새로고침 후 다시 수정해 주세요.")
    parent_category = await _validate_post_parent(posts_col, board_id, payload.parent_id, post_id)
    next_category = parent_category if payload.parent_id else payload.category
    old_mentioned = {item.get("user_id") for item in doc.get("mentioned_users", [])}
    mentioned = await resolve_mentions(payload.mentioned_user_ids, actor_id=str(current_user.id))
    new_mentioned_ids = {item.user_id for item in mentioned}

    diff = []
    for field, label in (("title", "제목"), ("part", "업무 파트"), ("category", "카테고리"), ("content", "내용"), ("parent_id", "상위 문서")):
        before = doc.get(field, "") or ""
        after = (next_category if field == "category" else getattr(payload, field)) or ""
        if before != after:
            diff.append({"key": field, "field": label, "before": before, "after": after})
    attachments = [a.model_dump() for a in payload.attachments]
    if doc.get("attachments", []) != attachments:
        before_names = ", ".join(a.get("original_name", "") for a in doc.get("attachments", []))
        after_names = ", ".join(a.get("original_name", "") for a in attachments)
        diff.append({"field": "첨부파일", "before": before_names, "after": after_names})
    previous_editor_ids = doc.get("editor_ids") or []
    if previous_editor_ids != payload.editor_ids:
        diff.append({"field": "편집자", "before": ", ".join(previous_editor_ids), "after": ", ".join(payload.editor_ids)})
    if next_owner_id != current_owner_id:
        diff.append({"field": "문서 책임자", "before": doc.get("owner_name") or doc.get("author_name", ""), "after": next_owner_name})
    if old_mentioned != new_mentioned_ids:
        diff.append({"field": "멘션", "before": ", ".join(sorted(uid for uid in old_mentioned if uid)), "after": ", ".join(sorted(new_mentioned_ids))})
    if not diff:
        return _post_to_out(doc)

    update_fields = {
        "title": payload.title,
        "part": payload.part,
        "category": next_category,
        "content": payload.content,
        "attachments": attachments,
        "parent_id": payload.parent_id,
        "editor_ids": payload.editor_ids,
        "owner_id": next_owner_id,
        "owner_name": next_owner_name,
        "mentioned_users": [m.model_dump() for m in mentioned],
        "updated_at": datetime.now(timezone.utc),
    }
    if "version" in doc:
        version_query = {"version": doc["version"]}
        update = {"$set": update_fields, "$inc": {"version": 1}}
    else:
        version_query = {"version": {"$exists": False}}
        update_fields["version"] = 2
        update = {"$set": update_fields}
    previous_snapshot = _post_version_snapshot(doc)
    doc = await posts_col.find_one_and_update(
        {"_id": _oid, "board_id": board_id, **version_query}, update, return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=409, detail="다른 사용자가 문서를 수정했습니다. 새로고침 후 다시 수정해 주세요.")
    history_col = MongoClientManager.get_board_post_histories_collection()
    changed_at = doc.get("updated_at") or datetime.now(timezone.utc)
    previous_version = (doc.get("version", 2) - 1)
    await history_col.update_one(
        {"post_id": post_id, "version": previous_version},
        {
            "$set": {"snapshot": previous_snapshot},
            "$setOnInsert": {
                "post_id": post_id,
                "version": previous_version,
                "diff": [],
                "changed_by": doc.get("author_name", ""),
                "changed_at": doc.get("created_at") or changed_at,
            },
        },
        upsert=True,
    )
    await history_col.update_one(
        {"post_id": post_id, "version": doc.get("version", 1)},
        {
            "$set": {
                "snapshot": _post_version_snapshot(doc),
                "diff": diff,
                "changed_by": current_user.full_name or current_user.email,
                "changed_at": changed_at,
            },
            "$setOnInsert": {"post_id": post_id, "version": doc.get("version", 1)},
        },
        upsert=True,
    )
    followers = [uid for uid in (doc.get("follower_ids") or []) if uid != str(current_user.id)]
    if followers:
        await notify_users(
            user_ids=followers,
            notification_type="BOARD_UPDATED",
            title="관심 문서가 수정되었습니다",
            message=f"{current_user.full_name or current_user.email}님이 '{doc.get('title', '')}' 문서를 수정했습니다.",
            sender_user_id=str(current_user.id),
            sender_name=current_user.full_name or current_user.email,
            target_type="BOARD",
            target_id=post_id,
            target_url=f"/board/{board_id}/post/{post_id}",
        )
    added_mentions = [m for m in mentioned if m.user_id not in old_mentioned]
    if added_mentions:
        await notify_mentions(
            mentioned_users=added_mentions,
            comment_id=f"{post_id}:v{doc.get('version', 1)}",
            target_type="BOARD",
            target_id=post_id,
            target_title=doc.get("title", ""),
            actor_id=str(current_user.id),
            actor_name=current_user.full_name or current_user.email,
            target_url=f"/board/{board_id}/post/{post_id}",
        )
    return _post_to_out(doc)


@router.delete("/{board_id}/posts/{post_id}", status_code=204)
async def delete_post(
    board_id: str,
    post_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col = MongoClientManager.get_board_posts_collection()
    _oid = parse_oid(post_id, "잘못된 게시글 ID입니다.")
    doc = await posts_col.find_one({"_id": _oid, "board_id": board_id})
    if not doc:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if (doc.get("owner_id") or doc.get("author_id")) != current_user.id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    if await posts_col.find_one({"board_id": board_id, "parent_id": post_id}):
        raise HTTPException(status_code=400, detail="하위 문서를 먼저 이동하거나 삭제해 주세요.")
    await posts_col.delete_one({"_id": _oid})
    await MongoClientManager.get_board_post_comments_collection().delete_many({"board_id": board_id, "post_id": post_id})


@router.get("/{board_id}/posts/{post_id}/history", response_model=list[PostHistoryOut])
async def list_post_history(board_id: str, post_id: str, _=Depends(get_current_user)):
    posts_col = MongoClientManager.get_board_posts_collection()
    post = await posts_col.find_one({"_id": parse_oid(post_id, "잘못된 문서 ID입니다."), "board_id": board_id})
    if not post:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    col = MongoClientManager.get_board_post_histories_collection()
    current_version = post.get("version", 1)
    current_snapshot = _post_version_snapshot(post)
    await col.update_one(
        {"post_id": post_id, "version": current_version},
        {
            "$set": {"snapshot": current_snapshot},
            "$setOnInsert": {
                "post_id": post_id,
                "version": current_version,
                "diff": [],
                "changed_by": post.get("author_name", ""),
                "changed_at": post.get("created_at") or post.get("updated_at") or datetime.now(timezone.utc),
            },
        },
        upsert=True,
    )

    # Older history rows stored only diffs. Rebuild their text snapshots by
    # walking backward from the current version, then persist the result.
    latest = await col.find_one({"post_id": post_id, "version": current_version})
    working = dict(latest.get("snapshot") or current_snapshot)
    history_by_version = {
        item.get("version"): item
        async for item in col.find({"post_id": post_id}).sort("version", -1)
        if isinstance(item.get("version"), int)
    }
    legacy_keys = {
        "제목": "title",
        "업무 파트": "part",
        "카테고리": "category",
        "내용": "content",
        "상위 문서": "parent_id",
    }
    for version in range(current_version, 1, -1):
        version_row = history_by_version.get(version)
        if not version_row:
            break
        previous = dict(working)
        for item in version_row.get("diff", []):
            key = item.get("key") or legacy_keys.get(item.get("field", ""))
            if key in ("title", "part", "category", "content", "parent_id"):
                previous[key] = item.get("before") or (None if key == "parent_id" else "")
        previous_version = version - 1
        await col.update_one(
            {"post_id": post_id, "version": previous_version},
            {
                "$setOnInsert": {
                    "post_id": post_id,
                    "version": previous_version,
                    "diff": [],
                    "changed_by": post.get("author_name", ""),
                    "changed_at": post.get("created_at") or datetime.now(timezone.utc),
                },
                "$set": {"snapshot": previous},
            },
            upsert=True,
        )
        previous_row = await col.find_one({"post_id": post_id, "version": previous_version})
        working = dict(previous_row.get("snapshot") or previous)

    docs = [doc async for doc in col.find({"post_id": post_id}).sort("version", -1)]
    return [
        PostHistoryOut(
            id=str(d["_id"]),
            post_id=post_id,
            diff=d.get("diff", []),
            changed_by=d.get("changed_by", ""),
            changed_at=fmt_dt(d.get("changed_at")),
            version=d.get("version"),
            snapshot=d.get("snapshot"),
        )
        for d in docs
    ]


async def _get_board_post(board_id: str, post_id: str):
    posts_col = MongoClientManager.get_board_posts_collection()
    post = await posts_col.find_one({
        "_id": parse_oid(post_id, "잘못된 문서 ID입니다."),
        "board_id": board_id,
    })
    if not post:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    return posts_col, post


@router.post("/{board_id}/posts/{post_id}/follow")
async def follow_post(
    board_id: str,
    post_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col, _post = await _get_board_post(board_id, post_id)
    uid = str(current_user.id)
    await posts_col.update_one({"_id": _post["_id"]}, {"$addToSet": {"follower_ids": uid}})
    return {"following": True}


@router.delete("/{board_id}/posts/{post_id}/follow")
async def unfollow_post(
    board_id: str,
    post_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col, post = await _get_board_post(board_id, post_id)
    await posts_col.update_one(
        {"_id": post["_id"]}, {"$pull": {"follower_ids": str(current_user.id)}}
    )
    return {"following": False}


@router.get("/{board_id}/posts/{post_id}/follow")
async def get_post_follow_status(
    board_id: str,
    post_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    _posts_col, post = await _get_board_post(board_id, post_id)
    return {"following": str(current_user.id) in (post.get("follower_ids") or [])}


@router.post("/{board_id}/posts/{post_id}/adopt", response_model=PostOut)
async def adopt_post(
    board_id: str,
    post_id: str,
    payload: AdoptPostVersion,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col, post = await _get_board_post(board_id, post_id)
    if post.get("adopted_by") not in (None, str(current_user.id)) and not current_user.is_admin:
        raise HTTPException(status_code=409, detail="이미 다른 사용자가 채택한 문서입니다.")
    version_row = await MongoClientManager.get_board_post_histories_collection().find_one({
        "post_id": post_id,
        "version": payload.version,
        "snapshot": {"$exists": True},
    })
    if not version_row:
        raise HTTPException(status_code=404, detail="선택한 버전 내용을 찾을 수 없습니다.")
    target = version_row["snapshot"]
    current = _post_version_snapshot(post)
    diff = []
    labels = {
        "title": "제목",
        "part": "업무 파트",
        "category": "카테고리",
        "content": "내용",
        "parent_id": "상위 문서",
    }
    for key, label in labels.items():
        before, after = current.get(key), target.get(key)
        if before != after:
            diff.append({"key": key, "field": label, "before": before, "after": after})
    if current.get("attachments", []) != target.get("attachments", []):
        before_names = ", ".join(item.get("original_name", "") for item in current.get("attachments", []))
        after_names = ", ".join(item.get("original_name", "") for item in target.get("attachments", []))
        diff.append({"key": "attachments", "field": "첨부파일", "before": before_names, "after": after_names})

    now = datetime.now(timezone.utc)
    history_col = MongoClientManager.get_board_post_histories_collection()
    current_version = post.get("version", 1)
    current_version_query = {"version": post["version"]} if "version" in post else {"version": {"$exists": False}}
    if diff:
        await history_col.update_one(
            {"post_id": post_id, "version": current_version},
            {
                "$set": {"snapshot": current},
                "$setOnInsert": {
                    "post_id": post_id,
                    "version": current_version,
                    "diff": [],
                    "changed_by": post.get("author_name", ""),
                    "changed_at": post.get("created_at") or now,
                },
            },
            upsert=True,
        )
    next_version = current_version + 1 if diff else current_version
    fields = {
        "adopted_by": str(current_user.id),
        "adopted_name": current_user.full_name or current_user.email,
        "adopted_at": now,
        "adopted_version": payload.version,
    }
    if diff:
        fields.update(target)
        fields["version"] = next_version
        fields["updated_at"] = now
    updated = await posts_col.find_one_and_update(
        {"_id": post["_id"], **current_version_query},
        {"$set": fields},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="문서가 변경되었습니다. 새로고침 후 다시 시도해 주세요.")
    if diff:
        await history_col.update_one(
            {"post_id": post_id, "version": next_version},
            {
                "$set": {
                    "snapshot": _post_version_snapshot(updated),
                    "diff": diff,
                    "changed_by": current_user.full_name or current_user.email,
                    "changed_at": now,
                },
                "$setOnInsert": {"post_id": post_id, "version": next_version},
            },
            upsert=True,
        )
        followers = [uid for uid in (post.get("follower_ids") or []) if uid != str(current_user.id)]
        if followers:
            await notify_users(
                user_ids=followers,
                notification_type="BOARD_UPDATED",
                title="관심 문서가 채택된 버전으로 변경되었습니다",
                message=f"{current_user.full_name or current_user.email}님이 '{updated.get('title', '')}' 문서에 v{payload.version}을 채택했습니다.",
                sender_user_id=str(current_user.id),
                sender_name=current_user.full_name or current_user.email,
                target_type="BOARD",
                target_id=post_id,
                target_url=f"/board/{board_id}/post/{post_id}",
            )
    return _post_to_out(updated)


@router.delete("/{board_id}/posts/{post_id}/adopt", response_model=PostOut)
async def clear_post_adoption(
    board_id: str,
    post_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    posts_col, post = await _get_board_post(board_id, post_id)
    if post.get("adopted_by") not in (None, str(current_user.id)) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="채택을 취소할 권한이 없습니다.")
    updated = await posts_col.find_one_and_update(
        {"_id": post["_id"]},
        {"$unset": {"adopted_by": "", "adopted_name": "", "adopted_at": "", "adopted_version": ""}},
        return_document=True,
    )
    return _post_to_out(updated)


def _comment_to_out(doc: dict) -> BoardCommentOut:
    return BoardCommentOut(
        id=str(doc["_id"]),
        board_id=doc["board_id"],
        post_id=doc["post_id"],
        author_id=doc["author_id"],
        author_name=doc.get("author_name", ""),
        content=doc.get("content", ""),
        mentioned_users=doc.get("mentioned_users") or [],
        reactions=doc.get("reactions") or [],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("/{board_id}/posts/{post_id}/comments", response_model=list[BoardCommentOut])
async def list_board_comments(
    board_id: str,
    post_id: str,
    _current_user: UserPublic = Depends(get_current_user),
):
    await _get_board_post(board_id, post_id)
    col = MongoClientManager.get_board_post_comments_collection()
    docs = await col.find({"board_id": board_id, "post_id": post_id}).sort("created_at", 1).to_list(None)
    return [_comment_to_out(doc) for doc in docs]


@router.post("/{board_id}/posts/{post_id}/comments", response_model=BoardCommentOut, status_code=201)
async def create_board_comment(
    board_id: str,
    post_id: str,
    body: BoardCommentCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    _posts_col, post = await _get_board_post(board_id, post_id)
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="댓글 내용을 입력해 주세요.")
    mentioned = await resolve_mentions(body.mentioned_user_ids, actor_id=str(current_user.id))
    now = datetime.now(timezone.utc)
    doc = {
        "board_id": board_id,
        "post_id": post_id,
        "author_id": str(current_user.id),
        "author_name": current_user.full_name or current_user.email,
        "content": content,
        "mentioned_users": [m.model_dump() for m in mentioned],
        "reactions": [],
        "created_at": now,
        "updated_at": now,
    }
    col = MongoClientManager.get_board_post_comments_collection()
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    if mentioned:
        await notify_mentions(
            mentioned_users=mentioned,
            comment_id=str(result.inserted_id),
            target_type="BOARD",
            target_id=post_id,
            target_title=post.get("title", ""),
            actor_id=str(current_user.id),
            actor_name=current_user.full_name or current_user.email,
            target_url=f"/board/{board_id}/post/{post_id}",
        )
    return _comment_to_out(doc)


@router.delete("/{board_id}/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_board_comment(
    board_id: str,
    post_id: str,
    comment_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_board_post_comments_collection()
    query = {
        "_id": parse_oid(comment_id, "잘못된 댓글 ID입니다."),
        "board_id": board_id,
        "post_id": post_id,
    }
    comment = await col.find_one(query)
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if comment["author_id"] != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="댓글을 삭제할 권한이 없습니다.")
    await col.delete_one(query)


ALLOWED_BOARD_REACTION_EMOJIS = {"👍", "❤️", "😂", "🎉", "👀", "🙏", "🚀"}


@router.post("/{board_id}/posts/{post_id}/comments/{comment_id}/reactions", response_model=BoardCommentOut)
async def toggle_board_comment_reaction(
    board_id: str,
    post_id: str,
    comment_id: str,
    body: CommentReactionToggle,
    current_user: UserPublic = Depends(get_current_user),
):
    if body.emoji not in ALLOWED_BOARD_REACTION_EMOJIS:
        raise HTTPException(status_code=400, detail="지원하지 않는 이모지입니다.")
    col = MongoClientManager.get_board_post_comments_collection()
    query = {
        "_id": parse_oid(comment_id, "잘못된 댓글 ID입니다."),
        "board_id": board_id,
        "post_id": post_id,
    }
    doc = await col.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    reactions = doc.get("reactions") or []
    uid = str(current_user.id)
    display_name = current_user.full_name or current_user.email
    group = next((item for item in reactions if item["emoji"] == body.emoji), None)
    if group is None:
        reactions.append({"emoji": body.emoji, "users": [{"user_id": uid, "display_name": display_name}]})
    elif any(user["user_id"] == uid for user in group["users"]):
        group["users"] = [user for user in group["users"] if user["user_id"] != uid]
        if not group["users"]:
            reactions = [item for item in reactions if item["emoji"] != body.emoji]
    else:
        group["users"].append({"user_id": uid, "display_name": display_name})
    updated = await col.find_one_and_update(query, {"$set": {"reactions": reactions}}, return_document=True)
    return _comment_to_out(updated)
