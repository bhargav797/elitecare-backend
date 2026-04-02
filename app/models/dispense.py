from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base
from app.utils.date_utils import get_ist_now


class Dispense(Base):
    __tablename__ = "dispenses"

    id = Column(Integer, primary_key=True, index=True)

    # Which prescription was dispensed
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Who is the patient (easy history lookup)
    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Who dispensed (pharmacist)
    pharmacist_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )

    dispensed_at = Column(DateTime(timezone=True), default=get_ist_now)

    # Optional relationships (safe to keep)
    prescription = relationship("Prescription", backref="dispenses")
    patient = relationship("User",overlaps="dispenses_as_patient", foreign_keys=[patient_id])
    pharmacist = relationship("User",overlaps="dispenses_as_pharmacist", foreign_keys=[pharmacist_id])
