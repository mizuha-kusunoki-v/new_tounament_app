import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.tournaments import router as tournaments_router
from app.bootstrap import bootstrap_admin
from app.database import SessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        bootstrap_admin(db)
    except Exception:
        # Never let a bootstrap hiccup (e.g. migrations not yet applied on a
        # fresh instance) prevent the app from starting and serving requests.
        logger.exception("Admin bootstrap failed; continuing startup without it")
    finally:
        db.close()
    yield


app = FastAPI(title="2v2 Shuffle Tournament API", lifespan=lifespan)

# Comma-separated list, e.g. "http://localhost:3000,https://new-tounament-frontend.onrender.com"
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allow_origins = [origin.strip() for origin in _allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tournaments_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}
