import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware

from app.routers import health, issues, jira_ui, auth, admin, assets, watch, pilot, inspection, job, job_result

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

    inspection_checklists = MongoClientManager.get_inspection_checklists_collection()
    await inspection_checklists.create_index("inspection_month", unique=True)
    await inspection_checklists.create_index("person_in_charge")

    inspection_history = MongoClientManager.get_inspection_history_collection()
    await inspection_history.create_index("checklist_id")
    await inspection_history.create_index("changed_at")

    job_plans = MongoClientManager.get_job_plans_collection()
    await job_plans.create_index("work_date")
    await job_plans.create_index("worker")
    await job_plans.create_index("status")

    job_plans_history = MongoClientManager.get_job_plans_history_collection()
    await job_plans_history.create_index("plan_id")
    await job_plans_history.create_index("changed_at")

    job_results = MongoClientManager.get_job_results_collection()
    await job_results.create_index("work_date")
    await job_results.create_index("worker")
    await job_results.create_index("result")

    job_results_history = MongoClientManager.get_job_results_history_collection()
    await job_results_history.create_index("result_id")
    await job_results_history.create_index("changed_at")

    poller = None
    print(f"PILOT_ENABLED: {settings.PILOT_ENABLED}")
    if settings.PILOT_ENABLED:
        poller = JiraPollerService()
        poller.start()
        print("JiraPollerService started")

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
app.include_router(pilot.router, prefix="/pilot", tags=["pilot"])
app.include_router(inspection.router, prefix="/inspection", tags=["inspection"])
app.include_router(job.router, prefix="/job", tags=["job"])
app.include_router(job_result.router, prefix="/job-result", tags=["job-result"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
