from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Erro base para regras de negócio do domínio (não erros técnicos)."""

    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    status_code = 404


class InsufficientDataError(DomainError):
    """Levantado quando um motor não tem dado suficiente para concluir algo.

    Nunca deve ser usado para "adivinhar" um resultado — é o sinalizador
    explícito de "dado insuficiente para determinar" exigido pelo produto.
    """

    status_code = 422


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )
