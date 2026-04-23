from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.core.diag import _boot, _ready
from app.db.session import SessionLocal
from app.routers.auth import router as auth_router
from app.routers.geospatial import router as geospatial_router
from app.routers.health import router as health_router
from app.services.auth import ensure_default_user
from app.services.places import warm_cache

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        warm_cache(db)
        ensure_default_user(db)
    _boot()
    yield


app = FastAPI(title="Toroto Geospatial API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _auth_gate(request: Request, call_next):
    if not _ready() and request.url.path.startswith("/geospatial"):
        return JSONResponse({"detail": "Service unavailable"}, status_code=503)

    if request.url.path.startswith("/geospatial"):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)
        try:
            jwt.decode(
                auth_header[7:],
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

    return await call_next(request)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(geospatial_router)
