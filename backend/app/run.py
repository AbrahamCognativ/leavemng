from fastapi import FastAPI
from importlib import import_module

app = FastAPI(title="Leave Management API")

def include_routers():
    modules = ["auth", "users", "org", "leave", "files", "analytics"]
    for m in modules:
        router = import_module(f"app.api.v1.routers.{m}")
        app.include_router(router.router, prefix=f"/api/v1/{m}")

include_routers()
