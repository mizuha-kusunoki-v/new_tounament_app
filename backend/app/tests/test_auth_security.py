import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-pytest-only")

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth import security


def test_hash_password_roundtrip():
    hashed = security.hash_password("correct-horse-battery-staple")
    assert security.verify_password("correct-horse-battery-staple", hashed)
    assert not security.verify_password("wrong-password", hashed)


def test_hash_password_is_salted():
    h1 = security.hash_password("same-password")
    h2 = security.hash_password("same-password")
    assert h1 != h2


def test_create_and_decode_access_token_roundtrip():
    token = security.create_access_token("alice")
    payload = security.decode_access_token(token)
    assert payload["sub"] == "alice"


def test_decode_rejects_tampered_token():
    token = security.create_access_token("alice")
    header, payload, signature = token.split(".")
    # Reverse the signature rather than flipping one character: a single
    # flipped base64 character can, depending on bit alignment, decode to
    # the same underlying byte and leave the signature accidentally valid,
    # making this assertion flaky. Reversing 32+ bytes of HMAC output isn't.
    tampered = f"{header}.{payload}.{signature[::-1]}"
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(tampered)


def test_decode_rejects_expired_token():
    now = datetime.now(timezone.utc)
    expired_payload = {"sub": "alice", "iat": now - timedelta(days=10), "exp": now - timedelta(days=3)}
    expired_token = jwt.encode(expired_payload, security._jwt_secret(), algorithm=security.JWT_ALGORITHM)
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(expired_token)
