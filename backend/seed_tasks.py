from sqlalchemy import text

from app.database import SessionLocal


def seed_tasks():
    db = SessionLocal()

    try:
        companies = db.execute(
            text(
                """
                SELECT id, name
                FROM companies
                ORDER BY id
                LIMIT 2
                """
            )
        ).mappings().all()

        if not companies:
            print("No companies found.")
            return

        first_company = companies[0]

        db.execute(
            text(
                """
                INSERT INTO tasks (
                    company_id,
                    task_type,
                    process_date,
                    pay_date,
                    status
                )
                VALUES (
                    :company_id,
                    'payroll',
                    '2026-08-24',
                    '2026-08-26',
                    'pending'
                )
                """
            ),
            {"company_id": first_company["id"]},
        )

        if len(companies) > 1:
            second_company = companies[1]

            db.execute(
                text(
                    """
                    INSERT INTO tasks (
                        company_id,
                        task_type,
                        due_date,
                        status
                    )
                    VALUES (
                        :company_id,
                        'sales_tax',
                        '2026-08-27',
                        'in_progress'
                    )
                    """
                ),
                {"company_id": second_company["id"]},
            )

        db.commit()

        print("Tasks created.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_tasks()