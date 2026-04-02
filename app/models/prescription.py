from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base
from app.utils.date_utils import get_ist_now

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False
    )

    patient_id = Column(
    Integer,
    ForeignKey("users.id", ondelete="CASCADE")
)

    doctor_id = Column(
    Integer,
    ForeignKey("users.id", ondelete="CASCADE")
)

    diagnosis = Column(String, nullable=False)
    medicines = Column(String, nullable=False)
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=get_ist_now)
