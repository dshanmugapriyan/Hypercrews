import uuid
from sqlalchemy import String, Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    opportunities: Mapped[list["Opportunity"]] = relationship("Opportunity", back_populates="company", cascade="all, delete-orphan")
    domains: Mapped[list["Domain"]] = relationship("Domain", back_populates="company", cascade="all, delete-orphan")

class Domain(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "domains"
    
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    domain_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    domain_age_days: Mapped[int | None] = mapped_column(nullable=True)
    registrar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    company: Mapped["Company"] = relationship("Company", back_populates="domains")
