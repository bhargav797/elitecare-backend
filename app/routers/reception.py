from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role, get_current_user
from app.models.appointment import Appointment
from app.models.user import User
from app.models.billing import Bill, Payment
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.schemas.reception import ReceptionAppointmentCreate, PatientRegisterReception
from app.core.security import hash_password
from sqlalchemy import func, case
from datetime import date, datetime, timedelta
from app.utils.date_utils import get_ist_today_range

router = APIRouter(
    prefix="/reception",
    tags=["Reception"],
    dependencies=[Depends(require_role("receptionist"))]
)

# =====================================================
# GET ALL PATIENTS
@router.get("/patients")
def get_all_patients(db: Session = Depends(get_db)):
    patients = (
        db.query(User.id, User.email, PatientProfile.first_name, PatientProfile.middle_name, PatientProfile.last_name)
        .outerjoin(PatientProfile, User.id == PatientProfile.user_id)
        .filter(User.role == "patient", User.is_active == True)
        .order_by(User.email)
        .all()
    )
    return [
        {
            "id": p.id,
            "email": p.email,
            "first_name": p.first_name,
            "middle_name": p.middle_name,
            "last_name": p.last_name
        }
        for p in patients
    ]


# =====================================================
# REGISTER PATIENT
# =====================================================
@router.post("/patients", status_code=status.HTTP_201_CREATED)
def register_patient(data: PatientRegisterReception, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # 1. Create User
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role="patient",
        is_active=True
    )
    db.add(user)
    db.flush() # Get user.id

    # 2. Create Patient Profile
    profile_data = data.dict(exclude={"email", "password"})
    profile = PatientProfile(
        user_id=user.id,
        **profile_data
    )
    db.add(profile)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create patient: {str(e)}")

    db.refresh(user)

    return {"message": "Patient registered successfully", "patient_id": user.id}


# =====================================================
# GET RECEPTION DASHBOARD DATA
# =====================================================
@router.get("/dashboard")
def get_reception_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today_start, tomorrow_start = get_ist_today_range()

    # 1. Total pending appointments
    total_pending = db.query(Appointment).filter(Appointment.status == "pending").count()

    # Statistics strictly for today (IST)
    
    todays_appointments = (
        db.query(
            User.email.label("doctor_email"),
            DoctorProfile.first_name,
            DoctorProfile.last_name,
            func.count(Appointment.id).label("total"),
            func.sum(case((Appointment.status == "pending", 1), else_=0)).label("pending"),
            func.sum(case((Appointment.status == "completed", 1), else_=0)).label("completed")
        )
        .join(User, Appointment.doctor_id == User.id)
        .outerjoin(DoctorProfile, User.id == DoctorProfile.user_id)
        # Filter for appointments scheduled FOR today or created TODAY
        .filter(
            (Appointment.created_at >= today_start - timedelta(hours=6)) & 
            (Appointment.created_at < tomorrow_start + timedelta(hours=6))
        )
        .group_by(User.email, DoctorProfile.first_name, DoctorProfile.last_name)
        .all()
    )

    doctor_breakdown = [
        {
            "doctor_email": doc.doctor_email,
            "first_name": doc.first_name,
            "last_name": doc.last_name,
            "total": int(doc.total),
            "pending": int(doc.pending or 0),
            "completed": int(doc.completed or 0)
        }
        for doc in todays_appointments
    ]


    # 3. Billing Summary
    # Today's collection
    todays_collection = db.query(func.sum(Payment.amount)).filter(Payment.payment_date >= today_start, Payment.payment_date < tomorrow_start).scalar() or 0.0

    # Total unpaid amount (all time)
    unpaid_total = db.query(func.sum(Bill.remaining_amount)).filter(Bill.payment_status != "paid").scalar() or 0.0

    # Recent 5 bills
    recent_bills_query = (
        db.query(Bill, User.email.label("patient_email"))
        .join(User, Bill.patient_id == User.id)
        .order_by(Bill.id.desc())
        .limit(5)
        .all()
    )
    
    recent_bills = [
        {
            "bill_number": bill.bill_number,
            "patient_email": patient_email,
            "date": bill.created_at,
            "total_amount": bill.total_amount,
            "status": bill.payment_status
        }
        for bill, patient_email in recent_bills_query
    ]

    return {
        "pending_appointments_count": total_pending,
        "doctor_breakdown": doctor_breakdown,
        "billing": {
            "todays_collection": float(todays_collection),
            "unpaid_total": float(unpaid_total),
            "recent_bills": recent_bills
        }
    }


