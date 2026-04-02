from typing import Optional
from pydantic import BaseModel

class MedicineCreate(BaseModel):
    name: str
    stock: int
    price: float = 0.0


class UpdateMedicine(BaseModel):
    name: Optional[str] = None
    stock: Optional[int] = None
    price: Optional[float] = None


class DispensePrescription(BaseModel):
    prescription_id: int


class MedicineResponse(BaseModel):
    id: int
    name: str
    stock: int
    price: float

    class Config:
        from_attributes = True
