import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware

from app.routers import health, issues, jira_ui, auth, admin, assets, watch

from app.db.mongo import MongoClientManager


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
    yield

    # ---- shutdown ----
    await MongoClientManager.close_client()


app = FastAPI(title="Jira Task Viewer API", version="1.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/auth", tags=["issues"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(issues.router, prefix="/issues", tags=["issues"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(jira_ui.router, prefix="/jira", tags=["jira"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(watch.router, prefix="/watch", tags=["watch"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
