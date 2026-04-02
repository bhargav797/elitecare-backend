from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
import cloudinary
import cloudinary.uploader

from app.database import get_db
from app.dependencies.auth import require_role, get_current_user

from app.models.user import User
from app.models.patient_profile import PatientProfile
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.doctor_profile import DoctorProfile
from app.models.lab_request import LabRequest
from app.models.lab_report_file import LabReportFile
from app.models.dispense import Dispense
from app.models.billing import Bill
from sqlalchemy import func

from app.schemas.patient import (
    PatientProfile as PatientProfileSchema,
    PatientProfileUpdate,
    PatientAppointment
)

router = APIRouter(
    prefix="/patient",
    tags=["Patient"],
    dependencies=[Depends(require_role("patient"))]
)

# Cloudinary Setup (Defaults to user's known cloud name if env missing)
cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "dxjc26piq"),
  api_key = os.getenv("CLOUDINARY_API_KEY", "116523992497645"), # Assuming dummy or needs actual
  api_secret = os.getenv("CLOUDINARY_API_SECRET", "1mQx_5168S_83mJ_kH7Kks"), # Assuming dummy or needs actual
  secure = True
)

# =====================================================
# VIEW PATIENT PROFILE
# =====================================================
@router.get("/profile", response_model=PatientProfileSchema)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )

    if not patient:
        # Auto-create empty profile linked to user
        from datetime import date
        patient = PatientProfile(
            user_id=current_user.id,
            first_name="",
            last_name="",
            dob=date(1900, 1, 1), # Temporary default
            gender="",
            blood_group="",
            mobile="",
            address_line="",
            city="",
            state="",
            pincode="",
            emergency_contact="",
            emergency_relation="",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    patient.email = current_user.email
    return patient


@router.put("/profile", response_model=PatientProfileSchema)
def update_my_profile(
    data: PatientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )

    if not patient:
        from datetime import date
        patient = PatientProfile(
            user_id=current_user.id,
            first_name="",
            last_name="",
            dob=date(1900, 1, 1),
            gender="",
            blood_group="",
            mobile="",
            address_line="",
            city="",
            state="",
            pincode="",
            emergency_contact="",
            emergency_relation="",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)

    db.commit()
    db.refresh(patient)

    patient.email = current_user.email
    return patient


@router.post("/profile/upload-photo")
def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found. Please update profile details first.")

    try:
        # Upload the file to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder="patient_profiles",
            public_id=f"user_{current_user.id}_avatar"
        )
        url = result.get("secure_url")

        # Save URL to database
        patient.profile_photo_url = url
        db.commit()

        return {"message": "Photo uploaded successfully", "url": url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/account")
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "Account successfully deleted"}



# =====================================================
# BOOK APPOINTMENT
# =====================================================
class PatientAppointmentCreate(BaseModel):
    reason: str


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
def book_appointment(
    data: PatientAppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = Appointment(
        patient_id=current_user.id,
        patient_email=current_user.email,
        doctor_id=None,
        reason=data.reason,
        status="pending",
        is_lab_required=True # ✅ Default to True so it doesn't auto-complete on "No Medicine"
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment requested successfully",
        "appointment_id": appointment.id,
        "status": appointment.status
    }


# =====================================================
# VIEW MY APPOINTMENTS
# =====================================================
@router.get("/appointments", response_model=list[PatientAppointment])
def get_my_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Appointment)
        .filter(Appointment.patient_id == current_user.id)
        .order_by(Appointment.id.desc())
        .all()
    )


# =====================================================
# VIEW PRESCRIPTIONS
# =====================================================
@router.get("/prescriptions")
def get_my_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(
            Prescription,
            User.email.label("doctor_email"),
            DoctorProfile.first_name.label("doctor_first_name"),
            DoctorProfile.last_name.label("doctor_last_name")
        )
        .join(User, Prescription.doctor_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .filter(Prescription.patient_id == current_user.id)
        .order_by(Prescription.id.desc())
        .all()
    )

    return [
        {
            "id": prescription.id,
            "doctor_email": doctor_email,
            "doctor_first_name": doctor_first_name,
            "doctor_last_name": doctor_last_name,
            "diagnosis": prescription.diagnosis,
            "medicines": prescription.medicines,
            "notes": prescription.notes,
            "created_at": prescription.created_at
        }
        for prescription, doctor_email, doctor_first_name, doctor_last_name in rows
    ]


