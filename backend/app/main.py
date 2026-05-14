from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.admin import router as admin_router
from app.api.game import router as game_router
from app.api.fleet import router as fleet_router

settings = get_settings()

app = FastAPI(
    title="Forente Planeter API",
    version="0.1.0",
    description="Space strategy game — tick-based",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.game_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(game_router)
app.include_router(fleet_router)


@app.get("/health")
async def health():
    return {"status": "ok", "game": settings.game_name}
