from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User

# ✅ CORRECT PROFILE MODELS
from app.models.doctor_profile import DoctorProfile
from app.models.lab_profile import LabProfile
from app.models.pharmacy_profile import PharmacyProfile
from app.models.receptionist_profile import ReceptionistProfile
from app.models.billing import Bill, BillItem, Payment, BillItemType, PaymentMode

from app.schemas.admin import (
    UserResponse,
    UpdateUserRole,
    UpdateUserStatus,
    DoctorCreate,
    LabCreate,
    PharmacyCreate,
    ReceptionistCreate
)

from app.core.security import hash_password
from app.dependencies.auth import require_role

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role("admin"))]
)

# =====================================================
# CREATE DOCTOR
# =====================================================
@router.post("/create-doctor", status_code=status.HTTP_201_CREATED)
def create_doctor(
    data: DoctorCreate,
    db: Session = Depends(get_db)
):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role="doctor",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = DoctorProfile(
        user_id=user.id,
        first_name=data.first_name,
        middle_name=data.middle_name,
        last_name=data.last_name,
        dob=data.dob,
        gender=data.gender,
        registration_number=data.registration_number,
        council_name=data.council_name,
        specialization=data.specialization,
        experience_years=data.experience_years,
        qualification=data.qualification,
        mobile=data.mobile,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode
    )

    db.add(profile)
    db.commit()

    return {"message": "Doctor created successfully", "user_id": user.id}


# =====================================================
# CREATE LAB
# =====================================================
@router.post("/create-lab", status_code=status.HTTP_201_CREATED)
def create_lab(
    data: LabCreate,
    db: Session = Depends(get_db)
):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role="lab",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = LabProfile(
        user_id=user.id,
        lab_name=data.lab_name,
        registration_number=data.registration_number,
        lab_type=data.lab_type,
        contact_person=data.contact_person,
        contact_number=data.contact_number,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        nabl_accredited=data.nabl_accredited,
        accreditation_number=data.accreditation_number
    )

    db.add(profile)
    db.commit()

    return {"message": "Lab created successfully", "user_id": user.id}


# =====================================================
# CREATE PHARMACY
# =====================================================
@router.post("/create-pharmacy", status_code=status.HTTP_201_CREATED)
def create_pharmacy(
    data: PharmacyCreate,
    db: Session = Depends(get_db)
):
    # password check
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # email check
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # create user
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role="pharmacy",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # ✅ OPTION 1: ONLY MODEL FIELDS
    profile = PharmacyProfile(
        user_id=user.id,
        pharmacy_name=data.pharmacy_name,
        license_number=data.drug_license_number,
        license_type=data.license_type
    )

    db.add(profile)
    db.commit()

    return {
        "message": "Pharmacy created successfully",
        "user_id": user.id
    }


# =====================================================
# CREATE RECEPTIONIST
# =====================================================
@router.post("/create-receptionist", status_code=status.HTTP_201_CREATED)
def create_receptionist(
    data: ReceptionistCreate,
    db: Session = Depends(get_db)
):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role="receptionist",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = ReceptionistProfile(
        user_id=user.id,
        first_name=data.first_name,
        middle_name=data.middle_name,
        last_name=data.last_name,
        dob=data.dob,
        gender=data.gender,
        languages_known=data.languages_known,
        mobile=data.mobile,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode
    )

    db.add(profile)
    db.commit()

    return {"message": "Receptionist created successfully", "user_id": user.id}


