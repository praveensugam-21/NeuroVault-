from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class UserLogin(UserBase):
    password: str


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_admin: bool = False
    oauth_provider: str = "local"
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class PINSetup(BaseModel):
    pin: str = Field(
        ...,
        min_length=4,
        max_length=6,
        pattern="^[0-9]+$",
        description="PIN must be 4 to 6 numeric digits"
    )


class PINVerify(BaseModel):
    pin: str


class GoogleLoginRequest(BaseModel):
    id_token: str
