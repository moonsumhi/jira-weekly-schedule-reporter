"""SR 접수/상태변경 시 요청자에게 메일 발송.

Redmine(issues_controller.rb의 create_emailsend/update_emailsend)이 쓰는 사내 메일
발송 서비스를 그대로 재사용한다. 이 서비스는 SMTP를 직접 쓰지 않고, 수신자 목록과
병합용 데이터를 폼 데이터로 POST 받아 자체적으로 메일을 만들어 보낸다.

메일 서비스 자체는 Spring(Java, ServiceController#callmailTemplatePost)이지만
호출하는 쪽(레드마인)이 Ruby라서, tcpdump로 실제 성공 요청을 캡처해보니
`sendUserEmail`은 대괄호 없이 키 하나(다중 수신자는 같은 키 반복), `dataMap`은
JSON이 아니라 Ruby `Hash#to_s` 형식 문자열(`{"key"=>"value", ...}`)로 온다.
그대로 재현해서 보낸다.
"""
import asyncio
import logging
import urllib.parse
from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _sanitize_for_mail(text: str) -> str:
    """mail-service가 백슬래시(\\)+백틱(`) 조합, 그리고 줄바꿈(개행) 자체를 포함한
    요청을 404로 거부하는 것을 확인했다 (아마 방화벽/보안 필터). 마크다운 에디터에서
    인라인 코드 안 언더스코어가 자동으로 \\_ 로 이스케이프되며 백슬래시+백틱 패턴이
    흔히 생기고, 사용자가 설명/제목에 엔터를 치면 개행이 들어가므로, 메일 발송 전
    둘 다 제거·치환한다.
    """
    text = text.replace("\\", "").replace("`", "")
    text = text.replace("\r\n", " / ").replace("\n", " / ").replace("\r", " / ")
    return text


