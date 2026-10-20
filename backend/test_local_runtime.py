from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text

from alembic import command
from test_migrations import alembic_config


def test_fastapi_serves_build_and_keeps_api_404(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "test-secret")
    from app.main import create_app
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>Task Tracker build</html>")
    (dist / "assets" / "app.js").write_text("console.log('built')")
    with TestClient(create_app(dist)) as client:
        assert "Task Tracker build" in client.get("/").text
        assert "console.log" in client.get("/assets/app.js").text
        assert "Task Tracker build" in client.get("/calendar").text
        api_404 = client.get("/api/invalid-route")
        assert api_404.status_code == 404
        assert api_404.json() == {"detail": "Not Found"}


def test_missing_build_has_useful_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "test-secret")
    from app.main import create_app
    with TestClient(create_app(tmp_path / "missing")) as client:
        response = client.get("/")
        assert response.status_code == 503
        assert "npm run build" in response.text


def test_fresh_sqlite_migrates_with_foreign_keys_and_persists(tmp_path, monkeypatch):
    path = tmp_path / "fresh.db"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url, monkeypatch), "head")
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        connection.execute(text("INSERT INTO companies (id, name, ein) VALUES (91, 'Local', '91')"))
    engine.dispose()
    reopened = create_engine(url)
    with reopened.connect() as connection:
        assert connection.execute(text("SELECT name FROM companies WHERE id=91")).scalar_one() == "Local"
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    reopened.dispose()
