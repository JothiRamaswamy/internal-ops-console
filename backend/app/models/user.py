from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.enums import UserRole, user_role_enum


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(user_role_enum, nullable=False)

    assigned_kyc_cases = relationship(
        "KycCase",
        back_populates="assigned_reviewer",
        foreign_keys="KycCase.assigned_reviewer_id",
    )
    decided_kyc_cases = relationship(
        "KycCase",
        back_populates="decided_by",
        foreign_keys="KycCase.decided_by_id",
    )
    requested_refunds = relationship("Refund", back_populates="requested_by")
    audit_events = relationship("AuditEvent", back_populates="actor")
