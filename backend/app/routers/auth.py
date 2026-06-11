from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import UserCreate, UserResponse, Token, PINSetup, PINVerify
from app.services.security import SecurityService


router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new account. Hashes the password.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account with this email already registered"
        )
    
    hashed_password = SecurityService.get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Standard OAuth2 password flow login. Returns JWT access token.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not SecurityService.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = SecurityService.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/pin/setup", status_code=status.HTTP_200_OK)
def setup_pin(pin_data: PINSetup, current_user: User = Depends(SecurityService.get_current_user), db: Session = Depends(get_db)):
    """
    Configures a secondary PIN to lock/unlock highly sensitive files.
    """
    hashed_pin = SecurityService.get_password_hash(pin_data.pin)
    current_user.pin_hash = hashed_pin
    db.commit()
    return {"message": "Security PIN successfully configured."}

@router.post("/pin/verify", status_code=status.HTTP_200_OK)
def verify_pin(pin_data: PINVerify, current_user: User = Depends(SecurityService.get_current_user)):
    """
    Verifies secondary security PIN.
    """
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
    Returns list of audit logs for security transparency.
    """
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id
    ).order_by(AuditLog.timestamp.desc()).limit(30).all()
    
    return [
        {
            "id": l.id,
            "action": l.action,
            "document_id": l.document_id,
            "timestamp": l.timestamp
        } for l in logs
    ]

