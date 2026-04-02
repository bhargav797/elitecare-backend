from pydantic import BaseModel, EmailStr
from typing import Optional

class LabProfileUpdate(BaseModel):
    lab_name: Optional[str] = None
    registration_number: Optional[str] = None
    lab_type: Optional[str] = None
    profile_photo_url: Optional[str] = None

    contact_person: Optional[str] = None
    contact_number: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    nabl_accredited: Optional[str] = None
    accreditation_number: Optional[str] = None

class LabProfileResponse(BaseModel):
    id: int
    user_id: int
    email: Optional[EmailStr] = None
    
    lab_name: str
    registration_number: str
    lab_type: str
    profile_photo_url: Optional[str] = None

    contact_person: str
    contact_number: str

    address: str
    city: str
    state: str
    pincode: str

    nabl_accredited: Optional[str] = None
    accreditation_number: Optional[str] = None

    class Config:
        from_attributes = True
