import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_db():
        with TestingSession() as db:
            yield db

    from app.core.config import settings
    monkeypatch.setattr(settings, "documents_dir", tmp_path / "documents")
    monkeypatch.setattr(settings, "exports_dir", tmp_path / "exports")
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def scenario_id(client):
    company = client.post("/api/v1/companies", json={
        "name": "Empresa Modelo Educacional Ltda.",
        "trade_name": "Empresa Modelo",
        "educational_id": "EDU-EMP-001",
        "business_type": "Comércio e serviços",
        "city": "Cuiabá",
        "state": "MT",
        "opening_balance": 12000,
    })
    assert company.status_code == 201
    scenario = client.post("/api/v1/scenarios", json={
        "company_id": company.json()["id"],
        "name": "Ano letivo 2026",
        "period_type": "annual",
        "start_date": "2026-01-01",
        "seed": 365,
    })
    assert scenario.status_code == 201
    return scenario.json()["id"]

