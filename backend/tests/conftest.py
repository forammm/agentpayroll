import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.db import Base, get_db
from app.langgraph_app.tools.llm_client import ExplanationClient, LlmGenerationError
from app.main import app
from app.models.payroll_rule import PayrollRule
from app.models.payslip import Payslip
from app.models.timesheet import Timesheet
from app.models.user import User
from app.schemas.verification import VerificationExplanation


@pytest.fixture()
def db_engine():
    """A fresh in-memory SQLite database per test. The app's models already
    create_all cleanly against SQLite (verified against the real Alembic
    migration too - see backend/README.md), so this gives fast, isolated
    tests without requiring a live Postgres instance."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session_factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session(db_session_factory):
    db = db_session_factory()
    yield db
    db.close()


@pytest.fixture()
def client(db_session_factory, tmp_path, monkeypatch):
    def _override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_user(db_session_factory):
    db = db_session_factory()
    user = User(id=uuid.uuid4(), email="test.user@example.com", full_name="Test User")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture()
def make_user(db_session_factory):
    def _make(email: str = "other.user@example.com", full_name: str = "Other User") -> User:
        db = db_session_factory()
        user = User(id=uuid.uuid4(), email=email, full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user

    return _make


@pytest.fixture()
def make_payroll_rule(db_session_factory):
    def _make(user_id, **overrides) -> PayrollRule:
        defaults = dict(
            id=uuid.uuid4(),
            user_id=user_id,
            normal_rate=Decimal("30.00"),
            overtime_rate=Decimal("45.00"),
            saturday_rate=Decimal("37.50"),
            sunday_rate=Decimal("45.00"),
            public_holiday_rate=Decimal("60.00"),
            overnight_rate=Decimal("33.00"),
            early_morning_rate=Decimal("31.50"),
            evening_rate=Decimal("31.50"),
        )
        defaults.update(overrides)
        db = db_session_factory()
        rule = PayrollRule(**defaults)
        db.add(rule)
        db.commit()
        db.refresh(rule)
        db.close()
        return rule

    return _make


@pytest.fixture()
def make_timesheet(db_session_factory):
    def _make(user_id, work_date, start_time=time(9, 0), end_time=time(17, 0), break_minutes=30, shift_type="normal") -> Timesheet:
        start_dt = datetime.combine(work_date, start_time)
        end_dt = datetime.combine(work_date, end_time)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        hours_worked = Decimal((end_dt - start_dt).total_seconds() / 3600 - break_minutes / 60).quantize(Decimal("0.01"))
        db = db_session_factory()
        shift = Timesheet(
            id=uuid.uuid4(),
            user_id=user_id,
            work_date=work_date,
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
            shift_type=shift_type,
            hours_worked=hours_worked,
        )
        db.add(shift)
        db.commit()
        db.refresh(shift)
        db.close()
        return shift

    return _make


@pytest.fixture()
def make_payslip(db_session_factory):
    def _make(user_id, **overrides) -> Payslip:
        defaults = dict(
            id=uuid.uuid4(),
            user_id=user_id,
            file_name="payslip.pdf",
            status="EXTRACTED",
            used_ocr=False,
        )
        defaults.update(overrides)
        db = db_session_factory()
        payslip = Payslip(**defaults)
        db.add(payslip)
        db.commit()
        db.refresh(payslip)
        db.close()
        return payslip

    return _make


class FakeExplanationClient(ExplanationClient):
    """Test double for the LLM explanation call - see app.langgraph_app.tools.llm_client.
    Records the context it was called with so tests can assert what was (and wasn't)
    sent to the model."""

    def __init__(self, response: VerificationExplanation | None = None, raise_error: bool = False):
        self.response = response or VerificationExplanation(summary="fake explanation", evidence=[], uncertainties=[], next_steps=[])
        self.raise_error = raise_error
        self.called_with: dict | None = None

    def generate_explanation(self, context: dict) -> VerificationExplanation:
        self.called_with = context
        if self.raise_error:
            raise LlmGenerationError("simulated LLM failure")
        return self.response


@pytest.fixture()
def fake_llm_client():
    return FakeExplanationClient()
