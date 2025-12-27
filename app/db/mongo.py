from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.core.config import settings


class MongoClientManager:
    _client: Optional[AsyncIOMotorClient] = None

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
        return db["users"]

    @classmethod
    async def close_client(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None