# =====================================================
# VIEW LAB RESULTS
# =====================================================
@router.get("/lab-results")
def get_my_lab_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(
            LabRequest.id,
            LabRequest.test_name,
            LabRequest.reason,
            LabRequest.status,
            LabRequest.created_at,
            LabReportFile.id.label("report_id"),
            LabReportFile.file_path,
            LabReportFile.created_at,
            User.email.label("doctor_email"),
            DoctorProfile.first_name.label("doctor_first_name"),
            DoctorProfile.last_name.label("doctor_last_name")
        )
        .join(User, LabRequest.doctor_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .outerjoin(
            LabReportFile,
            LabReportFile.lab_request_id == LabRequest.id
        )
        .filter(LabRequest.patient_id == current_user.id)
        .order_by(LabRequest.id.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "test_name": r.test_name,
            "reason": r.reason,
            "status": r.status,
            "doctor_email": r.doctor_email,
            "doctor_first_name": r.doctor_first_name,
            "doctor_last_name": r.doctor_last_name,
            "report_id": r.report_id,
            "file_path": r.file_path,
            "uploaded_at": r.created_at,
            "created_at": r.created_at,
        }
        for r in rows
    ]


# =====================================================
# CANCEL APPOINTMENT
# =====================================================
@router.put("/appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_user.id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.status == "cancelled":
        raise HTTPException(status_code=400, detail="Appointment already cancelled")

    appointment.status = "cancelled"
    db.commit()

    return {
        "message": "Appointment cancelled successfully",
        "appointment_id": appointment.id,
        "status": appointment.status
    }


# =====================================================
# VIEW DISPENSED MEDICINES
# =====================================================
@router.get("/dispensed-medicines")
def get_dispensed_medicines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(
            Dispense,
            Prescription.medicines,
            Dispense.dispensed_at
        )
        .join(Prescription, Dispense.prescription_id == Prescription.id)
        .filter(Dispense.patient_id == current_user.id)
        .order_by(Dispense.dispensed_at.desc())
        .all()
    )

    return [
        {
            "dispense_id": dispense.id,
            "prescription_id": dispense.prescription_id,
            "medicines": medicines,
            "dispensed_at": dispensed_at
        }
        for dispense, medicines, dispensed_at in rows
    ]


# =====================================================
# GET PATIENT DASHBOARD DATA
# =====================================================
@router.get("/dashboard")
def get_patient_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Appointments (Latest status and last 5)
    appointments = (
        db.query(
            Appointment, 
            User.email.label("doctor_email"),
            DoctorProfile.first_name.label("doctor_first_name"),
            DoctorProfile.last_name.label("doctor_last_name")
        )
        .outerjoin(User, Appointment.doctor_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .filter(Appointment.patient_id == current_user.id)
        .order_by(Appointment.id.desc())
        .limit(5)
        .all()
    )
    
    recent_appointments = []
    for appt, doc_email, doc_fname, doc_lname in appointments:
        recent_appointments.append({
            "id": appt.id,
            "status": appt.status,
            "reason": appt.reason,
            "doctor_email": doc_email,
            "doctor_first_name": doc_fname,
            "doctor_last_name": doc_lname,
            "date": appt.created_at
        })

    latest_appointment = recent_appointments[0] if recent_appointments else None

    # 2. Latest Prescription
    latest_prescription = (
        db.query(
            Prescription, 
            User.email.label("doctor_email"),
            DoctorProfile.first_name.label("doctor_first_name"),
            DoctorProfile.last_name.label("doctor_last_name")
        )
        .join(User, Prescription.doctor_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .filter(Prescription.patient_id == current_user.id)
        .order_by(Prescription.id.desc())
        .first()
    )
    
    prescription_data = None
    if latest_prescription:
        presc, doc_email, doc_fname, doc_lname = latest_prescription
        prescription_data = {
            "id": presc.id,
            "doctor_email": doc_email,
            "doctor_first_name": doc_fname,
            "doctor_last_name": doc_lname,
            "diagnosis": presc.diagnosis,
            "medicines": presc.medicines,
            "notes": presc.notes,
            "date": presc.created_at
        }

    # 3. Latest Lab Report Update Alert
    latest_lab = (
        db.query(LabRequest, LabReportFile)
        .outerjoin(LabReportFile, LabReportFile.lab_request_id == LabRequest.id)
        .filter(LabRequest.patient_id == current_user.id)
        .order_by(LabRequest.id.desc())
        .first()
    )
    
    lab_data = None
    if latest_lab:
        req, rep = latest_lab
        lab_data = {
            "id": req.id,
            "test_name": req.test_name,
            "status": req.status,
            "report_available": bool(rep),
            "date": req.created_at
        }

    # 4. Unpaid Bills Summary
    unpaid_bills = (
        db.query(
            func.count(Bill.id).label("count"),
            func.sum(Bill.remaining_amount).label("total")
        )
        .filter(
            Bill.patient_id == current_user.id,
            Bill.payment_status != "paid"
        )
        .first()
    )

    return {
        "appointments": {
            "latest": latest_appointment,
            "recent": recent_appointments
        },
        "latest_prescription": prescription_data,
        "latest_lab_request": lab_data,
        "billing": {
            "unpaid_count": unpaid_bills.count or 0,
            "unpaid_total": float(unpaid_bills.total or 0)
        }
    }
