from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class LabProfile(Base):
    __tablename__ = "lab_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    lab_name = Column(String, nullable=False)
    profile_photo_url = Column(String, nullable=True)
    registration_number = Column(String, nullable=False)
    lab_type = Column(String, nullable=False)

    contact_person = Column(String, nullable=False)
    contact_number = Column(String, nullable=False)

    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    nabl_accredited = Column(String, nullable=True)
    accreditation_number = Column(String, nullable=True)

    user = relationship("User", back_populates="lab_profile")
