from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from app import models  # noqa: F401 - registers tables on Base.metadata
from app.auth import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from app.database import Base, get_db
from app.routes import router


@pytest.fixture
def api_client(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-password")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "test-session-secret-that-is-not-for-production")

    database_path = tmp_path / "task_tracker_test.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX uq_tasks_occurrence
                ON tasks (
                    company_id,
                    task_type,
                    COALESCE(process_date, ''),
                    COALESCE(due_date, '')
                )
                """
            )
        )

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-session-secret-that-is-not-for-production",
        session_cookie=SESSION_COOKIE_NAME,
        max_age=SESSION_MAX_AGE_SECONDS,
        same_site="lax",
        https_only=False,
    )
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, test_session

    engine.dispose()
