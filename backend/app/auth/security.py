"""Password hashing and JWT issuance/verification for admin accounts.

Deliberately independent of the manage_token/public_slug capability-URL
scheme used elsewhere in this app -- those remain unchanged for actually
running a tournament. This is only for the admin dashboard (list every
tournament, delete one, manage other admin accounts).
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

JWT_ALGORITHM = "HS256"
JWT_EXPIRY = timedelta(days=7)


def _jwt_secret() -> str:
    # Read lazily (not at import time) so a missing env var only breaks
    # actual login/verification, not merely importing this module.
    return os.environ["ADMIN_JWT_SECRET"]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": username, "iat": now, "exp": now + JWT_EXPIRY}
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
