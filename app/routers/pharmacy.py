from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile

from app.database import get_db
from app.dependencies.auth import get_current_user, allow_roles
from app.models.medicine import Medicine
from app.models.dispense import Dispense
from app.models.prescription import Prescription
from app.models.appointment import Appointment   # ✅ ADDED
from app.models.user import User
from app.schemas.pharmacy import (
    MedicineCreate,
    UpdateMedicine,
    DispensePrescription,
    MedicineResponse
)
from sqlalchemy import func, case
from datetime import date, datetime, timedelta

router = APIRouter(
    prefix="/pharmacy",
    tags=["Pharmacy"]
)

# =====================================================
# GET PHARMACY DASHBOARD DATA
# =====================================================
@router.get("/dashboard", dependencies=[Depends(allow_roles(["pharmacy"]))])
def get_pharmacy_dashboard(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())
    tomorrow_start = today_start + timedelta(days=1)

    # 1. Pending Prescriptions & Next Prescription
    PatientUser = aliased(User)
    DoctorUser = aliased(User)
    PP = aliased(PatientProfile)
    DP = aliased(DoctorProfile)

    pending_query = (
        db.query(
            Prescription,
            (PP.first_name + " " + PP.last_name).label("patient_name"),
            PatientUser.email.label("patient_email"),
            (DP.first_name + " " + DP.last_name).label("doctor_name"),
            DoctorUser.email.label("doctor_email")
        )
        .join(PatientUser, Prescription.patient_id == PatientUser.id)
        .join(PP, PatientUser.id == PP.user_id, isouter=True)
        .join(DoctorUser, Prescription.doctor_id == DoctorUser.id)
        .join(DP, DoctorUser.id == DP.user_id, isouter=True)
        .filter(
            ~db.query(Dispense)
             .filter(Dispense.prescription_id == Prescription.id)
             .exists(),
            Prescription.medicines != "[]",
            Prescription.medicines != ""
        )
        .order_by(Prescription.id.asc())
        .all()
    )

    pending_count = len(pending_query)
    next_prescription = None
    if pending_count > 0:
        first_p, p_name, p_email, d_name, d_email = pending_query[0]
        next_prescription = {
            "id": first_p.id,
            "patient_name": p_name or p_email.split('@')[0],
            "patient_email": p_email,
            "doctor_name": f"Dr. {d_name}" if d_name else f"Dr. {d_email.split('@')[0]}",
            "doctor_email": d_email,
            "time": first_p.created_at
        }

    # 2. Dispensed Today
    dispensed_today_count = (
        db.query(Dispense)
        .filter(
            Dispense.dispensed_at >= today_start,
            Dispense.dispensed_at < tomorrow_start
        )
        .count()
    )

    # 3. Low Stock Items (Threshold: 20)
    LOW_STOCK_THRESHOLD = 20
    low_stock_query = (
        db.query(Medicine)
        .filter(Medicine.stock <= LOW_STOCK_THRESHOLD)
        .order_by(Medicine.stock.asc())
        .all()
    )
    low_stock_count = len(low_stock_query)
    low_stock_items = [
        {"id": m.id, "name": m.name, "stock": m.stock}
        for m in low_stock_query
    ]

    # 4. Recent Dispenses (Today)
    recent_dispenses_query = (
        db.query(
            Dispense,
            User.email.label("patient_email"),
            (PatientProfile.first_name + " " + PatientProfile.last_name).label("patient_name")
        )
        .join(User, Dispense.patient_id == User.id)
        .join(PatientProfile, User.id == PatientProfile.user_id, isouter=True)
        .filter(
            Dispense.dispensed_at >= today_start,
            Dispense.dispensed_at < tomorrow_start
        )
        .order_by(Dispense.dispensed_at.desc())
        .limit(10)
        .all()
    )
    
    history_list = [
        {
            "id": d.id,
            "prescription_id": d.prescription_id,
            "patient_name": p_name or p_email.split('@')[0],
            "patient_email": p_email,
            "time": d.dispensed_at
        }
        for d, p_email, p_name in recent_dispenses_query
    ]

    return {
        "stats": {
            "pending_prescriptions": pending_count,
            "dispensed_today": dispensed_today_count,
            "low_stock": low_stock_count
        },
        "next_prescription": next_prescription,
        "low_stock_items": low_stock_items,
        "history": history_list
    }


