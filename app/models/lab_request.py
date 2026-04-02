from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.utils.date_utils import get_ist_now

class LabRequest(Base):
    __tablename__ = "lab_requests"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(
    Integer,
    ForeignKey("users.id", ondelete="CASCADE")
)

    test_name = Column(String, nullable=False)
    reason = Column(String, nullable=False)

    status = Column(String, default="pending")  # pending | completed
    created_at = Column(DateTime(timezone=True), default=get_ist_now)

    appointment = relationship("Appointment")
    doctor = relationship("User", foreign_keys=[doctor_id])
    patient = relationship("User", overlaps="lab_requests", foreign_keys=[patient_id])
