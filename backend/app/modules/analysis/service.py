from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.analysis import models
from app.modules.analysis.schemas import AnalysisReport, AnalysisRequest
from app.modules.compatibility import service as compatibility_service
from app.modules.compatibility.schemas import CompatibilityCheckRequest
from app.modules.recommendation import service as recommendation_service
from app.modules.recommendation.schemas import RecommendationRequest
from app.modules.users.models import User


def build_report(db: Session, request: AnalysisRequest) -> AnalysisReport:
    system = request.system

    # Compatibilidade do sistema JÁ MONTADO do usuário — distinto das checagens de
    # compatibilidade feitas internamente pelo motor de recomendação sobre candidatos de
    # upgrade. Isso é o que permite o relatório apontar, por exemplo, que a fonte atual do
    # usuário já está subdimensionada para a GPU atual, independente de qualquer upgrade.
    current_compat = compatibility_service.run_compatibility_check(
        db,
        CompatibilityCheckRequest(
            cpu_model_name=system.cpu_model_name,
            gpu_model_name=system.gpu_model_name,
            motherboard_model_name=system.motherboard_model_name,
            ram_model_name=system.ram_model_name,
            storage_model_name=system.storage_model_name,
            psu_model_name=system.psu_model_name,
            case_model_name=system.case_model_name,
            cooler_model_name=system.cooler_model_name,
        ),
    )

    recommendation = recommendation_service.generate_recommendations(
        db,
        RecommendationRequest(
            system=system,
            profile=request.profile,
            resolution=request.resolution,
            graphics_quality=request.graphics_quality,
            target_fps=request.target_fps,
            workload_type=request.workload_type,
        ),
    )

    return AnalysisReport(
        system=system,
        profile=request.profile,
        current_compatibility=current_compat.results,
        bottleneck=recommendation.bottleneck,
        bottleneck_note=recommendation.bottleneck_note,
        recommendations=recommendation.recommendations,
        bundle=recommendation.bundle,
        summary=recommendation.summary,
    )


def run_analysis(db: Session, user: User, request: AnalysisRequest) -> models.AnalysisHistory:
    report = build_report(db, request)
    history = models.AnalysisHistory(
        user_id=user.id,
        profile=request.profile.value,
        report=report.model_dump(mode="json"),
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def list_history(db: Session, user: User, limit: int = 20) -> list[models.AnalysisHistory]:
    stmt = (
        select(models.AnalysisHistory)
        .where(models.AnalysisHistory.user_id == user.id)
        .order_by(models.AnalysisHistory.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_history_entry(db: Session, user: User, history_id: int) -> models.AnalysisHistory:
    entry = db.get(models.AnalysisHistory, history_id)
    if entry is None or entry.user_id != user.id:
        raise NotFoundError(f"Análise '{history_id}' não encontrada.")
    return entry
