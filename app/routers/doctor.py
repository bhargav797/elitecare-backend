import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import os
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from app.utils.date_utils import get_ist_today_range
from datetime import datetime
import logging

from app.database import get_db
from app.dependencies.auth import require_role, get_current_user

from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.lab_request import LabRequest
from app.models.lab_report_file import LabReportFile
from app.models.user import User
from app.models.doctor_profile import DoctorProfile
from sqlalchemy import func, case
from datetime import date, datetime, timedelta

from app.schemas.prescription import PrescriptionCreate
from app.schemas.lab_request import LabRequestCreate
from app.schemas.doctor_profile import DoctorProfileUpdate, DoctorProfileResponse


router = APIRouter(
    prefix="/doctor",
    tags=["Doctor"],
    dependencies=[Depends(require_role("doctor"))]
)

# =====================================================
# GET DOCTOR DASHBOARD DATA
# =====================================================
@router.get("/dashboard")
def get_doctor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.patient_profile import PatientProfile
    today_start, tomorrow_start = get_ist_today_range()

    # 1. Appointments Data
    appointments_query = (
        db.query(
            Appointment, 
            User.email.label("patient_email_db"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name
        )
        .outerjoin(User, Appointment.patient_id == User.id)
        .outerjoin(PatientProfile, User.id == PatientProfile.user_id)
        .outerjoin(Prescription, Prescription.appointment_id == Appointment.id)
        .filter(
            Appointment.doctor_id == current_user.id,
            or_(
                # 1. Active patients (Pending or In Progress) Scheduled for today or earlier
                and_(
                    Appointment.status.in_(["pending", "in_progress"]),
                    or_(
                        Appointment.scheduled_date == None,
                        Appointment.scheduled_date < tomorrow_start
                    )
                ),
                # 2. Patients completed TODAY (strictly IST)
                and_(
                    Appointment.status == "completed",
                    or_(
                        and_(
                            Prescription.created_at >= today_start,
                            Prescription.created_at < tomorrow_start
                        ),
                        and_(
                            # Using Appointment.created_at as fallback for logic consistency
                            # though prescriptions should exist for completed ones.
                            Appointment.created_at >= today_start,
                            Appointment.created_at < tomorrow_start
                        )
                    )
                )
            )
        )
        .distinct()
        .order_by(Appointment.id.asc())
        .all()
    )

    total_today = 0
    pending_today = 0
    completed_today = 0
    queue_list = []
    next_patient = None

    for appt, p_email, first, middle, last in appointments_query:
        total_today += 1
        if appt.status in ["pending", "in_progress"]:
            pending_today += 1
            if not next_patient and appt.status == "pending": # Only auto-select 'pending' as next
                next_patient = {
                    "id": appt.id,
                    "patient_email": p_email or appt.patient_email,
                    "patient_first_name": first,
                    "patient_middle_name": middle,
                    "patient_last_name": last,
                    "reason": appt.reason,
                    "time": appt.created_at
                }
        elif appt.status == "completed":
            completed_today += 1
            
        queue_list.append({
            "id": appt.id,
            "patient_email": p_email or appt.patient_email,
            "patient_first_name": first,
            "patient_middle_name": middle,
            "patient_last_name": last,
            "reason": appt.reason,
            "status": appt.status,
            "time": appt.created_at
        })

    # 2. Lab Reports pending review
    # Find lab requests assigned to this doctor that have a report uploaded AND not reviewed
    pending_labs = (
        db.query(LabRequest)
        .join(LabReportFile, LabReportFile.lab_request_id == LabRequest.id)
        .filter(
            LabRequest.doctor_id == current_user.id,
            LabReportFile.is_reviewed == False
        )
        .count()
    )

    return {
        "stats": {
            "total_today": total_today,
            "pending_today": pending_today,
            "completed_today": completed_today,
            "pending_labs": pending_labs
        },
        "next_patient": next_patient,
        "queue": queue_list
    }


# =====================================================
# DOCTOR PROFILE
# =====================================================
@router.get("/profile", response_model=DoctorProfileResponse)
def get_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
        
    # include email
    profile_dict = {
        column.name: getattr(profile, column.name) 
        for column in profile.__table__.columns
    }
    profile_dict["email"] = current_user.email
    return profile_dict


@router.put("/profile")
def update_doctor_profile(
    data: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    return {"message": "Profile updated successfully"}


@router.post("/profile/upload-photo")
def upload_doctor_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    import cloudinary
    import cloudinary.uploader
    import os

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dxjc26piq"),
        api_key=os.getenv("CLOUDINARY_API_KEY", "116523992497645"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET", "1mQx_5168S_83mJ_kH7Kks"),
        secure=True
    )

    try:
        result = cloudinary.uploader.upload(
            file.file,
            folder="doctor_profiles",
            public_id=f"user_{current_user.id}_avatar"
        )
        photo_url = result.get("secure_url")

        profile.profile_photo_url = photo_url
        db.commit()

        return {"message": "Photo uploaded successfully", "url": photo_url}
    except Exception as e:
        logging.error(f"Error saving photo to Cloudinary: {e}")
        raise HTTPException(status_code=500, detail="Could not save profile photo")

@router.delete("/account")
def delete_doctor_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        user_to_delete = db.query(User).filter(User.id == current_user.id).first()
        if not user_to_delete:
            raise HTTPException(status_code=404, detail="User not found")
            
        db.delete(user_to_delete)
        db.commit()
        return {"message": "Account deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# GET MY APPOINTMENTS (ALL ACTIVE)
# =====================================================
@router.get("/appointments")
def get_my_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.patient_profile import PatientProfile
    logging.info(f"Fetching appointments for doc {current_user.id}")
    rows = (
        db.query(
            Appointment.id.label("appt_id"),
            Appointment.reason.label("reason"),
            Appointment.status.label("status"),
            Appointment.patient_id.label("pid"), 
            Appointment.patient_email.label("p_email"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name
        )
        .outerjoin(PatientProfile, Appointment.patient_id == PatientProfile.user_id)
        .filter(
            Appointment.doctor_id == current_user.id,
            Appointment.status.notin_(["completed", "cancelled"])
        )
        .order_by(Appointment.id.desc())
        .all()
    )
    
    return [
        {
            "id": r.appt_id,
            "patient_id": r.pid,
            "patient_email": r.p_email,
            "patient_first_name": r.first_name,
            "patient_middle_name": r.middle_name,
            "patient_last_name": r.last_name,
            "reason": r.reason,
            "status": r.status
        }
        for r in rows
    ]
@router.get("/appointments/pending-prescription")
def get_pending_prescription_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.patient_profile import PatientProfile
    rows = (
        db.query(
            Appointment.id.label("appt_id"),
            Appointment.reason.label("reason"),
            Appointment.status.label("status"),
            Appointment.patient_id.label("pid"),
            Appointment.patient_email.label("p_email"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name
        )
        .outerjoin(PatientProfile, Appointment.patient_id == PatientProfile.user_id)
        .outerjoin(Prescription, Prescription.appointment_id == Appointment.id)
        .filter(
            Appointment.doctor_id == current_user.id,
            Appointment.status.notin_(["completed", "cancelled"]),
            Prescription.id == None,
            or_(
                Appointment.scheduled_date == None,
                Appointment.scheduled_date <= datetime.now()
            )
        )
        .order_by(Appointment.id.desc())
        .all()
    )

    return [
        {
            "id": r.appt_id,
            "patient_id": r.pid,
            "patient_email": r.p_email,
            "patient_first_name": r.first_name,
            "patient_middle_name": r.middle_name,
            "patient_last_name": r.last_name,
            "reason": r.reason,
            "status": "Prescription Pending" if r.status == "in_progress" else "Pending"
        }
        for r in rows
    ]


@router.get("/appointments/pending-lab")
def get_pending_lab_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.patient_profile import PatientProfile
    rows = (
        db.query(
            Appointment.id.label("appt_id"),
            Appointment.reason.label("reason"),
            Appointment.status.label("status"),
            Appointment.patient_id.label("pid"),
            Appointment.patient_email.label("p_email"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name
        )
        .outerjoin(PatientProfile, Appointment.patient_id == PatientProfile.user_id)
        .outerjoin(LabRequest, LabRequest.appointment_id == Appointment.id)
        .filter(
            Appointment.doctor_id == current_user.id,
            Appointment.status.notin_(["completed", "cancelled"]),
            Appointment.is_lab_required == True,
            LabRequest.id == None
        )
        .order_by(Appointment.id.desc())
        .all()
    )

    return [
        {
            "id": r.appt_id,
            "patient_id": r.pid,
            "patient_email": r.p_email,
            "patient_first_name": r.first_name,
            "patient_middle_name": r.middle_name,
            "patient_last_name": r.last_name,
            "reason": r.reason,
            "status": "Lab Pending" if r.status == "in_progress" else "Pending"
        }
        for r in rows
    ]


@router.put("/appointments/{appointment_id}/skip-lab")
def skip_lab_request(
    appointment_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == current_user.id
    ).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    app.is_lab_required = False
    
    # If prescription is also done (or not needed?), maybe complete? 
    # For now, just marking lab not required is enough to hide it from the list.
    # If both are done, we could check and auto-complete, but let's keep it simple.
    
    # Check if prescription exists
    has_prescription = db.query(Prescription).filter(Prescription.appointment_id == app.id).first()
    
    if has_prescription:
        # If prescription is done and we skip lab, we are done
        app.status = "completed"
    else:
        # Still waiting for prescription
        app.status = "in_progress"

    db.commit()
    return {"message": "Lab marked as not needed"}


    # Update existing to "No Medicine" but preserve user input if possible OR overwrite
    # User said: "why auto daignosic and note is writeen i want when i click on no medicine then only no medicne should apply nothing else."
    # So we should probably use what is sent, or if not sent, use "No Medicine Required"
    
    # We need to accept body data. 
    # Let's use Body() or a Pydantic model. 
    # Since I can't easily add a class here without scrolling up, I'll use Body
    pass # Replaced by full function below

from pydantic import BaseModel
class SkipPrescriptionData(BaseModel):
    diagnosis: str = "No Medicine Required"
    notes: str = "Marked as no medicine needed"

@router.put("/appointments/{appointment_id}/skip-prescription")
def skip_prescription(
    appointment_id: int,
    data: SkipPrescriptionData, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f">>> SKIP PRESCRIPTION CALLED FOR {appointment_id} <<<")
    logging.info(f"Skipping prescription for appt {appointment_id} by user {current_user.id}")
    app = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == current_user.id
    ).first()
    
    if not app:
        logging.error(f"Appointment {appointment_id} not found for doctor {current_user.id}")
        raise HTTPException(status_code=404, detail="Appointment not found")

    print(f">>> DEBUG: Appt {app.id}, is_lab_required={app.is_lab_required}, type={type(app.is_lab_required)} <<<")
        
    # Check if we already have a prescription
    existing = db.query(Prescription).filter(Prescription.appointment_id == app.id).first()
    
    # User feedback: "when i click on no medicine then only no medicne should apply nothing else"
    # This implies they want the "medicines" list to be empty, but likely the diagnosis/notes to be CLEAN or user-specified.
    # We are receiving data.diagnosis and data.notes now.
    
    diag_to_use = data.diagnosis
    notes_to_use = data.notes
    
    if existing:
        existing.diagnosis = diag_to_use
        existing.medicines = "[]"
        existing.notes = notes_to_use
    else:
        presc = Prescription(
            appointment_id=app.id,
            patient_id=app.patient_id,
            doctor_id=current_user.id,
            diagnosis=diag_to_use,
            medicines="[]",
            notes=notes_to_use
        )
        db.add(presc)

    # Update appointment status
    # If lab is NOT required, then we are done -> completed
    if not app.is_lab_required:
        app.status = "completed"
    else:
        app.status = "in_progress"
    
    db.commit()
    return {"message": "Prescription marked as not needed"}


# =====================================================
# WRITE PRESCRIPTION
# =====================================================
@router.post("/prescriptions")
def create_prescription(
    data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == data.appointment_id,
        Appointment.doctor_id == current_user.id
    ).first()

    if not appointment:
        logging.error(f"Prescription Failed: Appointment {data.appointment_id} not found or mismatch")
        raise HTTPException(status_code=404, detail="Appointment not found")

    print(f">>> DEBUG: Create Presc Appt {appointment.id}, is_lab_required={appointment.is_lab_required} <<<")

    prescription = Prescription(
        appointment_id=appointment.id,
        patient_id=appointment.patient_id,
        doctor_id=current_user.id,
        diagnosis=data.diagnosis,
        medicines=data.medicines,
        notes=data.notes
    )

    db.add(prescription)

    # ✅ FIX: appointment should move out of pending
    old_status = appointment.status
    
    if not appointment.is_lab_required:
        appointment.status = "completed"
    else:
        appointment.status = "in_progress"
        
    logging.info(f"Prescription Created for Appt {appointment.id}. Status change: {old_status} -> {appointment.status}")

    # ✅ HANDLE FOLLOW-UP APPOINTMENT
    if data.follow_up_date:
        # Fetch patient email explicitly to avoid None errors
        patient = db.query(User).filter(User.id == appointment.patient_id).first()
        p_email = patient.email if patient else appointment.patient_email

        if not p_email:
             # Fallback or error if still missing (shouldn't happen for valid user)
             logging.error(f"Could not find email for patient {appointment.patient_id}")
             raise HTTPException(status_code=500, detail="Patient email not found for follow-up")

        follow_up_appt = Appointment(
            patient_id=appointment.patient_id,
            patient_email=p_email, # ✅ Use explicitly fetched email
            doctor_id=current_user.id,
            reason=f"Follow-up: {appointment.reason}",
            status="pending",
            scheduled_date=data.follow_up_date,
            is_lab_required=False 
        )
        db.add(follow_up_appt)
        logging.info(f"Created Follow-up Appointment for {data.follow_up_date}")

    db.commit()

    return {"message": "Prescription created successfully"}


# =====================================================
# REQUEST LAB TEST
# =====================================================
@router.post("/lab-requests")
def create_lab_request(
    data: LabRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == data.appointment_id,
        Appointment.doctor_id == current_user.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    lab_request = LabRequest(
        appointment_id=appointment.id,
        patient_id=appointment.patient_id,
        doctor_id=current_user.id,
        test_name=data.test_name,
        reason=data.reason,
        status="pending"
    )

    db.add(lab_request)

    # ✅ FIX: appointment should move out of pending
    appointment.status = "in_progress"

    db.commit()
    db.refresh(lab_request)

    return {
        "message": "Lab request submitted successfully",
        "lab_request_id": lab_request.id
    }
