from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime

from app.database import get_db
from app.models.user import User
from app.models.doctor_profile import DoctorProfile
from app.models.patient_profile import PatientProfile
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.lab_request import LabRequest
from app.models.lab_report_file import LabReportFile
from app.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/health-records",
    tags=["Health Records"]
)

# --- Response Schemas ---

class HistoryItem(BaseModel):
    date: datetime
    type: str # "Appointment", "Lab", "Prescription"
    title: str
    description: str
    details: Optional[dict] = None

class HealthRecordResponse(BaseModel):
    patient_id: int
    blood_group: Optional[str]
    allergies: List[str]
    conditions: List[str]
    history: List[HistoryItem]

# --- Helper Functions ---

def parse_csv(csv_str: Optional[str]) -> List[str]:
    if not csv_str:
        return []
    return [item.strip() for item in csv_str.split(",") if item.strip()]

# --- Endpoints ---

@router.get("/{patient_id}", response_model=HealthRecordResponse)
def get_patient_health_records(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Authorization Check
    # Patient can only see their own records.
    # Doctor can see any patient's records.
    if current_user.role == "patient" and current_user.id != patient_id:
         raise HTTPException(status_code=403, detail="Not authorized to view these records")
    
    if current_user.role not in ["patient", "doctor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    # 2. Fetch Patient Profile
    # 2. Fetch Patient Profile (Optional but recommended)
    patient_profile = db.query(PatientProfile).filter(PatientProfile.user_id == patient_id).first()
    
    # Defaults in case profile is missing
    blood_group = None
    allergies = []
    conditions = []
    
    if patient_profile:
        blood_group = patient_profile.blood_group
        allergies = parse_csv(patient_profile.known_allergies)
        conditions = parse_csv(patient_profile.existing_conditions)

    # 3. Aggregate History
    history = []

    # -- Appointments --
    try:
        appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).all()
        for appt in appointments:
            history.append(HistoryItem(
                date=appt.created_at,
                type="Appointment",
                title=f"Appointment: {appt.status}",
                description=appt.reason,
                details={"doctor_id": appt.doctor_id}
            ))
    except Exception as e:
        print(f"Error fetching appointments: {e}")

    # -- Prescriptions --
    try:
        prescriptions = db.query(Prescription).filter(Prescription.patient_id == patient_id).all()
        for presc in prescriptions:
            history.append(HistoryItem(
                date=presc.created_at,
                type="Prescription",
                title=f"Prescription for {presc.diagnosis}",
                description=presc.medicines, # JSON string of meds
                details={"notes": presc.notes, "diagnosis": presc.diagnosis}
            ))
    except Exception as e:
        print(f"Error fetching prescriptions: {e}")

    # -- Lab Requests/Reports --
    try:
        lab_requests = db.query(LabRequest).filter(LabRequest.patient_id == patient_id).all()
        for lab in lab_requests:
            # Check for report files
            report_files = db.query(LabReportFile).filter(LabReportFile.lab_request_id == lab.id).all()
            file_links = [{"name": f.file_name, "path": f.file_path, "id": f.id} for f in report_files]
            
            history.append(HistoryItem(
                date=lab.created_at,
                type="Lab Report",
                title=f"Lab: {lab.test_name}",
                description=f"Status: {lab.status}",
                details={"reason": lab.reason, "files": file_links}
            ))
    except Exception as e:
        print(f"Error fetching lab reports: {e}")

    # Sort history by date descending
    history.sort(key=lambda x: x.date, reverse=True)

    return HealthRecordResponse(
        patient_id=patient_id,
        blood_group=blood_group,
        allergies=allergies,
        conditions=conditions,
        history=history
    )
