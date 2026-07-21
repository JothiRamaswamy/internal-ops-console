"""KYC provider abstraction.

The console normalizes every vendor into one internal model. Real adapters
(Persona, Stripe Identity) are stubbed so no external calls happen in the
prototype; only `MockKycProvider` is functional.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
            raw={"provider": "MOCK_VENDOR", "id": provider_case_id},
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


class StripeIdentityProvider(KycProvider):
    """Placeholder adapter — wire up the Stripe Identity API here in production."""

    def get_case(self, provider_case_id: str) -> NormalizedKycResult:
        raise NotImplementedError(
            "StripeIdentityProvider is not implemented in the prototype."
        )

    def request_more_info(self, provider_case_id: str) -> None:
        raise NotImplementedError(
            "StripeIdentityProvider is not implemented in the prototype."
        )
