from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import UploadFile, File
from app.database import get_db
from app.dependencies.auth import require_role, allow_roles
import os
import cloudinary
import cloudinary.uploader
from app.models.lab_request import LabRequest
from app.models.lab_report_file import LabReportFile
from app.models.appointment import Appointment
from app.models.billing import Pricing
from app.schemas.lab import LabPricingCreate, LabPricingUpdate, LabPricingOut
from app.dependencies.auth import get_current_user
from app.models.user import User
from sqlalchemy import func, case
from datetime import date, datetime, timedelta
from app.utils.date_utils import get_ist_today_range
from sqlalchemy.orm import aliased
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile

router = APIRouter(
    prefix="/lab",
    tags=["Lab"]
    # Removed global dependency to allow granular control
)

# =====================================================
# GET LAB DASHBOARD DATA
# =====================================================
@router.get("/dashboard", dependencies=[Depends(require_role("lab"))])
def get_lab_dashboard(db: Session = Depends(get_db)):
    today_start, tomorrow_start = get_ist_today_range()

    # 1. Pending Requests & Next Patient
    PatientUser = aliased(User)
    DoctorUser = aliased(User)

    pending_query = (
        db.query(
            LabRequest,
            PatientUser.email.label("patient_email"),
            DoctorUser.email.label("doctor_email"),
            PatientProfile.first_name.label("p_first"),
            PatientProfile.middle_name.label("p_middle"),
            PatientProfile.last_name.label("p_last"),
            DoctorProfile.first_name.label("d_first"),
            DoctorProfile.last_name.label("d_last")
        )
        .join(PatientUser, LabRequest.patient_id == PatientUser.id)
        .join(DoctorUser, LabRequest.doctor_id == DoctorUser.id)
        .outerjoin(PatientProfile, LabRequest.patient_id == PatientProfile.user_id)
        .outerjoin(DoctorProfile, LabRequest.doctor_id == DoctorProfile.user_id)
        .filter(LabRequest.status == "pending")
        .order_by(LabRequest.id.asc())
        .all()
    )

    pending_count = len(pending_query)
    next_patient = None
    if pending_count > 0:
        first_r, p_email, d_email, pf, pm, pl, df, dl = pending_query[0]
        p_name = f"{pf or ''} {pm or ''} {pl or ''}".strip() or p_email
        d_name = f"Dr. {df or ''} {dl or ''}".strip() if (df or dl) else d_email

        next_patient = {
            "id": first_r.id,
            "patient_email": p_email,
            "patient_name": p_name,
            "doctor_email": d_email,
            "doctor_name": d_name,
            "test_name": first_r.test_name,
            "time": first_r.created_at
        }

    # 2. Uploaded Today
    uploaded_today = (
        db.query(LabReportFile)
        .filter(
            LabReportFile.created_at >= today_start,
            LabReportFile.created_at < tomorrow_start
        )
        .count()
    )

    # 3. Total Active Services
    total_services = (
        db.query(Pricing)
        .filter(
            Pricing.service_type.like("lab_test_%"),
            Pricing.is_active == "true"
        )
        .count()
    )

    # 4. Recent Uploads (Today)
    recent_uploads_query = (
        db.query(
            LabReportFile,
            User.email.label("patient_email"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name
        )
        .join(User, LabReportFile.patient_id == User.id)
        .outerjoin(PatientProfile, LabReportFile.patient_id == PatientProfile.user_id)
        .filter(
            LabReportFile.created_at >= today_start,
            LabReportFile.created_at < tomorrow_start
        )
        .order_by(LabReportFile.created_at.desc())
        .limit(10)
        .all()
    )
    
    # We need the test name. Let's fetch the associated LabRequest for each report
    history_list = []
    for report, p_email, pf, pm, pl in recent_uploads_query:
        p_name = f"{pf or ''} {pm or ''} {pl or ''}".strip() or p_email
        lab_req = db.query(LabRequest).filter(LabRequest.id == report.lab_request_id).first()
        test_name = lab_req.test_name if lab_req else "Unknown Test"
        
        history_list.append({
            "id": report.id,
            "file_name": report.file_name,
            "patient_email": p_email,
            "patient_name": p_name,
            "test_name": test_name,
            "time": report.created_at
        })

    return {
        "stats": {
            "pending_requests": pending_count,
            "uploaded_today": uploaded_today,
            "total_services": total_services
        },
        "next_patient": next_patient,
        "history": history_list
    }


# =====================================================
# GET ALL PENDING LAB REQUESTS
# =====================================================
@router.get("/requests", dependencies=[Depends(require_role("lab"))])
def get_lab_requests(db: Session = Depends(get_db)):
    PatientUser = aliased(User)
    DoctorUser = aliased(User)

    rows = (
        db.query(
            LabRequest,
            PatientUser.email.label("patient_email"),
            DoctorUser.email.label("doctor_email"),
            PatientProfile.first_name.label("p_first"),
            PatientProfile.middle_name.label("p_middle"),
            PatientProfile.last_name.label("p_last"),
            DoctorProfile.first_name.label("d_first"),
            DoctorProfile.last_name.label("d_last")
        )
        .join(PatientUser, LabRequest.patient_id == PatientUser.id)
        .join(DoctorUser, LabRequest.doctor_id == DoctorUser.id)
        .outerjoin(PatientProfile, LabRequest.patient_id == PatientProfile.user_id)
        .outerjoin(DoctorProfile, LabRequest.doctor_id == DoctorProfile.user_id)
        .filter(LabRequest.status == "pending")
        .order_by(LabRequest.id.desc())
        .all()
    )

    return [
        {
            "id": lab_request.id,
            "patient_email": patient_email,
            "patient_name": f"{pf or ''} {pm or ''} {pl or ''}".strip() or patient_email,
            "doctor_email": doctor_email,
            "doctor_name": f"Dr. {df or ''} {dl or ''}".strip() if (df or dl) else doctor_email,
            "test_name": lab_request.test_name,
            "reason": lab_request.reason,
            "status": lab_request.status
        }
        for lab_request, patient_email, doctor_email, pf, pm, pl, df, dl in rows
    ]


# =====================================================
# UPLOAD LAB RESULT
# =====================================================
@router.post("/requests/{lab_request_id}/upload", dependencies=[Depends(require_role("lab"))])
def upload_lab_report(
    lab_request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lab_request = db.query(LabRequest).filter(
        LabRequest.id == lab_request_id
    ).first()

    if not lab_request:
        raise HTTPException(status_code=404, detail="Lab request not found")

    safe_filename = f"lab{current_user.id}_req{lab_request_id}_{file.filename}"
    
    try:
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="lab_reports",
            resource_type="auto",
            public_id=safe_filename.rsplit('.', 1)[0]
        )
        secure_url = upload_result.get("secure_url")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to Cloudinary: {str(e)}")

    report = LabReportFile(
        lab_request_id=lab_request.id,
        patient_id=lab_request.patient_id,
        doctor_id=lab_request.doctor_id,
        lab_id=current_user.id,
        file_name=file.filename,
        file_path=secure_url
    )

    db.add(report)

    # mark lab request completed
    lab_request.status = "completed"

    db.commit()
    
    # Auto-generate bill for lab test
    try:
        from app.utils.auto_billing import auto_generate_lab_test_bill
        # Use a system user ID or receptionist ID - for now using lab user
        auto_generate_lab_test_bill(db, lab_request.id, current_user.id)
    except Exception as e:
        # Log error but don't fail the upload
        print(f"Auto-bill generation failed: {e}")

    return {"message": "Lab report uploaded successfully"}

# =====================================================
# MARK LAB RESULT AS REVIEWED
# =====================================================
@router.put("/reports/{report_id}/mark-reviewed", dependencies=[Depends(require_role("doctor"))])
def mark_lab_report_reviewed(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(LabReportFile).filter(
        LabReportFile.id == report_id,
        LabReportFile.doctor_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Lab report not found or unauthorized")

    report.is_reviewed = True
    
    # Trigger auto-completion of appointment
    lab_request = db.query(LabRequest).filter(LabRequest.id == report.lab_request_id).first()
    if lab_request and lab_request.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == lab_request.appointment_id).first()
        
        if appointment and appointment.status == "in_progress":
            # Check if all lab requests for this appointment are completed and reviewed
            all_requests = db.query(LabRequest).filter(LabRequest.appointment_id == appointment.id).all()
            
            all_done = True
            for req in all_requests:
                if req.status != "completed":
                    all_done = False
                    break
                
                # Check if all reports for this request are reviewed
                reports = db.query(LabReportFile).filter(LabReportFile.lab_request_id == req.id).all()
                if not reports or any(not r.is_reviewed for r in reports):
                    all_done = False
                    break
            
            if all_done:
                appointment.status = "completed"
                print(f">>> AUTO-COMPLETING APPOINTMENT {appointment.id} after lab review <<<")
                try:
                    from app.utils.auto_billing import auto_generate_appointment_bill
                    auto_generate_appointment_bill(db, appointment.id, current_user.id)
                except Exception as e:
                    print(f"Auto-billing failed: {e}")

    db.commit()

    return {"message": "Report marked as reviewed"}


# =====================================================
# LAB PRICING MANAGEMENT (Using Billing Pricing Table)
# =====================================================

@router.get("/pricing", response_model=list[LabPricingOut], dependencies=[Depends(allow_roles(["lab", "doctor", "admin", "receptionist"]))])
def get_lab_pricing(db: Session = Depends(get_db)):
    # Filter only lab tests (service_type starts with 'lab_test_')
    # and only active ones (optional, but good for management)
    return db.query(Pricing).filter(
        Pricing.service_type.like("lab_test_%"),
        Pricing.is_active == "true"
    ).all()

@router.post("/pricing", response_model=LabPricingOut, dependencies=[Depends(require_role("lab"))])
def create_lab_pricing(data: LabPricingCreate, db: Session = Depends(get_db)):
    # Auto-generate service_type
    # e.g., "Full Body Checkup" -> "lab_test_full_body_checkup"
    slug = data.service_name.lower().replace(" ", "_")
    service_type = f"lab_test_{slug}"
    
    # Check if exists
    if db.query(Pricing).filter(Pricing.service_type == service_type).first():
        raise HTTPException(
            status_code=400, 
            detail=f"Lab test pricing for '{data.service_name}' already exists"
        )
    
    pricing = Pricing(
        service_type=service_type,
        service_name=data.service_name,
        base_price=data.base_price,
        default_tax_percent=data.default_tax_percent,
        default_discount_percent=data.default_discount_percent,
        description=data.description,
        is_active="true"
    )
    
    db.add(pricing)
    db.commit()
    db.refresh(pricing)
    return pricing

@router.put("/pricing/{id}", response_model=LabPricingOut, dependencies=[Depends(require_role("lab"))])
def update_lab_pricing(id: int, data: LabPricingUpdate, db: Session = Depends(get_db)):
    pricing = db.query(Pricing).filter(Pricing.id == id).first()
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")
        
    # Security check: Ensure we are only editing lab tests
    if not pricing.service_type.startswith("lab_test_"):
        raise HTTPException(status_code=403, detail="Cannot modify non-lab pricing")
    
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pricing, key, value)
        
    db.commit()
    db.refresh(pricing)
    return pricing

@router.delete("/pricing/{id}", dependencies=[Depends(require_role("lab"))])
def delete_lab_pricing(id: int, db: Session = Depends(get_db)):
    pricing = db.query(Pricing).filter(Pricing.id == id).first()
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")

    # Security check
    if not pricing.service_type.startswith("lab_test_"):
        raise HTTPException(status_code=403, detail="Cannot delete non-lab pricing")
        
    # Soft delete
    pricing.is_active = "false"
    db.commit()
    return {"message": "Pricing deactivated"}


# =====================================================
# LAB PROFILE MANAGEMENT
# =====================================================
from app.models.lab_profile import LabProfile
from app.schemas.lab_profile import LabProfileResponse, LabProfileUpdate

@router.get("/profile", response_model=LabProfileResponse, dependencies=[Depends(require_role("lab"))])
def get_lab_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(LabProfile).filter(LabProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_data = profile.__dict__.copy()
    profile_data["email"] = current_user.email
    return profile_data

@router.put("/profile", response_model=LabProfileResponse, dependencies=[Depends(require_role("lab"))])
def update_lab_profile(
    data: LabProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(LabProfile).filter(LabProfile.user_id == current_user.id).first()
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

@router.post("/profile/upload-photo", dependencies=[Depends(require_role("lab"))])
def upload_lab_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(LabProfile).filter(LabProfile.user_id == current_user.id).first()
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
            folder="lab_profiles",
            public_id=f"user_{current_user.id}_avatar"
        )
        photo_url = result.get("secure_url")

        profile.profile_photo_url = photo_url
        db.commit()

        return {"message": "Photo uploaded successfully", "url": photo_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save profile photo: {e}")

@router.delete("/account", dependencies=[Depends(require_role("lab"))])
def delete_lab_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.delete(current_user) # Cascade deletes the profile
    db.commit()
    return {"message": "Account deleted successfully"}

