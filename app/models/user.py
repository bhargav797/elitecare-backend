from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy import Boolean


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # -------------------------
    # INTERNAL RELATIONSHIPS
    # -------------------------

    _appointments_as_patient = relationship(
        "Appointment",
        foreign_keys="Appointment.patient_id",
        cascade="all, delete",
        passive_deletes=True
    )

    _appointments_as_doctor = relationship(
        "Appointment",
        foreign_keys="Appointment.doctor_id",
        cascade="all, delete",
        passive_deletes=True
    )

    # -------------------------
    # BACKWARD-COMPAT PROPERTY
    # -------------------------

    @property
    def appointments(self):
        """
        Backward-compatible access:
        user.appointments
        """
        return (
            (self._appointments_as_patient or [])
            + (self._appointments_as_doctor or [])
        )

    # -------------------------
    # OTHER RELATIONSHIPS
    # -------------------------

    prescriptions_as_patient = relationship(
        "Prescription",
        foreign_keys="Prescription.patient_id",
        cascade="all, delete",
        passive_deletes=True
    )

    prescriptions_as_doctor = relationship(
        "Prescription",
        foreign_keys="Prescription.doctor_id",
        cascade="all, delete",
        passive_deletes=True
    )

    lab_requests = relationship(
        "LabRequest",
        foreign_keys="LabRequest.patient_id",
        cascade="all, delete",
        passive_deletes=True
    )

    dispenses_as_patient = relationship(
        "Dispense",
        foreign_keys="Dispense.patient_id",
        cascade="all, delete",
        passive_deletes=True
    )

    dispenses_as_pharmacist = relationship(
        "Dispense",
        foreign_keys="Dispense.pharmacist_id",
        cascade="all, delete",
        passive_deletes=True
    )

    patient_profile = relationship(
        "PatientProfile",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False
    )

    doctor_profile = relationship(
        "DoctorProfile",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False
    )

    pharmacy_profile = relationship(
        "PharmacyProfile",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False
    )

    receptionist_profile = relationship(
        "ReceptionistProfile",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False
    )

    lab_profile = relationship(
    "LabProfile",
    cascade="all, delete",
    passive_deletes=True,
    uselist=False
)

    bills_as_patient = relationship(
        "Bill",
        foreign_keys="Bill.patient_id",
        cascade="all, delete",
        passive_deletes=True
    )