# =====================================================
# GET PRESCRIPTIONS (NOT YET DISPENSED)
# =====================================================
@router.get("/prescriptions", dependencies=[Depends(allow_roles(["pharmacy"]))])
def get_prescriptions(db: Session = Depends(get_db)):
    PatientUser = aliased(User)
    DoctorUser = aliased(User)
    PP = aliased(PatientProfile)
    DP = aliased(DoctorProfile)

    rows = (
        db.query(
            Prescription,
            PatientUser.email.label("patient_email"),
            (PP.first_name + " " + PP.last_name).label("patient_name"),
            DoctorUser.email.label("doctor_email"),
            (DP.first_name + " " + DP.last_name).label("doctor_name")
        )
        .join(PatientUser, Prescription.patient_id == PatientUser.id)
        .join(PP, PatientUser.id == PP.user_id, isouter=True)
        .join(DoctorUser, Prescription.doctor_id == DoctorUser.id)
        .join(DP, DoctorUser.id == DP.user_id, isouter=True)
        .filter(
            ~db.query(Dispense)
             .filter(Dispense.prescription_id == Prescription.id)
             .exists(),
            # ✅ Filter out empty medicines (JSON "[]" or empty string)
            Prescription.medicines != "[]",
            Prescription.medicines != ""
        )
        .order_by(Prescription.id.desc())
        .all()
    )

    return [
        {
            "id": p.id,
            "patient_email": p_email,
            "patient_name": p_name or p_email.split('@')[0],
            "doctor_email": d_email,
            "doctor_name": d_name or d_email.split('@')[0],
            "medicines": p.medicines,
            "notes": p.notes,
            "created_at": p.created_at
        }
        for p, p_email, p_name, d_email, d_name in rows
    ]


