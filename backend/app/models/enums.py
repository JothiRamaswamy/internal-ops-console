import enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    OPS_REVIEWER = "OPS_REVIEWER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    READ_ONLY = "READ_ONLY"


class KycStatus(str, enum.Enum):
    PENDING_VENDOR = "PENDING_VENDOR"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REQUESTED_MORE_INFO = "REQUESTED_MORE_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class KycVendor(str, enum.Enum):
    PERSONA = "PERSONA"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PaymentProvider(str, enum.Enum):
    STRIPE = "STRIPE"
    ADYEN = "ADYEN"
    MOCK_PROVIDER = "MOCK_PROVIDER"


class PaymentStatus(str, enum.Enum):
    SUCCEEDED = "SUCCEEDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    FULLY_REFUNDED = "FULLY_REFUNDED"
    DISPUTED = "DISPUTED"
    FAILED = "FAILED"


class RefundStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class RefundReason(str, enum.Enum):
    DUPLICATE_CHARGE = "DUPLICATE_CHARGE"
    NOT_DELIVERED = "NOT_DELIVERED"
    CUSTOMER_REQUEST = "CUSTOMER_REQUEST"
    FRAUDULENT_CHARGE = "FRAUDULENT_CHARGE"
    BILLING_ERROR = "BILLING_ERROR"
    GOODWILL = "GOODWILL"
    OTHER = "OTHER"


class FeatureFlagType(str, enum.Enum):
    BOOLEAN = "BOOLEAN"
    STRING = "STRING"
    NUMBER = "NUMBER"
    JSON = "JSON"


class FeatureFlagEnvironment(str, enum.Enum):
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


# Shared SQLAlchemy enum type instances. Reusing a single instance per named
# type prevents Postgres "type already exists" errors when the same enum is
# referenced by multiple columns/tables.
user_role_enum = SAEnum(UserRole, name="user_role")
kyc_status_enum = SAEnum(KycStatus, name="kyc_status")
kyc_vendor_enum = SAEnum(KycVendor, name="kyc_vendor")
risk_level_enum = SAEnum(RiskLevel, name="risk_level")
payment_provider_enum = SAEnum(PaymentProvider, name="payment_provider")
payment_status_enum = SAEnum(PaymentStatus, name="payment_status")
refund_status_enum = SAEnum(RefundStatus, name="refund_status")
refund_reason_enum = SAEnum(RefundReason, name="refund_reason")
feature_flag_type_enum = SAEnum(FeatureFlagType, name="feature_flag_type")
feature_flag_environment_enum = SAEnum(
    FeatureFlagEnvironment, name="feature_flag_environment"
)