def _fmt_date(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _ruby_hash_str(data: dict[str, str]) -> str:
    """Ruby Hash#to_s 형식 문자열로 직렬화한다 (예: {"key"=>"value", ...}).

    실제 발신 측(레드마인, Ruby)이 tcpdump로 캡처한 요청에서 dataMap을 JSON이
    아니라 이 형식으로 보내는 것을 확인했다. 값에 큰따옴표가 있으면 이스케이프한다.
    """
    escaped = {k: str(v).replace('"', '\\"') for k, v in data.items()}
    parts = [f'"{k}"=>"{v}"' for k, v in escaped.items()]
    return "{" + ", ".join(parts) + "}"


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


async def _load_firewall_emails() -> list[str]:
    """관리자가 환경설정(env_categories, key=firewall_notify_emails) 화면에서 등록한
    방화벽 담당자 메일 목록을 불러온다. 활성화된 항목만 대상."""
    from app.db.mongo import MongoClientManager
    col = MongoClientManager.get_env_categories_collection()
    doc = await col.find_one({"key": "firewall_notify_emails"})
    if not doc:
        return []
    # 항목의 표시 이름(label)과 실제 발송 대상 이메일(value)을 분리해 저장하는 화면으로
    # 바뀌었지만, value 없이 label에 이메일을 직접 넣어둔 과거 데이터도 있으므로 폴백한다.
    return [
        (i.get("value") or i.get("label", "")).strip()
        for i in doc.get("items", [])
        if i.get("is_active", True) and (i.get("value") or i.get("label", "")).strip()
    ]


_MAX_RETRY_ON_404 = 3
_RETRY_DELAY_SECONDS = 2.0

_EVENT_URLS = {
    "reviewed": lambda: settings.SR_MAIL_SERVICE_URL,   # 검토 완료(승인) → Backoffice_IssueInfo 템플릿
    "assigned": lambda: settings.SR_MAIL_ASSIGN_URL,    # 담당자 배정 → issueAssign 템플릿(신규)
    "completed": lambda: settings.SR_MAIL_FINISH_URL,   # 처리완료 → Backoffice_IssueFinish 템플릿
}


async def _post_mail(url: str, recipients: list[str], data_map: dict[str, str], log_prefix: str) -> None:
    """dataMap 폼 바디를 만들어 mail-service에 POST. 404면 최대 _MAX_RETRY_ON_404회 재시도.

    실패해도 예외를 삼키고 로그만 남긴다 (호출 측의 본 작업을 막지 않기 위함).
    """
    form_items: list[tuple[str, str]] = [("sendUserEmail", r) for r in recipients]
    form_items.append(("dataMap", _ruby_hash_str(data_map)))
    # httpx 0.28의 data=list[tuple] 조합이 AsyncClient에서 비동기 스트림을 만들지 못하는
    # 버그가 있어(RuntimeError: Attempted to send an sync request...), 폼 바디를 직접
    # urlencode해서 content로 보낸다.
    body = urllib.parse.urlencode(form_items)

    logger.info("%s 메일 발송 요청 상세: url=%s body=%s", log_prefix, url, body)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for attempt in range(1, _MAX_RETRY_ON_404 + 1):
                resp = await client.post(
                    url,
                    content=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                logger.info(
                    "%s 메일 발송 요청: to=%s status_code=%s response=%s",
                    log_prefix, recipients, resp.status_code, resp.text[:500],
                )
                # 404는 mail-service가 요청을 라우팅/매칭하는 단계에서 끊긴 것으로,
                # 실제 발송 로직에 도달하지 못했다는 뜻이라 재시도해도 중복 발송이 아니다.
                if resp.status_code != 404 or attempt == _MAX_RETRY_ON_404:
                    break
                logger.warning("%s 메일 발송 404, 재시도 %s/%s", log_prefix, attempt, _MAX_RETRY_ON_404)
                await asyncio.sleep(_RETRY_DELAY_SECONDS)
    except Exception as e:
        logger.warning("%s 메일 발송 실패: %s: %s", log_prefix, type(e).__name__, e)


async def send_delayed_digest(
    to_email: str, to_name: str, sr_items: list[dict], issue_items: list[dict],
) -> None:
    """담당자 한 명에게 그날의 지연 SR/이슈 목록을 한 통으로 보낸다.

    sr_items: [{"sr_no", "title", "days_late"}, ...]
    issue_items: [{"key", "title", "days_late"}, ...]
    """
    total = len(sr_items) + len(issue_items)
    if total == 0:
        return

    # mail-service가 실제 개행 문자를 포함한 요청을 404로 거부하므로(_sanitize_for_mail 참고),
    # 줄바꿈이 아니라 " / " 구분자로 항목을 나열한다.
    lines = [f"{i['sr_no']}: {i['title']} (D+{i['days_late']})" for i in sr_items]
    lines += [f"{i['key']}: {i['title']} (D+{i['days_late']})" for i in issue_items]

    data_map = {
        "subject": _sanitize_for_mail(f"[지연 일정 알림] {to_name}님, 지연된 일정이 {total}건 있습니다"),
        "description": _sanitize_for_mail(" / ".join(lines)),
        "start_date": _fmt_date(datetime.now()),
        "adminInfo": to_name or "-",
    }
    await _post_mail(
        settings.SR_MAIL_DELAYED_DIGEST_URL, [to_email], data_map,
        log_prefix=f"지연 다이제스트(to={to_email})",
    )


async def send_sr_notification(doc: dict, event: str) -> None:
    """SR 문서(dict)를 바탕으로 요청자에게 알림 메일을 발송한다.

    event="reviewed"  → 검토 완료(승인) 메일. 수신자: 요청자
                        (단, request_type="FIREWALL"이면 환경설정에 등록된 방화벽 담당자 메일도 추가)
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

    if event == "reviewed" and doc.get("request_type") == "FIREWALL":
        for email in await _load_firewall_emails():
            if email not in recipients:
                recipients.append(email)

    if not recipients:
        logger.warning("SR 메일 발송 스킵 (수신자 없음): sr_no=%s, event=%s", doc.get("sr_no"), event)
        return

    # 방화벽 신청은 공통 description 입력란이 없고 유형별 항목인 '업무 목적'
    # (type_detail.purpose)에 내용을 적으므로, 메일 내용은 그쪽을 사용한다.
    description = doc.get("description")
    if doc.get("request_type") == "FIREWALL":
        description = (doc.get("type_detail") or {}).get("purpose") or description

    # 실제 메일 템플릿(Backoffice_IssueInfo.html, th:text)이 읽는 키만 채운다:
    # subject(제목) / description(내용) / start_date(생성일자) /
    # adminInfo(담당자) / custom_field_values(요청자) / due_date(마감일자)
    data_map = {
        "subject": _sanitize_for_mail(doc.get("title") or "-"),
        "description": _sanitize_for_mail(description or "-"),
        "start_date": _fmt_date(doc.get("created_at")),
        "adminInfo": doc.get("assignee_name") or "-",
        "custom_field_values": doc.get("requester_name") or "-",
        "due_date": _fmt_date(doc.get("desired_due_date")),
    }

    url = _EVENT_URLS.get(event, lambda: settings.SR_MAIL_SERVICE_URL)()
    await _post_mail(
        url, recipients, data_map,
        log_prefix=f"SR(sr_no={doc.get('sr_no')}, event={event})",
    )
