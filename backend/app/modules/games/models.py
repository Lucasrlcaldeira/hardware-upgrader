from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Game(Base):
    """Um jogo com dado de benchmark real cadastrado. Não é o catálogo de hardware — é um
    conjunto deliberadamente pequeno, só com jogos para os quais há benchmark real e citável
    (ver GameBenchmark). Um jogo digitado pelo usuário que não está aqui significa
    'sem dado real disponível', nunca é motivo para estimar/inventar um número."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class GameBenchmark(Base):
    """Um resultado de benchmark real e citado: (jogo, GPU, resolução) -> FPS médio medido
    por terceiros. Nunca é um número calculado/estimado pelo sistema — cada linha tem uma
    fonte (site + CPU usado no teste) rastreável em source_url. O preset de qualidade nem
    sempre é declarado pela fonte original; quality_preset_note torna essa incerteza
    explícita em vez de fingir precisão que não existe."""

    __tablename__ = "game_benchmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    gpu_id: Mapped[int] = mapped_column(ForeignKey("gpu_models.id"), index=True)
    resolution: Mapped[str] = mapped_column(String(10))
    avg_fps: Mapped[int] = mapped_column(Integer)
    test_cpu_model: Mapped[str] = mapped_column(String(100))
    quality_preset_note: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(300))
