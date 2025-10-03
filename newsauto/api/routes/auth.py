"""Authentication endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from newsauto.core.config import Settings, get_settings
from newsauto.core.database import get_db
from newsauto.models.user import User

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str
    expires_in: int


class UserCreate(BaseModel):
    """User creation model."""

    email: str
    username: str
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""

    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool

    class Config:
        from_attributes = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None, settings: Settings = None
):
    """Create JWT token."""
    if settings is None:
        settings = get_settings()

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Register a new user."""
    if not settings.enable_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Registration is disabled"
        )

    # Check if user exists
    existing = (
        db.query(User)
        .filter((User.email == user_data.email) | (User.username == user_data.username))
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Login and get access token."""
    # Authenticate user
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create token
    access_token = create_access_token(data={"sub": user.username}, settings=settings)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiration_hours * 3600,
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout (client should discard token)."""
    return {"message": "Successfully logged out"}
