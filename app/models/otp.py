from sqlalchemy import Column, String, DateTime
from app.database import Base

class EmailOTP(Base):
    __tablename__ = "email_otps"

    email = Column(String, primary_key=True, index=True)
    otp = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
