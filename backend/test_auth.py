from sqlalchemy import text

from app.auth import session_cookie_same_site, session_cookie_secure


def login(client):
    return client.post("/api/auth/login", json={"password": "test-admin-password"})


def test_login_session_refresh_and_logout(api_client):
    client, _ = api_client

    assert client.get("/api/auth/session").json() == {"authenticated": False}
    assert client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401

    response = login(client)
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "Max-Age=43200" in response.headers["set-cookie"]
    assert client.get("/api/auth/session").json() == {"authenticated": True}

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/session").json() == {"authenticated": False}
    assert client.get("/api/clients").status_code == 401


def test_admin_endpoints_and_status_update_require_authentication(api_client):
    client, test_session = api_client
    payload = {
        "name": "Apex Builders",
        "ein": "12-3456789",
        "payroll_schedules": [],
        "sales_tax_registrations": [],
    }

    protected_requests = [
        ("get", "/api/clients", None),
        ("get", "/api/clients/1", None),
        ("post", "/api/clients", payload),
        ("put", "/api/clients/1", payload),
        ("delete", "/api/clients/1", None),
        ("patch", "/api/tasks/1", {"status": "completed"}),
    ]
    for method, path, body in protected_requests:
        response = client.request(method, path, json=body)
        assert response.status_code == 401

    assert login(client).status_code == 200
    created = client.post("/api/clients", json=payload)
    assert created.status_code == 201
    company_id = created.json()["id"]

    client_list = client.get("/api/clients")
    assert client_list.status_code == 200
    assert [company["id"] for company in client_list.json()] == [company_id]
    assert client.get(f"/api/clients/{company_id}").status_code == 200

    updated_payload = {**payload, "name": "Apex Builders Updated"}
    updated_client = client.put(f"/api/clients/{company_id}", json=updated_payload)
    assert updated_client.status_code == 200
    assert updated_client.json()["name"] == "Apex Builders Updated"

    with test_session.begin() as db:
        db.execute(
            text(
                """
                INSERT INTO sales_tax_registrations (
                    company_id, jurisdiction, frequency, next_due_date, active
                ) VALUES (:company_id, 'FL', 'monthly', '2026-08-20', TRUE)
                """
            ),
            {"company_id": company_id},
        )

    client.get("/api/tasks?week_start=2026-08-17&week_end=2026-08-23")

    task_id = client.get("/api/tasks?week_start=2026-08-17&week_end=2026-08-23").json()[0]["id"]
    updated = client.patch(f"/api/tasks/{task_id}", json={"status": "completed"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"

    assert client.delete(f"/api/clients/{company_id}").status_code == 204
    assert client.get("/api/clients").json() == []


def test_production_cookie_configuration(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_COOKIE_SAMESITE", "none")

    assert session_cookie_secure() is True
    assert session_cookie_same_site() == "none"
