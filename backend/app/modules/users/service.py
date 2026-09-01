import datetime as dt

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.modules.users import models
from app.modules.users.schemas import UserCreate

# pbkdf2_sha256 em vez de bcrypt: puramente Python, sem dependência de extensão nativa —
# evita a incompatibilidade conhecida entre passlib e versões recentes do pacote `bcrypt`.
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class InvalidCredentialsError(DomainError):
    status_code = 401


class EmailAlreadyRegisteredError(DomainError):
    status_code = 409


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(password, hashed_password)


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.scalar(select(models.User).where(models.User.email == email))


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def create_user(db: Session, data: UserCreate) -> models.User:
    if get_user_by_email(db, data.email) is not None:
        raise EmailAlreadyRegisteredError(
            f"Já existe um usuário cadastrado com o email '{data.email}'."
        )
    user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> models.User:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Email ou senha inválidos.")
    return user


def create_access_token(user: models.User) -> str:
    settings = get_settings()
    expire = dt.datetime.now(dt.UTC) + dt.timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": str(user.id), "email": user.email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidCredentialsError("Token inválido ou expirado.") from exc
    subject = payload.get("sub")
    if subject is None:
        raise InvalidCredentialsError("Token inválido.")
    return int(subject)
