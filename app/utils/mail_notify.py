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
from app.models.sr.service_request import SR_STATUS_LABEL, REQUEST_TYPE_LABEL

logger = logging.getLogger(__name__)


def _fmt_date(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


async def send_sr_notification(doc: dict, event: str) -> None:
    """SR 문서(dict)를 바탕으로 요청자에게 알림 메일을 발송한다.

    메일 발송 실패는 SR 접수/처리 자체를 막지 않도록 예외를 삼키고 로그만 남긴다.
    """
    email = doc.get("requester_email")
    if not email:
        logger.warning("SR 메일 발송 스킵 (요청자 이메일 없음): sr_no=%s", doc.get("sr_no"))
        return

    status = doc.get("status", "")
    data_map = {
        "id": str(doc.get("_id", "")),
        "sr_no": doc.get("sr_no", ""),
        "subject": doc.get("title") or "-",
        "description": doc.get("description") or "-",
        "status": SR_STATUS_LABEL.get(status, status),
        "tracker": REQUEST_TYPE_LABEL.get(doc.get("request_type", ""), doc.get("request_type", "")),
        "author": doc.get("requester_name") or "-",
        "requestor": doc.get("requester_name") or "-",
        "assigned_to": doc.get("assignee_name") or "-",
        "adminInfo": doc.get("assignee_name") or "-",
        "start_date": _fmt_date(doc.get("created_at")),
        "due_date": _fmt_date(doc.get("desired_due_date")),
        "event": event,
    }

    form_items: list[tuple[str, str]] = [("sendUserEmail[]", email)]
    form_items += [(f"dataMap[{k}]", str(v)) for k, v in data_map.items()]
    # httpx 0.28의 data=list[tuple] 조합이 AsyncClient에서 비동기 스트림을 만들지 못하는
    # 버그가 있어(RuntimeError: Attempted to send an sync request...), 폼 바디를 직접
    # urlencode해서 content로 보낸다 (Rails 쪽은 sendUserEmail[]/dataMap[key] 중첩 표기를 기대함).
    body = urllib.parse.urlencode(form_items)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                settings.SR_MAIL_SERVICE_URL,
                content=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            logger.info(
                "SR 메일 발송 요청: sr_no=%s event=%s to=%s status_code=%s",
                doc.get("sr_no"), event, email, resp.status_code,
            )
    except Exception as e:
        logger.warning(
            "SR 메일 발송 실패 (sr_no=%s, event=%s): %s: %s",
            doc.get("sr_no"), event, type(e).__name__, e,
        )