# =====================================================
# CREATE APPOINTMENT (RECEPTION)
# =====================================================
@router.post("/appointments", status_code=status.HTTP_201_CREATED)
def create_appointment(
    data: ReceptionAppointmentCreate,
    db: Session = Depends(get_db)
):
    patient = db.query(User).filter(
        User.email == data.patient_email,
        User.role == "patient",
        User.is_active == True
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = db.query(User).filter(
        User.id == data.doctor_id,
        User.role == "doctor",
        User.is_active == True
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    appointment = Appointment(
        patient_id=patient.id,
        patient_email=patient.email,
        doctor_id=doctor.id,
        reason=data.reason,
        status="pending"  # ✅ FIX
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment booked successfully",
        "appointment_id": appointment.id,
        "status": appointment.status
    }


# =====================================================
# VIEW PENDING APPOINTMENTS (FOR ASSIGNMENT)
# =====================================================
@router.get("/appointments/pending")
def get_pending_appointments(db: Session = Depends(get_db)):
    return (
        db.query(Appointment)
        .filter(
            Appointment.status == "pending",
            Appointment.doctor_id == None
        )
        .order_by(Appointment.id.desc())
        .all()
    )


# =====================================================
# GET ALL APPOINTMENTS
# =====================================================
@router.get("/appointments")
def get_all_appointments(db: Session = Depends(get_db)):
    appointments = (
        db.query(
            Appointment.id,
            Appointment.patient_email,
            Appointment.reason,
            Appointment.status,
            Appointment.created_at,
            PatientProfile.first_name.label("p_first"),
            PatientProfile.middle_name.label("p_middle"),
            PatientProfile.last_name.label("p_last")
        )
        .outerjoin(User, Appointment.patient_email == User.email)
        .outerjoin(PatientProfile, User.id == PatientProfile.user_id)
        .order_by(Appointment.id.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "patient_email": a.patient_email,
            "reason": a.reason,
            "status": a.status,
            "created_at": a.created_at,
            "patient_first_name": a.p_first,
            "patient_middle_name": a.p_middle,
            "patient_last_name": a.p_last
        }
        for a in appointments
    ]


# =====================================================
# ASSIGN DOCTOR
# =====================================================
@router.put("/appointments/{appointment_id}/assign")
def assign_doctor(
    appointment_id: int,
    doctor_id: int,
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    doctor = db.query(User).filter(
        User.id == doctor_id,
        User.role == "doctor",
        User.is_active == True
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    appointment.doctor_id = doctor.id
    appointment.status = "pending"  # ✅ FIX
    db.commit()

    return {
        "message": "Doctor assigned successfully",
        "appointment_id": appointment.id,
        "doctor_id": doctor.id,
        "status": appointment.status
    }


# =====================================================
# UPDATE APPOINTMENT STATUS
# =====================================================
@router.put("/appointments/{appointment_id}/status")
def update_appointment_status(
    appointment_id: int,
    status_value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    allowed_statuses = [
        "pending",
        "cancelled",
        "completed"
    ]

    if status_value not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # If completing appointment, use the complete endpoint logic
    if status_value == "completed":
        if appointment.status == "completed":
            raise HTTPException(status_code=400, detail="Appointment already completed")
        
        appointment.status = "completed"
        db.commit()
        
        # Auto-generate bill for appointment
        try:
            from app.utils.auto_billing import auto_generate_appointment_bill
            bill = auto_generate_appointment_bill(db, appointment_id, current_user.id)
            if bill:
                return {
                    "message": "Appointment completed and bill generated",
                    "appointment_id": appointment.id,
                    "bill_id": bill.id,
                    "bill_number": bill.bill_number,
                    "total_amount": bill.total_amount,
                    "status": appointment.status
                }
        except Exception as e:
            print(f"Auto-bill generation failed: {e}")
            # Continue even if bill generation fails
    else:
        appointment.status = status_value
        db.commit()

    return {
        "message": "Appointment status updated successfully",
        "appointment_id": appointment.id,
        "status": appointment.status
    }

# =====================================================
# CANCEL APPOINTMENT
# =====================================================
@router.put("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = "cancelled"
    db.commit()

    return {"message": "Appointment cancelled"}


# =====================================================
# COMPLETE APPOINTMENT & AUTO-GENERATE BILL
# =====================================================
@router.put("/appointments/{appointment_id}/complete")
def complete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark appointment as completed and auto-generate bill"""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status == "completed":
        raise HTTPException(status_code=400, detail="Appointment already completed")

    appointment.status = "completed"
    db.commit()
    
    # Auto-generate bill for appointment
    try:
        from app.utils.auto_billing import auto_generate_appointment_bill
        bill = auto_generate_appointment_bill(db, appointment_id, current_user.id)
        if bill:
            return {
                "message": "Appointment completed and bill generated",
                "appointment_id": appointment.id,
                "bill_id": bill.id,
                "bill_number": bill.bill_number,
                "total_amount": bill.total_amount
            }
    except Exception as e:
        print(f"Auto-bill generation failed: {e}")
    
    return {
        "message": "Appointment completed",
        "appointment_id": appointment.id
    }


# =====================================================
# GET ALL DOCTORS
# =====================================================
@router.get("/doctors")
def get_all_doctors(db: Session = Depends(get_db)):
    doctors = (
        db.query(User.id, User.email, DoctorProfile.first_name, DoctorProfile.last_name, DoctorProfile.specialization)
        .outerjoin(DoctorProfile, User.id == DoctorProfile.user_id)
        .filter(User.role == "doctor", User.is_active == True)
        .order_by(User.email)
        .all()
    )
    return [
        {
            "id": d.id,
            "email": d.email,
            "first_name": d.first_name,
            "last_name": d.last_name,
            "specialization": d.specialization
        }
        for d in doctors
    ]

# =====================================================
# RECEPTIONIST PROFILE MANAGEMENT
# =====================================================
from app.models.receptionist_profile import ReceptionistProfile
from app.schemas.receptionist_profile import ReceptionistProfileResponse, ReceptionistProfileUpdate
import os
from datetime import datetime
from fastapi import UploadFile, File

@router.get("/profile", response_model=ReceptionistProfileResponse)
def get_receptionist_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(ReceptionistProfile).filter(ReceptionistProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_data = profile.__dict__.copy()
    profile_data["email"] = current_user.email
    return profile_data

@router.put("/profile", response_model=ReceptionistProfileResponse)
def update_receptionist_profile(
    data: ReceptionistProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(ReceptionistProfile).filter(ReceptionistProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)

    profile_data = profile.__dict__.copy()
    profile_data["email"] = current_user.email
    return profile_data

@router.post("/profile/upload-photo")
def upload_receptionist_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(ReceptionistProfile).filter(ReceptionistProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

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
            folder="receptionist_profiles",
            public_id=f"user_{current_user.id}_avatar"
        )
        photo_url = result.get("secure_url")

        profile.profile_photo_url = photo_url
        db.commit()

        return {"message": "Photo uploaded successfully", "url": photo_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save profile photo: {e}")

@router.delete("/account")
def delete_receptionist_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully"}
