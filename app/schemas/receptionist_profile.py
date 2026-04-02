from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class ReceptionistProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    profile_photo_url: Optional[str] = None

    languages_known: Optional[str] = None

    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

class ReceptionistProfileResponse(BaseModel):
    id: int
    user_id: int
    email: Optional[EmailStr] = None
    
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: date
    gender: str
    profile_photo_url: Optional[str] = None

    languages_known: Optional[str] = None

    mobile: str
    address: str
    city: str
    state: str
    pincode: str

    class Config:
        from_attributes = True
