# app/routers/auth.py
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from app.database import get_db
from app.models import User, RefreshToken, UserRole
from app.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from app.auth.jwt import create_access_token, create_refresh_token, hash_token
from app.auth.rbac import require_admin
from app.auth.jwt import get_current_user
from app.config import settings
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user. Default role: UPLOADER."""
    # Check email not already taken
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.UPLOADER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log.info("user_registered", user_id=str(user.id), email=user.email)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with email + password. Returns access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Use consistent timing to prevent user enumeration
    if not user or not verify_password(body.password, user.hashed_password):
        log.warning("login_failed", email=body.email, ip=request.client.host)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Create tokens
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )
    raw_refresh, hashed_refresh = create_refresh_token()

    # Persist refresh token
    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=request.client.host,
    )
    db.add(refresh_entry)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    log.info("user_logged_in", user_id=str(user.id), email=user.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new token pair (rotation)."""
    token_hash = hash_token(body.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
        )
    )
    stored = result.scalar_one_or_none()

    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old token (rotation — each refresh token is single-use)
    stored.revoked = True

    # Load user
    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    # Issue new pair
    access_token = create_access_token(str(user.id), user.email, user.role.value)
    raw_refresh, hashed_refresh = create_refresh_token()

    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Revoke a refresh token on logout."""
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if stored:
        stored.revoked = True
        await db.commit()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Return the currently authenticated user's profile."""
    result = await db.execute(select(User).where(User.id == current_user["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_admin)])
async def update_user_role(
    user_id: str,
    role: UserRole,
    db: AsyncSession = Depends(get_db),
):
    """Admin only: change a user's role."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    await db.commit()
    return {"user_id": user_id, "new_role": role}
