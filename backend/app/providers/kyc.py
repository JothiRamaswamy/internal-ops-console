"""KYC provider abstraction.

The console integrates a single KYC vendor (Persona) and normalizes it into one
internal model. The real `PersonaKycProvider` adapter is stubbed so no external
calls happen in the prototype; `MockKycProvider` is the functional in-prototype
implementation that stands in for the Persona API. The abstract `KycProvider`
interface is the seam to swap the mock for the real adapter (or an additional
vendor later) without touching the services, RBAC, or UI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.enums import KycStatus, RiskLevel

# Vendor inquiry status strings -> the console's canonical KYC lifecycle.
# The vendor only tells us how far *its* checks got; the APPROVED / REJECTED
# decision belongs to a human reviewer inside the console, so vendor states map
# no further than NEEDS_REVIEW.
PERSONA_STATUS_MAP: dict[str, KycStatus] = {
    "created": KycStatus.PENDING_VENDOR,
    "pending": KycStatus.PENDING_VENDOR,
    "processing": KycStatus.PENDING_VENDOR,
    "completed": KycStatus.NEEDS_REVIEW,
    "needs_review": KycStatus.NEEDS_REVIEW,
    "approved": KycStatus.NEEDS_REVIEW,
    "declined": KycStatus.NEEDS_REVIEW,
    "failed": KycStatus.NEEDS_REVIEW,
}


def map_persona_status(status: str | None) -> KycStatus:
    """Normalize a Persona inquiry status into the internal KYC status."""
    return PERSONA_STATUS_MAP.get((status or "").lower(), KycStatus.PENDING_VENDOR)


def risk_level_from_score(score: int | None) -> RiskLevel:
    """Bucket a raw 0-100 vendor risk score into a stable risk band."""
    if score is None:
        return RiskLevel.LOW
    if score <= 30:
        return RiskLevel.LOW
    if score <= 60:
        return RiskLevel.MEDIUM
    if score <= 85:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


@dataclass
class NormalizedKycResult:
    provider_case_id: str
    overall_status: str
    risk_score: int | None
    document_result: str
    selfie_result: str
    watchlist_result: str
    address_result: str
    reason_codes: list[str]
    raw: dict


class KycProvider(ABC):
    @abstractmethod
    def get_case(self, provider_case_id: str) -> NormalizedKycResult: ...

    @abstractmethod
    def request_more_info(self, provider_case_id: str) -> None: ...


class MockKycProvider(KycProvider):
    def get_case(self, provider_case_id: str) -> NormalizedKycResult:
        return NormalizedKycResult(
            provider_case_id=provider_case_id,
            overall_status="needs_review",
            risk_score=50,
            document_result="passed",
            selfie_result="passed",
            watchlist_result="clear",
            address_result="passed",
            reason_codes=[],
            raw={"provider": "PERSONA", "id": provider_case_id},
        )

    def request_more_info(self, provider_case_id: str) -> None:  # noqa: D401
        # No-op for the mock provider.
        return None


class PersonaKycProvider(KycProvider):
    """Placeholder adapter — wire up the Persona API here in production."""

    def get_case(self, provider_case_id: str) -> NormalizedKycResult:
        raise NotImplementedError("PersonaKycProvider is not implemented in the prototype.")

    def request_more_info(self, provider_case_id: str) -> None:
        raise NotImplementedError("PersonaKycProvider is not implemented in the prototype.")
