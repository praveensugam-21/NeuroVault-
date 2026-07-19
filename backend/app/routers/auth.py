from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import UserCreate, UserResponse, Token, PINSetup, PINVerify, GoogleLoginRequest
from app.services.security import SecurityService
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/config")
def get_auth_config():
    """Returns public authentication config, like Google Client ID."""
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new account within this deployment.
    The first account registered automatically becomes admin.
    Passwords are hashed using Argon2id.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account with this email already registered"
        )

    # First user in the deployment becomes admin
    is_first_user = db.query(User).count() == 0

    hashed_password = SecurityService.get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        is_admin=is_first_user
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Standard OAuth2 password login.
    Returns a short-lived JWT access token (15 min) and a long-lived refresh token (30 days).
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not SecurityService.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Re-hash password with current Argon2 parameters if it was hashed with weaker settings
    if SecurityService.password_needs_rehash(user.hashed_password):
        user.hashed_password = SecurityService.get_password_hash(form_data.password)

    # Generate access + refresh token pair
    access_token = SecurityService.create_access_token(data={"sub": user.email})
    raw_refresh, hashed_refresh = SecurityService.create_refresh_token()

    # Store hashed refresh token (only the hash, never the raw value)
    user.refresh_token_hash = hashed_refresh
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="LOGIN",
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token_str: str, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token + rotated refresh token.
    The old refresh token is immediately invalidated (rotation prevents replay attacks).
    """
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token"
    )

    # Find user with a stored refresh token hash
    users = db.query(User).filter(User.refresh_token_hash.isnot(None)).all()
    matched_user = None
    for u in users:
        if SecurityService.verify_refresh_token(refresh_token_str, u.refresh_token_hash):
            matched_user = u
            break

    if not matched_user:
        raise invalid_exc

    # Rotate: generate new token pair
    access_token = SecurityService.create_access_token(data={"sub": matched_user.email})
    raw_refresh, hashed_refresh = SecurityService.create_refresh_token()
    matched_user.refresh_token_hash = hashed_refresh
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer"
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invalidate the user's refresh token. Future refresh requests will fail until next login.
    """
    current_user.refresh_token_hash = None
    audit = AuditLog(user_id=current_user.id, action="LOGOUT")
    db.add(audit)
    db.commit()
    return {"message": "Logged out successfully. Refresh token revoked."}


@router.post("/pin/setup", status_code=status.HTTP_200_OK)
def setup_pin(
    pin_data: PINSetup,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """Configure a secondary PIN for locking/unlocking sensitive documents."""
    hashed_pin = SecurityService.get_password_hash(pin_data.pin)
    current_user.pin_hash = hashed_pin
    db.commit()
    return {"message": "Security PIN successfully configured."}


@router.post("/pin/verify", status_code=status.HTTP_200_OK)
def verify_pin(
    pin_data: PINVerify,
    current_user: User = Depends(SecurityService.get_current_user)
):
    """Verify the secondary security PIN."""
    if not current_user.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No security PIN has been set up for this account."
        )
    if not SecurityService.verify_password(pin_data.pin, current_user.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect security PIN."
        )
    return {"message": "PIN verified."}


@router.get("/audit-logs", response_model=List[dict])
def get_audit_logs(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the last 50 security audit log entries for the current user.
    Gives complete transparency over who did what and when.
    """
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id
    ).order_by(AuditLog.timestamp.desc()).limit(50).all()

    return [
        {
            "id": l.id,
            "action": l.action,
            "document_id": l.document_id,
            "ip_address": l.ip_address,
            "timestamp": l.timestamp
        }
        for l in logs
    ]


@router.post("/google/verify", response_model=Token)
def verify_google(
    payload: GoogleLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verify Google OAuth2 ID token.
    If valid, authenticates the user, auto-linking or registering as needed.
    """
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    try:
        client_id = settings.GOOGLE_CLIENT_ID
        id_info = id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            client_id if client_id else None
        )
        
        if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
            
        google_id = id_info.get("sub")
        email = id_info.get("email")
        if not google_id or not email:
            raise ValueError("Token missing google_id or email.")
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find user by Google ID or by Email (for auto-linking)
    user = db.query(User).filter(
        (User.oauth_id == google_id) | (User.email == email)
    ).first()

    if not user:
        # Create a new Google OAuth user
        is_first_user = db.query(User).count() == 0
        user = User(
            email=email,
            oauth_provider="google",
            oauth_id=google_id,
            is_admin=is_first_user
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Auto-link: if user was registered with standard email/password or had different OAuth state,
        # update it to Google OAuth parameters.
        updated = False
        if user.oauth_provider != "google":
            user.oauth_provider = "google"
            updated = True
        if user.oauth_id != google_id:
            user.oauth_id = google_id
            updated = True
        if updated:
            db.commit()

    # Generate access + refresh token pair
    access_token = SecurityService.create_access_token(data={"sub": user.email})
    raw_refresh, hashed_refresh = SecurityService.create_refresh_token()

    user.refresh_token_hash = hashed_refresh
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="LOGIN_GOOGLE",
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer"
    }


from pydantic import BaseModel
from typing import Optional

class AIConfigRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None

@router.get("/ai-config")
def get_ai_config(current_user: User = Depends(SecurityService.get_current_user)):
    """
    Returns the current active AI configuration (Gemini & Ollama settings),
    masking the Gemini API key for security.
    """
    # Only admins can view the AI settings
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can view AI configuration.")

    raw_key = settings.GEMINI_API_KEY or ""
    masked_key = ""
    if raw_key:
        if len(raw_key) > 8:
            masked_key = f"{raw_key[:5]}...{raw_key[-4:]}"
        else:
            masked_key = "********"

    return {
        "gemini_api_key": masked_key,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "gemini_model": settings.GEMINI_MODEL,
        "ollama_model": settings.OLLAMA_MODEL
    }

@router.post("/ai-config")
def update_ai_config(
    payload: AIConfigRequest,
    current_user: User = Depends(SecurityService.get_current_user)
):
    """
    Updates the active AI configuration. Writes to the persistent uploads/custom_settings.json
    and hot-reloads the settings in memory.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can update AI configuration.")

    import os
    import json
    custom_path = os.path.join(settings.UPLOADS_DIR, "custom_settings.json")

    # Read existing custom config if it exists
    custom_data = {}
    if os.path.exists(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                custom_data = json.load(f)
        except Exception:
            custom_data = {}

    has_updates = False
    if payload.gemini_api_key is not None:
        key_stripped = payload.gemini_api_key.strip()
        # Only write if it's not the masked placeholder
        if "..." not in key_stripped and key_stripped != "********":
            custom_data["GEMINI_API_KEY"] = key_stripped
            settings.GEMINI_API_KEY = key_stripped
            
            # Reset GeminiService broken state so it re-verifies the new key
            from app.services.gemini_service import GeminiService
            GeminiService._broken = False
            GeminiService._verified = False
            GeminiService._client = None
            has_updates = True

    if payload.ollama_base_url is not None:
        url_stripped = payload.ollama_base_url.strip()
        custom_data["OLLAMA_BASE_URL"] = url_stripped
        settings.OLLAMA_BASE_URL = url_stripped
        
        # Reset Ollama client check if applicable
        from app.services.ollama_service import OllamaService
        has_updates = True

    if has_updates:
        # Write back to persistent uploads directory
        try:
            with open(custom_path, "w", encoding="utf-8") as f:
                json.dump(custom_data, f, indent=4)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to persist custom settings: {str(e)}")

    return {"message": "AI configuration updated successfully."}

