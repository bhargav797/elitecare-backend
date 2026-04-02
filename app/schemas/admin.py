from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

# =====================================================
# COMMON ADMIN SCHEMAS
# =====================================================

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        orm_mode = True


class UpdateUserRole(BaseModel):
    role: str


class UpdateUserStatus(BaseModel):
    is_active: bool


# =====================================================
# DOCTOR CREATE
# =====================================================
class DoctorCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: date
    gender: str

    registration_number: str
    council_name: str
    specialization: str
    experience_years: int
    qualification: str

    mobile: str
    address: str
    city: str
    state: str
    pincode: str


# =====================================================
# LAB CREATE
# =====================================================
class LabCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    lab_name: str
    registration_number: str
    lab_type: str

    contact_person: str
    contact_number: str

    address: str
    city: str
    state: str
    pincode: str

    nabl_accredited: Optional[str] = None
    accreditation_number: Optional[str] = None


# =====================================================
# PHARMACY CREATE
# =====================================================
class PharmacyCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    pharmacy_name: str
    drug_license_number: str
    license_type: str

    pharmacist_name: str
    pharmacist_registration: str
    qualification: str

    mobile: str
    address: str
    city: str
    state: str
    pincode: str

    home_delivery: str


# =====================================================
# RECEPTIONIST CREATE
# =====================================================
class ReceptionistCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: date
    gender: str
    languages_known: Optional[str] = None

    mobile: str
    address: str
    city: str
    state: str
    pincode: str
