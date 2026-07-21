import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Base,
    Customer,
    FeatureFlag,
    FeatureFlagValue,
    Payment,
    User,
)
from app.models.enums import (
    FeatureFlagEnvironment,
    FeatureFlagType,
    PaymentProvider,
    PaymentStatus,
    UserRole,
)

DEFAULT_TEST_URL = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/internal_ops_test"
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL)


def _ensure_database() -> None:
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[-1]
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_database()
    eng = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine) -> Session:
    # Clean slate per test.
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE audit_events, kyc_case_events, kyc_cases, refunds, "
                "payments, feature_flag_versions, feature_flag_values, "
                "feature_flags, processed_webhook_events, customers, users "
                "RESTART IDENTITY CASCADE"
            )
        )
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def users(db) -> dict[str, User]:
    specs = [
        ("user_admin", "admin@example.com", "Alex Admin", UserRole.ADMIN),
        ("user_ops", "ops@example.com", "Olivia Ops", UserRole.OPS_REVIEWER),
        ("user_support", "support@example.com", "Sam Support",
         UserRole.SUPPORT_AGENT),
        ("user_readonly", "readonly@example.com", "Riley Readonly",
         UserRole.READ_ONLY),
    ]
    out: dict[str, User] = {}
    for uid, email, name, role in specs:
        u = User(id=uid, email=email, name=name, role=role)
        db.add(u)
        out[role.value] = u
    db.commit()
    return out


@pytest.fixture
def customer(db) -> Customer:
    c = Customer(
        id="cust_test", email="c@example.com", first_name="Test",
        last_name="Customer", country_code="US",
    )
    db.add(c)
    db.commit()
    return c


def make_payment(db, customer, *, amount_minor=100000, provider_pid="pi_test_0001",
                 status=PaymentStatus.SUCCEEDED) -> Payment:
    p = Payment(
        provider=PaymentProvider.MOCK_PROVIDER,
        provider_payment_id=provider_pid,
        customer_id=customer.id,
        order_id="ORD-TEST",
        amount_minor=amount_minor,
        currency="USD",
        status=status,
        payment_method_brand="visa",
        payment_method_last4="4242",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def flag_config(enabled: bool, pct: int = 100, filters=None) -> dict:
    return {
        "enabled": enabled,
        "rollout_percentage": pct if enabled else 0,
        "filters": filters or [],
    }


def make_flag(db, users, *, key="test-flag", prod_value=False) -> FeatureFlag:
    flag = FeatureFlag(
        key=key, description="Test flag", type=FeatureFlagType.BOOLEAN,
        owner="platform", tags=["test"],
    )
    db.add(flag)
    db.flush()
    for env, val in [
        (FeatureFlagEnvironment.DEVELOPMENT, True),
        (FeatureFlagEnvironment.STAGING, False),
        (FeatureFlagEnvironment.PRODUCTION, prod_value),
    ]:
        db.add(FeatureFlagValue(
            flag_id=flag.id, environment=env, value=flag_config(val), version=1,
            updated_by_id=users["ADMIN"].id,
        ))
    db.commit()
    db.refresh(flag)
    return flag
