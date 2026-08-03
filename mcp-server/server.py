import json
import os
from datetime import datetime

from bson import ObjectId
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("APP_DB_NAME")

_client = MongoClient(MONGO_URI)
db = _client[DB_NAME]

mcp = FastMCP("백오피스")

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
