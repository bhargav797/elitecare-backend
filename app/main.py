from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

# ✅ IMPORT ALL MODELS (REGISTER TABLES)
from app.models.user import User
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.lab_profile import LabProfile
from app.models.pharmacy_profile import PharmacyProfile
from app.models.receptionist_profile import ReceptionistProfile
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.lab_request import LabRequest
from app.models.lab_report_file import LabReportFile
from app.models.dispense import Dispense
from app.models.medicine import Medicine
from app.models.billing import Bill, BillItem, Payment, Pricing
from app.models.otp import EmailOTP

# ✅ IMPORT ROUTERS
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.doctor import router as doctor_router
from app.routers.reception import router as reception_router
from app.routers.lab import router as lab_router
from app.routers.pharmacy import router as pharmacy_router
from app.routers.patient import router as patient_router
from app.routers.patient_public import router as patient_public_router
from app.routers.lab_reports import router as lab_reports_router
from app.routers.billing import router as billing_router
from app.routers.health_records import router as health_records_router

app = FastAPI(title="Hospital Management System API")

from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
# Split by comma if multiple URLs are provided, and strip white spaces
allowed_origins = [url.strip() for url in frontend_url.split(",")] if frontend_url else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

# Create uploads directory if not exists
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ✅ NOW TABLES WILL BE CREATED
Base.metadata.create_all(bind=engine)

# ✅ ROUTERS
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(doctor_router)
app.include_router(reception_router)
app.include_router(lab_router)
app.include_router(pharmacy_router)
app.include_router(patient_public_router)
app.include_router(patient_router)
app.include_router(lab_reports_router)
app.include_router(billing_router)
app.include_router(health_records_router)

@app.get("/")
def health():
    return {"status": "Backend running"}



