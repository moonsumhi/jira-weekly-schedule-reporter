from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.core.config import settings


class MongoClientManager:
    _client: Optional[AsyncIOMotorClient] = None

    # Collection name constants
    USERS = "users"
    PENDING_USERS = "pending_users"
    ASSETS_SERVERS = "assets_servers"
    ASSETS_SERVER_HISTORY = "assets_server_history"
    ASSETS_NETWORK = "assets_network"
    ASSETS_NETWORK_HISTORY = "assets_network_history"
    ASSETS_SECURITY = "assets_security"
    ASSETS_SECURITY_HISTORY = "assets_security_history"
    ASSETS_DBMS = "assets_dbms"
    ASSETS_DBMS_HISTORY = "assets_dbms_history"
    ASSETS_VMWARE = "assets_vmware"
    ASSETS_VMWARE_HISTORY = "assets_vmware_history"
    ASSETS_RACKS = "assets_racks"
    ASSETS_RACKS_HISTORY = "assets_racks_history"
    WATCH_ASSIGNMENTS = "watch_assignments"
    WATCH_HISTORY = "watch_history"

    # 랙 물리 배치(어느 자산이 어느 랙의 몇 U에 있는지)의 단일 원본과 이력.
    # 자산 문서에 rack_id/U를 중복 저장하지 않고 여기서만 관리한다.
    RACK_PLACEMENTS = "rack_placements"
    RACK_PLACEMENTS_HISTORY = "rack_placements_history"

    # 카테고리 → (자산 컬렉션, 이력 컬렉션) 매핑
    CATEGORY_COLLECTIONS: dict = {
        "서버":         (ASSETS_SERVERS,  ASSETS_SERVER_HISTORY),
        "네트워크":     (ASSETS_NETWORK,  ASSETS_NETWORK_HISTORY),
        "정보보호시스템": (ASSETS_SECURITY, ASSETS_SECURITY_HISTORY),
        "DBMS":        (ASSETS_DBMS,     ASSETS_DBMS_HISTORY),
        "VMware":      (ASSETS_VMWARE,   ASSETS_VMWARE_HISTORY),
        "랙":          (ASSETS_RACKS,    ASSETS_RACKS_HISTORY),
    }

    # 카테고리별 랙 배치 성격. placement_mode:
    #   RACK_U   — 물리적으로 랙 U를 직접 점유(서버·네트워크·정보보호시스템)
    #   ROOM     — 서버실 단위 배치(랙 자신)
    #   VIA_HOST — 논리 자산이라 호스트 물리서버 위치를 따름(DBMS·VMware)
    ASSET_CATEGORY_CONFIG: dict = {
        "서버":         {"placement_mode": "RACK_U",   "default_u_height": 2},
        "네트워크":     {"placement_mode": "RACK_U",   "default_u_height": 1},
        "정보보호시스템": {"placement_mode": "RACK_U",   "default_u_height": 1},
        "DBMS":        {"placement_mode": "VIA_HOST"},
        "VMware":      {"placement_mode": "VIA_HOST"},
        "랙":          {"placement_mode": "ROOM"},
    }
    PILOT_POLL_STATE = "pilot_poll_state"
    DELAYED_DIGEST_STATE = "delayed_digest_state"
    JOB_PLANS = "job_plans"
    JOB_PLANS_HISTORY = "job_plans_history"
    JOB_NON_SERVICE_PLANS = "job_non_service_plans"
    JOB_NON_SERVICE_PLANS_HISTORY = "job_non_service_plans_history"
    JOB_RESULTS = "job_results"
    JOB_RESULTS_HISTORY = "job_results_history"
    FORM_TEMPLATES = "form_templates"
    FORM_ENTRIES = "form_entries"
    RECURRING_ISSUE_TEMPLATES = "recurring_issue_templates"
    MENUS = "menus"
    BOARDS = "boards"
    BOARD_POSTS = "board_posts"
    BOARD_POST_HISTORIES = "board_post_histories"
    NOTICES = "notices"
    AUTH_LOGS = "auth_logs"
    ACTIVITY_LOGS = "activity_logs"
    HEALTH_REPORTS = "health_reports"
    HEALTH_ACTIONS = "health_report_actions"
    APP_SETTINGS = "app_settings"
    LINKS = "links"
    DDAYS = "ddays"
    ENV_CATEGORIES = "env_categories"

    # ── Service Request (SR) ─────────────────────────────────────
    SERVICE_REQUESTS        = "service_requests"
    SR_COMMENTS             = "sr_comments"
    SR_ATTACHMENTS          = "sr_attachments"
    SR_HISTORIES            = "sr_histories"
    SR_STATUS_HISTORIES     = "sr_status_histories"
    SR_DUE_DATE_HISTORIES   = "sr_due_date_histories"
    SR_COUNTER              = "sr_counters"

    # ── Notifications ────────────────────────────────────────────
    NOTIFICATIONS = "notifications"

    # ── Project Management (PM) ──────────────────────────────────
    PM_ORGANIZATIONS = "pm_organizations"
    PM_ORG_MEMBERS = "pm_org_members"
    PM_PROJECTS = "pm_projects"
    PM_PROJECT_MEMBERS = "pm_project_members"
    PM_PROJECT_FAVORITES = "pm_project_favorites"
    PM_ISSUES = "pm_issues"
    PM_SPRINTS = "pm_sprints"
    PM_LABELS = "pm_labels"
    PM_ISSUE_COMMENTS = "pm_issue_comments"
    PM_ISSUE_HISTORY = "pm_issue_history"
    PM_WEEKLY_REPORTS = "pm_weekly_reports"
    PM_MONTHLY_REPORTS = "pm_monthly_reports"



    @classmethod
    def init_client(cls) -> None:
        """
        앱 시작 시 한 번만 호출해서 클라이언트 생성.
        """
        if cls._client is None:
            cls._client = AsyncIOMotorClient(settings.MONGO_URI)

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """
        어디서든 Mongo 클라이언트 필요할 때 호출.
        """
        if cls._client is None:
            # 안전하게, 혹시 startup에서 안 불렀을 때 대비
            cls.init_client()
        return cls._client

    @classmethod
    def get_db(cls):
        client = cls.get_client()
        return client[settings.APP_DB_NAME]

    @classmethod
    def get_users_collection(cls):
        db = cls.get_db()
        return db[cls.USERS]

    @classmethod
    def get_pending_users_collection(cls):
        db = cls.get_db()
        return db[cls.PENDING_USERS]

    @classmethod
    def get_assets_servers_collection(cls):
        return cls.get_db()[cls.ASSETS_SERVERS]

    @classmethod
    def get_assets_server_history_collection(cls):
        return cls.get_db()[cls.ASSETS_SERVER_HISTORY]

    @classmethod
    def get_asset_collection(cls, category: str):
        col_name, _ = cls.CATEGORY_COLLECTIONS.get(category, (cls.ASSETS_SERVERS, cls.ASSETS_SERVER_HISTORY))
        return cls.get_db()[col_name]

    @classmethod
    def get_asset_history_collection(cls, category: str):
        _, hist_name = cls.CATEGORY_COLLECTIONS.get(category, (cls.ASSETS_SERVERS, cls.ASSETS_SERVER_HISTORY))
        return cls.get_db()[hist_name]

    @classmethod
    def get_rack_placements_collection(cls):
        return cls.get_db()[cls.RACK_PLACEMENTS]

    @classmethod
    def get_rack_placements_history_collection(cls):
        return cls.get_db()[cls.RACK_PLACEMENTS_HISTORY]

    @classmethod
    def get_watch_assignments_collection(cls):
        return cls.get_db()[cls.WATCH_ASSIGNMENTS]

    @classmethod
    def get_watch_history_collection(cls):
        return cls.get_db()[cls.WATCH_HISTORY]

    @classmethod
    def get_pilot_poll_state_collection(cls):
        return cls.get_db()[cls.PILOT_POLL_STATE]

    @classmethod
    def get_delayed_digest_state_collection(cls):
        return cls.get_db()[cls.DELAYED_DIGEST_STATE]

    @classmethod
    def get_job_plans_collection(cls):
        return cls.get_db()[cls.JOB_PLANS]

    @classmethod
    def get_job_plans_history_collection(cls):
        return cls.get_db()[cls.JOB_PLANS_HISTORY]

    @classmethod
    def get_job_non_service_plans_collection(cls):
        return cls.get_db()[cls.JOB_NON_SERVICE_PLANS]

    @classmethod
    def get_job_non_service_plans_history_collection(cls):
        return cls.get_db()[cls.JOB_NON_SERVICE_PLANS_HISTORY]

    @classmethod
    def get_job_results_collection(cls):
        return cls.get_db()[cls.JOB_RESULTS]

    @classmethod
    def get_job_results_history_collection(cls):
        return cls.get_db()[cls.JOB_RESULTS_HISTORY]

    @classmethod
    def get_form_templates_collection(cls):
        return cls.get_db()[cls.FORM_TEMPLATES]

    @classmethod
    def get_form_entries_collection(cls):
        return cls.get_db()[cls.FORM_ENTRIES]

    @classmethod
    def get_menus_collection(cls):
        return cls.get_db()[cls.MENUS]

    @classmethod
    def get_links_collection(cls):
        return cls.get_db()[cls.LINKS]

    @classmethod
    def get_env_categories_collection(cls):
        return cls.get_db()[cls.ENV_CATEGORIES]

    @classmethod
    def get_ddays_collection(cls):
        return cls.get_db()[cls.DDAYS]

    @classmethod
    def get_boards_collection(cls):
        return cls.get_db()[cls.BOARDS]

    @classmethod
    def get_board_posts_collection(cls):
        return cls.get_db()[cls.BOARD_POSTS]

    @classmethod
    def get_board_post_histories_collection(cls):
        return cls.get_db()[cls.BOARD_POST_HISTORIES]

    @classmethod
    def get_notices_collection(cls):
        return cls.get_db()[cls.NOTICES]

    @classmethod
    def get_auth_logs_collection(cls):
        return cls.get_db()[cls.AUTH_LOGS]

    @classmethod
    def get_activity_logs_collection(cls):
        return cls.get_db()[cls.ACTIVITY_LOGS]

    # ── PM 컬렉션 접근자 ─────────────────────────────────────────
    @classmethod
    def get_pm_organizations_collection(cls):
        return cls.get_db()[cls.PM_ORGANIZATIONS]

    @classmethod
    def get_pm_org_members_collection(cls):
        return cls.get_db()[cls.PM_ORG_MEMBERS]

    @classmethod
    def get_pm_projects_collection(cls):
        return cls.get_db()[cls.PM_PROJECTS]

    @classmethod
    def get_pm_project_members_collection(cls):
        return cls.get_db()[cls.PM_PROJECT_MEMBERS]

    @classmethod
    def get_pm_project_favorites_collection(cls):
        return cls.get_db()[cls.PM_PROJECT_FAVORITES]

    @classmethod
    def get_pm_issues_collection(cls):
        return cls.get_db()[cls.PM_ISSUES]

    @classmethod
    def get_recurring_issue_templates_collection(cls):
        return cls.get_db()[cls.RECURRING_ISSUE_TEMPLATES]

    @classmethod
    def get_pm_sprints_collection(cls):
        return cls.get_db()[cls.PM_SPRINTS]

    @classmethod
    def get_pm_labels_collection(cls):
        return cls.get_db()[cls.PM_LABELS]

    @classmethod
    def get_pm_issue_comments_collection(cls):
        return cls.get_db()[cls.PM_ISSUE_COMMENTS]

    @classmethod
    def get_pm_issue_history_collection(cls):
        return cls.get_db()[cls.PM_ISSUE_HISTORY]

    @classmethod
    def get_pm_weekly_reports_collection(cls):
        return cls.get_db()[cls.PM_WEEKLY_REPORTS]

    @classmethod
    def get_pm_monthly_reports_collection(cls):
        return cls.get_db()[cls.PM_MONTHLY_REPORTS]

    @classmethod
    async def close_client(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None
