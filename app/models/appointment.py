from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.date_utils import get_ist_now


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    # who booked
    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # stored for easy display (as your code already uses it)
    patient_email = Column(String, nullable=False)

    # doctor (can be null initially)
    doctor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )

    # appointment details
    reason = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    is_lab_required = Column(Boolean, default=True)
    scheduled_date = Column(DateTime, nullable=True)  # For future/follow-up appointments
    created_at = Column(DateTime(timezone=True), default=get_ist_now, nullable=False)

    # relationships
    patient = relationship(
        "User",
        foreign_keys=[patient_id],
        overlaps="_appointments_as_patient"
    )

    doctor = relationship(
        "User",
        foreign_keys=[doctor_id],
        overlaps="_appointments_as_doctor"
    )
