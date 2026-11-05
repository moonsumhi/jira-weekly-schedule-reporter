import json
import os
from datetime import datetime

import httpx
from bson import ObjectId
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("APP_DB_NAME")

_client = MongoClient(MONGO_URI)
db = _client[DB_NAME]

# ── 백엔드 API 클라이언트 (쓰기 작업용) ────────────────────────────────────────
# MCP엔 로그인 유저가 없으므로 전용 서비스 계정으로 로그인해 JWT를 얻어 쓰기 API를
# 호출한다. Mongo 직접 쓰기 대신 백엔드 API를 재사용해 중복검사·감사로그·검증을 그대로 탄다.
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8000").rstrip("/")
MCP_SVC_EMAIL = os.getenv("MCP_SVC_EMAIL")
MCP_SVC_PASSWORD = os.getenv("MCP_SVC_PASSWORD")

_token_cache: dict[str, str | None] = {"token": None}


def _login() -> str:
    if not MCP_SVC_EMAIL or not MCP_SVC_PASSWORD:
        raise RuntimeError("서비스 계정 미설정 (MCP_SVC_EMAIL / MCP_SVC_PASSWORD 환경변수 필요)")
    resp = httpx.post(
        f"{BACKEND_API_URL}/auth/login",
        data={"username": MCP_SVC_EMAIL, "password": MCP_SVC_PASSWORD},
        timeout=10.0,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _token_cache["token"] = token
    return token


def _backend_post(path: str, json_body: dict, params: dict | None = None) -> httpx.Response:
    """JWT를 붙여 백엔드에 POST. 토큰이 없거나 401이면 재로그인 후 1회 재시도."""
    token = _token_cache["token"] or _login()
    url = f"{BACKEND_API_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.post(url, json=json_body, params=params, headers=headers, timeout=15.0)
    if resp.status_code == 401:
        token = _login()
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(url, json=json_body, params=params, headers=headers, timeout=15.0)
    return resp

def _backend_get(path: str) -> httpx.Response:
    token = _token_cache["token"] or _login()
    url = f"{BACKEND_API_URL}{path}"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    if resp.status_code == 401:
        token = _login()
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    return resp


# 내부망 배포 — DNS rebinding 보호를 끄지 않으면 외부 서버(LibreChat 등) 요청이 421로 거부된다.
mcp = FastMCP(
    "백오피스",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)

ASSET_COLLECTIONS = {
    "서버": "assets_servers",
    "네트워크": "assets_network",
    "정보보호시스템": "assets_security",
    "DBMS": "assets_dbms",
    "VMware": "assets_vmware",
}


def _serialize(obj):
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = "id" if k == "_id" else k
            out[key] = _serialize(v)
        return out
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _dump(docs) -> str:
    return json.dumps(_serialize(docs), ensure_ascii=False, indent=2)


# ── 자산 ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_assets(category: str = "서버", limit: int = 100, skip: int = 0) -> str:
    """
    자산 목록을 조회합니다.
    category: 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware

    total(전체 개수)과 items(이번 페이지)를 함께 반환합니다. has_more 가 true면
    아직 더 있는 것이므로 skip 을 늘려(예: skip=100) 다음 페이지를 이어서 조회하세요.
    사용자에게 답할 때는 total 기준으로 "전체 N건 중 …"임을 밝히세요.
    """
    col = ASSET_COLLECTIONS.get(category, "assets_servers")
    q = {"is_deleted": {"$ne": True}}
    total = db[col].count_documents(q)
    docs = list(db[col].find(
        q,
        {"_id": 1, "name": 1, "ip": 1, "asset_id": 1, "asset_no": 1, "fields": 1, "updated_at": 1}
    ).skip(skip).limit(limit))
    return _dump({
        "category": category,
        "total": total,
        "returned": len(docs),
        "skip": skip,
        "has_more": skip + len(docs) < total,
        "items": docs,
    })


@mcp.tool()
def get_asset_schema(category: str = "서버") -> str:
    """자산 등록에 필요한 실제 백오피스 입력 스키마와 유형별 필수값을 조회합니다.

    category: 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware.
    응답의 schema는 system_info의 CPU·메모리·디스크·하드웨어·네트워크 필드,
    타입, 범위와 허용값을 포함합니다. system_info는 서버 유형에서만 입력합니다.
    요청하기 전 확인해 누락된 필수 항목을 사용자에게 물어보세요.
    """
    if category not in ASSET_COLLECTIONS:
        return _dump({"error": f"알 수 없는 category '{category}'. 사용 가능: {', '.join(ASSET_COLLECTIONS)}"})
    try:
        response = _backend_get('/assets/mcp-schema')
        response.raise_for_status()
        return _dump({'category': category, **response.json()})
    except Exception as exc:
        return _dump({'error': f'자산 등록 스키마를 불러오지 못했습니다: {type(exc).__name__}: {exc}'})


@mcp.tool()
def create_asset(
    category: str,
    name: str,
    ip: str = "",
    asset_id: str = "",
    asset_no: str = "",
    fields: dict | str | None = None,
    system_info: dict | str | None = None,
    db_series: str = "",
    confirm_duplicate_ip: bool = False,
) -> str:
    """자산을 등록하고 관리자 전용 롤백 이력을 남깁니다.

    먼저 get_asset_schema(category)로 필수 항목과 system_info 스키마를 확인하세요.
    category: 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware. 랙 배치는 지원하지 않습니다.
    name: 호스트명, ip: IP, asset_no: 자산번호 (모두 필수). asset_id는 고유 식별자(선택).
    fields: 구분, 서버명(자산명), 설명, 운영체제(배포판/기종/DB 종류)가 필수인 JSON 객체.
    DBMS는 fields.version 또는 db_series가 필요하며 정보보호시스템은 fields.제조사가 필요합니다.
    system_info: 서버에만 사용하는 JSON 객체. 스키마의 camelCase와 snake_case 모두 허용합니다.
      cpu, memory, memory_modules, disks,
    hardware, network_interfaces, notes의 세부 키와 제약은 get_asset_schema에서 확인하세요.
    EoS/EoL은 백엔드가 검증된 근거로 자동 계산하며, 근거가 없으면 확인 필요로 남깁니다.
    동일 유형 IP가 이미 있으면 기존 후보를 알려줍니다. 사용자에게 명시적으로 확인받은
    경우에만 confirm_duplicate_ip=true로 다시 요청하세요. 자산 ID 중복은 등록할 수 없습니다.
    등록 결과의 batch_id는 백오피스 관리자가 해당 건을 되돌릴 때 사용할 수 있습니다.
    네트워크 오류나 응답 유실 시 재시도 전에 먼저 기존 자산과 등록 이력을 확인하세요.
    """
    if category not in ASSET_COLLECTIONS:
        return _dump({'ok': False, 'error': f"알 수 없는 category '{category}'. 사용 가능: {', '.join(ASSET_COLLECTIONS)}"})

    def parse_object(value, label):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                raise ValueError(f'{label}은 JSON 객체여야 합니다.')
        if not isinstance(value, dict):
            raise ValueError(f'{label}은 JSON 객체여야 합니다.')
        return value

    try:
        fields = parse_object(fields, 'fields') or {}
        system_info = parse_object(system_info, 'system_info')
    except ValueError as exc:
        return _dump({'ok': False, 'error': str(exc), 'note': 'get_asset_schema로 입력 형식을 확인하세요.'})
    body = {'category': category, 'name': name, 'ip': ip, 'asset_id': asset_id or None,
            'asset_no': asset_no, 'fields': fields, 'system_info': system_info,
            'db_series': db_series or None, 'confirm_duplicate_ip': confirm_duplicate_ip}
    try:
        resp = _backend_post('/assets/mcp-create', body)
    except Exception as exc:
        return _dump({'ok': False, 'error': f'백엔드 호출 실패: {type(exc).__name__}: {exc}',
                      'note': '응답 유실 가능성이 있으므로 재시도 전에 기존 자산과 등록 이력을 확인하세요.'})
    if resp.status_code in (200, 201):
        return _dump({'ok': True, **resp.json()})
    try:
        detail = resp.json().get('detail', resp.text[:500])
    except (ValueError, AttributeError):
        detail = resp.text[:500]
    return _dump({'ok': False, 'status': resp.status_code, 'detail': detail,
                  'note': '중복 IP는 사용자에게 확인받은 경우에만 confirm_duplicate_ip=true로 재요청하세요.' if isinstance(detail, dict) and detail.get('code') == 'DUPLICATE_IP' else 'get_asset_schema로 필수 항목과 입력 형식을 확인하세요.'})


@mcp.tool()
def search_assets(query: str, category: str = "서버", limit: int = 100, skip: int = 0) -> str:
    """
    자산을 이름·IP·자산ID로 검색합니다.
    category: 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware

    total(조건에 맞는 전체 개수)과 items(이번 페이지)를 함께 반환합니다.
    has_more 가 true면 skip 을 늘려 다음 페이지를 이어서 조회하세요.
    """
    col = ASSET_COLLECTIONS.get(category, "assets_servers")
    flt = {
        "is_deleted": {"$ne": True},
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"ip": {"$regex": query, "$options": "i"}},
            {"asset_id": {"$regex": query, "$options": "i"}},
        ],
    }
    total = db[col].count_documents(flt)
    docs = list(db[col].find(flt, {'_import_journals': 0, '_rollback_asset_id': 0}).skip(skip).limit(limit))
    return _dump({
        "category": category,
        "query": query,
        "total": total,
        "returned": len(docs),
        "skip": skip,
        "has_more": skip + len(docs) < total,
        "items": docs,
    })


