from sqlalchemy import text


def test_calendar_range_uses_process_and_due_dates_without_duplicates(api_client):
    client, test_session = api_client

    with test_session.begin() as db:
        company_id = db.execute(
            text("INSERT INTO companies (name, ein) VALUES ('Apex Builders', '12-3456789')")
        ).lastrowid
        db.execute(
            text(
                """
                INSERT INTO payroll_profiles (
                    company_id, frequency, payroll_platform, next_pay_date, next_process_date
                ) VALUES (
                    :company_id, 'weekly', 'Gusto', '2026-08-07', '2026-08-03'
                )
                """
            ),
            {"company_id": company_id},
        )
        db.execute(
            text(
                """
                INSERT INTO sales_tax_profiles (company_id, frequency, next_due_date)
                VALUES (:company_id, 'monthly', '2026-08-20')
                """
            ),
            {"company_id": company_id},
        )

    url = "/api/tasks?week_start=2026-07-27&week_end=2026-09-06"
    first_response = client.get(url)
    second_response = client.get(url)

    assert first_response.status_code == 200
    tasks = first_response.json()
    assert any(
        task["task_type"] == "payroll" and task["process_date"] == "2026-08-03" for task in tasks
    )
    assert any(
        task["task_type"] == "sales_tax" and task["due_date"] == "2026-08-20" for task in tasks
    )
    assert len(second_response.json()) == len(tasks)

    with test_session() as db:
        stored_count = db.execute(text("SELECT COUNT(*) FROM tasks")).scalar_one()
    assert stored_count == len(tasks)
