from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import FeatureFlagEnvironment, FeatureFlagType, RefundReason


# --- Auth ---
class LoginRequest(BaseModel):
    user_id: str | None = None
    email: str | None = None


# --- KYC ---
class ApproveKycRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class RejectKycRequest(BaseModel):
    reason: str = Field(min_length=1)
    explanation: str | None = Field(default=None, max_length=2000)


class RequestMoreInfoRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


# --- Refunds ---
class CreateRefundRequest(BaseModel):
    amount_minor: int = Field(gt=0)
    reason: RefundReason
    note: str | None = Field(default=None, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=255)


# --- Feature flags ---
class SetFlagValueRequest(BaseModel):
    environment: FeatureFlagEnvironment
    value: Any
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=1000)


class CreateFlagRequest(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    type: FeatureFlagType = FeatureFlagType.BOOLEAN
    owner: str | None = Field(default=None, max_length=255)
    tags: list[str] = Field(default_factory=list)
