
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from .env")

engine = create_engine(database_url, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT version(), current_database()")
        )
        version, database_name = result.one()

        print("Neon connection successful!")
        print("Database:", database_name)
        print("PostgreSQL version:", version)

except Exception as exc:
    print("Neon connection failed:", exc)

finally:
    engine.dispose()
