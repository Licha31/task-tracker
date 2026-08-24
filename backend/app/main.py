import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app import models  # noqa: F401 - registers tables before create_all
from app.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    get_required_setting,
    session_cookie_same_site,
    session_cookie_secure,
    validate_auth_settings,
)
from app.database import Base, engine
from app.routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def get_frontend_origins() -> list[str]:
    configured = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def create_app() -> FastAPI:
    validate_auth_settings()
    application = FastAPI(title="Task Tracker API", lifespan=lifespan)

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

    @application.get("/")
    def root():
        return {"message": "Task Tracker API running"}

    return application


app = create_app()
