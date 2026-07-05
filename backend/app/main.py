import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tournaments import router as tournaments_router

app = FastAPI(title="2v2 Shuffle Tournament API")

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


@app.get("/health")
def health():
    return {"status": "ok"}
