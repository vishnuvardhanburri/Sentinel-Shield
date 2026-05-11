import os
import sys

import jwt
import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from auth.jwt_handler import JWT_ALGORITHM, JWT_SECRET, JWTHandler, revoke_token_id, verify_refresh_token


def test_access_tokens_include_unique_jti():
    handler = JWTHandler()
    token_a = handler.create_access_token({"sub": "a@example.com", "email": "a@example.com", "role": "STAFF"})
    token_b = handler.create_access_token({"sub": "a@example.com", "email": "a@example.com", "role": "STAFF"})

    payload_a = jwt.decode(token_a, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    payload_b = jwt.decode(token_b, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    assert payload_a["jti"]
    assert payload_b["jti"]
    assert payload_a["jti"] != payload_b["jti"]


def test_refresh_token_cannot_be_used_as_access_token():
    handler = JWTHandler()
    refresh = handler.create_refresh_token({"sub": "a@example.com", "email": "a@example.com", "role": "STAFF"})

    with pytest.raises(HTTPException) as exc:
        handler.verify_token(refresh)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token type"


def test_revoked_token_is_rejected():
    handler = JWTHandler()
    token = handler.create_access_token({"sub": "a@example.com", "email": "a@example.com", "role": "STAFF"})
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    revoke_token_id(payload["jti"])

    with pytest.raises(HTTPException) as exc:
        handler.verify_token(token)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token revoked"


def test_refresh_token_verifier_accepts_only_refresh_tokens():
    handler = JWTHandler()
    refresh = handler.create_refresh_token({"sub": "a@example.com", "email": "a@example.com", "role": "STAFF"})
    access = handler.create_access_token({"sub": "a@example.com", "email": "a@example.com", "role": "STAFF"})

    assert verify_refresh_token(refresh).sub == "a@example.com"
    with pytest.raises(HTTPException) as exc:
        verify_refresh_token(access)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token type"
