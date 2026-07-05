import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-pytest-only")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        # Exposed so tests can seed rows (e.g. an AdminUser) directly into
        # this test's isolated in-memory DB, bypassing the HTTP layer for setup.
        test_client.SessionLocal = TestingSessionLocal
        yield test_client
    app.dependency_overrides.clear()
