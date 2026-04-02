import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse, Response
import urllib.request
import cloudinary
import cloudinary.uploader
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.models.lab_report_file import LabReportFile
from app.models.lab_request import LabRequest

# -----------------------------------
# Router setup
# -----------------------------------
router = APIRouter(
    prefix="/lab/reports",
    tags=["Lab Reports"]
)

# -----------------------------------
# File storage config
# -----------------------------------
UPLOAD_DIR = "uploads/lab_reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =====================================================
# LAB → UPLOAD REPORT (PDF) FOR A LAB REQUEST
# =====================================================
@router.post(
    "/upload",
    dependencies=[Depends(require_role("lab"))]
)
def upload_lab_report(
    lab_request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only PDF allowed
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Fetch lab request
    lab_request = db.query(LabRequest).filter(
        LabRequest.id == lab_request_id
    ).first()

    if not lab_request:
        raise HTTPException(status_code=404, detail="Lab request not found")

    # Build safe filename
    safe_filename = f"lab{current_user.id}_req{lab_request_id}_{file.filename}"

    # Upload to Cloudinary
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

    # Save DB record
    report = LabReportFile(
        lab_request_id=lab_request_id,
        patient_id=lab_request.patient_id,
        doctor_id=lab_request.doctor_id,
        lab_id=current_user.id,
        file_name=file.filename,
        file_path=secure_url
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Lab report uploaded successfully",
        "report_id": report.id
    }

# =====================================================
# PATIENT → VIEW OWN LAB REPORTS
# =====================================================
@router.get(
    "/patient",
    dependencies=[Depends(require_role("patient"))]
)
def get_patient_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.user import User
    from app.models.patient_profile import PatientProfile

    reports = (
        db.query(
            LabReportFile,
            PatientProfile.first_name.label("patient_first_name"),
            PatientProfile.middle_name.label("patient_middle_name"),
            PatientProfile.last_name.label("patient_last_name")
        )
        .outerjoin(PatientProfile, LabReportFile.patient_id == PatientProfile.user_id)
        .filter(LabReportFile.patient_id == current_user.id)
        .all()
    )

    return [
        {
            **r[0].__dict__,
            "patient_first_name": r.patient_first_name,
            "patient_middle_name": r.patient_middle_name,
            "patient_last_name": r.patient_last_name
        }
        for r in reports
    ]

# =====================================================
# DOCTOR → VIEW OWN PATIENT LAB REPORTS
# =====================================================
@router.get(
    "/doctor",
    dependencies=[Depends(require_role("doctor"))]
)
def get_doctor_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.user import User
    from app.models.patient_profile import PatientProfile

    reports = (
        db.query(
            LabReportFile,
            User.email.label("patient_email"),
            PatientProfile.first_name.label("patient_first_name"),
            PatientProfile.middle_name.label("patient_middle_name"),
            PatientProfile.last_name.label("patient_last_name")
        )
        .join(User, LabReportFile.patient_id == User.id)
        .outerjoin(PatientProfile, LabReportFile.patient_id == PatientProfile.user_id)
        .filter(LabReportFile.doctor_id == current_user.id)
        .all()
    )

    return [
        {
            **r[0].__dict__,
            "patient_email": r.patient_email,
            "patient_first_name": r.patient_first_name,
            "patient_middle_name": r.patient_middle_name,
            "patient_last_name": r.patient_last_name
        }
        for r in reports
    ]

# =====================================================
# PREVIEW PDF (PATIENT / DOCTOR)
# =====================================================
@router.get("/preview/{report_id}")
def preview_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(LabReportFile).filter(
        LabReportFile.id == report_id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Access control
    if current_user.role == "patient" and report.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if current_user.role == "doctor" and report.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.file_path.startswith("http"):
        return {"type": "redirect", "url": report.file_path}

    return FileResponse(
        path=report.file_path,
        media_type="application/pdf"
    )

# =====================================================
# DOWNLOAD PDF (PATIENT / DOCTOR)
# =====================================================
@router.get("/download/{report_id}")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(LabReportFile).filter(
        LabReportFile.id == report_id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Access control
    if current_user.role == "patient" and report.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if current_user.role == "doctor" and report.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.file_path.startswith("http"):
        url = report.file_path
        if "/upload/" in url and "fl_attachment" not in url:
            url = url.replace("/upload/", "/upload/fl_attachment/")
        return {"type": "redirect", "url": url}

    return FileResponse(
        path=report.file_path,
        filename=report.file_name,
        media_type="application/pdf"
    )
