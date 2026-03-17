"""
routes/auth.py — Authentication & profile endpoints
────────────────────────────────────────────────────
POST /auth/register  – create passenger account
POST /auth/login     – return JWT token
GET  /auth/me        – current user + profile
PUT  /auth/profile   – update PassengerProfile
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
)
from ..database import get_db
from ..models import PassengerProfile, User, UserRole
from ..schemas import (
    PassengerProfileOut,
    PassengerProfileUpdate,
    Token,
    UserLogin,
    UserOut,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ──────────────────────────────────────────────────────
#  Register
# ──────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new passenger account",
)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> UserOut:
    """
    Create a new **passenger** user.
    An empty `PassengerProfile` is created automatically — it must be
    completed (passport number) before the user can make a booking.
    """
    user = create_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        db=db,
    )
    return user


# ──────────────────────────────────────────────────────
#  Login
# ──────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive JWT access token",
)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    Authenticate with email / password and receive a **Bearer** JWT token.
    Include it in subsequent requests as:
    `Authorization: Bearer <token>`
    """
    user = authenticate_user(payload.email, payload.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Lazy-create profile if missing (safety net for legacy accounts)
    if user.role == UserRole.passenger and user.profile is None:
        db.add(PassengerProfile(user_id=user.id))
        db.commit()

    return Token(access_token=create_access_token(user_id=user.id))


# ──────────────────────────────────────────────────────
#  Me
# ──────────────────────────────────────────────────────

@router.get(
    "/me",
    summary="Get current user and passenger profile",
)
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    """Return the authenticated user's info and their `PassengerProfile`."""
    profile_out = (
        PassengerProfileOut.model_validate(current_user.profile)
        if current_user.profile
        else None
    )
    return {
        "user": UserOut.model_validate(current_user),
        "profile": profile_out,
    }


# ──────────────────────────────────────────────────────
#  Update profile
# ──────────────────────────────────────────────────────

@router.put(
    "/profile",
    response_model=PassengerProfileOut,
    summary="Update passenger profile",
)
def update_profile(
    payload: PassengerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PassengerProfileOut:
    """
    Partially update the authenticated user's `PassengerProfile`.
    Only fields that are **provided** (non-null) in the request body are saved.
    """
    profile: Optional[PassengerProfile] = current_user.profile
    if profile is None:
        # safety net — create if somehow missing
        profile = PassengerProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
