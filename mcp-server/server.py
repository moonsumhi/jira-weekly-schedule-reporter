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
def list_assets(category: str = "서버", limit: int = 50) -> str:
    """
    자산 목록을 조회합니다.
    category: 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware
    """
    col = ASSET_COLLECTIONS.get(category, "assets_servers")
    docs = list(db[col].find(
        {"is_deleted": {"$ne": True}},
        {"_id": 1, "name": 1, "ip": 1, "asset_id": 1, "asset_no": 1, "fields": 1, "updated_at": 1}
    ).limit(limit))
    return _dump(docs)


def _asset_field_keys(category: str, sample: int = 200) -> list[str]:
    """해당 유형 기존 자산들이 fields에 실제로 쓰는 키를, 자주 쓰인 순으로 반환한다."""
    col = ASSET_COLLECTIONS.get(category)
    if not col:
        return []
    counts: dict[str, int] = {}
    for doc in db[col].find({"is_deleted": {"$ne": True}}, {"fields": 1}).limit(sample):
        for k in (doc.get("fields") or {}):
            counts[k] = counts.get(k, 0) + 1
    return sorted(counts, key=lambda k: -counts[k])


def _asset_schema(category: str) -> dict:
    """create_asset 입력에 참고할 스키마(고정 필드 + 기존 fields 키)."""
    return {
        "category": category,
        "top_level_fields": {
            "name": "자산 이름 (필수)",
            "ip": "IP 주소",
            "asset_id": "유형별 고유 PK (중복 방지용, 있으면 채움)",
            "asset_no": "자산번호",
        },
        "field_keys": _asset_field_keys(category),  # fields dict에 쓰는 키 (기존 자산 기준)
        "note": "fields에는 위 field_keys를 참고해 {키:값}으로 넣으세요. 해당 없는 값은 생략.",
    }


@mcp.tool()
def get_asset_schema(category: str = "서버") -> str:
    """자산 등록(create_asset) 전에, 해당 유형이 어떤 필드를 쓰는지 알려줍니다.

    category: 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware
    기존 자산들이 실제로 쓰는 fields 키 목록을 돌려주니, 그 키에 맞춰 create_asset의
    fields를 구성하세요.
    """
    if category not in ASSET_COLLECTIONS:
        return _dump({"error": f"알 수 없는 category '{category}'. 사용 가능: {', '.join(ASSET_COLLECTIONS)}"})
    return _dump(_asset_schema(category))


@mcp.tool()
def create_asset(
    category: str,
    name: str,
    ip: str = "",
    asset_id: str = "",
    asset_no: str = "",
    fields: dict | str | None = None,
) -> str:
    """자산을 백오피스에 등록합니다. (서버·네트워크·보안장비·DBMS·VMware 등 모든 유형)

    사람이 붙여넣은 장비 정보를 파싱해서 호출하세요.

    category : 자산 유형 (필수) — 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware
    name     : 자산 이름 (필수)
    ip       : IP 주소 (없으면 비워둠)
    asset_id : 유형별 고유 PK. 재등록 시 중복 방지에 쓰이므로 고유 식별자를 알면 채우세요.
    asset_no : 자산번호 (있으면)
    fields   : 그 외 나머지 속성 전부를 {키: 값} 형태로. 어떤 키로 넣을지는 붙여넣은
               정보의 항목명에 맞춰 자유롭게 판단하세요. (한글 키 권장)
               필드 키가 애매하면 먼저 get_asset_schema(category)로 기존 자산이 쓰는
               필드 키를 확인하고 그에 맞추면 됩니다.

    성공 시 생성된 자산 정보를 반환합니다. 실패 시 사유와 함께 schema_hint(사용 가능한
    필드 정보)를 돌려주니, 그걸 참고해 fields를 고쳐서 다시 호출하세요.
    """
    if category not in ASSET_COLLECTIONS:
        return _dump({
            "ok": False,
            "error": f"알 수 없는 category '{category}'. 사용 가능: {', '.join(ASSET_COLLECTIONS)}",
        })

    # 약한 LLM이 fields를 dict가 아니라 JSON 문자열로 넘기는 경우가 많아 관대하게 파싱한다.
    if isinstance(fields, str):
        try:
            fields = json.loads(fields) if fields.strip() else {}
        except (json.JSONDecodeError, ValueError):
            return _dump({
                "ok": False,
                "error": f"fields 를 JSON 객체로 파싱하지 못했습니다: {fields[:200]}",
                "schema_hint": _asset_schema(category),
                "note": "fields 는 {\"키\":\"값\"} 형태의 JSON 객체여야 합니다. schema_hint 를 참고해 다시 호출하세요.",
            })
    if not isinstance(fields, dict):
        fields = {}

    merged_fields: dict = dict(fields)
    merged_fields.setdefault("자산유형", category)

    body = {
        "ip": ip,
        "name": name,
        "asset_id": asset_id or None,
        "asset_no": asset_no or None,
        "fields": merged_fields,
    }
    try:
        resp = _backend_post(
            "/assets", body, params={"category": category, "source": "mcp"}
        )
    except Exception as e:
        return _dump({"ok": False, "error": f"백엔드 호출 실패: {type(e).__name__}: {e}"})

    if resp.status_code in (200, 201):
        return _dump({"ok": True, "asset": resp.json()})
    if resp.status_code == 409:
        return _dump({
            "ok": False,
            "error": "이미 존재하는 자산입니다(중복). asset_id 또는 IP가 기존 자산과 겹칩니다. "
                     "재시도하지 말고 사용자에게 알리거나, 다른 자산이면 값을 바꿔 호출하세요.",
            "detail": resp.text[:300],
        })
    # 검증오류(422/400 등) — LLM이 스키마를 몰라 헤매지 않도록 사용 가능한 필드 정보를 함께 준다.
    return _dump({
        "ok": False,
        "status": resp.status_code,
        "error": resp.text[:300],
        "schema_hint": _asset_schema(category),
        "note": "위 schema_hint의 필드에 맞춰 입력을 고쳐서 다시 호출하세요.",
    })


