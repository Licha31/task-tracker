from sqlalchemy import text

from app.database import engine


def add_columns():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE payroll_profiles
                ADD COLUMN semi_monthly_day_1 INTEGER
                """
            )
        )

        connection.execute(
            text(
                """
                ALTER TABLE payroll_profiles
                ADD COLUMN semi_monthly_day_2 INTEGER
                """
            )
        )

    print("Semi-monthly columns added.")


if __name__ == "__main__":
    add_columns()