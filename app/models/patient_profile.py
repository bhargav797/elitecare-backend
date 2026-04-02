from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    first_name = Column(String, nullable=False)
    middle_name = Column(String)
    last_name = Column(String, nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(String, nullable=False)
    profile_photo_url = Column(String, nullable=True)

    blood_group = Column(String, nullable=False)
    mobile = Column(String, nullable=False)

    address_line = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    emergency_contact = Column(String, nullable=False)
    emergency_relation = Column(String, nullable=False)

    existing_conditions = Column(String)
    known_allergies = Column(String)
    current_medication = Column(String)

    insurance_provider = Column(String)
    policy_number = Column(String)
    govt_scheme = Column(String)
    scheme_id = Column(String)

    user = relationship("User", back_populates="patient_profile")
