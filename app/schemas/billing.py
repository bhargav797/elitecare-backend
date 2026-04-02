from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"


class PaymentMode(str, Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    INSURANCE = "insurance"


class BillItemType(str, Enum):
    CONSULTATION = "consultation"
    LAB_TEST = "lab_test"
    MEDICINE = "medicine"
    PROCEDURE = "procedure"
    OTHER = "other"


# =====================================================
# PRICING SCHEMAS
# =====================================================

class PricingCreate(BaseModel):
    service_type: str = Field(..., description="Unique service identifier (e.g., 'consultation_fee', 'lab_test_blood')")
    service_name: str
    base_price: float = Field(..., gt=0)
    default_tax_percent: float = Field(default=18.0, ge=0, le=100)
    default_discount_percent: float = Field(default=0.0, ge=0, le=100)
    description: Optional[str] = None


class PricingUpdate(BaseModel):
    service_name: Optional[str] = None
    base_price: Optional[float] = Field(None, gt=0)
    default_tax_percent: Optional[float] = Field(None, ge=0, le=100)
    default_discount_percent: Optional[float] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    is_active: Optional[str] = None


class PricingResponse(BaseModel):
    id: int
    service_type: str
    service_name: str
    base_price: float
    default_tax_percent: float
    default_discount_percent: float
    description: Optional[str]
    is_active: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# BILL ITEM SCHEMAS
# =====================================================

class BillItemCreate(BaseModel):
    item_type: BillItemType
    description: str
    quantity: int = Field(default=1, gt=0)
    unit_price: float = Field(..., gt=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    tax_percent: float = Field(default=18.0, ge=0, le=100)
    reference_id: Optional[int] = None


class BillItemResponse(BaseModel):
    id: int
    item_type: str
    description: str
    quantity: int
    unit_price: float
    discount_percent: float
    tax_percent: float
    item_subtotal: float
    item_discount: float
    item_tax: float
    item_total: float
    reference_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# PAYMENT SCHEMAS
# =====================================================

class PaymentCreate(BaseModel):
    bill_id: int
    amount: float = Field(..., gt=0)
    payment_mode: PaymentMode
    transaction_id: Optional[str] = None
    insurance_provider: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    bill_id: int
    amount: float
    payment_mode: str
    payment_date: datetime
    transaction_id: Optional[str]
    insurance_provider: Optional[str]
    notes: Optional[str]
    collected_by_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# BILL SCHEMAS
# =====================================================

class BillCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    lab_request_id: Optional[int] = None
    dispense_id: Optional[int] = None
    items: List[BillItemCreate]
    discount_amount: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None


class BillUpdate(BaseModel):
    discount_amount: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class BillResponse(BaseModel):
    id: int
    patient_id: int
    appointment_id: Optional[int]
    lab_request_id: Optional[int]
    dispense_id: Optional[int]
    bill_number: str
    bill_date: datetime
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    payment_status: str
    paid_amount: float
    remaining_amount: float
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    items: List[BillItemResponse]
    payments: List[PaymentResponse] = []

    class Config:
        from_attributes = True


class BillSummaryResponse(BaseModel):
    id: int
    bill_number: str
    bill_date: datetime
    patient_email: str
    total_amount: float
    payment_status: str
    paid_amount: float
    remaining_amount: float

    class Config:
        from_attributes = True


# =====================================================
# AUTO-BILL GENERATION SCHEMAS
# =====================================================

class AutoBillAppointment(BaseModel):
    appointment_id: int
    consultation_fee: Optional[float] = None  # If not provided, uses pricing table


class AutoBillLabTest(BaseModel):
    lab_request_id: int
    test_price: Optional[float] = None  # If not provided, uses pricing table


class AutoBillMedicine(BaseModel):
    dispense_id: int
    medicine_costs: Optional[List[dict]] = None  # [{"medicine_name": "Paracetamol", "quantity": 2, "unit_price": 50}]
