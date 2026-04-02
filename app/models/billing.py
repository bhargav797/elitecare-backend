from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.date_utils import get_ist_now
import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"


class PaymentMode(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    INSURANCE = "insurance"


class BillItemType(str, enum.Enum):
    CONSULTATION = "consultation"
    LAB_TEST = "lab_test"
    MEDICINE = "medicine"
    PROCEDURE = "procedure"
    OTHER = "other"


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    
    # Patient information
    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Related entities (can be null if bill is standalone)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    lab_request_id = Column(Integer, ForeignKey("lab_requests.id"), nullable=True)
    dispense_id = Column(Integer, ForeignKey("dispenses.id"), nullable=True)
    
    # Bill details
    bill_number = Column(String, unique=True, nullable=False, index=True)
    bill_date = Column(DateTime(timezone=True), default=get_ist_now, nullable=False)
    
    # Financial breakdown
    subtotal = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    tax_amount = Column(Float, default=0.0, nullable=False)  # GST
    total_amount = Column(Float, nullable=False)
    
    # Payment information
    payment_status = Column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False
    )
    paid_amount = Column(Float, default=0.0, nullable=False)
    remaining_amount = Column(Float, nullable=False)
    
    # Created by
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=get_ist_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_ist_now, onupdate=get_ist_now, nullable=False)
    
    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], overlaps="bills_as_patient")
    created_by = relationship("User", foreign_keys=[collected_by_id] if 'collected_by_id' in locals() else [created_by_id])
    appointment = relationship("Appointment", backref="bills")
    lab_request = relationship("LabRequest", backref="bills")
    dispense = relationship("Dispense", backref="bills")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan")


class BillItem(Base):
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(
        Integer,
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Item details
    item_type = Column(Enum(BillItemType), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_percent = Column(Float, default=0.0, nullable=False)
    tax_percent = Column(Float, default=0.0, nullable=False)  # GST percentage
    
    # Calculated amounts
    item_subtotal = Column(Float, nullable=False)  # quantity * unit_price
    item_discount = Column(Float, default=0.0, nullable=False)
    item_tax = Column(Float, default=0.0, nullable=False)
    item_total = Column(Float, nullable=False)  # subtotal - discount + tax
    
    # Reference to source (optional)
    reference_id = Column(Integer, nullable=True)  # Can reference prescription_id, lab_request_id, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=get_ist_now, nullable=False)
    
    # Relationships
    bill = relationship("Bill", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(
        Integer,
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Payment details
    amount = Column(Float, nullable=False)
    payment_mode = Column(Enum(PaymentMode), nullable=False)
    payment_date = Column(DateTime(timezone=True), default=get_ist_now, nullable=False)
    
    # Additional information
    transaction_id = Column(String, nullable=True)  # For card/UPI transactions
    insurance_provider = Column(String, nullable=True)  # If payment_mode is insurance
    notes = Column(Text, nullable=True)
    
    # Collected by
    collected_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=get_ist_now, nullable=False)
    
    # Relationships
    bill = relationship("Bill", back_populates="payments")
    collected_by = relationship("User", foreign_keys=[collected_by_id])


class Pricing(Base):
    __tablename__ = "pricing"

    id = Column(Integer, primary_key=True, index=True)
    
    # Service details
    service_type = Column(String, nullable=False, unique=True, index=True)
    # Examples: "consultation_fee", "lab_test_blood", "lab_test_xray", "medicine_markup_percent"
    
    service_name = Column(String, nullable=False)
    base_price = Column(Float, nullable=False)
    
    # Tax and discount defaults
    default_tax_percent = Column(Float, default=18.0, nullable=False)  # Default GST 18%
    default_discount_percent = Column(Float, default=0.0, nullable=False)
    
    # Additional info
    description = Column(Text, nullable=True)
    is_active = Column(String, default="true", nullable=False)  # Using String for simplicity
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=get_ist_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_ist_now, onupdate=get_ist_now, nullable=False)
