from datetime import date

import pytest
from sqlalchemy import text

from app.monthly_pdf import month_bounds, prepare_monthly_tasks


@pytest.mark.parametrize(
    ("year", "month", "expected"),
    [
        (2026, 2, (date(2026, 2, 1), date(2026, 2, 28))),
        (2024, 2, (date(2024, 2, 1), date(2024, 2, 29))),
        (2026, 9, (date(2026, 9, 1), date(2026, 9, 30))),
        (2026, 12, (date(2026, 12, 1), date(2026, 12, 31))),
    ],
)
def test_month_bounds_are_exact(year, month, expected):
    assert month_bounds(year, month) == expected


def test_printable_month_uses_operational_dates_and_omits_status(api_client):
    _client, test_session = api_client
    with test_session.begin() as db:
        company_id = db.execute(
            text("INSERT INTO companies (name, ein) VALUES ('Apex Builders', '12-3456789')")
        ).lastrowid
        payroll_id = db.execute(
            text(
                """
                INSERT INTO payroll_schedules (
                    company_id, label, jurisdiction, frequency, payroll_platform,
                    next_pay_date, next_process_date, active
                ) VALUES (:company_id, 'Employees', 'FL', 'weekly', 'Gusto',
                    '2026-09-04', '2026-09-01', TRUE)
                """
            ),
            {"company_id": company_id},
        ).lastrowid
        tax_id = db.execute(
            text(
                """
                INSERT INTO sales_tax_registrations (
                    company_id, jurisdiction, frequency, next_due_date, active
                ) VALUES (:company_id, 'GA', 'monthly', '2026-09-20', TRUE)
                """
            ),
            {"company_id": company_id},
        ).lastrowid
        db.execute(
            text(
                """
                INSERT INTO tasks (
                    company_id, payroll_schedule_id, task_type,
                    process_date, pay_date, status
                ) VALUES
                    (:company_id, :payroll_id, 'payroll', '2026-08-31', '2026-09-04', 'pending'),
                    (:company_id, :payroll_id, 'payroll', '2026-09-01', '2026-09-04', 'completed'),
                    (:company_id, :payroll_id, 'payroll', '2026-10-01', '2026-10-04', 'in_progress')
                """
            ),
            {"company_id": company_id, "payroll_id": payroll_id},
        )
        db.execute(
            text(
                """
                INSERT INTO tasks (
                    company_id, sales_tax_registration_id, task_type, due_date, status
                ) VALUES
                    (:company_id, :tax_id, 'sales_tax', '2026-09-20', 'in_progress'),
                    (:company_id, :tax_id, 'sales_tax', '2026-10-20', 'completed')
                """
            ),
            {"company_id": company_id, "tax_id": tax_id},
        )

    with test_session() as db:
        printable = prepare_monthly_tasks(db, 2026, 9)

    assert [item.operational_date for item in printable] == [date(2026, 9, 1), date(2026, 9, 20)]
    assert printable[0].task == "Payroll"
    assert printable[0].schedule == "Employees"
    assert printable[0].pay_date == date(2026, 9, 4)
    assert printable[1].task == "Sales Tax"
    assert printable[1].schedule == "—"
    assert printable[1].pay_date is None
    assert all("status" not in item.__dataclass_fields__ for item in printable)


