from pydantic import BaseModel
from datetime import datetime

class AppointmentResponse(BaseModel):
    id: int
    patient_email: str
    reason: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
