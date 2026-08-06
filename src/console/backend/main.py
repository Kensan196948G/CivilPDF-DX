from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from database import engine, Base
from api import (
    apps_router,
    electronic_delivery_router,
    organizations_router,
    auth_router,
    users_router,
    documents_router,
    workflows_router,
    projects_router,
    audit_logs_router,
    stats_router,
    m365_router,
    ocr_router,
    privacy_router,
    ai_router,
    ai_settings_router,
    search_router,
    editor_router,
    revisions_router,
)
from middleware import AuditMiddleware
from middleware.security import SecurityHeadersMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic in production)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    if settings.debug:
        # Ensure the dev-bypass admin exists so unauthenticated requests work.
        from database import SessionLocal
        from auth.dependencies import _get_or_create_dev_user

        db = SessionLocal()
        try:
            _get_or_create_dev_user(db)
            logger.warning(
                "⚠️  DEV AUTH BYPASS ACTIVE — all unauthenticated requests run as dev-admin. "
                "Set DEBUG=false in production."
            )
        finally:
            db.close()

    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="建設業特化PDFプラットフォーム 管理コンソール API",
    lifespan=lifespan,
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(AuditMiddleware)

# API routes
API_PREFIX = "/api/v1"
app.include_router(apps_router, prefix=API_PREFIX)
app.include_router(electronic_delivery_router, prefix=API_PREFIX)
app.include_router(organizations_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(documents_router, prefix=API_PREFIX)
app.include_router(workflows_router, prefix=API_PREFIX)
app.include_router(projects_router, prefix=API_PREFIX)
app.include_router(audit_logs_router, prefix=API_PREFIX)
app.include_router(stats_router, prefix=API_PREFIX)
app.include_router(m365_router, prefix=API_PREFIX)
app.include_router(ocr_router, prefix=API_PREFIX)
app.include_router(privacy_router, prefix=API_PREFIX)
app.include_router(ai_router, prefix=API_PREFIX)
app.include_router(ai_settings_router, prefix=API_PREFIX)
app.include_router(search_router, prefix=API_PREFIX)
app.include_router(editor_router, prefix=API_PREFIX)
app.include_router(revisions_router, prefix=API_PREFIX)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": "/docs",
        "health": "/health",
    }
