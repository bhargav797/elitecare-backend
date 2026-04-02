from pydantic import BaseModel, EmailStr
from typing import Optional

class PharmacyProfileUpdate(BaseModel):
    pharmacy_name: Optional[str] = None
    license_number: Optional[str] = None
    license_type: Optional[str] = None
    profile_photo_url: Optional[str] = None

class PharmacyProfileResponse(BaseModel):
    id: int
    user_id: int
    email: Optional[EmailStr] = None
    
    pharmacy_name: str
    license_number: str
    license_type: str
    profile_photo_url: Optional[str] = None

    class Config:
        from_attributes = True
