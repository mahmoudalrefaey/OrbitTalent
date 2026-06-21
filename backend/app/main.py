"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import analytics, auth, candidates, jobs, usage
from app.schemas import HealthOut

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="OrbitTalent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(analytics.router)
app.include_router(usage.router)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    # Public endpoint (pre-login). Per-tenant cost lives behind /usage.
    return HealthOut(
        status="ok",
        llm_enabled=settings.llm_enabled,
        provider=settings.provider,
        today_cost_usd=0.0,
    )
