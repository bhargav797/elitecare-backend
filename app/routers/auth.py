from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Response

from fastapi import Depends
from app.dependencies.auth import get_current_user
from app.database import get_db
from app.schemas.auth import (
    LoginSchema, RegisterSchema, ResetPasswordSendOTP, 
    ResetPasswordVerify, ChangePasswordOTPVerify
)
from app.models.user import User
from app.models.otp import EmailOTP
from app.utils.email import send_otp_email
import random
from datetime import datetime, timedelta
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

@router.post("/reset-password/send-otp")
def reset_password_send_otp(data: ResetPasswordSendOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # Prevent user enumeration, just return pseudo-success
        return {"message": "If that email is valid, an OTP has been sent."}

    otp = str(random.randint(100000, 999999))
    db_otp = db.query(EmailOTP).filter(EmailOTP.email == data.email).first()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    if db_otp:
        db_otp.otp = otp
        db_otp.expires_at = expires_at
    else:
        db_otp = EmailOTP(email=data.email, otp=otp, expires_at=expires_at)
        db.add(db_otp)
        
    db.commit()

    if send_otp_email(data.email, otp):
        return {"message": "If that email is valid, an OTP has been sent."}
    else:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")


@router.put("/reset-password/verify-and-change")
def reset_password_verify_change(data: ResetPasswordVerify, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request")

    db_otp = db.query(EmailOTP).filter(EmailOTP.email == data.email).first()
    if not db_otp or db_otp.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    if db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired")
        
    user.hashed_password = hash_password(data.new_password)
    db.delete(db_otp) # delete OTP after use
    db.commit()

    return {"message": "Password reset successfully!"}


@router.post("/change-password/send-otp")
def change_password_send_otp(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    otp = str(random.randint(100000, 999999))
    db_otp = db.query(EmailOTP).filter(EmailOTP.email == current_user.email).first()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    if db_otp:
        db_otp.otp = otp
        db_otp.expires_at = expires_at
    else:
        db_otp = EmailOTP(email=current_user.email, otp=otp, expires_at=expires_at)
        db.add(db_otp)
        
    db.commit()

    if send_otp_email(current_user.email, otp):
        return {"message": "OTP sent successfully to your email"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")


@router.put("/change-password/verify-and-change")
def change_password_verify_change(data: ChangePasswordOTPVerify, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_otp = db.query(EmailOTP).filter(EmailOTP.email == current_user.email).first()
    if not db_otp or db_otp.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    if db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired")
        
    # Re-fetch user
    user = db.query(User).filter(User.id == current_user.id).first()
    user.hashed_password = hash_password(data.new_password)
    db.delete(db_otp) # delete OTP after use
    db.commit()

    return {"message": "Password updated successfully!"}

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