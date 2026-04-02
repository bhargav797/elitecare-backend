from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import date
import os
import cloudinary
import cloudinary.uploader
import json

from app.database import get_db
from app.models.user import User
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.schemas.patient import PatientRegister
from app.core.security import hash_password

import random
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.utils.email import send_otp_email
from app.models.otp import EmailOTP

class SendOTPSchema(BaseModel):
    email: str

class VerifyOTPSchema(BaseModel):
    email: str
    otp: str

router = APIRouter(
    prefix="/patient",
    tags=["Patient (Public)"]
)

# Cloudinary Setup (Defaults to user's known cloud name if env missing)
cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "dxjc26piq"),
  api_key = os.getenv("CLOUDINARY_API_KEY", "116523992497645"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET", "1mQx_5168S_83mJ_kH7Kks"),
  secure = True
)

# =====================================================
# PATIENT REGISTRATION (PUBLIC)
# =====================================================

@router.post("/send-otp")
def send_otp(data: SendOTPSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate 6-digit OTP
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
        return {"message": "OTP sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

@router.post("/verify-otp")
def verify_otp(data: VerifyOTPSchema, db: Session = Depends(get_db)):
    db_otp = db.query(EmailOTP).filter(EmailOTP.email == data.email).first()
    
    if not db_otp:
        raise HTTPException(status_code=400, detail="OTP not requested for this email")
        
    if db_otp.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    if db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired")
        
    return {"message": "OTP verified successfully"}

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_patient(
    data: str = Form(...),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        # Parse the JSON string from formData into a dictionary first
        parsed_data = json.loads(data)
        # Validate against our Pydantic schema
        reg_data = PatientRegister(**parsed_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid form data: {str(e)}")

    if reg_data.password != reg_data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if db.query(User).filter(User.email == reg_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=reg_data.email,
        hashed_password=hash_password(reg_data.password),
        role="patient",
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    photo_url = None
    if photo:
        try:
            result = cloudinary.uploader.upload(
                photo.file,
                folder="patient_profiles",
                public_id=f"user_{user.id}_avatar"
            )
            photo_url = result.get("secure_url")
        except Exception as e:
            # We don't fail registration if photo upload fails, just log it.
            print(f"Failed to upload profile photo: {e}")

    patient = PatientProfile(
        user_id=user.id,
        first_name=reg_data.first_name,
        middle_name=reg_data.middle_name,
        last_name=reg_data.last_name,
        dob=reg_data.dob,
        gender=reg_data.gender,
        blood_group=reg_data.blood_group,
        mobile=reg_data.mobile,
        address_line=reg_data.address_line,
        city=reg_data.city,
        state=reg_data.state,
        pincode=reg_data.pincode,
        emergency_contact=reg_data.emergency_contact,
        emergency_relation=reg_data.emergency_relation,
        existing_conditions=reg_data.existing_conditions,
        known_allergies=reg_data.known_allergies,
        current_medication=reg_data.current_medication,
        insurance_provider=reg_data.insurance_provider,
        policy_number=reg_data.policy_number,
        govt_scheme=reg_data.govt_scheme,
        scheme_id=reg_data.scheme_id,
        profile_photo_url=photo_url
    )

    db.add(patient)
    db.commit()

    return {
        "message": "Patient registered successfully",
        "user_id": user.id
    }

@router.get("/doctors")
def get_public_doctors(db: Session = Depends(get_db)):
    doctors = (
        db.query(
            User.id, 
            DoctorProfile.first_name, 
            DoctorProfile.last_name, 
            DoctorProfile.specialization,
            DoctorProfile.profile_photo_url
        )
        .outerjoin(DoctorProfile, User.id == DoctorProfile.user_id)
        .filter(User.role == "doctor", User.is_active == True)
        .all()
    )
    return [
        {
            "id": d.id,
            "name": f"Dr. {d.first_name} {d.last_name}" if d.last_name else f"Dr. {d.first_name}",
            "role": "Specialist", 
            "specialty": d.specialization or "General",
            "image": d.profile_photo_url or "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&q=80&w=500"
        }
        for d in doctors if d.first_name
    ]