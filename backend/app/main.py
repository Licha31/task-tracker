import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    get_required_setting,
    session_cookie_same_site,
    session_cookie_secure,
    validate_auth_settings,
)
from app.routes import router


def get_frontend_origins() -> list[str]:
    configured = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(frontend_dist: Path = FRONTEND_DIST) -> FastAPI:
    validate_auth_settings()
    application = FastAPI(title="Task Tracker API")

    application.add_middleware(
        SessionMiddleware,
        secret_key=get_required_setting("ADMIN_SESSION_SECRET"),
        session_cookie=SESSION_COOKIE_NAME,
        max_age=SESSION_MAX_AGE_SECONDS,
        same_site=session_cookie_same_site(),
        https_only=session_cookie_secure(),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_frontend_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router)

    assets = frontend_dist / "assets"
    if assets.is_dir():
        application.mount("/assets", StaticFiles(directory=assets), name="assets")

    @application.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        index = frontend_dist / "index.html"
        if not index.is_file() or not assets.is_dir():
            return PlainTextResponse(
                "Frontend build missing. Run `npm run build` in frontend/ before starting Task Tracker.",
                status_code=503,
            )
        return FileResponse(index)

    return application


app = create_app()
