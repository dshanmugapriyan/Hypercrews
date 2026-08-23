"""Scan model — verification run and intelligence artifacts."""
from __future__ import annotations
import uuid
from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import RiskLevel, ScanStatus, TimestampMixin, UUIDPrimaryKeyMixin

class Scan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scans"
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel), nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
    identity_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    payment_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    communication_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    opportunity_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    company_trust: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    opportunity: Mapped["Opportunity"] = relationship(back_populates="scans")
    user: Mapped["User | None"] = relationship(back_populates="scans")
    risk_signals: Mapped[list["RiskSignal"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    model_predictions: Mapped[list["ModelPrediction"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    verification_checks: Mapped[list["VerificationCheck"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    scam_fingerprints: Mapped[list["ScamFingerprint"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    report: Mapped["Report | None"] = relationship(back_populates="scan", uselist=False)

class Entity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "entities"
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(1000), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opportunity: Mapped["Opportunity"] = relationship(back_populates="entities")

class RiskSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_signals"
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scan: Mapped["Scan"] = relationship(back_populates="risk_signals")

class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence"
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attribution_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scan: Mapped["Scan"] = relationship(back_populates="evidence_items")

class ModelPrediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_predictions"
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    output_key: Mapped[str] = mapped_column(String(100), nullable=False)
    output_value: Mapped[float] = mapped_column(Float, nullable=False)
    is_demo_prediction: Mapped[bool] = mapped_column(default=True, nullable=False)
    scan: Mapped["Scan"] = relationship(back_populates="model_predictions")

class VerificationCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "verification_checks"
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scan: Mapped["Scan"] = relationship(back_populates="verification_checks")

class ScamFingerprint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scam_fingerprints"
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scan: Mapped["Scan"] = relationship(back_populates="scam_fingerprints")

class ScamPattern(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scam_patterns"
    pattern_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    pattern_category: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_data: Mapped[str | None] = mapped_column(String, nullable=True)

