from enum import Enum

class Role(str, Enum):
    admin = "admin"
    doctor = "doctor"
    receptionist = "receptionist"
    lab = "lab"
    pharmacist = "pharmacist"
    patient = "patient"
