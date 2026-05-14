import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware

from app.routers import health, issues, jira_ui, auth, admin, assets, watch, pilot, inspection, job, job_result, job_non_service, test, form_templates, form_entries, menus, boards

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.db.startup import run_startup
from app.services.jira_poller import JiraPollerService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    MongoClientManager.init_client()
    await run_startup()

    poller = None
    if settings.PILOT_ENABLED:
        poller = JiraPollerService()
        poller.start()
        logging.getLogger(__name__).info("JiraPollerService started")

    yield

    # ---- shutdown ----
    if poller:
        poller.stop()
    await MongoClientManager.close_client()


app = FastAPI(title="Jira Task Viewer API", version="1.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.trycloudflare\.com",
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
app.include_router(job_non_service.router, prefix="/job-non-service", tags=["job-non-service"])
app.include_router(test.router, prefix="/test", tags=["test"])
app.include_router(form_templates.router, prefix="/form-templates", tags=["form-templates"])
app.include_router(form_entries.router, prefix="/form-entries", tags=["form-entries"])
app.include_router(menus.router, prefix="/menus", tags=["menus"])
app.include_router(boards.router, prefix="/boards", tags=["boards"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
