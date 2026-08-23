import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# Re-export schemas enums or map them for SQLAlchemy
from app.schemas.common import InputType, RiskLevel, ScanStatus

class ScamFingerprintType(str, PyEnum):
    PAYMENT_SCAM = "payment_scam"
    URGENCY = "urgency"
    CREDENTIAL_HARVESTING = "credential_harvesting"
    IDENTITY_IMPERSONATION = "identity_impersonation"

class VerificationCheckStatus(str, PyEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    PENDING = "PENDING"

class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
