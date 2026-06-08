"""
GET-intercepting middleware that logs page views to activity_logs.
Each (user, page) combination is deduplicated with a 5-minute cooldown.
"""
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_token
from app.db.mongo import MongoClientManager

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


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Only log successful GET requests
        if request.method != "GET" or response.status_code >= 400:
            return response

        query_params = dict(request.query_params)
        page = _match_page(request.url.path, query_params)
        if not page:
            return response

        token = _extract_token(request)
        if not token:
            return response

        email = decode_token(token)
        if not email:
            return response

        now = datetime.now(timezone.utc)
        key = (email, page)
        last = _cache.get(key)
        if last and (now - last) < _COOLDOWN:
            return response

        _cache[key] = now

        try:
            col = MongoClientManager.get_activity_logs_collection()
            await col.insert_one({
                "action": "VIEW",
                "changed_at": now,
                "changed_by": email,
                "diff": [{"path": "페이지", "before": None, "after": page}],
            })
        except Exception:
            pass  # never break the actual request

        return response
