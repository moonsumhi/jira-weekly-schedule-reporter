"""SR 접수/상태변경 시 요청자에게 메일 발송.

Redmine(issues_controller.rb의 create_emailsend/update_emailsend)이 쓰는 사내 메일
발송 서비스를 그대로 재사용한다. 이 서비스는 SMTP를 직접 쓰지 않고, 수신자 목록과
병합용 데이터를 폼 데이터로 POST 받아 자체적으로 메일을 만들어 보낸다.
Rails 쪽이 `sendUserEmail[]=...`, `dataMap[key]=...` 형태(중첩 파라미터)로 파싱하므로
httpx에도 동일한 키 형식으로 넘겨야 한다.
"""
import logging
import urllib.parse
from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _fmt_date(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


async def _get_assignee_email(assignee_id: Any) -> str | None:
    if not assignee_id:
        return None
    from bson import ObjectId
    from app.db.mongo import MongoClientManager
    try:
        oid = assignee_id if isinstance(assignee_id, ObjectId) else ObjectId(str(assignee_id))
    except Exception:
        return None
    users = MongoClientManager.get_users_collection()
    user = await users.find_one({"_id": oid})
    return user.get("email") if user else None


_EVENT_URLS = {
    "reviewed": lambda: settings.SR_MAIL_SERVICE_URL,   # 검토 완료(승인) → Backoffice_IssueInfo 템플릿
    "assigned": lambda: settings.SR_MAIL_ASSIGN_URL,    # 담당자 배정 → issueAssign 템플릿(신규)
    "completed": lambda: settings.SR_MAIL_FINISH_URL,   # 처리완료 → Backoffice_IssueFinish 템플릿
}


async def send_sr_notification(doc: dict, event: str) -> None:
    """SR 문서(dict)를 바탕으로 요청자에게 알림 메일을 발송한다.

    event="reviewed"  → 검토 완료(승인) 메일. 수신자: 요청자
    event="assigned"  → 담당자 배정 메일 (issueAssign 템플릿, 신규). 수신자: 요청자 + 담당자
    event="completed" → 처리완료 메일. 수신자: 요청자 + 담당자

    메일 발송 실패는 SR 접수/처리 자체를 막지 않도록 예외를 삼키고 로그만 남긴다.
    """
    recipients: list[str] = []
    requester_email = doc.get("requester_email")
    if requester_email:
        recipients.append(requester_email)

    if event in ("assigned", "completed"):
        assignee_email = await _get_assignee_email(doc.get("assignee_id"))
        if assignee_email and assignee_email not in recipients:
            recipients.append(assignee_email)

    if not recipients:
        logger.warning("SR 메일 발송 스킵 (수신자 없음): sr_no=%s, event=%s", doc.get("sr_no"), event)
        return

    # 실제 메일 템플릿(Backoffice_IssueInfo.html, th:text)이 읽는 키만 채운다:
    # subject(제목) / description(내용) / start_date(생성일자) /
    # adminInfo(담당자) / custom_field_values(요청자) / due_date(마감일자)
    data_map = {
        "subject": doc.get("title") or "-",
        "description": doc.get("description") or "-",
        "start_date": _fmt_date(doc.get("created_at")),
        "adminInfo": doc.get("assignee_name") or "-",
        "custom_field_values": doc.get("requester_name") or "-",
        "due_date": _fmt_date(doc.get("desired_due_date")),
    }

    form_items: list[tuple[str, str]] = [("sendUserEmail[]", r) for r in recipients]
    form_items += [(f"dataMap[{k}]", str(v)) for k, v in data_map.items()]
    # httpx 0.28의 data=list[tuple] 조합이 AsyncClient에서 비동기 스트림을 만들지 못하는
    # 버그가 있어(RuntimeError: Attempted to send an sync request...), 폼 바디를 직접
    # urlencode해서 content로 보낸다 (Rails 쪽은 sendUserEmail[]/dataMap[key] 중첩 표기를 기대함).
    body = urllib.parse.urlencode(form_items)
    url = _EVENT_URLS.get(event, lambda: settings.SR_MAIL_SERVICE_URL)()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                url,
                content=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            logger.info(
                "SR 메일 발송 요청: sr_no=%s event=%s to=%s status_code=%s",
                doc.get("sr_no"), event, recipients, resp.status_code,
            )
    except Exception as e:
        logger.warning(
            "SR 메일 발송 실패 (sr_no=%s, event=%s): %s: %s",
            doc.get("sr_no"), event, type(e).__name__, e,
        )
