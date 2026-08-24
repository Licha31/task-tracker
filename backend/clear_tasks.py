from sqlalchemy import text

from app.database import engine


with engine.begin() as connection:
    connection.execute(text("DELETE FROM tasks"))

print("Tasks cleared.")