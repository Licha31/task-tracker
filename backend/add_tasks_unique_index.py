from sqlalchemy import text

from app.database import engine


def add_unique_index():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_tasks_occurrence
                ON tasks (
                    company_id,
                    task_type,
                    COALESCE(process_date, ''),
                    COALESCE(due_date, '')
                )
                """
            )
        )

    print("Tasks unique index created.")


if __name__ == "__main__":
    add_unique_index()