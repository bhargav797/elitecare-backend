from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Response

from fastapi import Depends
from app.dependencies.auth import get_current_user
from app.database import get_db
from app.schemas.auth import LoginSchema, RegisterSchema
from app.models.user import User
from app.core.security import (
    create_access_token,
    verify_password,
    hash_password
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/login")
def login(
    data: LoginSchema,
    response: Response,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        {
            "sub": user.email,
            "role": user.role
        },
        expires_minutes=60
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,      # set True in production (HTTPS)
        samesite="lax",
        path="/",
        max_age=60 * 60
    )

    return {
        "message": "Login successful",
        "role": user.role,
        "access_token": token  # ✅ Return token for frontend usage
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=False,
        samesite="lax"
    )
    return {"message": "Logged out successfully"}

@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role
    )
    db.add(user)
    db.commit()
    return {"message": "User created"}


@router.put("/change-password")
def change_password(
    data: dict,  # Or a proper Pydantic schema
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(
            status_code=400,
            detail="current_password and new_password are required"
        )

    # Re-fetch user to be perfectly safe (though current_user has hashed_password)
    user = db.query(User).filter(User.id == current_user.id).first()
    
    if not user or not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    user.hashed_password = hash_password(new_password)
    db.commit()

    return {"message": "Password updated successfully"}

@router.get("/me")
def get_me(user = Depends(get_current_user)):
    profile = None
    first_name = ""
    last_name = ""
    if user.role == "doctor" and user.doctor_profile:
        profile = user.doctor_profile
    elif user.role == "patient" and user.patient_profile:
        # Fallback handle list evaluation safely just in case mapping behaves as proxy list
        profile = user.patient_profile[0] if isinstance(user.patient_profile, list) else user.patient_profile
    elif user.role in ["reception", "receptionist"] and user.receptionist_profile:
        profile = user.receptionist_profile
    elif user.role == "lab" and user.lab_profile:
        profile = user.lab_profile
        first_name = profile.lab_name
    elif user.role == "pharmacy" and user.pharmacy_profile:
        profile = user.pharmacy_profile
        first_name = profile.pharmacy_name

    if profile and not first_name:
        first_name = getattr(profile, "first_name", "")
        last_name = getattr(profile, "last_name", "")

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "first_name": first_name,
        "last_name": last_name,
        "profile_photo_url": getattr(profile, "profile_photo_url", "") if profile else ""
    }