@mcp.tool()
def get_asset(asset_db_id: str, category: str = "서버") -> str:
    """
    자산 상세 정보와 변경 이력을 조회합니다.
    asset_db_id: list_assets 결과의 id 값
    """
    col = ASSET_COLLECTIONS.get(category, "assets_servers")
    hist_col = "assets_server_history" if col == "assets_servers" else col + "_history"
    doc = db[col].find_one({"_id": ObjectId(asset_db_id)}, {"_import_journals": 0, "_rollback_asset_id": 0})
    history = list(db[hist_col].find({"asset_id": asset_db_id}).sort("changed_at", -1).limit(10))
    return _dump({"asset": doc, "history": history})


# ── PM 이슈 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_projects() -> str:
    """PM 프로젝트 목록을 조회합니다."""
    docs = list(db["pm_projects"].find(
        {},
        {"_id": 1, "name": 1, "key": 1, "description": 1, "status": 1}
    ).limit(50))
    return _dump(docs)


@mcp.tool()
def get_project_status(project_id: str) -> str:
    """프로젝트의 이슈 상태별 현황을 조회합니다."""
    pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    result = list(db["pm_issues"].aggregate(pipeline))
    return _dump(result)


@mcp.tool()
def list_issues(
    project_id: str = None,
    status: str = None,
    assignee_name: str = None,
    issue_type: str = None,
    limit: int = 30,
) -> str:
    """
    이슈 목록을 조회합니다.
    status: BACKLOG | TODO | IN_PROGRESS | DONE
    issue_type: EPIC | STORY | TASK | BUG | SUB_TASK
    """
    flt: dict = {}
    if project_id:
        flt["project_id"] = project_id
    if status:
        flt["status"] = status
    if assignee_name:
        flt["assignee_name"] = {"$regex": assignee_name, "$options": "i"}
    if issue_type:
        flt["type"] = issue_type
    docs = list(db["pm_issues"].find(flt, {
        "_id": 1, "number": 1, "title": 1, "status": 1, "type": 1,
        "priority": 1, "assignee_name": 1, "due_date": 1,
        "story_points": 1, "effort_md": 1,
    }).sort("number", -1).limit(limit))
    return _dump(docs)


