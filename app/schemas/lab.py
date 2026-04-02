from pydantic import BaseModel

# =====================================
# CREATE LAB RESULT (USED BY LAB ROUTER)
# =====================================
class LabResultCreate(BaseModel):
    lab_request_id: int
    result: str


# =====================================
# RESPONSE SCHEMA (OPTIONAL)
# =====================================
class LabResultResponse(BaseModel):
    id: int
    lab_request_id: int
    result: str

    class Config:
        from_attributes = True  # Pydantic v2

from typing import Optional


# =====================================
# LAB PRICING SCHEMAS
# =====================================

class LabPricingBase(BaseModel):
    service_name: str
    base_price: float
    default_tax_percent: Optional[float] = 18.0
    default_discount_percent: Optional[float] = 0.0
    description: Optional[str] = None

class LabPricingCreate(LabPricingBase):
    pass

class LabPricingUpdate(BaseModel):
    service_name: Optional[str] = None
    base_price: Optional[float] = None
    default_tax_percent: Optional[float] = None
    default_discount_percent: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[str] = None

class LabPricingOut(LabPricingBase):
    id: int
    service_type: str
    is_active: str

    class Config:
        from_attributes = True
