from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from importlib import import_module
from app.settings import get_settings
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

# Load environment-specific settings
settings = get_settings()

# Make settings available globally via app.state


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

app = FastAPI(
    title=f"Leave Management API [{settings.APP_ENV.upper()}]",
    description=f"API for managing employee leave requests and approvals.\n\n**Environment:** `{settings.APP_ENV}`\n\n**Register URL:** `{settings.REGISTER_URL}`",
    version="1.0.0",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "swagger-ui-client"
    },
    # swagger_ui_parameters={
    #     "docExpansion": "none",
    #     "defaultModelsExpandDepth": -1,
    #     "displayRequestDuration": True,
    #     "persistAuthorization": True,
    # },
    openapi_tags=[
        {"name": "auth", "description": "Authentication and authorization endpoints"},
        {"name": "users", "description": "User management endpoints"},
        {"name": "org", "description": "Organization units endpoints"},
        {"name": "leave", "description": "Leave requests endpoints"},
        {"name": "files", "description": "Files endpoints"},
        {"name": "analytics", "description": "Analytics endpoints"},
        {"name": "audit_logs", "description": "Audit logs endpoints"},
    ]
)

# Attach settings to app.state so they are available everywhere
app.state.settings = settings
# Usage: from fastapi import Request; settings = request.app.state.settings

origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:4200/",
    "http://192.168.1.78:8080",
    "http://192.168.1.78:4200/",
    "https://internal.cognativ.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # expose_headers=["Content-Length", "Content-Type", "*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight responses for 10 minutes
)
# Add a global dependency to require Authorization except for /login


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow OPTIONS requests for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        if (request.url.path.startswith("/api/v1/auth/login")
                or request.url.path.startswith("/docs")
                or request.url.path.startswith("/openapi")
                or request.url.path.startswith("/redoc")
                or request.url.path.startswith("/api/v1/auth/reset-password-invite")
                or request.url.path.startswith("/api/v1/auth/forgot-password")
                ):
            return await call_next(request)
        # Only require token for API routes
        if request.url.path.startswith("/api/v1/"):
            authorization: str = request.headers.get("Authorization")
            if not authorization or not authorization.lower().startswith("bearer "):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401, content={
                        "detail": "Not authenticated. Add 'Authorization: Bearer <token>' header."})
        return await call_next(request)


app.add_middleware(AuthRequiredMiddleware)


def include_routers():
    modules = [
        "auth",
        "users",
        "org",
        "leave",
        "files",
        "analytics",
        "leave_types",
        "leave_policy",
        "audit_logs"]
    for m in modules:
        router = import_module(f"app.api.v1.routers.{m}")
        # Use kebab-case for leave-policy and leave-types
        if m == "leave_policy":
            prefix = "/api/v1/leave-policy"
        elif m == "leave_types":
            prefix = "/api/v1/leave-types"
        elif m == "audit_logs":
            prefix = "/api/v1/audit-logs"
        else:
            prefix = f"/api/v1/{m}"
        app.include_router(router.router, prefix=prefix)


include_routers()

# Mount uploads directory as static files
try:
    # Get the path to the uploads directory
    from app.api.v1.routers.files import UPLOAD_DIR
    uploads_path = Path(UPLOAD_DIR)

    # Create the directory if it doesn't exist
    os.makedirs(uploads_path, exist_ok=True)

    # Mount the directory to serve static files
    app.mount(
        "/uploads",
        StaticFiles(
            directory=str(uploads_path)),
        name="uploads")
    print(f"[INFO] Mounted uploads directory: {uploads_path}")
except (AttributeError, TypeError, Exception) as e:
    print(f"[WARN] Could not mount uploads directory: {e}")

# Start the leave accrual scheduler (monthly)
try:
    from app.utils.scheduler import run_accrual_scheduler
    run_accrual_scheduler()
except (AttributeError, TypeError, Exception) as e:
    print(f"[WARN] Could not start accrual scheduler: {e}")
