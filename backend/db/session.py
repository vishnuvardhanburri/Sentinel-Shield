"""
Sentinel Shield v2 — Database Session Manager
Supports PostgreSQL (cloud) and SQLite (air-gap) via DATABASE_URL env var.
"""
import os
from sqlalchemy import create_engine
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
    seed_db()


def seed_db():
    """Seed the database with a default Super Admin if empty."""
    db = SessionLocal()
    try:
        # Check if users table is empty
        admin_exists = db.query(User).filter(User.email == "admin@demo.com").first()
        if not admin_exists:
            # Using a simplified hash approach to bypass cloud library conflicts
            hashed_pwd = pwd_context.hash("demo1234")
            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin@demo.com",
                full_name="Sentinel Master Admin",
                hashed_password=hashed_pwd,
                role="SUPER_ADMIN",
                department="GLOBAL_SECURITY",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("🛡️ SENTINEL DB: Default Master Admin seeded successfully. [READY]")
        else:
            print("🛡️ SENTINEL DB: Master Admin already exists. [READY]")
    except Exception as e:
        print(f"❌ SENTINEL DB ERROR: Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
