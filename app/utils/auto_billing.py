from sqlalchemy.orm import Session
from app.models.billing import Bill, BillItem, PaymentStatus, Pricing
from app.models.user import User
from app.utils.billing_utils import (
    generate_bill_number,
    calculate_item_totals,
    calculate_bill_totals,
    get_pricing
)


def auto_generate_appointment_bill(
    db: Session,
    appointment_id: int,
    created_by_user_id: int,
    consultation_fee: float = None
) -> Bill:
    """Auto-generate bill for appointment completion"""
    from app.models.appointment import Appointment
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        return None
    
    # Check if bill already exists
    existing_bill = db.query(Bill).filter(Bill.appointment_id == appointment_id).first()
    if existing_bill:
        return existing_bill
    
    # Get consultation fee
    if consultation_fee is None:
        pricing = get_pricing(db, "consultation_fee")
        consultation_fee = pricing.base_price if pricing else 500.0
    
    # Calculate item totals
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
        created_by_id=created_by_user_id
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
    
    return bill


def auto_generate_lab_test_bill(
    db: Session,
    lab_request_id: int,
    created_by_user_id: int,
    test_price: float = None
) -> Bill:
    """Auto-generate bill for lab test completion"""
    from app.models.lab_request import LabRequest
    
    lab_request = db.query(LabRequest).filter(LabRequest.id == lab_request_id).first()
    if not lab_request:
        return None
    
    # Check if bill already exists
    existing_bill = db.query(Bill).filter(Bill.lab_request_id == lab_request_id).first()
    if existing_bill:
        return existing_bill
    
    # Get test price
    if test_price is None:
        # 1. Try exact match using same slug logic as Lab service creation
        # e.g., "Full Body Checkup" -> "lab_test_full_body_checkup"
        slug = lab_request.test_name.lower().replace(" ", "_")
        service_type = f"lab_test_{slug}"
        
        pricing = get_pricing(db, service_type)
        
        if not pricing:
            # 2. Try simple search by name just in case of mismatch
            # This handles cases where maybe the slug logic changed or name has special chars
            pricing = db.query(Pricing).filter(
                Pricing.service_name.ilike(lab_request.test_name),
                Pricing.service_type.like("lab_test_%")
            ).first()

        test_price = pricing.base_price if pricing else 1000.0  # Default fallback
    
    # Calculate item totals
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
        created_by_id=created_by_user_id
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
    
    return bill


def auto_generate_medicine_bill(
    db: Session,
    dispense_id: int,
    created_by_user_id: int,
    medicine_costs: list = None
) -> Bill:
    """Auto-generate bill for medicine dispensing"""
    from app.models.dispense import Dispense
    from app.models.prescription import Prescription
    
    dispense = db.query(Dispense).filter(Dispense.id == dispense_id).first()
    if not dispense:
        return None
    
    # Check if bill already exists
    existing_bill = db.query(Bill).filter(Bill.dispense_id == dispense_id).first()
    if existing_bill:
        return existing_bill
    
    # Get prescription
    prescription = db.query(Prescription).filter(Prescription.id == dispense.prescription_id).first()
    if not prescription:
        return None
    
    # Create bill items
    if medicine_costs:
        items_data = medicine_costs
    else:
        # Default: create a single item
        items_data = [{
            "medicine_name": prescription.medicines,
            "quantity": 1,
            "unit_price": 200.0
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
        created_by_id=created_by_user_id
    )
    
    db.add(bill)
    db.flush()
    
    # Add items
    for item in bill_items:
        item.bill_id = bill.id
        db.add(item)
    
    db.commit()
    db.refresh(bill)
    
    return bill
