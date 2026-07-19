import secrets
from datetime import datetime, timedelta
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

# OAuth2 scheme for Authorization: Bearer header extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Argon2id hasher — the most secure variant of Argon2
# Parameters are tuned for a good security/performance balance on commodity hardware
_argon2_hasher = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,  # 64 MB of memory
    parallelism=4,      # Number of parallel threads
    hash_len=32,        # Length of the hash in bytes
    salt_len=16         # Length of the random salt in bytes
)


class SecurityService:

    # ── Password Hashing (Argon2id) ──────────────────────────────────────────

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a plain-text password using Argon2id."""
        return _argon2_hasher.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain-text password against an Argon2id hash.
        Also handles legacy bcrypt hashes transparently.
        """
        # Try Argon2 first
        try:
            return _argon2_hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            pass

        # Fallback: attempt bcrypt verification for migrated legacy accounts
        try:
            import bcrypt
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    @staticmethod
    def password_needs_rehash(hashed_password: str) -> bool:
        """
        Argon2 can detect whether a hash was generated with weaker parameters.
        If so, we should rehash on next login.
        """
        try:
            return _argon2_hasher.check_needs_rehash(hashed_password)
        except Exception:
            return False

    # ── JWT Access Tokens ────────────────────────────────────────────────────

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a short-lived JWT access token (default 15 minutes)."""
        from datetime import timezone
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # ── Refresh Tokens ───────────────────────────────────────────────────────

    @staticmethod
    def create_refresh_token() -> tuple[str, str]:
        """
        Generate a cryptographically secure refresh token.
        Returns (raw_token, hashed_token).
        The raw token is sent to the client; only the hash is stored in the DB.
        """
        raw_token = secrets.token_urlsafe(64)
        hashed = _argon2_hasher.hash(raw_token)
        return raw_token, hashed

    @staticmethod
    def verify_refresh_token(raw_token: str, stored_hash: str) -> bool:
        """Verify a raw refresh token against the stored Argon2 hash."""
        try:
            return _argon2_hasher.verify(stored_hash, raw_token)
        except Exception:
            return False

    # ── Current User Dependency ──────────────────────────────────────────────

    @staticmethod
    def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> User:
        """
        FastAPI dependency: validates JWT access token and returns the active User.
        Raises HTTP 401 if the token is missing, expired, or tampered with.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            email: str = payload.get("sub")
            token_type: str = payload.get("type")
            if email is None or token_type != "access":
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise credentials_exception

        # Rehash password silently on next login if Argon2 params have been upgraded
        if SecurityService.password_needs_rehash(user.hashed_password):
            pass  # Will be handled at login time with fresh plain-text password

        return user
