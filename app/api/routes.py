import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import current_user, require_roles
from app.models import (
    AuditLog,
    AvailabilitySlot,
    Consultation,
    ConsultationStatus,
    Doctor,
    IdempotencyRecord,
    Payment,
    Prescription,
    Role,
    SlotStatus,
    User,
)
from app.schemas import (
    BookingCreate,
    ConsultationResponse,
    DoctorCreate,
    DoctorResponse,
    LoginRequest,
    PrescriptionCreate,
    PrescriptionResponse,
    RegisterRequest,
    SlotCreate,
    SlotResponse,
    TokenResponse,
    UserResponse,
)
from app.services.audit import record_audit

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, password_hash=hash_password(payload.password), full_name=payload.full_name, role=Role.PATIENT)
    db.add(user)
    record_audit(db, None, "user.registered", "user", details={"role": "patient"})
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return user


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    record_audit(db, user, "auth.login_succeeded", "user", str(user.id))
    db.commit()
    token = create_access_token(str(user.id), user.role.value)
    return TokenResponse(access_token=token, expires_in=settings.access_token_minutes * 60)


@router.get("/users/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user


@router.post("/doctors", response_model=DoctorResponse, status_code=201)
def create_doctor_profile(payload: DoctorCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.DOCTOR))):
    if db.scalar(select(Doctor).where(Doctor.user_id == user.id)):
        raise HTTPException(status_code=409, detail="Doctor profile already exists")
    doctor = Doctor(user_id=user.id, specialization=payload.specialization, license_number=payload.license_number, verified=False)
    db.add(doctor)
    record_audit(db, user, "doctor.profile_created", "doctor")
    try:
        db.commit()
        db.refresh(doctor)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="License number already registered")
    return doctor


@router.get("/doctors", response_model=list[DoctorResponse])
def search_doctors(
    specialization: str | None = Query(default=None, max_length=120),
    verified_only: bool = True,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(Doctor)
    if verified_only:
        query = query.where(Doctor.verified.is_(True))
    if specialization:
        query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))
    return list(db.scalars(query.order_by(Doctor.specialization).limit(limit).offset(offset)))


@router.post("/admin/doctors/{doctor_id}/verify", response_model=DoctorResponse)
def verify_doctor(doctor_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor.verified = True
    record_audit(db, admin, "doctor.verified", "doctor", str(doctor.id))
    db.commit()
    db.refresh(doctor)
    return doctor


@router.post("/doctors/me/availability", response_model=SlotResponse, status_code=201)
def create_slot(payload: SlotCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.DOCTOR))):
    if payload.starts_at.tzinfo is None or payload.ends_at.tzinfo is None or payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Provide timezone-aware timestamps and end after start")
    doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    if not doctor.verified:
        raise HTTPException(status_code=403, detail="Doctor must be verified before publishing availability")
    slot = AvailabilitySlot(doctor_id=doctor.id, starts_at=payload.starts_at, ends_at=payload.ends_at)
    db.add(slot)
    record_audit(db, user, "availability.created", "availability_slot")
    db.commit()
    db.refresh(slot)
    return slot


@router.get("/doctors/{doctor_id}/availability", response_model=list[SlotResponse])
def list_slots(doctor_id: uuid.UUID, db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=100)):
    return list(db.scalars(select(AvailabilitySlot).where(
        AvailabilitySlot.doctor_id == doctor_id,
        AvailabilitySlot.status == SlotStatus.AVAILABLE,
        AvailabilitySlot.starts_at >= datetime.now(timezone.utc),
    ).order_by(AvailabilitySlot.starts_at).limit(limit)))


@router.post("/consultations", response_model=ConsultationResponse, status_code=201)
def book_consultation(
    payload: BookingCreate,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=255),
    db: Session = Depends(get_db),
    patient: User = Depends(require_roles(Role.PATIENT)),
):
    request_hash = hashlib.sha256(json.dumps({"slot_id": str(payload.slot_id), "reason": payload.reason}, sort_keys=True).encode()).hexdigest()
    existing = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.actor_id == patient.id, IdempotencyRecord.key == idempotency_key))
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency key reused with a different request")
        response.status_code = existing.response_status
        return existing.response_body

    try:
        # Serialize idempotency handling for this actor/key using a PostgreSQL advisory transaction lock.
        lock_key = int.from_bytes(hashlib.sha256(f"{patient.id}:{idempotency_key}".encode()).digest()[:8], "big", signed=True)
        db.execute(select(func.pg_advisory_xact_lock(lock_key)))
        existing = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.actor_id == patient.id, IdempotencyRecord.key == idempotency_key))
        if existing:
            if existing.request_hash != request_hash:
                raise HTTPException(status_code=409, detail="Idempotency key reused with a different request")
            response.status_code = existing.response_status
            return existing.response_body

        slot = db.scalar(select(AvailabilitySlot).where(AvailabilitySlot.id == payload.slot_id).with_for_update())
        if not slot or slot.status != SlotStatus.AVAILABLE or slot.starts_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=409, detail="Availability slot is unavailable")
        doctor = db.get(Doctor, slot.doctor_id)
        if not doctor or not doctor.verified:
            raise HTTPException(status_code=409, detail="Doctor is not available for booking")
        consultation = Consultation(patient_id=patient.id, doctor_id=doctor.id, slot_id=slot.id, status=ConsultationStatus.BOOKED, reason=payload.reason)
        slot.status = SlotStatus.BOOKED
        db.add(consultation)
        db.flush()
        result = {
            "id": str(consultation.id), "patient_id": str(consultation.patient_id),
            "doctor_id": str(consultation.doctor_id), "slot_id": str(consultation.slot_id),
            "status": consultation.status.value, "reason": consultation.reason,
            "created_at": consultation.created_at.isoformat(),
        }
        db.add(IdempotencyRecord(actor_id=patient.id, key=idempotency_key, request_hash=request_hash, response_status=201, response_body=result))
        record_audit(db, patient, "consultation.booked", "consultation", str(consultation.id))
        db.commit()
        response.status_code = 201
        return result
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slot has already been booked")


