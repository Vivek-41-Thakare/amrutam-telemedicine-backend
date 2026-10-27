from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import ConsultationStatus, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)

    @field_validator("password")
    @classmethod
    def password_has_complexity(cls, value: str) -> str:
        if not any(c.islower() for c in value) or not any(c.isupper() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must include lowercase, uppercase, and a digit")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: Role
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class DoctorCreate(BaseModel):
    specialization: str = Field(min_length=2, max_length=120)
    license_number: str = Field(min_length=3, max_length=120)


class DoctorResponse(BaseModel):
    id: UUID
    user_id: UUID
    specialization: str
    license_number: str
    verified: bool
    model_config = ConfigDict(from_attributes=True)


class SlotCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime


class SlotResponse(BaseModel):
    id: UUID
    doctor_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    slot_id: UUID
    reason: str = Field(min_length=3, max_length=1000)


class ConsultationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    slot_id: UUID
    status: ConsultationStatus
    reason: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PrescriptionCreate(BaseModel):
    content: str = Field(min_length=3, max_length=10000)


class PrescriptionResponse(BaseModel):
    id: UUID
    consultation_id: UUID
    doctor_id: UUID
    patient_id: UUID
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