# =====================================================
# GET ALL USERS
# =====================================================
@router.get("/users", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


# =====================================================
# DASHBOARD STATS
# =====================================================
@router.get("/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = total_users - active_users

    roles = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    role_counts = {role: count for role, count in roles if role}

    # Revenue Stats
    total_rev = db.query(func.sum(Bill.paid_amount)).scalar() or 0.0
    total_pend = db.query(func.sum(Bill.remaining_amount)).scalar() or 0.0

    # Revenue by Category
    rev_by_cat_raw = (
        db.query(BillItem.item_type, func.sum(BillItem.item_total))
        .join(Bill, BillItem.bill_id == Bill.id)
        .filter(Bill.payment_status != "pending") # Only count items from paid/partially paid bills? 
        # Actually, item_total is what is BILLED. 
        # Let's count all billed items for breakdown
        .group_by(BillItem.item_type)
        .all()
    )
    rev_by_cat = {item_type.value: total for item_type, total in rev_by_cat_raw if item_type}

    # Revenue by Payment Mode
    rev_by_mode_raw = (
        db.query(Payment.payment_mode, func.sum(Payment.amount))
        .group_by(Payment.payment_mode)
        .all()
    )
    rev_by_mode = {mode.value: total for mode, total in rev_by_mode_raw if mode}

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "role_counts": role_counts,
        "revenue": {
            "total_collected": total_rev,
            "total_pending": total_pend,
            "by_category": rev_by_cat,
            "by_payment_mode": rev_by_mode
        }
    }


@router.get("/revenue-detailed")
def get_revenue_detailed(
    start_date: str = None,
    end_date: str = None,
    selected_date: str = None,
    db: Session = Depends(get_db)
):
    from app.models.patient_profile import PatientProfile
    from app.models.user import User as UserModel
    from datetime import datetime, timedelta

    # Date parsing
    is_lifetime = False
    try:
        if selected_date and selected_date.strip():
            parsed_start = datetime.strptime(selected_date, "%Y-%m-%d")
            # For "single date", end is same day + 1
            parsed_end = parsed_start + timedelta(days=1)
        elif start_date and start_date.strip():
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date and end_date.strip():
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            else:
                parsed_end = parsed_start + timedelta(days=1)
        else:
            is_lifetime = True
            parsed_start = None
            parsed_end = None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Base bill query
    bill_query = db.query(Bill)
    if not is_lifetime:
        bill_query = bill_query.filter(Bill.bill_date.between(parsed_start, parsed_end))

    # 1. Stats
    total_rev = db.query(func.sum(Bill.paid_amount))
    total_pend = db.query(func.sum(Bill.remaining_amount))
    bill_count_query = db.query(func.count(Bill.id))
    total_billed_query = db.query(func.sum(Bill.total_amount))

    if not is_lifetime:
        total_rev = total_rev.filter(Bill.bill_date.between(parsed_start, parsed_end))
        total_pend = total_pend.filter(Bill.bill_date.between(parsed_start, parsed_end))
        bill_count_query = bill_count_query.filter(Bill.bill_date.between(parsed_start, parsed_end))
        total_billed_query = total_billed_query.filter(Bill.bill_date.between(parsed_start, parsed_end))

    total_rev = total_rev.scalar() or 0.0
    total_pend = total_pend.scalar() or 0.0
    bill_count = bill_count_query.scalar() or 0
    total_billed = total_billed_query.scalar() or 0.0
    avg_bill = total_rev / bill_count if bill_count > 0 else 0.0

    # 2. Daily Collection Trend (Always show 30 days for context)
    from app.utils.date_utils import get_ist_now
    ist_now = get_ist_now()
    trend_end = parsed_end if (not is_lifetime and parsed_end) else ist_now + timedelta(days=1)
    trend_start = trend_end - timedelta(days=30)
    
    daily_rev_raw = (
        db.query(func.date(Bill.bill_date).label("d"), func.sum(Bill.total_amount).label("amt")) # Changed to total_amount
        .filter(Bill.bill_date.between(trend_start, trend_end))
        .group_by(func.date(Bill.bill_date))
        .all()
    )
    # Ensure keys are strings in YYYY-MM-DD format
    daily_rev_dict = {str(row.d): (row.amt or 0.0) for row in daily_rev_raw}
    daily_revenue_trend = []
    for i in range(30):
        d_obj = trend_start.date() + timedelta(days=i)
        date_key = d_obj.strftime("%Y-%m-%d")
        daily_revenue_trend.append({
            "date": d_obj.strftime("%d %b"),
            "amount": float(daily_rev_dict.get(date_key, 0.0))
        })

    # 3. Registry (within range or global)
    recent_bills_query = (
        db.query(
            Bill,
            PatientProfile.first_name,
            PatientProfile.last_name,
            UserModel.email.label("patient_email")
        )
        .join(UserModel, Bill.patient_id == UserModel.id)
        .outerjoin(PatientProfile, UserModel.id == PatientProfile.user_id)
    )
    
    if not is_lifetime:
        recent_bills_query = recent_bills_query.filter(Bill.bill_date.between(parsed_start, parsed_end))
    
    recent_bills_query = recent_bills_query.order_by(Bill.id.desc()).limit(200).all()

    recent_bills = [
        {
            "id": b.id,
            "bill_number": b.bill_number,
            "patient_name": f"{pf or ''} {pl or ''}".strip() or pe,
            "total_amount": b.total_amount,
            "paid_amount": b.paid_amount,
            "remaining_amount": b.remaining_amount,
            "status": b.payment_status,
            "date": b.bill_date,
        }
        for b, pf, pl, pe in recent_bills_query
    ]

    return {
        "stats": {
            "total_collected": total_rev,
            "total_pending": total_pend,
            "total_billed": total_billed,
            "avg_bill_value": avg_bill,
            "total_bills": bill_count,
            "is_lifetime": is_lifetime
        },
        "daily_trend": daily_revenue_trend,
        "recent_bills": recent_bills
    }


# =====================================================
# UPDATE USER ROLE
# =====================================================
@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    data: UpdateUserRole,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = data.role
    db.commit()

    return {
        "message": "User role updated successfully",
        "user_id": user.id,
        "new_role": user.role
    }


# =====================================================
# ACTIVATE / DEACTIVATE USER
# =====================================================
@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    data: UpdateUserStatus,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = data.is_active
    db.commit()

    return {
        "message": "User status updated successfully",
        "user_id": user.id,
        "is_active": user.is_active
    }


# =====================================================
# DELETE USER
# =====================================================
@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully", "user_id": user_id}
