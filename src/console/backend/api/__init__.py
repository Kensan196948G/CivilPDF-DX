from api.auth import router as auth_router
from api.users import router as users_router
from api.documents import router as documents_router
from api.workflows import router as workflows_router
from api.projects import router as projects_router
from api.audit_logs import router as audit_logs_router

__all__ = [
    "auth_router",
    "users_router",
    "documents_router",
    "workflows_router",
    "projects_router",
    "audit_logs_router",
]
