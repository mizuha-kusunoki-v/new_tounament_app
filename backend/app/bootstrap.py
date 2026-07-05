"""Creates the very first admin account from env vars on startup, so a
Render free-tier deployment (no shell access) can still get its first admin
without a CLI. Only acts when admin_users is completely empty -- safe to run
on every restart. Any admin after the first is created through the app
itself (POST /admin/users), no env vars or shell needed for those."""

import logging
import os

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models import AdminUser

logger = logging.getLogger(__name__)


def bootstrap_admin(db: Session) -> None:
    if db.query(AdminUser).count() > 0:
        return

    username = os.getenv("ADMIN_BOOTSTRAP_USERNAME")
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
    if not username or not password:
        logger.warning(
            "No admin_users exist and ADMIN_BOOTSTRAP_USERNAME/ADMIN_BOOTSTRAP_PASSWORD "
            "are unset; skipping admin bootstrap."
        )
        return

    db.add(AdminUser(username=username, password_hash=hash_password(password)))
    db.commit()
    logger.info("Bootstrapped initial admin user %r", username)
