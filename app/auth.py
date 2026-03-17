"""
auth.py — Business logic for authentication
────────────────────────────────────────────
Contains:
  • Password hashing / verification  (passlib + bcrypt)
  • JWT creation / decoding          (python-jose)
  • FastAPI dependencies             (get_current_user, role guards)

Routes do NOT contain any of this logic — they call these functions.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole
from .schemas import TokenData

# ──────────────────────────────────────────────────────
#  Configuration  (change SECRET_KEY in production!)
# ──────────────────────────────────────────────────────

SECRET_KEY = "CHANGE-ME-IN-PRODUCTION-USE-32+-RANDOM-CHARS"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ──────────────────────────────────────────────────────
#  Password hashing
# ──────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain[:72])


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain[:72], hashed)


# ──────────────────────────────────────────────────────
#  JWT helpers
# ──────────────────────────────────────────────────────

def create_access_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create and return a signed JWT access token.

    Payload:
      sub  – str(user_id)
      exp  – expiry timestamp
    """
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate the JWT.
    Returns TokenData on success, None on any error.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        raw_id: str = payload.get("sub")
        if raw_id is None:
            return None
        return TokenData(user_id=int(raw_id))
    except (JWTError, ValueError):
        return None


# ──────────────────────────────────────────────────────
#  User authentication helpers
# ──────────────────────────────────────────────────────

def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    Look up user by email and verify password.
    Returns the User object on success, None otherwise.
    """
    user: Optional[User] = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(email: str, password: str, full_name: str, db: Session) -> User:
    """
    Register a new passenger user.
    Raises HTTPException 409 if the email is already taken.
    Auto-creates an empty PassengerProfile.
    """
    from .models import PassengerProfile  # local import avoids circular issues

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=UserRole.passenger,
    )
    db.add(user)
    db.flush()  # get user.id without full commit

    # Auto-create empty profile — required for booking
    db.add(PassengerProfile(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


# ──────────────────────────────────────────────────────
#  FastAPI dependencies
# ──────────────────────────────────────────────────────

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extract and validate bearer token,
    then return the corresponding active User from the DB.
    """
    token_data = _decode_token(token)
    if token_data is None:
        raise _CREDENTIALS_EXCEPTION

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise _CREDENTIALS_EXCEPTION
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    return user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Dependency — allow only staff or admin."""
    if current_user.role not in (UserRole.staff, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency — allow only admin."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
