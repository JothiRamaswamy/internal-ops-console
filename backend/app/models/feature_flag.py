from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow
from app.models.enums import (
    FeatureFlagEnvironment,
    FeatureFlagType,
    feature_flag_environment_enum,
    feature_flag_type_enum,
)


class FeatureFlag(IdMixin, TimestampMixin, Base):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    type: Mapped[FeatureFlagType] = mapped_column(
        feature_flag_type_enum, nullable=False
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    values = relationship(
        "FeatureFlagValue",
        back_populates="flag",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "FeatureFlagVersion",
        back_populates="flag",
        order_by="FeatureFlagVersion.created_at.desc()",
        cascade="all, delete-orphan",
    )


class FeatureFlagValue(IdMixin, Base):
    __tablename__ = "feature_flag_values"
    __table_args__ = (UniqueConstraint("flag_id", "environment"),)

    flag_id: Mapped[str] = mapped_column(
        ForeignKey("feature_flags.id"), nullable=False
    )
    environment: Mapped[FeatureFlagEnvironment] = mapped_column(
        feature_flag_environment_enum, nullable=False
    )
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSONB, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    flag = relationship("FeatureFlag", back_populates="values")
    updated_by = relationship("User")


class FeatureFlagVersion(IdMixin, Base):
    __tablename__ = "feature_flag_versions"

    flag_id: Mapped[str] = mapped_column(
        ForeignKey("feature_flags.id"), nullable=False
    )
    environment: Mapped[FeatureFlagEnvironment] = mapped_column(
        feature_flag_environment_enum, nullable=False
    )
    previous_value: Mapped[dict | list | str | int | float | bool | None] = (
        mapped_column(JSONB, nullable=True)
    )
    new_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSONB, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    changed_by_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    flag = relationship("FeatureFlag", back_populates="versions")
    changed_by = relationship("User")
