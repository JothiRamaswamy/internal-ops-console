"""Payment-provider abstraction.

`MockPaymentProvider` supports deterministic failure simulation: any payment
whose provider id ends in ``FAIL`` returns a failed refund. Real Stripe/Adyen
adapters are stubbed so no external calls happen in the prototype.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.base import new_id


@dataclass
class ProviderRefundResult:
    success: bool
    provider_refund_id: str | None
    failure_reason: str | None = None


@dataclass
class RefundInput:
    provider_payment_id: str
    amount_minor: int
    currency: str
    idempotency_key: str


class PaymentProviderAdapter(ABC):
    @abstractmethod
    def create_refund(self, data: RefundInput) -> ProviderRefundResult: ...


class MockPaymentProvider(PaymentProviderAdapter):
    def create_refund(self, data: RefundInput) -> ProviderRefundResult:
        if data.provider_payment_id.endswith("FAIL"):
            return ProviderRefundResult(
                success=False,
                provider_refund_id=None,
                failure_reason="Provider declined the refund (simulated failure).",
            )
        return ProviderRefundResult(
            success=True,
            provider_refund_id=f"re_mock_{new_id()[:16]}",
        )


class StripePaymentProvider(PaymentProviderAdapter):
    """Placeholder adapter — wire up the Stripe Refunds API here in production."""

    def create_refund(self, data: RefundInput) -> ProviderRefundResult:
        raise NotImplementedError(
            "StripePaymentProvider is not implemented in the prototype."
        )


class AdyenPaymentProvider(PaymentProviderAdapter):
    """Placeholder adapter — wire up the Adyen refunds API here in production."""

    def create_refund(self, data: RefundInput) -> ProviderRefundResult:
        raise NotImplementedError(
            "AdyenPaymentProvider is not implemented in the prototype."
        )


def get_payment_provider(provider_name: str) -> PaymentProviderAdapter:
    """Resolve an adapter. The prototype always uses the mock implementation."""
    return MockPaymentProvider()
