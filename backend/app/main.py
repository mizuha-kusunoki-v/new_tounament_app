from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tournaments import router as tournaments_router

app = FastAPI(title="2v2 Shuffle Tournament API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tournaments_router)


@app.get("/health")
def health():
    return {"status": "ok"}
