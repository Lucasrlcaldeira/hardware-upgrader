from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.modules.analysis.router import router as analysis_router
from app.modules.catalog.router import router as catalog_router
from app.modules.compatibility.router import router as compatibility_router
from app.modules.detection.router import router as detection_router
from app.modules.performance.router import router as performance_router
from app.modules.recommendation.router import router as recommendation_router
from app.modules.users.router import router as users_router

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Diagnóstico de hardware e recomendação de upgrades de PC.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(catalog_router)
app.include_router(detection_router)
app.include_router(compatibility_router)
app.include_router(performance_router)
app.include_router(recommendation_router)
app.include_router(users_router)
app.include_router(analysis_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
