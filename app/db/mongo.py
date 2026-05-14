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
    WATCH_ASSIGNMENTS = "watch_assignments"

    # 카테고리 → (자산 컬렉션, 이력 컬렉션) 매핑
    CATEGORY_COLLECTIONS: dict = {
        "서버":         (ASSETS_SERVERS,  ASSETS_SERVER_HISTORY),
        "네트워크":     (ASSETS_NETWORK,  ASSETS_NETWORK_HISTORY),
        "정보보호시스템": (ASSETS_SECURITY, ASSETS_SECURITY_HISTORY),
        "DBMS":        (ASSETS_DBMS,     ASSETS_DBMS_HISTORY),
        "VMware":      (ASSETS_VMWARE,   ASSETS_VMWARE_HISTORY),
    }
    PILOT_POLL_STATE = "pilot_poll_state"
    INSPECTION_CHECKLISTS = "inspection_checklists"
    INSPECTION_HISTORY = "inspection_history"
    JOB_PLANS = "job_plans"
    JOB_PLANS_HISTORY = "job_plans_history"
    JOB_NON_SERVICE_PLANS = "job_non_service_plans"
    JOB_NON_SERVICE_PLANS_HISTORY = "job_non_service_plans_history"
    JOB_RESULTS = "job_results"
    JOB_RESULTS_HISTORY = "job_results_history"
    FORM_TEMPLATES = "form_templates"
    FORM_ENTRIES = "form_entries"
    MENUS = "menus"
    BOARDS = "boards"
    BOARD_POSTS = "board_posts"


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
    def get_watch_assignments_collection(cls):
        return cls.get_db()[cls.WATCH_ASSIGNMENTS]

    @classmethod
    def get_pilot_poll_state_collection(cls):
        return cls.get_db()[cls.PILOT_POLL_STATE]

    @classmethod
    def get_inspection_checklists_collection(cls):
        return cls.get_db()[cls.INSPECTION_CHECKLISTS]

    @classmethod
    def get_inspection_history_collection(cls):
        return cls.get_db()[cls.INSPECTION_HISTORY]

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
    def get_boards_collection(cls):
        return cls.get_db()[cls.BOARDS]

    @classmethod
    def get_board_posts_collection(cls):
        return cls.get_db()[cls.BOARD_POSTS]

    @classmethod
    async def close_client(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None
