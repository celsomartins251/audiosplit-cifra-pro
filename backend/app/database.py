import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/audiosplit.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def apply_sqlite_compat_migrations():
    # Small additive migration for existing development databases.
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "analysis_jobs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("analysis_jobs")}
    additions = {
        "updated_at": "DATETIME",
        "progress": "INTEGER NOT NULL DEFAULT 0",
        "result_json": "TEXT",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE analysis_jobs ADD COLUMN {name} {sql_type}"))
