from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ReceptionistProfile(Base):
    __tablename__ = "receptionist_profiles"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # PERSONAL DETAILS
    first_name = Column(String, nullable=False)
    middle_name = Column(String)
    last_name = Column(String, nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(String, nullable=False)
    profile_photo_url = Column(String, nullable=True)

    # EXTRA DETAILS (THIS FIXES YOUR ERROR)
    languages_known = Column(String)

    # CONTACT & ADDRESS
    mobile = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    # RELATIONSHIP
    user = relationship("User", back_populates="receptionist_profile")
