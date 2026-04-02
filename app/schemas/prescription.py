from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PrescriptionCreate(BaseModel):
    appointment_id: int
    diagnosis: str
    medicines: str
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None


class PatientPrescription(BaseModel):
    id: int
    appointment_id: int
    doctor_email: str
    diagnosis: str
    medicines: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
