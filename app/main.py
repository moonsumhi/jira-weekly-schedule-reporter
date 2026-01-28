import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware

from app.routers import health, issues, jira_ui, auth, admin, assets, watch

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.services.jira_poller import JiraPollerService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    MongoClientManager.init_client()
    users = MongoClientManager.get_users_collection()
    await users.create_index("email", unique=True)

    watch = MongoClientManager.get_watch_assignments_collection()
    await watch.create_index("start")
    await watch.create_index("end")
    await watch.create_index("assignee")

    assets = MongoClientManager.get_assets_servers_collection()
    await assets.create_index("ip")

    history = MongoClientManager.get_assets_server_history_collection()
    await history.create_index("asset_id")
    await history.create_index("changed_at")

    poller = None
    if settings.PILOT_ENABLED:
        poller = JiraPollerService()
        poller.start()

    yield

    # ---- shutdown ----
    if poller:
        poller.stop()
    await MongoClientManager.close_client()


app = FastAPI(title="Jira Task Viewer API", version="1.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(issues.router, prefix="/issues", tags=["issues"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(jira_ui.router, prefix="/jira", tags=["jira"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(watch.router, prefix="/watch", tags=["watch"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
