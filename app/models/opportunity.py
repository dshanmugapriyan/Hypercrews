import uuid
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

class Opportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"
    
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'email', 'screenshot', 'linkedin'
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    
    company: Mapped["Company | None"] = relationship("Company", back_populates="opportunities")
    scans: Mapped[list["Scan"]] = relationship("Scan", back_populates="opportunity", cascade="all, delete-orphan")
    entities: Mapped[list["Entity"]] = relationship("Entity", back_populates="opportunity", cascade="all, delete-orphan")
