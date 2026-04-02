from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

class ReceptionAppointmentCreate(BaseModel):
    patient_email: EmailStr
    doctor_id: int
    reason: str

class PatientRegisterReception(BaseModel):
    email: EmailStr
    password: str
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