@mcp.tool()
def search_assets(query: str, category: str = "서버") -> str:
    """
    자산을 이름·IP·자산ID로 검색합니다.
    category: 서버 | 네트워크 | 정보보호시스템 | DBMS | VMware
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
    docs = list(db[col].find(flt).limit(20))
    return _dump(docs)


@mcp.tool()
def get_asset(asset_db_id: str, category: str = "서버") -> str:
    """
    자산 상세 정보와 변경 이력을 조회합니다.
    asset_db_id: list_assets 결과의 id 값
    """
    col = ASSET_COLLECTIONS.get(category, "assets_servers")
    hist_col = col + "_history"
    doc = db[col].find_one({"_id": ObjectId(asset_db_id)})
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
def list_service_requests(status: str = None, assignee: str = None, limit: int = 30) -> str:
    """
    서비스 요청(SR) 목록을 조회합니다.
    status: OPEN | IN_PROGRESS | DONE | CLOSED 등
    """
    flt: dict = {}
    if status:
        flt["status"] = status
    if assignee:
        flt["assignee"] = {"$regex": assignee, "$options": "i"}
    docs = list(db["service_requests"].find(flt, {
        "_id": 1, "sr_id": 1, "title": 1, "status": 1,
        "requester": 1, "assignee": 1, "type": 1, "created_at": 1,
    }).sort("created_at", -1).limit(limit))
    return _dump(docs)


@mcp.tool()
def get_service_request(sr_id: str) -> str:
    """SR 상세 정보를 조회합니다. sr_id는 SR-2026-0001 형식 또는 DB ObjectId 모두 가능합니다."""
    if len(sr_id) == 24:
        doc = db["service_requests"].find_one({"_id": ObjectId(sr_id)})
    else:
        doc = db["service_requests"].find_one({"sr_id": sr_id})
    return _dump(doc)


# ── ISMS-P ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_vulnerabilities(
    risk_level: str = None,
    action_status: str = None,
    assignee: str = None,
    limit: int = 30,
) -> str:
    """
    ISMS-P 취약점 목록을 조회합니다.
    risk_level: 상 | 중 | 하
    action_status: 미조치 | 조치완료 | 접속불가 등
    """
    flt: dict = {}
    if risk_level:
        flt["risk_level"] = risk_level
    if action_status:
        flt["action_status"] = action_status
    if assignee:
        flt["assignee"] = {"$regex": assignee, "$options": "i"}
    docs = list(db["isms_vulnerabilities"].find(flt, {
        "_id": 1, "asset_name": 1, "ip_address": 1, "check_item": 1,
        "risk_level": 1, "action_status": 1, "assignee": 1, "planned_date": 1,
    }).limit(limit))
    return _dump(docs)


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
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.run(transport="sse")
