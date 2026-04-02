from pydantic import BaseModel

# ==========================
# CREATE (USED BY DOCTOR)
# ==========================
class LabRequestCreate(BaseModel):
    appointment_id: int
    test_name: str
    reason: str


# ==========================
# RESPONSE (USED BY LAB)
# ==========================
class LabRequestResponse(BaseModel):
    id: int
    patient_email: str
    doctor_email: str
    test_name: str
    reason: str
    status: str

    class Config:
        from_attributes = True  # ✅ Pydantic v2 fix
