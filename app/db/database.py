import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Environment detection
ENV = os.getenv("ENVIRONMENT", "local")  # local, cloud_run, or proxy

DB_NAME = os.getenv("DB_NAME", "app_db")
# For local development on macOS Homebrew, default to current system user
# For cloud/proxy, use app_user
if ENV == "local":
    import getpass
    DB_USER = os.getenv("DB_USER", getpass.getuser())
else:
    DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "")

if ENV == "cloud_run":
    # Cloud Run with Unix socket connection
    INSTANCE_CONN_NAME = os.getenv("INSTANCE_CONN_NAME")
    DB_SOCKET_DIR = "/cloudsql"
    encoded_password = quote_plus(DB_PASS) if DB_PASS else ""
    DATABASE_URL = (
        f"postgresql+psycopg://{DB_USER}:{encoded_password}@/{DB_NAME}"
        f"?host={DB_SOCKET_DIR}/{INSTANCE_CONN_NAME}"
    )
elif ENV == "proxy":
    # VPS proxy connecting via Cloud SQL Proxy (TCP on localhost:5432)
    encoded_password = quote_plus(DB_PASS) if DB_PASS else ""
    DATABASE_URL = (
        f"postgresql+psycopg://{DB_USER}:{encoded_password}@localhost:5432/{DB_NAME}"
    )
else:
    # Local development - use standard PostgreSQL connection
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    encoded_password = quote_plus(DB_PASS) if DB_PASS else ""
    DATABASE_URL = (
        f"postgresql+psycopg://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=2,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency for getting a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()