@router.get("/consultations", response_model=list[ConsultationResponse])
def list_consultations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role == Role.PATIENT:
        query = select(Consultation).where(Consultation.patient_id == user.id)
    elif user.role == Role.DOCTOR:
        doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
        if not doctor:
            return []
        query = select(Consultation).where(Consultation.doctor_id == doctor.id)
    else:
        query = select(Consultation)
    return list(db.scalars(query.order_by(Consultation.created_at.desc()).limit(100)))


@router.post("/consultations/{consultation_id}/start", response_model=ConsultationResponse)
def start_consultation(consultation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.DOCTOR))):
    doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
    consultation = db.get(Consultation, consultation_id)
    if not doctor or not consultation or consultation.doctor_id != doctor.id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if consultation.status not in (ConsultationStatus.BOOKED, ConsultationStatus.CONFIRMED):
        raise HTTPException(status_code=409, detail="Invalid consultation state transition")
    consultation.status = ConsultationStatus.IN_PROGRESS
    record_audit(db, user, "consultation.started", "consultation", str(consultation.id))
    db.commit()
    db.refresh(consultation)
    return consultation


@router.post("/consultations/{consultation_id}/complete", response_model=ConsultationResponse)
def complete_consultation(consultation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.DOCTOR))):
    doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
    consultation = db.get(Consultation, consultation_id)
    if not doctor or not consultation or consultation.doctor_id != doctor.id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if consultation.status != ConsultationStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Only in-progress consultations can be completed")
    consultation.status = ConsultationStatus.COMPLETED
    record_audit(db, user, "consultation.completed", "consultation", str(consultation.id))
    db.commit()
    db.refresh(consultation)
    return consultation


@router.post("/consultations/{consultation_id}/cancel", response_model=ConsultationResponse)
def cancel_consultation(consultation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    consultation = db.get(Consultation, consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    doctor = db.get(Doctor, consultation.doctor_id)
    allowed = (user.role == Role.PATIENT and consultation.patient_id == user.id) or (user.role == Role.DOCTOR and doctor and doctor.user_id == user.id) or user.role == Role.ADMIN
    if not allowed:
        raise HTTPException(status_code=403, detail="Not permitted to cancel this consultation")
    if consultation.status not in (ConsultationStatus.BOOKED, ConsultationStatus.CONFIRMED):
        raise HTTPException(status_code=409, detail="Consultation can no longer be cancelled")
    consultation.status = ConsultationStatus.CANCELLED
    slot = db.get(AvailabilitySlot, consultation.slot_id)
    if slot:
        slot.status = SlotStatus.AVAILABLE
    record_audit(db, user, "consultation.cancelled", "consultation", str(consultation.id))
    db.commit()
    db.refresh(consultation)
    return consultation


@router.post("/consultations/{consultation_id}/prescriptions", response_model=PrescriptionResponse, status_code=201)
def create_prescription(consultation_id: uuid.UUID, payload: PrescriptionCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.DOCTOR))):
    doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
    consultation = db.get(Consultation, consultation_id)
    if not doctor or not consultation or consultation.doctor_id != doctor.id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if consultation.status not in (ConsultationStatus.IN_PROGRESS, ConsultationStatus.COMPLETED):
        raise HTTPException(status_code=409, detail="Prescription requires an active or completed consultation")
    prescription = Prescription(consultation_id=consultation.id, doctor_id=doctor.id, patient_id=consultation.patient_id, content=payload.content)
    db.add(prescription)
    record_audit(db, user, "prescription.created", "prescription")
    db.commit()
    db.refresh(prescription)
    return prescription


@router.get("/consultations/{consultation_id}/prescriptions", response_model=list[PrescriptionResponse])
def list_prescriptions(consultation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    consultation = db.get(Consultation, consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    doctor = db.get(Doctor, consultation.doctor_id)
    allowed = (user.role == Role.PATIENT and consultation.patient_id == user.id) or (user.role == Role.DOCTOR and doctor and doctor.user_id == user.id) or user.role == Role.ADMIN
    if not allowed:
        raise HTTPException(status_code=403, detail="Not permitted")
    return list(db.scalars(select(Prescription).where(Prescription.consultation_id == consultation_id).order_by(Prescription.created_at.desc())))


@router.get("/admin/analytics/consultations")
def consultation_analytics(db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    total = db.scalar(select(func.count()).select_from(Consultation)) or 0
    by_status = db.execute(select(Consultation.status, func.count()).group_by(Consultation.status)).all()
    return {"total_consultations": total, "by_status": {status.value: count for status, count in by_status}}


@router.get("/admin/audit-logs")
def audit_logs(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return [{"id": str(r.id), "actor_id": str(r.actor_id) if r.actor_id else None, "action": r.action, "resource_type": r.resource_type, "resource_id": r.resource_id, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/admin/payments")
def list_payments(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    rows = db.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(limit))
    return [{"id": str(r.id), "consultation_id": str(r.consultation_id), "amount_minor": r.amount_minor, "currency": r.currency, "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]
