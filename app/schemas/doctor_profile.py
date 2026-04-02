from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

# =====================================================
# DOCTOR PROFILE (DASHBOARD)
# =====================================================
class DoctorProfileResponse(BaseModel):
    id: int
    user_id: int
    email: Optional[EmailStr] = None

    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: Optional[date] = None
    gender: Optional[str] = None
    profile_photo_url: Optional[str] = None

    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    registration_number: Optional[str] = None
    council_name: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    qualification: Optional[str] = None

    class Config:
        from_attributes = True

class DoctorProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    profile_photo_url: Optional[str] = None

    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    registration_number: Optional[str] = None
    council_name: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    qualification: Optional[str] = None
