import hmac
import os
from typing import Literal, cast

from fastapi import HTTPException, Request, status

SESSION_COOKIE_NAME = "task_tracker_admin"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60


def get_required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be configured")
    return value


def validate_auth_settings() -> None:
    get_required_setting("ADMIN_PASSWORD")
    get_required_setting("ADMIN_SESSION_SECRET")


def session_cookie_secure() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def session_cookie_same_site() -> Literal["lax", "strict", "none"]:
    value = os.getenv("ADMIN_COOKIE_SAMESITE", "lax").lower()
    if value not in {"lax", "strict", "none"}:
        raise RuntimeError("ADMIN_COOKIE_SAMESITE must be lax, strict, or none")
    return cast(Literal["lax", "strict", "none"], value)


def password_is_valid(candidate: str) -> bool:
    return hmac.compare_digest(candidate, get_required_setting("ADMIN_PASSWORD"))


def require_admin(request: Request) -> None:
    if request.session.get("access") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