def test_pdf_endpoint_supports_multiple_sources_and_preserves_status(api_client):
    client, test_session = api_client
    with test_session.begin() as db:
        company_id = db.execute(
            text("INSERT INTO companies (name, ein) VALUES ('Beacon & Sons <LLC>', '98-7654321')")
        ).lastrowid
        for label, jurisdiction, process_date, pay_date in [
            ("Employees", "FL", "2026-09-01", "2026-09-04"),
            ("Owners", "NY", "2026-09-10", "2026-09-15"),
        ]:
            db.execute(
                text(
                    """
                    INSERT INTO payroll_schedules (
                        company_id, label, jurisdiction, frequency, payroll_platform,
                        next_pay_date, next_process_date, active
                    ) VALUES (
                        :company_id, :label, :jurisdiction, 'monthly', 'Gusto',
                        :pay_date, :process_date, TRUE
                    )
                    """
                ),
                {
                    "company_id": company_id,
                    "label": label,
                    "jurisdiction": jurisdiction,
                    "process_date": process_date,
                    "pay_date": pay_date,
                },
            )
        for jurisdiction, due_date in [("GA", "2026-09-20"), ("CA", "2026-09-30")]:
            db.execute(
                text(
                    """
                    INSERT INTO sales_tax_registrations (
                        company_id, jurisdiction, frequency, next_due_date, active
                    ) VALUES (:company_id, :jurisdiction, 'monthly', :due_date, TRUE)
                    """
                ),
                {"company_id": company_id, "jurisdiction": jurisdiction, "due_date": due_date},
            )

    response = client.get("/api/tasks/monthly-pdf?year=2026&month=9")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="task-schedule-2026-09.pdf"'
    )
    assert response.content.startswith(b"%PDF-")
    with test_session.begin() as db:
        task_id = db.execute(text("SELECT id FROM tasks ORDER BY id LIMIT 1")).scalar_one()
        db.execute(
            text("UPDATE tasks SET status = 'completed' WHERE id = :task_id"),
            {"task_id": task_id},
        )

    repeated_response = client.get("/api/tasks/monthly-pdf?year=2026&month=9")
    assert repeated_response.status_code == 200
    with test_session() as db:
        rows = (
            db.execute(text("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status"))
            .mappings()
            .all()
        )
        printable = prepare_monthly_tasks(db, 2026, 9)
    assert rows == [
        {"status": "completed", "count": 1},
        {"status": "pending", "count": 4},
    ]
    assert len(printable) == 5
    assert {item.schedule for item in printable if item.task == "Payroll"} == {
        "Employees",
        "Owners",
    }
    assert {item.jurisdiction for item in printable if item.task == "Sales Tax"} == {"GA", "CA"}


def test_pdf_endpoint_rejects_invalid_month(api_client):
    client, _test_session = api_client
    response = client.get("/api/tasks/monthly-pdf?year=2026&month=13")
    assert response.status_code == 422


def test_task_api_keeps_id_order_while_pdf_sorts_same_date_by_client(api_client):
    client, test_session = api_client
    with test_session.begin() as db:
        task_ids = []
        for name, ein in [("Zulu Co", "11-1111111"), ("Alpha Co", "22-2222222")]:
            company_id = db.execute(
                text("INSERT INTO companies (name, ein) VALUES (:name, :ein)"),
                {"name": name, "ein": ein},
            ).lastrowid
            schedule_id = db.execute(
                text(
                    """
                    INSERT INTO payroll_schedules (
                        company_id, label, jurisdiction, frequency, payroll_platform,
                        next_pay_date, next_process_date, active
                    ) VALUES (
                        :company_id, 'Employees', 'FL', 'monthly', 'Gusto',
                        '2026-09-04', '2026-09-01', FALSE
                    )
                    """
                ),
                {"company_id": company_id},
            ).lastrowid
            task_ids.append(
                db.execute(
                    text(
                        """
                        INSERT INTO tasks (
                            company_id, payroll_schedule_id, task_type,
                            process_date, pay_date, status
                        ) VALUES (
                            :company_id, :schedule_id, 'payroll',
                            '2026-09-01', '2026-09-04', 'pending'
                        )
                        """
                    ),
                    {"company_id": company_id, "schedule_id": schedule_id},
                ).lastrowid
            )

    response = client.get("/api/tasks?week_start=2026-09-01&week_end=2026-09-01")
    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == task_ids
    assert [task["company_name"] for task in response.json()] == ["Zulu Co", "Alpha Co"]

    with test_session() as db:
        printable = prepare_monthly_tasks(db, 2026, 9)
    assert [task.client for task in printable] == ["Alpha Co", "Zulu Co"]
