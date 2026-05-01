import os
import secrets

os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("LICENSE_MASTER_SECRET", secrets.token_urlsafe(48))
os.environ.setdefault("ACTOR_HASH_SALT", secrets.token_urlsafe(32))
os.environ.setdefault("LEDGER_MASTER_SALT", secrets.token_urlsafe(32))
