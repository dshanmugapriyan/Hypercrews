"""Report (Trust Report / Opportunity Passport) and CommunityReport models."""
from __future__ import annotations
import uuid
from sqlalchemy import Boolean, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), unique=True, nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False, default="TRUST_REPORT")
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_slug: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    scan: Mapped["Scan"] = relationship(back_populates="report")

class CommunityReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "community_reports"
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    scan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user: Mapped["User | None"] = relationship(back_populates="community_reports")
