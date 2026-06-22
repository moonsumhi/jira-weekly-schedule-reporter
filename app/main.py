import logging
import time
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

# 서버 시작 시각을 Build ID로 사용 (rebuild 감지용)
BUILD_ID = str(int(time.time()))

from app.routers import health, issues, jira_ui, auth, admin, assets, watch, pilot, inspection, job, job_result, job_non_service, test, form_templates, form_entries, menus, boards, health_reports, health_actions, links, ddays
from app.routers import settings as settings_router

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.db.startup import run_startup
from app.services.jira_poller import JiraPollerService
from app.middleware.activity_logger import ActivityLoggerMiddleware


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


class BuildIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Build-Id"] = BUILD_ID
        return response


_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# 외부 접속이어도 허용할 경로 프리픽스 (로그인/회원가입/비밀번호변경/설정저장)
_INTERNAL_EXEMPT = ("/auth/login", "/auth/register", "/auth/change-password", "/auth/prefs", "/health/", "/pilot/")


class ExternalReadOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in _WRITE_METHODS:
            path = request.url.path
            if not any(path.startswith(p) for p in _INTERNAL_EXEMPT):
                from app.utils.ip import is_internal_ip
                if not await is_internal_ip(request):
                    from starlette.responses import JSONResponse
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "내부 접속에서만 사용할 수 있습니다."},
                    )
        return await call_next(request)


app = FastAPI(title="Jira Task Viewer API", version="1.3.0", lifespan=lifespan)

app.add_middleware(BuildIdMiddleware)
app.add_middleware(ExternalReadOnlyMiddleware)
app.add_middleware(ActivityLoggerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.trycloudflare\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Build-Id"],
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
app.include_router(health_reports.router, prefix="/health-reports", tags=["health-reports"])
app.include_router(health_actions.router, prefix="/health-reports", tags=["health-actions"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])
app.include_router(links.router, prefix="/links", tags=["links"])
app.include_router(ddays.router, prefix="/ddays", tags=["ddays"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
