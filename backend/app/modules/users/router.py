from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.users import schemas, service
from app.modules.users.models import User

router = APIRouter(prefix="/users", tags=["users"])
_bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = service.decode_access_token(credentials.credentials)
    user = service.get_user_by_id(db, user_id)
    if user is None:
        raise service.InvalidCredentialsError("Usuário do token não existe mais.")
    return user


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    return service.create_user(db, payload)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.Token:
    user = service.authenticate(db, payload.email, payload.password)
    return schemas.Token(access_token=service.create_access_token(user))


@router.get("/me", response_model=schemas.UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
