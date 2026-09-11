from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    name: str = Field(..., min_length=2, description="Student name")
    student_class: str = Field("10th", description="e.g., 'Class 10' or '10th'")
    preferred_language: str = Field("English", description="English, Telugu, or Hindi")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    student_class: str
    preferred_language: str
    preferred_subjects: str
    learning_level: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StudentProfileUpdate(BaseModel):
    name: Optional[str] = None
    student_class: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_subjects: Optional[str] = None
    learning_level: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime
    profile: Optional[StudentProfileResponse] = None

    class Config:
        from_attributes = True
