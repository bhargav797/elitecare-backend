from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class PharmacyProfile(Base):
    __tablename__ = "pharmacy_profiles"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    pharmacy_name = Column(String, nullable=False)
    profile_photo_url = Column(String, nullable=True)
    license_number = Column(String, nullable=False)
    license_type = Column(String, nullable=False)

    user = relationship("User", back_populates="pharmacy_profile")
