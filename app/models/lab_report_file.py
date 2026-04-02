from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base
from app.utils.date_utils import get_ist_now

class LabReportFile(Base):
    __tablename__ = "lab_report_files"

    id = Column(Integer, primary_key=True, index=True)

    lab_request_id = Column(
    Integer,
    ForeignKey("lab_requests.id", ondelete="CASCADE")
)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lab_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    
    is_reviewed = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=get_ist_now)
