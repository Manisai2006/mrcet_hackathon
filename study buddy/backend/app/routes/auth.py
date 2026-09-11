from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, StudentProfile
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse, StudentProfileResponse, StudentProfileUpdate
from app.auth.security import get_password_hash, verify_password, create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication & Profile"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_student(user_in: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )
    
    # Create user
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create associated student profile
    new_profile = StudentProfile(
        user_id=new_user.id,
        name=user_in.name,
        student_class=user_in.student_class,
        preferred_language=user_in.preferred_language
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.post("/login", response_model=Token)
def login_student(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email, "id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout_student():
    # Client removes JWT token from localStorage/headers
    return {"message": "Successfully logged out."}

@router.get("/me", response_model=UserResponse)
def get_current_student_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=StudentProfileResponse)
def update_student_profile(
    profile_update: StudentProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    if profile_update.name is not None:
        profile.name = profile_update.name
    if profile_update.student_class is not None:
        profile.student_class = profile_update.student_class
    if profile_update.preferred_language is not None:
        profile.preferred_language = profile_update.preferred_language
    if profile_update.preferred_subjects is not None:
        profile.preferred_subjects = profile_update.preferred_subjects
    if profile_update.learning_level is not None:
        profile.learning_level = profile_update.learning_level

    db.commit()
    db.refresh(profile)
    return profile
