from fastapi import FastAPI
from importlib import import_module
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel, SecuritySchemeType
from fastapi import Security

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

app = FastAPI(title="Leave Management API", 
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "swagger-ui-client"
    },
    openapi_tags=[
        {"name": "auth", "description": "Authentication and authorization endpoints"},
        {"name": "users", "description": "User management endpoints"},
        {"name": "org", "description": "Organization units endpoints"},
        {"name": "leave", "description": "Leave requests endpoints"},
        {"name": "files", "description": "Files endpoints"},
        {"name": "analytics", "description": "Analytics endpoints"},
    ]
)

origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:4200/"
]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    ## expose_headers=["Content-Length", "Content-Type", "*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight responses for 10 minutes
)
# Add a global dependency to require Authorization except for /login
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class AuthRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/auth/login") or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi") or request.url.path.startswith("/redoc"):
            return await call_next(request)
        # Only require token for API routes
        if request.url.path.startswith("/api/v1/"):
            authorization: str = request.headers.get("Authorization")
            if not authorization or not authorization.lower().startswith("bearer "):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=401, content={"detail": "Not authenticated. Add 'Authorization: Bearer <token>' header."})
        return await call_next(request)

app.add_middleware(AuthRequiredMiddleware)

def include_routers():
    modules = ["auth", "users", "org", "leave", "files", "analytics", "leave_types", "leave_policy"]
    for m in modules:
        router = import_module(f"app.api.v1.routers.{m}")
        # Use kebab-case for leave-policy and leave-types
        if m == "leave_policy":
            prefix = "/api/v1/leave-policy"
        elif m == "leave_types":
            prefix = "/api/v1/leave-types"
        else:
            prefix = f"/api/v1/{m}"
        app.include_router(router.router, prefix=prefix)


include_routers()

# Start the leave accrual scheduler (monthly)
try:
    from app.utils.scheduler import run_accrual_scheduler
    run_accrual_scheduler()
except Exception as e:
    print(f"[WARN] Could not start accrual scheduler: {e}")
