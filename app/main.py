"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import system, webhooks
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In dev we auto-create tables for convenience. In production, migrations
    # (alembic) own the schema — see alembic/ and README.
    if not settings.is_production:
        from app.db.session import Base, engine
        from app.models import models  # noqa: F401  (register models on Base)

        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(system.router)
app.include_router(webhooks.router)


@app.get("/")
def root():
    return {"service": settings.app_name, "docs": "/docs"}
