"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api import portal, system, webhooks
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

# Signs the session cookie the portal login uses. settings.secret_key has a
# dev-only default — set a real one in .env before deploying anywhere real.
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.include_router(system.router)
app.include_router(webhooks.router)
app.include_router(portal.router)


@app.get("/")
def root():
    return {"service": settings.app_name, "docs": "/docs"}
