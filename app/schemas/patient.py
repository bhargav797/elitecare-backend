from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional, List


# =====================================================
# PATIENT REGISTRATION (SELF REGISTER)
# =====================================================
class PatientRegister(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: date
    gender: str
    blood_group: str
    mobile: str

    address_line: str
    city: str
    state: str
    pincode: str

    emergency_contact: str
    emergency_relation: str

    existing_conditions: Optional[str] = None
    known_allergies: Optional[str] = None
    current_medication: Optional[str] = None

    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    govt_scheme: Optional[str] = None
    scheme_id: Optional[str] = None

# =====================================================
# PATIENT PROFILE (DASHBOARD)
# =====================================================
class PatientProfile(BaseModel):
    id: int
    email: Optional[EmailStr] = None

    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    profile_photo_url: Optional[str] = None

    mobile: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    emergency_contact: Optional[str] = None
    emergency_relation: Optional[str] = None

    existing_conditions: Optional[str] = None
    known_allergies: Optional[str] = None
    current_medication: Optional[str] = None

    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    govt_scheme: Optional[str] = None
    scheme_id: Optional[str] = None

    class Config:
        from_attributes = True

class PatientProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    profile_photo_url: Optional[str] = None

    mobile: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    emergency_contact: Optional[str] = None
    emergency_relation: Optional[str] = None

    existing_conditions: Optional[str] = None
    known_allergies: Optional[str] = None
    current_medication: Optional[str] = None

    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    govt_scheme: Optional[str] = None
    scheme_id: Optional[str] = None


# =====================================================
# PATIENT APPOINTMENTS
# =====================================================
class PatientAppointment(BaseModel):
    id: int
    patient_email: EmailStr
    reason: str
    status: str
    scheduled_date: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# =====================================================
# PATIENT PRESCRIPTIONS
# =====================================================
class PatientPrescription(BaseModel):
    id: int
    appointment_id: int
    medicines: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# PATIENT LAB RESULTS
# =====================================================
class PatientLabResult(BaseModel):
    id: int
    lab_request_id: int
    result: str
    reported_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# PATIENT DASHBOARD RESPONSE (OPTIONAL BUT RECOMMENDED)
# =====================================================
class PatientDashboard(BaseModel):
    profile: PatientProfile
    appointments: List[PatientAppointment]
    prescriptions: List[PatientPrescription]
    lab_results: List[PatientLabResult]
