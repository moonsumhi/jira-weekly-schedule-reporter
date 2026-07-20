from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.issue import (
    IssueCreate, IssuePatch, IssueOut,
    IssueCommentCreate, IssueCommentPatch, IssueCommentOut,
    IssueHistoryOut, LabelCreate, LabelOut,
)
from app.routers.auth import get_current_user
from app.services.pm.permission import get_issue_or_404, require_pm_member
from app.services.pm.issue_service import next_issue_number, record_history, enrich_issue
from app.services.notification_service import create_notification
from app.services.mention_service import resolve_mentions, notify_mentions
from app.models.mention import MentionedUser

router = APIRouter()


# ── 이슈 CRUD ──────────────────────────────────────────────────────

@router.get("/{project_id}/issues", response_model=List[IssueOut])
async def list_issues(
    project_id: str,
    status: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    sprint_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    parent_issue_id: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    col = MongoClientManager.get_pm_issues_collection()

    query: dict = {"project_id": ObjectId(project_id)}
    if status:
        query["status"] = status
    if assignee_id:
        query["assignee_id"] = ObjectId(assignee_id)
    if priority:
        query["priority"] = priority
    if sprint_id:
        query["sprint_id"] = ObjectId(sprint_id)
    if type:
        query["type"] = type
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    if parent_issue_id:
        query["parent_issue_id"] = ObjectId(parent_issue_id)

    docs = await col.find(query).sort([("status", 1), ("order", 1)]).to_list(None)
    return [await enrich_issue(d) for d in docs]


@router.post("/{project_id}/issues", response_model=IssueOut, status_code=201)
async def create_issue(
    project_id: str,
    body: IssueCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    col = MongoClientManager.get_pm_issues_collection()

    pid = ObjectId(project_id)
    number = await next_issue_number(pid)
    now = datetime.now(timezone.utc)

    doc = {
        "project_id": pid,
        "number": number,
        "title": body.title,
        "description": body.description,
        "type": body.type,
        "status": body.status,
        "priority": body.priority,
        "assignee_id": ObjectId(body.assignee_id) if body.assignee_id else None,
        "reporter_id": ObjectId(current_user.id),
        "sprint_id": ObjectId(body.sprint_id) if body.sprint_id else None,
        "epic_id": ObjectId(body.epic_id) if body.epic_id else None,
        "parent_issue_id": ObjectId(body.parent_issue_id) if body.parent_issue_id else None,
        "label_ids": [ObjectId(x) for x in body.label_ids],
        "start_date": body.start_date,
        "due_date": body.due_date,
        "story_points": body.story_points,
        "effort_md": body.effort_md,
        "attachments": [a.model_dump() for a in body.attachments],
        "order": float(number),
        "created_at": now,
        "updated_at": now,
    }
    result = await col.insert_one(doc)
    created = await col.find_one({"_id": result.inserted_id})
    return await enrich_issue(created)


@router.get("/{project_id}/issues/{issue_id}", response_model=IssueOut)
async def get_issue(
    project_id: str,
    issue_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    doc = await get_issue_or_404(project_id, issue_id)
    return await enrich_issue(doc)


@router.patch("/{project_id}/issues/{issue_id}", response_model=IssueOut)
async def patch_issue(
    project_id: str,
    issue_id: str,
    body: IssuePatch,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    col = MongoClientManager.get_pm_issues_collection()

    old = await get_issue_or_404(project_id, issue_id)
    patch = body.model_dump(exclude_unset=True)

    update: dict = {}
    for oid_field in ("assignee_id", "sprint_id", "epic_id", "parent_issue_id"):
        if oid_field in patch:
            val = patch.pop(oid_field)
            update[oid_field] = ObjectId(val) if val else None
    if "label_ids" in patch:
        update["label_ids"] = [ObjectId(x) for x in patch.pop("label_ids")]
    update.update(patch)
    update["updated_at"] = datetime.now(timezone.utc)

    new_doc = await col.find_one_and_update(
        {"_id": ObjectId(issue_id)},
        {"$set": update},
        return_document=True,
    )

    # 모든 변경 필드 이력 기록
    uid = ObjectId(current_user.id)
    iid = ObjectId(issue_id)

    users_col = MongoClientManager.get_users_collection()
    issues_col = col
    sprints_col = MongoClientManager.get_pm_sprints_collection()
    labels_col = MongoClientManager.get_pm_labels_collection()

    _STATUS_KO = {"BACKLOG": "백로그", "TODO": "할 일", "IN_PROGRESS": "진행 중", "IN_REVIEW": "검토 중", "DONE": "완료"}
    _PRIORITY_KO = {"LOWEST": "최저", "LOW": "낮음", "MEDIUM": "보통", "HIGH": "높음", "HIGHEST": "최고"}
    _TYPE_KO = {"EPIC": "Epic", "STORY": "Story", "TASK": "Task", "BUG": "Bug", "SUB_TASK": "Sub-task"}

    async def _resolve(field: str, val) -> str | None:
        if val is None:
            return None
        if field == "status":
            return _STATUS_KO.get(str(val), str(val))
        if field == "priority":
            return _PRIORITY_KO.get(str(val), str(val))
        if field == "type":
            return _TYPE_KO.get(str(val), str(val))
        if field == "assignee_id":
            u = await users_col.find_one({"_id": val if isinstance(val, ObjectId) else ObjectId(str(val))}, {"full_name": 1, "email": 1})
            return (u.get("full_name") or u.get("email", str(val))) if u else str(val)
        if field == "sprint_id":
            s = await sprints_col.find_one({"_id": val if isinstance(val, ObjectId) else ObjectId(str(val))}, {"name": 1})
            return s.get("name", str(val)) if s else str(val)
        if field in ("epic_id", "parent_issue_id"):
            e = await issues_col.find_one({"_id": val if isinstance(val, ObjectId) else ObjectId(str(val))}, {"title": 1})
            return e.get("title", str(val)) if e else str(val)
        if field == "label_ids":
            if isinstance(val, list):
                names = []
                for lid in val:
                    lbl = await labels_col.find_one({"_id": lid if isinstance(lid, ObjectId) else ObjectId(str(lid))}, {"name": 1})
                    names.append(lbl.get("name", str(lid)) if lbl else str(lid))
                return ", ".join(names) if names else None
        if isinstance(val, list):
            return ", ".join(str(x) for x in val)
        return str(val)

    def _raw_str(v) -> str | None:
        if v is None:
            return None
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return str(v)

    skip = {"updated_at", "order"}
    for field, new_val in update.items():
        if field in skip:
            continue
        old_val = old.get(field)
        if _raw_str(old_val) != _raw_str(new_val):
            old_display = await _resolve(field, old_val)
            new_display = await _resolve(field, new_val)
            await record_history(iid, uid, field, old_display, new_display)

    enriched = await enrich_issue(new_doc)

    # 담당자 변경 시 새 담당자에게 알림
    old_assignee_id = old.get("assignee_id")
    new_assignee_raw = update.get("assignee_id")
    if new_assignee_raw and str(new_assignee_raw) != str(old_assignee_id or ""):
        new_assignee_str = str(new_assignee_raw)
        if new_assignee_str != str(current_user.id):
            await create_notification(
                recipient_user_id=new_assignee_str,
                notification_type="ASSIGNED",
                title="이슈 담당 배정",
                message=f"'{old.get('title', '')}' 이슈의 담당자로 배정되었습니다.",
                sender_user_id=str(current_user.id),
                sender_name=current_user.full_name or current_user.email,
                target_type="PM_ISSUE",
                target_id=issue_id,
                target_url=f"/pm/projects/{project_id}/board",
            )

    return enriched


@router.delete("/{project_id}/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    project_id: str,
    issue_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    await get_issue_or_404(project_id, issue_id)
    iid = ObjectId(issue_id)
    await MongoClientManager.get_pm_issue_comments_collection().delete_many({"issue_id": iid})
    await MongoClientManager.get_pm_issue_history_collection().delete_many({"issue_id": iid})
    await MongoClientManager.get_pm_issues_collection().delete_one({"_id": iid})


# ── 댓글 ──────────────────────────────────────────────────────────

@router.get("/{project_id}/issues/{issue_id}/comments", response_model=List[IssueCommentOut])
async def list_comments(
    project_id: str,
    issue_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    await get_issue_or_404(project_id, issue_id)

    col = MongoClientManager.get_pm_issue_comments_collection()
    users_col = MongoClientManager.get_users_collection()

    docs = await col.find({"issue_id": ObjectId(issue_id)}).sort("created_at", 1).to_list(None)
    result = []
    for d in docs:
        user = await users_col.find_one({"_id": d["author_id"]}, {"full_name": 1, "email": 1})
        mentioned_users = [
            MentionedUser(user_id=m["user_id"], display_name=m["display_name"])
            for m in d.get("mentioned_users", [])
        ]
        result.append(IssueCommentOut(
            id=str(d["_id"]),
            issue_id=str(d["issue_id"]),
            parent_id=str(d["parent_id"]) if d.get("parent_id") else None,
            author_id=str(d["author_id"]),
            author_name=user.get("full_name") or user.get("email", "") if user else "",
            content=d["content"],
            attachments=d.get("attachments") or [],
            mentioned_users=mentioned_users,
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        ))
    return result


def _trunc(text: str | None, max_len: int = 60) -> str | None:
    if not text:
        return None
    return text[:max_len] + "…" if len(text) > max_len else text


@router.post("/{project_id}/issues/{issue_id}/comments", response_model=IssueCommentOut, status_code=201)
async def create_comment(
    project_id: str,
    issue_id: str,
    body: IssueCommentCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    await get_issue_or_404(project_id, issue_id)

    col = MongoClientManager.get_pm_issue_comments_collection()
    users_col = MongoClientManager.get_users_collection()
    now = datetime.now(timezone.utc)

    # 멘션 처리 — 프로젝트 멤버만 허용
    members_col = MongoClientManager.get_pm_project_members_collection()
    member_docs = await members_col.find({"project_id": ObjectId(project_id)}, {"user_id": 1}).to_list(None)
    allowed_ids = {str(m["user_id"]) for m in member_docs}
    mentioned = await resolve_mentions(
        body.mentioned_user_ids,
        actor_id=str(current_user.id),
        allowed_user_ids=allowed_ids,
    )

    result = await col.insert_one({
        "issue_id": ObjectId(issue_id),
        "parent_id": ObjectId(body.parent_id) if body.parent_id else None,
        "author_id": ObjectId(current_user.id),
        "content": body.content,
        "attachments": [a.model_dump() for a in body.attachments],
        "mentioned_users": [m.model_dump() for m in mentioned],
        "created_at": now,
        "updated_at": now,
    })
    comment_id_str = str(result.inserted_id)
    d = await col.find_one({"_id": result.inserted_id})
    user = await users_col.find_one({"_id": ObjectId(current_user.id)}, {"full_name": 1, "email": 1})
    sender_name = current_user.full_name or current_user.email

    new_display = _trunc(body.content) or (f"첨부파일 {len(body.attachments)}개" if body.attachments else None)
    await record_history(ObjectId(issue_id), ObjectId(current_user.id), "comment", None, new_display)

    # 이슈 담당자에게 댓글 알림 (작성자 자신 제외)
    issue_doc = await MongoClientManager.get_pm_issues_collection().find_one({"_id": ObjectId(issue_id)})
    if issue_doc and issue_doc.get("assignee_id"):
        assignee_str = str(issue_doc["assignee_id"])
        if assignee_str != str(current_user.id):
            preview = body.content[:40] + "…" if len(body.content) > 40 else body.content
            await create_notification(
                recipient_user_id=assignee_str,
                notification_type="COMMENT_CREATED",
                title="이슈 댓글",
                message=f"{sender_name}: {preview}",
                sender_user_id=str(current_user.id),
                sender_name=sender_name,
                target_type="PM_ISSUE",
                target_id=issue_id,
                target_url=f"/pm/projects/{project_id}/board",
            )

    # 멘션 알림
    issue_title = issue_doc.get("title", "") if issue_doc else ""
    if mentioned:
        await notify_mentions(
            mentioned_users=mentioned,
            comment_id=comment_id_str,
            target_type="PM_ISSUE",
            target_id=issue_id,
            target_title=issue_title,
            actor_id=str(current_user.id),
            actor_name=sender_name,
            target_url=f"/pm/projects/{project_id}/board?issueId={issue_id}&commentId={comment_id_str}",
        )

    return IssueCommentOut(
        id=str(d["_id"]),
        issue_id=str(d["issue_id"]),
        parent_id=str(d["parent_id"]) if d.get("parent_id") else None,
        author_id=str(d["author_id"]),
        author_name=user.get("full_name") or user.get("email", "") if user else "",
        content=d["content"],
        attachments=d.get("attachments") or [],
        mentioned_users=mentioned,
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


@router.patch("/{project_id}/issues/{issue_id}/comments/{comment_id}", response_model=IssueCommentOut)
async def patch_comment(
    project_id: str,
    issue_id: str,
    comment_id: str,
    body: IssueCommentPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    col = MongoClientManager.get_pm_issue_comments_collection()
    users_col = MongoClientManager.get_users_collection()

    old_doc = await col.find_one({"_id": ObjectId(comment_id), "author_id": ObjectId(current_user.id)})
    if not old_doc:
        raise HTTPException(status_code=403, detail="댓글을 찾을 수 없거나 수정 권한이 없습니다.")

    # 멘션 diff 처리
    old_mention_ids = {m["user_id"] for m in old_doc.get("mentioned_users", [])}
    members_col = MongoClientManager.get_pm_project_members_collection()
    member_docs = await members_col.find({"project_id": ObjectId(project_id)}, {"user_id": 1}).to_list(None)
    allowed_ids = {str(m["user_id"]) for m in member_docs}
    new_mentioned = await resolve_mentions(
        body.mentioned_user_ids,
        actor_id=str(current_user.id),
        allowed_user_ids=allowed_ids,
    )

    d = await col.find_one_and_update(
        {"_id": ObjectId(comment_id)},
        {"$set": {
            "content": body.content,
            "mentioned_users": [m.model_dump() for m in new_mentioned],
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True,
    )

    await record_history(
        ObjectId(issue_id), ObjectId(current_user.id), "comment",
        _trunc(old_doc.get("content")), _trunc(body.content),
    )

    # 새로 추가된 멘션에만 알림
    added_mentions = [m for m in new_mentioned if m.user_id not in old_mention_ids]
    if added_mentions:
        issue_doc = await MongoClientManager.get_pm_issues_collection().find_one({"_id": ObjectId(issue_id)})
        issue_title = issue_doc.get("title", "") if issue_doc else ""
        sender_name = current_user.full_name or current_user.email
        await notify_mentions(
            mentioned_users=added_mentions,
            comment_id=comment_id,
            target_type="PM_ISSUE",
            target_id=issue_id,
            target_title=issue_title,
            actor_id=str(current_user.id),
            actor_name=sender_name,
            target_url=f"/pm/projects/{project_id}/board?issueId={issue_id}&commentId={comment_id}",
        )

    user = await users_col.find_one({"_id": ObjectId(current_user.id)}, {"full_name": 1, "email": 1})
    return IssueCommentOut(
        id=str(d["_id"]),
        issue_id=str(d["issue_id"]),
        author_id=str(d["author_id"]),
        author_name=user.get("full_name") or user.get("email", "") if user else "",
        content=d["content"],
        mentioned_users=new_mentioned,
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


@router.delete("/{project_id}/issues/{issue_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    project_id: str,
    issue_id: str,
    comment_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    col = MongoClientManager.get_pm_issue_comments_collection()
    old_doc = await col.find_one({"_id": ObjectId(comment_id), "author_id": ObjectId(current_user.id)})
    await col.delete_one({"_id": ObjectId(comment_id), "author_id": ObjectId(current_user.id)})
    if old_doc:
        old_display = _trunc(old_doc.get("content")) or (
            f"첨부파일 {len(old_doc.get('attachments', []))}개" if old_doc.get("attachments") else None
        )
        await record_history(ObjectId(issue_id), ObjectId(current_user.id), "comment", old_display, None)


# ── 변경이력 ───────────────────────────────────────────────────────

@router.get("/{project_id}/issues/{issue_id}/history", response_model=List[IssueHistoryOut])
async def get_issue_history(
    project_id: str,
    issue_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    await get_issue_or_404(project_id, issue_id)

    col = MongoClientManager.get_pm_issue_history_collection()
    users_col = MongoClientManager.get_users_collection()

    docs = await col.find({"issue_id": ObjectId(issue_id)}).sort("created_at", -1).to_list(None)
    result = []
    for d in docs:
        user = await users_col.find_one({"_id": d["user_id"]}, {"full_name": 1, "email": 1})
        result.append(IssueHistoryOut(
            id=str(d["_id"]),
            issue_id=str(d["issue_id"]),
            user_id=str(d["user_id"]),
            user_name=user.get("full_name") or user.get("email", "") if user else "",
            field=d["field"],
            old_value=d.get("old_value"),
            new_value=d.get("new_value"),
            created_at=d["created_at"],
        ))
    return result


# ── 라벨 ──────────────────────────────────────────────────────────

@router.get("/{project_id}/labels", response_model=List[LabelOut])
async def list_labels(project_id: str, current_user: UserPublic = Depends(get_current_user)):
    await require_pm_member(current_user, project_id)

    docs = await MongoClientManager.get_pm_labels_collection().find(
        {"project_id": ObjectId(project_id)}
    ).to_list(None)
    return [LabelOut(id=str(d["_id"]), project_id=str(d["project_id"]), name=d["name"], color=d["color"]) for d in docs]


@router.post("/{project_id}/labels", response_model=LabelOut, status_code=201)
async def create_label(
    project_id: str,
    body: LabelCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    col = MongoClientManager.get_pm_labels_collection()

    result = await col.insert_one({
        "project_id": ObjectId(project_id),
        "name": body.name,
        "color": body.color,
    })
    d = await col.find_one({"_id": result.inserted_id})
    return LabelOut(id=str(d["_id"]), project_id=str(d["project_id"]), name=d["name"], color=d["color"])


@router.patch("/{project_id}/labels/{label_id}", response_model=LabelOut)
async def update_label(
    project_id: str,
    label_id: str,
    body: LabelCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    col = MongoClientManager.get_pm_labels_collection()
    d = await col.find_one_and_update(
        {"_id": ObjectId(label_id)},
        {"$set": {"name": body.name, "color": body.color}},
        return_document=True,
    )
    if not d:
        raise HTTPException(status_code=404, detail="라벨을 찾을 수 없습니다.")
    return LabelOut(id=str(d["_id"]), project_id=str(d["project_id"]), name=d["name"], color=d["color"])


@router.delete("/{project_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(
    project_id: str,
    label_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, project_id)

    await MongoClientManager.get_pm_labels_collection().delete_one({"_id": ObjectId(label_id)})
