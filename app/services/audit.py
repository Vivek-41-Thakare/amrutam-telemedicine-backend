from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(db: Session, actor: User | None, action: str, resource_type: str, resource_id: str | None = None, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    ))
