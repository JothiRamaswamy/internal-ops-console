"""Payment-provider abstraction.

`MockPaymentProvider` supports deterministic failure simulation: any payment
whose provider id ends in ``FAIL`` returns a failed refund. Real Stripe/Adyen
adapters are stubbed so no external calls happen in the prototype.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.base import new_id
from app.models.enums import PaymentStatus

# Stripe charge status strings -> the console's canonical payment status.
STRIPE_STATUS_MAP: dict[str, PaymentStatus] = {
    "succeeded": PaymentStatus.SUCCEEDED,
    "paid": PaymentStatus.SUCCEEDED,
    "failed": PaymentStatus.FAILED,
    "disputed": PaymentStatus.DISPUTED,
}


def map_stripe_status(
    status: str | None, amount_minor: int, amount_refunded_minor: int
) -> PaymentStatus:
    """Normalize a Stripe charge into the internal payment status.

    A failed/disputed charge keeps that status; otherwise the refunded amount
    (relative to the charge total) determines full vs. partial vs. none.
    """
    base = STRIPE_STATUS_MAP.get((status or "").lower(), PaymentStatus.SUCCEEDED)
    if base in (PaymentStatus.FAILED, PaymentStatus.DISPUTED):
        return base
    if amount_refunded_minor <= 0:
        return PaymentStatus.SUCCEEDED
    if amount_refunded_minor >= amount_minor:
        return PaymentStatus.FULLY_REFUNDED
    return PaymentStatus.PARTIALLY_REFUNDED


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
