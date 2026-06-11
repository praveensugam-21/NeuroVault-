from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class PINSetup(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, pattern="^[0-9]+$", description="PIN must be 4 to 6 numeric digits")

class PINVerify(BaseModel):
    pin: str
