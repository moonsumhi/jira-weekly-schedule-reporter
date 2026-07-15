from app.db.mongo import MongoClientManager


async def create_notification_indexes() -> None:
    col = MongoClientManager.get_db()[MongoClientManager.NOTIFICATIONS]
    await col.create_index([("recipient_user_id", 1), ("is_read", 1), ("is_archived", 1)])
    await col.create_index([("recipient_user_id", 1), ("created_at", -1)])
    await col.create_index("deduplication_key", sparse=True)
