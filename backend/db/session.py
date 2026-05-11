"""
Sovereign Shield v2 — Database Session Manager
Supports PostgreSQL (cloud) and SQLite (air-gap) via DATABASE_URL env var.
"""
import os
import secrets
from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import uuid
from passlib.context import CryptContext
from .models import Base, User

# Password hashing context (Using PBKDF2-SHA256 for cloud-native stability)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# DATABASE_URL examples:
#   PostgreSQL (cloud):  postgresql+psycopg2://user:pass@host:5432/sentinel
#   SQLite (air-gap):    sqlite:///./sentinel.db   ← default
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '../../sentinel.db'))}"
elif DATABASE_URL.startswith("postgresql://"):
    # SQLAlchemy requires postgresql+psycopg2 for the postgres driver
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# SQLite needs check_same_thread=False for multi-threaded FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """Create all tables and seed default admin. Call on startup."""
    Base.metadata.create_all(bind=engine)
    _ensure_user_metadata_column()
    _ensure_api_key_table()
    _ensure_user_session_device_columns()
    seed_db()


def seed_db():
    """First-run bootstrap: create one Super Admin with a random temporary password."""
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == "SUPER_ADMIN").first()
        if not admin_exists:
            admin_email = os.getenv("FIRST_RUN_ADMIN_EMAIL", "admin@sovereign.local")
            temporary_password = secrets.token_urlsafe(24)
            admin_user = User(
                id=str(uuid.uuid4()),
                email=admin_email,
                full_name="Sovereign Shield First-Run Admin",
                hashed_password=pwd_context.hash(temporary_password),
                role="SUPER_ADMIN",
                department="GLOBAL_SECURITY",
                is_active=True,
                metadata_={"force_password_change": True, "first_run_bootstrap": True},
            )
            db.add(admin_user)
            db.commit()
            print("CRITICAL FIRST-RUN BOOTSTRAP CREDENTIALS")
            print(f"Admin email: {admin_email}")
            print(f"Temporary password: {temporary_password}")
            print("Change this password immediately after first login. It will not be printed again.")
        else:
            print("SOVEREIGN DB: Super Admin exists. [READY]")
    except Exception as e:
        print(f"❌ SOVEREIGN DB ERROR: Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()


def _ensure_user_metadata_column():
    """Best-effort SQLite migration for older local buyer/demo databases."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("users")} if inspector.has_table("users") else set()
    if "metadata" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN metadata JSON DEFAULT '{}'"))


def _ensure_api_key_table():
    """Create API key table for older local databases."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    Base.metadata.tables["api_keys"].create(bind=engine, checkfirst=True)


def _ensure_user_session_device_columns():
    """Best-effort SQLite migration for cross-platform device sessions."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if not inspector.has_table("user_sessions"):
        Base.metadata.tables["user_sessions"].create(bind=engine, checkfirst=True)
        return
    columns = {col["name"] for col in inspector.get_columns("user_sessions")}
    additions = {
        "device_id": "VARCHAR(128)",
        "device_name": "VARCHAR(255)",
        "platform": "VARCHAR(50)",
        "app_version": "VARCHAR(50)",
        "refresh_jti": "VARCHAR(128)",
        "revoked_at": "DATETIME",
    }
    with engine.begin() as conn:
        for column, column_type in additions.items():
            if column not in columns:
                conn.execute(text(f"ALTER TABLE user_sessions ADD COLUMN {column} {column_type}"))


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
