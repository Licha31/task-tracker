from sqlalchemy import text

from test_auth import login


def payroll_schedule(label: str, jurisdiction: str, frequency: str = "weekly") -> dict:
    return {
        "label": label,
        "jurisdiction": jurisdiction,
        "sui_id": None,
        "sit_id": None,
        "principal_owner": None,
        "frequency": frequency,
        "payroll_platform": "Gusto",
        "next_pay_date": "2026-08-28",
        "next_process_date": "2026-08-24",
        "semi_monthly_day_1": 10 if frequency == "semi_monthly" else None,
        "semi_monthly_day_2": 25 if frequency == "semi_monthly" else None,
    }


def test_multiple_configurations_generate_independent_tasks_and_archive_safely(api_client):
    client, test_session = api_client
    assert login(client).status_code == 200

    payload = {
        "name": "ABC LLC",
        "ein": "12-3456789",
        "payroll_schedules": [
            payroll_schedule("Employees", "FL"),
            {
                **payroll_schedule("Owners", "GA", "semi_monthly"),
                "next_pay_date": "2026-08-25",
                "next_process_date": "2026-08-24",
            },
        ],
        "sales_tax_registrations": [
            {"jurisdiction": "FL", "frequency": "monthly", "next_due_date": "2026-08-24"},
            {"jurisdiction": "GA", "frequency": "quarterly", "next_due_date": "2026-08-24"},
        ],
    }
    created = client.post("/api/clients", json=payload)
    assert created.status_code == 201
    company = created.json()
    assert len(company["payroll_schedules"]) == 2
    assert len(company["sales_tax_registrations"]) == 2

    tasks = client.get("/api/tasks?week_start=2026-08-24&week_end=2026-08-30").json()
    payroll_tasks = [task for task in tasks if task["task_type"] == "payroll"]
    sales_tax_tasks = [task for task in tasks if task["task_type"] == "sales_tax"]
    assert {(task["source_label"], task["source_jurisdiction"]) for task in payroll_tasks} == {
        ("Employees", "FL"),
        ("Owners", "GA"),
    }
    assert {task["source_jurisdiction"] for task in sales_tax_tasks} == {"FL", "GA"}

    remaining_schedule = company["payroll_schedules"][1]
    remaining_registration = company["sales_tax_registrations"][1]
    updated_payload = {
        "name": company["name"],
        "ein": company["ein"],
        "payroll_schedules": [{**remaining_schedule, "label": "Owners Updated"}],
        "sales_tax_registrations": [remaining_registration],
    }
    updated = client.put(f"/api/clients/{company['id']}", json=updated_payload)
    assert updated.status_code == 200
    assert [item["label"] for item in updated.json()["payroll_schedules"]] == ["Owners Updated"]

    with test_session() as db:
        archived = db.execute(
            text(
                "SELECT label, active FROM payroll_schedules "
                "WHERE company_id = :company_id ORDER BY id"
            ),
            {"company_id": company["id"]},
        ).all()
        archived_registration_count = db.execute(
            text(
                "SELECT COUNT(*) FROM sales_tax_registrations "
                "WHERE company_id = :company_id AND active = FALSE"
            ),
            {"company_id": company["id"]},
        ).scalar_one()
    assert archived == [("Employees", False), ("Owners Updated", True)]
    assert archived_registration_count == 1

    historical = client.get("/api/tasks?week_start=2026-08-24&week_end=2026-08-30").json()
    assert any(task["source_label"] == "Employees" for task in historical)
    assert any(
        task["task_type"] == "sales_tax" and task["source_jurisdiction"] == "FL"
        for task in historical
    )

    future = client.get("/api/tasks?week_start=2026-09-07&week_end=2026-09-13").json()
    assert not any(task["source_label"] == "Employees" for task in future)
    assert any(task["source_label"] == "Owners Updated" for task in future)

    future_sales_tax = client.get("/api/tasks?week_start=2026-09-21&week_end=2026-09-27").json()
    assert not any(task["task_type"] == "sales_tax" for task in future_sales_tax)


def test_company_update_rejects_configuration_id_from_another_company(api_client):
    client, _ = api_client
    assert login(client).status_code == 200
    first = client.post(
        "/api/clients",
        json={
            "name": "First",
            "ein": "11-1111111",
            "payroll_schedules": [payroll_schedule("First Payroll", "FL")],
            "sales_tax_registrations": [],
        },
    ).json()
    second = client.post(
        "/api/clients",
        json={
            "name": "Second",
            "ein": "22-2222222",
            "payroll_schedules": [],
            "sales_tax_registrations": [],
        },
    ).json()

    response = client.put(
        f"/api/clients/{second['id']}",
        json={
            "name": second["name"],
            "ein": second["ein"],
            "payroll_schedules": [first["payroll_schedules"][0]],
            "sales_tax_registrations": [],
        },
    )
    assert response.status_code == 422