@mcp.tool()
def search_issues(query: str, project_id: str = None, limit: int = 20) -> str:
    """이슈를 제목·설명으로 검색합니다."""
    flt: dict = {"$or": [
        {"title": {"$regex": query, "$options": "i"}},
        {"description": {"$regex": query, "$options": "i"}},
    ]}
    if project_id:
        flt["project_id"] = project_id
    docs = list(db["pm_issues"].find(flt, {
        "_id": 1, "number": 1, "title": 1, "status": 1,
        "assignee_name": 1, "type": 1,
    }).limit(limit))
    return _dump(docs)


# ── 주간보고 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_weekly_reports(limit: int = 10) -> str:
    """주간보고 목록을 조회합니다."""
    docs = list(db["pm_weekly_reports"].find({}, {
        "_id": 1, "week_label": 1, "status": 1, "created_at": 1, "org_id": 1,
    }).sort("created_at", -1).limit(limit))
    return _dump(docs)


@mcp.tool()
def get_weekly_report(report_id: str) -> str:
    """주간보고 상세(수기 항목 포함)를 조회합니다."""
    doc = db["pm_weekly_reports"].find_one({"_id": ObjectId(report_id)})
    return _dump(doc)


# ── SR ───────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_service_requests(status: str = None, assignee: str = None, requester: str = None, limit: int = 30) -> str:
    """
    서비스 요청(SR) 목록을 조회합니다.
    status: SUBMITTED | REVIEWING | APPROVED | IN_PROGRESS | ON_HOLD | COMPLETED | CONFIRMING | CLOSED | REJECTED | CANCELLED
    assignee: 담당자 이름 (부분일치)
    requester: 요청자 이름 (부분일치)
    """
    flt: dict = {"deleted_at": None}
    if status:
        flt["status"] = status
    if assignee:
        flt["assignee_name"] = {"$regex": assignee, "$options": "i"}
    if requester:
        flt["requester_name"] = {"$regex": requester, "$options": "i"}
    docs = list(db["service_requests"].find(flt, {
        "_id": 1, "sr_no": 1, "title": 1, "status": 1,
        "requester_name": 1, "assignee_name": 1, "request_type": 1, "created_at": 1,
    }).sort("created_at", -1).limit(limit))
    return _dump(docs)


@mcp.tool()
def get_service_request(sr_id: str) -> str:
    """SR 상세 정보를 조회합니다. sr_id는 SR-2026-0001 형식 또는 DB ObjectId 모두 가능합니다."""
    if len(sr_id) == 24:
        doc = db["service_requests"].find_one({"_id": ObjectId(sr_id)})
    else:
        doc = db["service_requests"].find_one({"sr_no": sr_id})
    return _dump(doc)


# ── Watch ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_watch_assignments(limit: int = 20) -> str:
    """워치(당직) 배정 목록을 조회합니다."""
    docs = list(db["watch_assignments"].find(
        {},
        {"_id": 1, "date": 1, "assignee": 1, "type": 1, "note": 1}
    ).sort("date", -1).limit(limit))
    return _dump(docs)


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8002"))
    mcp.settings.host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp.settings.port = port
    mcp.run(transport="sse")
