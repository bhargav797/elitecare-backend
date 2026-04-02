from sqlalchemy.orm import Session
from datetime import datetime
from app.models.billing import Bill, BillItem, Payment, Pricing, PaymentStatus
from app.models.user import User
import random
import string


def generate_bill_number() -> str:
    """Generate a unique bill number: BILL-YYYYMMDD-XXXXXX"""
    date_str = datetime.now().strftime("%Y%m%d")
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BILL-{date_str}-{random_suffix}"


def calculate_item_totals(
    quantity: int,
    unit_price: float,
    discount_percent: float = 0.0,
    tax_percent: float = 18.0
) -> dict:
    """Calculate item subtotal, discount, tax, and total"""
    item_subtotal = quantity * unit_price
    item_discount = item_subtotal * (discount_percent / 100)
    item_subtotal_after_discount = item_subtotal - item_discount
    item_tax = item_subtotal_after_discount * (tax_percent / 100)
    item_total = item_subtotal_after_discount + item_tax
    
    return {
        "item_subtotal": round(item_subtotal, 2),
        "item_discount": round(item_discount, 2),
        "item_tax": round(item_tax, 2),
        "item_total": round(item_total, 2)
    }


def calculate_bill_totals(items: list, discount_amount: float = 0.0) -> dict:
    """Calculate bill subtotal, tax, and total from items"""
    subtotal = sum(item.item_subtotal for item in items)
    total_discount = discount_amount + sum(item.item_discount for item in items)
    total_tax = sum(item.item_tax for item in items)
    total_amount = subtotal - total_discount + total_tax
    
    return {
        "subtotal": round(subtotal, 2),
        "discount_amount": round(total_discount, 2),
        "tax_amount": round(total_tax, 2),
        "total_amount": round(total_amount, 2)
    }


def get_pricing(db: Session, service_type: str) -> Pricing:
    """Get pricing for a service type"""
    pricing = db.query(Pricing).filter(
        Pricing.service_type == service_type,
        Pricing.is_active == "true"
    ).first()
    return pricing


def get_or_create_pricing(
    db: Session,
    service_type: str,
    service_name: str,
    base_price: float,
    default_tax_percent: float = 18.0
) -> Pricing:
    """Get existing pricing or create default if not found"""
    pricing = get_pricing(db, service_type)
    
    if not pricing:
        # Create default pricing
        pricing = Pricing(
            service_type=service_type,
            service_name=service_name,
            base_price=base_price,
            default_tax_percent=default_tax_percent,
            default_discount_percent=0.0,
            is_active="true"
        )
        db.add(pricing)
        db.commit()
        db.refresh(pricing)
    
    return pricing


def update_bill_payment_status(bill: Bill, db: Session):
    """Update bill payment status based on payments"""
    total_paid = sum(payment.amount for payment in bill.payments)
    bill.paid_amount = round(total_paid, 2)
    bill.remaining_amount = round(bill.total_amount - total_paid, 2)
    
    if total_paid >= bill.total_amount:
        bill.payment_status = PaymentStatus.PAID
    elif total_paid > 0:
        bill.payment_status = PaymentStatus.PARTIAL
    else:
        bill.payment_status = PaymentStatus.PENDING
    
    db.commit()