# =====================================================
# GET MEDICINES
# =====================================================
@router.get("/medicines", response_model=list[MedicineResponse])
def get_medicines(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_role = current_user.role.strip().lower()
    print(f"DEBUG: User role (raw): '{current_user.role}', (normalized): '{user_role}'")
    
    allowed = ["pharmacy", "admin", "doctor"]
    if user_role not in allowed:
        print(f"DEBUG: Access denied. '{user_role}' not in {allowed}")
        raise HTTPException(status_code=403, detail=f"Access denied for role: {current_user.role}")
    
    medicines = db.query(Medicine).order_by(Medicine.name).all()
    return medicines


# =====================================================
# ADD MEDICINE
# =====================================================
# =====================================================
# ADD MEDICINE
# =====================================================
@router.post("/medicines")
def add_medicine(
    data: MedicineCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ["pharmacy", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    if db.query(Medicine).filter(Medicine.name == data.name).first():
        raise HTTPException(status_code=400, detail="Medicine already exists")

    medicine = Medicine(name=data.name, stock=data.stock, price=data.price)
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    return {"message": "Medicine added", "medicine_id": medicine.id}


# =====================================================
# UPDATE MEDICINE
# =====================================================
@router.put("/medicines/{medicine_id}")
def update_medicine(
    medicine_id: int, 
    data: UpdateMedicine, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ["pharmacy", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    if data.stock is not None:
        medicine.stock = data.stock
    if data.name is not None:
        medicine.name = data.name
    if data.price is not None:
        medicine.price = data.price

    db.commit()
    return {"message": "Medicine updated"}


# =====================================================
# DISPENSE PRESCRIPTION
# =====================================================
@router.post("/dispense", dependencies=[Depends(allow_roles(["pharmacy"]))])
def dispense_prescription(
    data: DispensePrescription,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prescription = db.query(Prescription).filter(
        Prescription.id == data.prescription_id
    ).first()

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if db.query(Dispense).filter(
        Dispense.prescription_id == prescription.id
    ).first():
        raise HTTPException(status_code=400, detail="Already dispensed")

    # 1. Parse medicines
    import json
    try:
        meds_list = json.loads(prescription.medicines)
        # Expected format: [{"name": "A", "quantity": 10}, ...]
        # Handle string format legacy support
        if isinstance(meds_list, str): 
             # It was a simple string just wrapped in quotes? or just fail back to legacy
             # If it was "Paracetamol, Ibuprofen" string
             med_names = [m.strip() for m in prescription.medicines.split(',')]
             meds_list = [{"name": n, "quantity": 1} for n in med_names]
    except:
        # Fallback for old simple string format
        med_names = [m.strip() for m in prescription.medicines.split(',')]
        meds_list = [{"name": n, "quantity": 1} for n in med_names]

    medicine_costs = []
    
    # 2. Check Stock & Calculate Costs
    for item in meds_list:
        name = item.get("name")
        qty = int(item.get("quantity", 1))
        
        med_db = db.query(Medicine).filter(Medicine.name == name).first()
        if not med_db:
            raise HTTPException(status_code=400, detail=f"Medicine '{name}' not found in inventory")
        
        if med_db.stock < qty:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for '{name}'. Available: {med_db.stock}")
            
        # Add to cost list
        medicine_costs.append({
            "medicine_name": name,
            "quantity": qty,
            "unit_price": med_db.price
        })

    # 3. Deduct Stock (only if all checks pass)
    for item in meds_list:
        name = item.get("name")
        qty = int(item.get("quantity", 1))
        med_db = db.query(Medicine).filter(Medicine.name == name).first()
        med_db.stock -= qty

    dispense = Dispense(
        prescription_id=prescription.id,
        patient_id=prescription.patient_id,
        pharmacist_id=current_user.id
    )

    db.add(dispense)

    # Mark appointment completed
    appointment = db.query(Appointment).filter(
        Appointment.id == prescription.appointment_id
    ).first()

    if appointment:
        appointment.status = "completed"
        db.commit()
        
        # Auto-generate bill for appointment completion
        try:
            from app.utils.auto_billing import auto_generate_appointment_bill
            # Check if bill already exists
            from app.models.billing import Bill
            existing_bill = db.query(Bill).filter(Bill.appointment_id == appointment.id).first()
            if not existing_bill:
                auto_generate_appointment_bill(db, appointment.id, current_user.id)
        except Exception as e:
            print(f"Auto-bill generation for appointment failed: {e}")

    db.commit()
    db.refresh(dispense)
    
    # Auto-generate bill for medicine dispensing using ACTUAL costs
    try:
        from app.utils.auto_billing import auto_generate_medicine_bill
        auto_generate_medicine_bill(db, dispense.id, current_user.id, medicine_costs)
    except Exception as e:
        print(f"Auto-bill generation for medicine failed: {e}")
    
    return {"message": "Prescription dispensed"}


# =====================================================
# DISPENSE HISTORY
# =====================================================
@router.get("/dispense-history", dependencies=[Depends(allow_roles(["pharmacy"]))])
def dispense_history(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Dispense,
            User.email.label("patient_email"),
            (PatientProfile.first_name + " " + PatientProfile.last_name).label("patient_name"),
            Prescription.medicines
        )
        .join(User, Dispense.patient_id == User.id)
        .join(PatientProfile, User.id == PatientProfile.user_id, isouter=True)
        .join(Prescription, Dispense.prescription_id == Prescription.id)
        .order_by(Dispense.dispensed_at.desc())
        .all()
    )

    return [
        {
            "id": d.id,
            "patient_email": p_email,
            "patient_name": p_name or p_email.split('@')[0],
            "prescription_id": d.prescription_id,
            "medicines": medicines,
            "dispensed_at": d.dispensed_at
        }
        for d, p_email, p_name, medicines in rows
    ]


# =====================================================
# DELETE MEDICINE
# =====================================================
@router.delete("/medicines/{medicine_id}")
def delete_medicine(
    medicine_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ["pharmacy", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    db.delete(medicine)
    db.commit()
    return {"message": "Medicine deleted"}

# =====================================================
# PHARMACY PROFILE MANAGEMENT
# =====================================================
from app.models.pharmacy_profile import PharmacyProfile
from app.schemas.pharmacy_profile import PharmacyProfileResponse, PharmacyProfileUpdate
import os
from datetime import datetime
from fastapi import UploadFile, File

@router.get("/profile", response_model=PharmacyProfileResponse, dependencies=[Depends(allow_roles(["pharmacy"]))])
def get_pharmacy_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(PharmacyProfile).filter(PharmacyProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_data = profile.__dict__.copy()
    profile_data["email"] = current_user.email
    return profile_data

@router.put("/profile", response_model=PharmacyProfileResponse, dependencies=[Depends(allow_roles(["pharmacy"]))])
def update_pharmacy_profile(
    data: PharmacyProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(PharmacyProfile).filter(PharmacyProfile.user_id == current_user.id).first()
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

@router.post("/profile/upload-photo", dependencies=[Depends(allow_roles(["pharmacy"]))])
def upload_pharmacy_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(PharmacyProfile).filter(PharmacyProfile.user_id == current_user.id).first()
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
            folder="pharmacy_profiles",
            public_id=f"user_{current_user.id}_avatar"
        )
        photo_url = result.get("secure_url")

        profile.profile_photo_url = photo_url
        db.commit()

        return {"message": "Photo uploaded successfully", "url": photo_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save profile photo: {e}")

@router.delete("/account", dependencies=[Depends(allow_roles(["pharmacy"]))])
def delete_pharmacy_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully"}
