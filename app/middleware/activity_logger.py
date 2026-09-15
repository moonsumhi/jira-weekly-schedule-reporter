"""
Middleware that logs selected page views and successful SR/PM mutations to
activity_logs. Page views are deduplicated with a 5-minute cooldown; mutations
are recorded for every successful request.
"""
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_token
from app.db.mongo import MongoClientManager

logger = logging.getLogger(__name__)


def _business_category(path: str) -> Optional[str]:
    if re.match(r"^/(?:admin/)?schedule/service-requests(?:/|$)", path):
        return "SR"
    if re.match(r"^/pm(?:/|$)", path):
        return "스케줄 관리"
    return None

# Only log the list-level GET, not individual resource fetches.
# Returns (page_name) or None.
def _match_page(path: str, query_params: dict) -> Optional[str]:
    # 자산 목록: GET /assets  (no extra path segments = list endpoint)
    if re.match(r"^/assets$", path):
        cat = query_params.get("category", "서버")
        return {
            "서버":          "서버 자산",
            "네트워크":      "네트워크 자산",
            "정보보호시스템": "정보보호시스템 자산",
            "DBMS":          "DBMS 자산",
            "VMware":        "VMware 자산",
        }.get(cat, "자산 목록")

    _RULES: list[tuple[re.Pattern, str]] = [
        (re.compile(r"^/auth/home-ping$"),          "메인 페이지"),
        (re.compile(r"^/form-entries$"),           "작업 관리"),
        (re.compile(r"^/watch$"),                  "당직 시간표"),
        (re.compile(r"^/inspection$"),             "서버실 점검"),
        (re.compile(r"^/issues/today-tasks"),      "Jira 검색"),
        (re.compile(r"^/boards/[^/]+/posts$"),     "게시판"),
        (re.compile(r"^/admin/audit-log$"),        "Audit Log"),
        (re.compile(r"^/admin/users$"),            "회원 관리"),
    ]
    for pattern, name in _RULES:
        if pattern.match(path):
            return name
    return None


# Dedup cache: (email, page) -> last logged datetime
_cache: dict[tuple[str, str], datetime] = {}
_COOLDOWN = timedelta(minutes=5)

_SENSITIVE_KEY_PARTS = (
    "password", "passwd", "token", "secret", "authorization", "api_key", "access_key",
)


def _audit_value(value: Any, key: str = "", depth: int = 0) -> Any:
    """Return a bounded, non-sensitive representation for an audit diff."""
    key_lower = key.casefold()
    if any(part in key_lower for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if depth >= 3:
        return "[…]"
    if isinstance(value, dict):
        items = list(value.items())[:30]
        result = {str(k): _audit_value(v, str(k), depth + 1) for k, v in items}
        if len(value) > len(items):
            result["…"] = f"{len(value) - len(items)}개 항목 생략"
        return result
    if isinstance(value, list):
        values = [_audit_value(v, key, depth + 1) for v in value[:20]]
        if len(value) > len(values):
            values.append(f"… {len(value) - len(values)}개 항목 생략")
        return values
    if isinstance(value, str) and len(value) > 1000:
        return f"{value[:1000]}… (이하 생략)"
    return value


def _payload_diff(payload: Any, query_params: dict[str, str]) -> list[dict[str, Any]]:
    diff: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            diff.append({
                "path": f"입력.{key}",
                "before": None,
                "after": _audit_value(value, str(key)),
            })
    elif payload is not None:
        diff.append({"path": "입력", "before": None, "after": _audit_value(payload)})

    for key, value in query_params.items():
        if isinstance(payload, dict) and key in payload:
            continue
        diff.append({
            "path": f"쿼리.{key}",
            "before": None,
            "after": _audit_value(value, key),
        })
    return diff


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/") or "/"
        category = _business_category(path)
        mutation = category and request.method in {"POST", "PUT", "PATCH", "DELETE"}

        # Read JSON before the downstream handler and replay the same bytes so
        # FastAPI can parse the request normally. Multipart uploads are left
        # untouched; their audit entry still includes the route and query data.
        payload: Any = None
        if mutation and request.headers.get("content-type", "").split(";", 1)[0].lower() == "application/json":
            try:
                raw_body = await request.body()
                if raw_body:
                    try:
                        payload = json.loads(raw_body)
                    except (TypeError, ValueError):
                        payload = None

                    body_sent = False

                    async def receive() -> dict[str, Any]:
                        nonlocal body_sent
                        if body_sent:
                            return {"type": "http.request", "body": b"", "more_body": False}
                        body_sent = True
                        return {"type": "http.request", "body": raw_body, "more_body": False}

                    request = Request(request.scope, receive)
            except Exception:
                logger.exception("감사 로그 요청 본문 확인 실패: %s %s", request.method, path)

        response = await call_next(request)

        if not 200 <= response.status_code < 300:
            return response

        query_params = dict(request.query_params)
        page = _match_page(path, query_params) if request.method == "GET" else None
        # Record the primary SR/PM resource fetches, not polling subrequests.
        if category and request.method == "GET" and re.fullmatch(
            r"/(?:admin/)?schedule/service-requests(?:/[a-fA-F0-9]{24})?"
            r"|/pm/(?:organizations|projects|weekly-reports|monthly-reports|recurring-issue-templates)(?:/[a-fA-F0-9]{24})?"
            r"|/pm/projects/[a-fA-F0-9]{24}/(?:issues|sprints)(?:/[a-fA-F0-9]{24})?", path
        ):
            page = category
        if mutation:
            page = category
        if not page:
            return response

        token = _extract_token(request)
        if not token:
            return response

        email = decode_token(token)
        if not email:
            return response

        now = datetime.now(timezone.utc)
        key = (email, path if category else page)
        last = _cache.get(key)
        if not mutation and last and (now - last) < _COOLDOWN:
            return response

        try:
            col = MongoClientManager.get_activity_logs_collection()
            action = "VIEW"
            if mutation:
                action = "DELETE" if request.method == "DELETE" else (
                    "CREATE" if response.status_code == 201 else "UPDATE"
                )
            route = request.scope.get("route")
            diff = [
                {"path": "페이지", "before": None, "after": page},
                {"path": "동작", "before": None, "after": getattr(route, "name", request.method)},
            ]
            if mutation:
                diff.extend(_payload_diff(payload, query_params))
            await col.insert_one({
                "action": action,
                "category": category or "활동",
                "asset_id": next((str(v) for k, v in reversed(list(request.path_params.items())) if k.endswith("_id")), ""),
                "source": f"{request.method} {path}",
                "changed_at": now,
                "changed_by": email,
                "diff": diff,
            })
            if not mutation:
                _cache[key] = now
        except Exception:
            logger.exception("활동 감사 로그 저장 실패: %s %s", request.method, path)

        return response
