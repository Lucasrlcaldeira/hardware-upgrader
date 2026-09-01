import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.users.models import User


class AnalysisHistory(Base):
    """Snapshot persistido de uma análise completa já executada.

    O relatório (compatibilidade atual + gargalo + recomendações) é guardado como JSON —
    é o retrato do resultado no momento da análise, não dado normalizado para consulta.
    O catálogo pode mudar depois sem afetar análises já registradas no histórico.
    """

    __tablename__ = "analysis_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile: Mapped[str] = mapped_column(String(30), index=True)
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=lambda: dt.datetime.now(dt.UTC), index=True
    )

    user: Mapped["User"] = relationship(back_populates="analyses")
