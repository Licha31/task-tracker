from app.database import engine
from app.models import Task


def add_unique_index():
    with engine.begin() as connection:
        for index in Task.__table__.indexes:
            index.create(bind=connection, checkfirst=True)

    print("Tasks unique index created.")


if __name__ == "__main__":
    add_unique_index()
