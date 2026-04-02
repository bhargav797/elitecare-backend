from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.dependencies.auth import require_role, get_current_user
from app.models.billing import Bill, BillItem, Payment, Pricing, PaymentStatus, PaymentMode
from app.models.user import User
from app.models.appointment import Appointment
from app.models.lab_request import LabRequest
from app.models.dispense import Dispense
from app.models.prescription import Prescription
from app.schemas.billing import (
    PricingCreate,
    PricingUpdate,
    PricingResponse,
    BillCreate,
    BillUpdate,
    BillResponse,
    BillSummaryResponse,
    BillItemCreate,
    PaymentCreate,
    PaymentResponse,
    AutoBillAppointment,
    AutoBillLabTest,
    AutoBillMedicine
)
from app.utils.billing_utils import (
    generate_bill_number,
    calculate_item_totals,
    calculate_bill_totals,
    get_pricing,
    get_or_create_pricing,
    update_bill_payment_status
)
from app.utils.pdf_generator import generate_invoice_pdf

router = APIRouter(
    prefix="/billing",
    tags=["Billing & Payments"]
)


# =====================================================
# ADMIN ENDPOINTS - PRICING MANAGEMENT
# =====================================================

@router.post("/admin/pricing", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
def create_pricing(
    data: PricingCreate,
    db: Session = Depends(get_db)
):
    """Admin: Create or update pricing for a service"""
    existing = db.query(Pricing).filter(Pricing.service_type == data.service_type).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Pricing for service_type '{data.service_type}' already exists. Use update endpoint."
        )
    
    pricing = Pricing(
        service_type=data.service_type,
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
    
    return {"message": "Pricing created successfully", "pricing": PricingResponse.model_validate(pricing)}


@router.get("/admin/pricing", dependencies=[Depends(require_role("admin"))])
def get_all_pricing(db: Session = Depends(get_db)):
    """Admin: Get all pricing configurations"""
    pricings = db.query(Pricing).order_by(Pricing.service_type).all()
    return [PricingResponse.model_validate(p) for p in pricings]


@router.get("/admin/pricing/{pricing_id}", dependencies=[Depends(require_role("admin"))])
def get_pricing_by_id(pricing_id: int, db: Session = Depends(get_db)):
    """Admin: Get pricing by ID"""
    pricing = db.query(Pricing).filter(Pricing.id == pricing_id).first()
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")
    return PricingResponse.model_validate(pricing)


@router.put("/admin/pricing/{pricing_id}", dependencies=[Depends(require_role("admin"))])
def update_pricing(
    pricing_id: int,
    data: PricingUpdate,
    db: Session = Depends(get_db)
):
    """Admin: Update pricing"""
    pricing = db.query(Pricing).filter(Pricing.id == pricing_id).first()
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")
    
    if data.service_name is not None:
        pricing.service_name = data.service_name
    if data.base_price is not None:
        pricing.base_price = data.base_price
    if data.default_tax_percent is not None:
        pricing.default_tax_percent = data.default_tax_percent
    if data.default_discount_percent is not None:
        pricing.default_discount_percent = data.default_discount_percent
    if data.description is not None:
        pricing.description = data.description
    if data.is_active is not None:
        pricing.is_active = data.is_active
    
    db.commit()
    db.refresh(pricing)
    
    return {"message": "Pricing updated successfully", "pricing": PricingResponse.model_validate(pricing)}


@router.delete("/admin/pricing/{pricing_id}", dependencies=[Depends(require_role("admin"))])
def delete_pricing(pricing_id: int, db: Session = Depends(get_db)):
    """Admin: Delete pricing (Hard Delete)"""
    pricing = db.query(Pricing).filter(Pricing.id == pricing_id).first()
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")
    
    db.delete(pricing)
    db.commit()
    
    return {"message": "Pricing deleted successfully"}


# =====================================================
# RECEPTIONIST ENDPOINTS - BILL CREATION & PAYMENT COLLECTION
# =====================================================

@router.post("/bills", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("receptionist"))])
def create_bill(
    data: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Receptionist: Create a new bill"""
    # Verify patient exists
    patient = db.query(User).filter(
        User.id == data.patient_id,
        User.role == "patient",
        User.is_active == True
    ).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify related entities if provided
    if data.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == data.appointment_id).first()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
    
    if data.lab_request_id:
        lab_request = db.query(LabRequest).filter(LabRequest.id == data.lab_request_id).first()
        if not lab_request:
            raise HTTPException(status_code=404, detail="Lab request not found")
    
    if data.dispense_id:
        dispense = db.query(Dispense).filter(Dispense.id == data.dispense_id).first()
        if not dispense:
            raise HTTPException(status_code=404, detail="Dispense not found")
    
    # Generate bill number
    bill_number = generate_bill_number()
    
    # Create bill items and calculate totals
    bill_items = []
    for item_data in data.items:
        totals = calculate_item_totals(
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount_percent=item_data.discount_percent,
            tax_percent=item_data.tax_percent
        )
        
        bill_item = BillItem(
            item_type=item_data.item_type,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount_percent=item_data.discount_percent,
            tax_percent=item_data.tax_percent,
            item_subtotal=totals["item_subtotal"],
            item_discount=totals["item_discount"],
            item_tax=totals["item_tax"],
            item_total=totals["item_total"],
            reference_id=item_data.reference_id
        )
        bill_items.append(bill_item)
    
    # Calculate bill totals
    bill_totals = calculate_bill_totals(bill_items, data.discount_amount)
    
    # Create bill
    bill = Bill(
        patient_id=data.patient_id,
        appointment_id=data.appointment_id,
        lab_request_id=data.lab_request_id,
        dispense_id=data.dispense_id,
        bill_number=bill_number,
        subtotal=bill_totals["subtotal"],
        discount_amount=bill_totals["discount_amount"],
        tax_amount=bill_totals["tax_amount"],
        total_amount=bill_totals["total_amount"],
        payment_status=PaymentStatus.PENDING,
        paid_amount=0.0,
        remaining_amount=bill_totals["total_amount"],
        created_by_id=current_user.id
    )
    
    db.add(bill)
    db.flush()  # Get bill ID
    
    # Add items to bill
    for item in bill_items:
        item.bill_id = bill.id
        db.add(item)
    
    db.commit()
    db.refresh(bill)
    
    return {
        "message": "Bill created successfully",
        "bill": BillResponse.model_validate(bill)
    }


@router.get("/bills", dependencies=[Depends(require_role("receptionist"))])
def get_all_bills(
    patient_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Receptionist: Get all bills with optional filters"""
    from app.models.patient_profile import PatientProfile
    query = (
        db.query(
            Bill, 
            User.email.label("patient_email"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name
        )
        .join(User, Bill.patient_id == User.id)
        .outerjoin(PatientProfile, User.id == PatientProfile.user_id)
    )
    
    if patient_id:
        query = query.filter(Bill.patient_id == patient_id)
    
    if status_filter:
        query = query.filter(Bill.payment_status == status_filter)
    
    results = query.order_by(Bill.id.desc()).all()
    
    bills = []
    for bill, patient_email, first, middle, last in results:
        bill_dict = BillResponse.model_validate(bill).model_dump()
        bill_dict["patient_email"] = patient_email
        bill_dict["patient_first_name"] = first
        bill_dict["patient_middle_name"] = middle
        bill_dict["patient_last_name"] = last
        bills.append(bill_dict)
    
    return bills


@router.get("/bills/{bill_id}", dependencies=[Depends(require_role("receptionist"))])
def get_bill_by_id(bill_id: int, db: Session = Depends(get_db)):
    """Receptionist: Get bill by ID"""
    from app.models.patient_profile import PatientProfile
    result = (
        db.query(
            Bill, 
            User.email.label("patient_email"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name,
            PatientProfile.profile_photo_url
        )
        .join(User, Bill.patient_id == User.id)
        .outerjoin(PatientProfile, User.id == PatientProfile.user_id)
        .filter(Bill.id == bill_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    bill, patient_email, first, middle, last, profile_photo_url = result
    bill_dict = BillResponse.model_validate(bill).model_dump()
    bill_dict["patient_email"] = patient_email
    bill_dict["patient_first_name"] = first
    bill_dict["patient_middle_name"] = middle
    bill_dict["patient_last_name"] = last
    bill_dict["patient_profile_photo_url"] = profile_photo_url
    
    # Add payment details
    payments = db.query(Payment).filter(Payment.bill_id == bill_id).all()
    bill_dict["payments"] = [PaymentResponse.model_validate(p).model_dump() for p in payments]
    
    return bill_dict


@router.post("/bills/{bill_id}/payments", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("receptionist"))])
def collect_payment(
    bill_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Receptionist: Collect payment for a bill"""
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify bill_id matches
    if data.bill_id != bill_id:
        raise HTTPException(status_code=400, detail="Bill ID mismatch")
    
    # Check if payment amount exceeds remaining amount
    if data.amount > bill.remaining_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount (₹{data.amount}) exceeds remaining amount (₹{bill.remaining_amount})"
        )
    
    # Create payment
    payment = Payment(
        bill_id=bill_id,
        amount=data.amount,
        payment_mode=data.payment_mode,
        transaction_id=data.transaction_id,
        insurance_provider=data.insurance_provider if data.payment_mode == PaymentMode.INSURANCE else None,
        notes=data.notes,
        collected_by_id=current_user.id
    )
    
    db.add(payment)
    db.flush()
    
    # Update bill payment status
    update_bill_payment_status(bill, db)
    
    db.refresh(bill)
    db.refresh(payment)
    
    return {
        "message": "Payment collected successfully",
        "payment": PaymentResponse.model_validate(payment),
        "bill_status": bill.payment_status.value,
        "remaining_amount": bill.remaining_amount
    }


@router.get("/bills/{bill_id}/download", dependencies=[Depends(require_role("receptionist"))])
def download_bill_pdf(bill_id: int, db: Session = Depends(get_db)):
    """Receptionist: Download bill as PDF"""
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    patient = db.query(User).filter(User.id == bill.patient_id).first()
    patient_email = patient.email if patient else "Unknown"
    
    from app.models.patient_profile import PatientProfile
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == bill.patient_id).first()
    
    first_name = profile.first_name if profile else None
    last_name = profile.last_name if profile else None
    profile_photo = profile.profile_photo_url if profile else None
    
    pdf_buffer = generate_invoice_pdf(
        bill=bill, 
        patient_email=patient_email,
        first_name=first_name,
        last_name=last_name,
        profile_photo=profile_photo
    )
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=bill_{bill.bill_number}.pdf"
        }
    )


# =====================================================
# PATIENT ENDPOINTS - VIEW BILLS & DOWNLOAD
# =====================================================

@router.get("/patient/bills", dependencies=[Depends(require_role("patient"))])
def get_my_bills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Patient: Get all my bills"""
    bills = db.query(Bill).filter(Bill.patient_id == current_user.id).order_by(Bill.id.desc()).all()
    
    # Fix: Manually construct response to include patient_email
    results = []
    for bill in bills:
        bill_dict = {
            "id": bill.id,
            "bill_number": bill.bill_number,
            "bill_date": bill.bill_date,
            "patient_email": current_user.email,
            "total_amount": bill.total_amount,
            "payment_status": bill.payment_status,
            "paid_amount": bill.paid_amount,
            "remaining_amount": bill.remaining_amount
        }
        results.append(BillSummaryResponse.model_validate(bill_dict).model_dump())
    
    return results


@router.get("/patient/bills/{bill_id}", dependencies=[Depends(require_role("patient"))])
def get_my_bill_by_id(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Patient: Get my bill by ID"""
    from app.models.patient_profile import PatientProfile
    result = (
        db.query(
            Bill, 
            User.email.label("patient_email"),
            PatientProfile.first_name,
            PatientProfile.middle_name,
            PatientProfile.last_name,
            PatientProfile.profile_photo_url
        )
        .join(User, Bill.patient_id == User.id)
        .outerjoin(PatientProfile, User.id == PatientProfile.user_id)
        .filter(
            Bill.id == bill_id,
            Bill.patient_id == current_user.id
        )
        .first()
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    bill, patient_email, first, middle, last, profile_photo_url = result
    
    bill_dict = BillResponse.model_validate(bill).model_dump()
    bill_dict["patient_email"] = patient_email
    bill_dict["patient_first_name"] = first
    bill_dict["patient_middle_name"] = middle
    bill_dict["patient_last_name"] = last
    bill_dict["patient_profile_photo_url"] = profile_photo_url
    
    # Add payment details
    payments = db.query(Payment).filter(Payment.bill_id == bill_id).all()
    bill_dict["payments"] = [PaymentResponse.model_validate(p).model_dump() for p in payments]
    
    return bill_dict


@router.get("/patient/bills/{bill_id}/download", dependencies=[Depends(require_role("patient"))])
def download_my_bill_pdf(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Patient: Download my bill as PDF"""
    bill = db.query(Bill).filter(
        Bill.id == bill_id,
        Bill.patient_id == current_user.id
    ).first()
    
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    from app.models.patient_profile import PatientProfile
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    
    first_name = profile.first_name if profile else None
    last_name = profile.last_name if profile else None
    profile_photo = profile.profile_photo_url if profile else None
    
    pdf_buffer = generate_invoice_pdf(
        bill=bill, 
        patient_email=current_user.email,
        first_name=first_name,
        last_name=last_name,
        profile_photo=profile_photo
    )
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=bill_{bill.bill_number}.pdf"
        }
    )


# =====================================================
# AUTO-BILL GENERATION ENDPOINTS
# =====================================================

@router.post("/auto/appointment", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("receptionist"))])
def auto_generate_appointment_bill(
    data: AutoBillAppointment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-generate bill after appointment completion"""
    appointment = db.query(Appointment).filter(Appointment.id == data.appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if bill already exists for this appointment
    existing_bill = db.query(Bill).filter(Bill.appointment_id == data.appointment_id).first()
    if existing_bill:
        raise HTTPException(status_code=400, detail="Bill already exists for this appointment")
    
    # Get consultation fee from pricing or use provided
    consultation_fee = data.consultation_fee
    if consultation_fee is None:
        pricing = get_pricing(db, "consultation_fee")
        if pricing:
            consultation_fee = pricing.base_price
        else:
            # Default consultation fee
            consultation_fee = 500.0
    
    # Create bill item for consultation
    item_totals = calculate_item_totals(
        quantity=1,
        unit_price=consultation_fee,
        discount_percent=0.0,
        tax_percent=18.0
    )
    
    bill_number = generate_bill_number()
    
    # Create bill
    bill = Bill(
        patient_id=appointment.patient_id,
        appointment_id=appointment.id,
        bill_number=bill_number,
        subtotal=item_totals["item_subtotal"],
        discount_amount=0.0,
        tax_amount=item_totals["item_tax"],
        total_amount=item_totals["item_total"],
        payment_status=PaymentStatus.PENDING,
        paid_amount=0.0,
        remaining_amount=item_totals["item_total"],
        created_by_id=current_user.id
    )
    
    db.add(bill)
    db.flush()
    
    # Create bill item
    bill_item = BillItem(
        bill_id=bill.id,
        item_type="consultation",
        description=f"Consultation Fee - Appointment #{appointment.id}",
        quantity=1,
        unit_price=consultation_fee,
        discount_percent=0.0,
        tax_percent=18.0,
        item_subtotal=item_totals["item_subtotal"],
        item_discount=0.0,
        item_tax=item_totals["item_tax"],
        item_total=item_totals["item_total"],
        reference_id=appointment.id
    )
    
    db.add(bill_item)
    db.commit()
    db.refresh(bill)
    
    return {
        "message": "Bill auto-generated for appointment",
        "bill": BillResponse.model_validate(bill)
    }


@router.post("/auto/lab-test", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("receptionist"))])
def auto_generate_lab_test_bill(
    data: AutoBillLabTest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-generate bill after lab report upload"""
    lab_request = db.query(LabRequest).filter(LabRequest.id == data.lab_request_id).first()
    if not lab_request:
        raise HTTPException(status_code=404, detail="Lab request not found")
    
    # Check if bill already exists
    existing_bill = db.query(Bill).filter(Bill.lab_request_id == data.lab_request_id).first()
    if existing_bill:
        raise HTTPException(status_code=400, detail="Bill already exists for this lab request")
    
    # Get test price from pricing or use provided
    test_price = data.test_price
    if test_price is None:
        # Try to get pricing based on test name
        service_type = f"lab_test_{lab_request.test_name.lower().replace(' ', '_')}"
        pricing = get_pricing(db, service_type)
        if pricing:
            test_price = pricing.base_price
        else:
            # Default lab test price
            test_price = 1000.0
    
    # Create bill item
    item_totals = calculate_item_totals(
        quantity=1,
        unit_price=test_price,
        discount_percent=0.0,
        tax_percent=18.0
    )
    
    bill_number = generate_bill_number()
    
    # Create bill
    bill = Bill(
        patient_id=lab_request.patient_id,
        lab_request_id=lab_request.id,
        bill_number=bill_number,
        subtotal=item_totals["item_subtotal"],
        discount_amount=0.0,
        tax_amount=item_totals["item_tax"],
        total_amount=item_totals["item_total"],
        payment_status=PaymentStatus.PENDING,
        paid_amount=0.0,
        remaining_amount=item_totals["item_total"],
        created_by_id=current_user.id
    )
    
    db.add(bill)
    db.flush()
    
    # Create bill item
    bill_item = BillItem(
        bill_id=bill.id,
        item_type="lab_test",
        description=f"Lab Test: {lab_request.test_name}",
        quantity=1,
        unit_price=test_price,
        discount_percent=0.0,
        tax_percent=18.0,
        item_subtotal=item_totals["item_subtotal"],
        item_discount=0.0,
        item_tax=item_totals["item_tax"],
        item_total=item_totals["item_total"],
        reference_id=lab_request.id
    )
    
    db.add(bill_item)
    db.commit()
    db.refresh(bill)
    
    return {
        "message": "Bill auto-generated for lab test",
        "bill": BillResponse.model_validate(bill)
    }


@router.post("/auto/medicine", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("receptionist"))])
def auto_generate_medicine_bill(
    data: AutoBillMedicine,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-generate bill after medicine dispensing"""
    dispense = db.query(Dispense).filter(Dispense.id == data.dispense_id).first()
    if not dispense:
        raise HTTPException(status_code=404, detail="Dispense not found")
    
    # Check if bill already exists
    existing_bill = db.query(Bill).filter(Bill.dispense_id == data.dispense_id).first()
    if existing_bill:
        raise HTTPException(status_code=400, detail="Bill already exists for this dispense")
    
    # Get prescription to get medicines
    prescription = db.query(Prescription).filter(Prescription.id == dispense.prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Parse medicines from prescription (assuming format: "Medicine1: qty, Medicine2: qty")
    # For now, we'll use provided medicine_costs or create a default item
    if data.medicine_costs:
        items_data = data.medicine_costs
    else:
        # Default: create a single item for all medicines
        items_data = [{
            "medicine_name": prescription.medicines,
            "quantity": 1,
            "unit_price": 200.0  # Default price
        }]
    
    bill_items = []
    for item_data in items_data:
        unit_price = item_data.get("unit_price", 200.0)
        quantity = item_data.get("quantity", 1)
        
        totals = calculate_item_totals(
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=0.0,
            tax_percent=18.0
        )
        
        bill_item = BillItem(
            item_type="medicine",
            description=item_data.get("medicine_name", "Medicines"),
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=0.0,
            tax_percent=18.0,
            item_subtotal=totals["item_subtotal"],
            item_discount=0.0,
            item_tax=totals["item_tax"],
            item_total=totals["item_total"],
            reference_id=prescription.id
        )
        bill_items.append(bill_item)
    
    # Calculate bill totals
    bill_totals = calculate_bill_totals(bill_items, 0.0)
    
    bill_number = generate_bill_number()
    
    # Create bill
    bill = Bill(
        patient_id=dispense.patient_id,
        dispense_id=dispense.id,
        bill_number=bill_number,
        subtotal=bill_totals["subtotal"],
        discount_amount=0.0,
        tax_amount=bill_totals["tax_amount"],
        total_amount=bill_totals["total_amount"],
        payment_status=PaymentStatus.PENDING,
        paid_amount=0.0,
        remaining_amount=bill_totals["total_amount"],
        created_by_id=current_user.id
    )
    
    db.add(bill)
    db.flush()
    
    # Add items
    for item in bill_items:
        item.bill_id = bill.id
        db.add(item)
    
    db.commit()
    db.refresh(bill)
    
    return {
        "message": "Bill auto-generated for medicine dispensing",
        "bill": BillResponse.model_validate(bill)
    }
