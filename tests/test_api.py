import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["educational_use_only"] is True


def test_generate_day_reports_and_exports(client, scenario_id):
    response = client.post(f"/api/v1/scenarios/{scenario_id}/days/generate", json={
        "simulation_date": "2026-03-16",
        "transaction_count": 4,
    })
    assert response.status_code == 201
    day = response.json()
    assert len(day["transactions"]) == 4
    assert all(t["documents"][0]["disclaimer"] == "SIMULAÇÃO EDUCACIONAL" for t in day["transactions"])

    duplicate = client.post(f"/api/v1/scenarios/{scenario_id}/days/generate", json={
        "simulation_date": "2026-03-16"
    })
    assert duplicate.status_code == 409

    report = client.get(f"/api/v1/scenarios/{scenario_id}/reports")
    assert report.status_code == 200
    assert "mini_dre" in report.json()

    for file_format in ("csv", "xlsx"):
        exported = client.get(f"/api/v1/scenarios/{scenario_id}/exports/{file_format}")
        assert exported.status_code == 200
        assert len(exported.content) > 100


def test_reject_day_outside_scenario(client, scenario_id):
    response = client.post(f"/api/v1/scenarios/{scenario_id}/days/generate", json={
        "simulation_date": "2027-01-01"
    })
    assert response.status_code == 422


def test_generate_loja_primavera_day(client):
    response = client.post("/api/v1/simulations/loja-primavera/days/generate", json={
        "date": "2026-12-10",
        "transaction_count": 8,
        "seed": 2026,
    })
    assert response.status_code == 201
    result = response.json()
    assert result["company"]["name"] == "Loja Primavera"
    assert result["movements_count"] == 8
    assert result["seasonality"]["level"] == "alta"
    assert result["opening_balance"] == 15000.0
    assert result["disclaimer"].startswith("SIMULAÇÃO EDUCACIONAL")
    assert result["spreadsheet_compatibility"]["one_row_per_movement"] is True

    allowed = {"entrada", "saida", "conta_a_pagar", "conta_a_receber"}
    for movement in result["movements"]:
        assert movement["classification"] in allowed
        assert movement["pedagogical_observation"]
        assert movement["document"]["disclaimer"] == "SIMULAÇÃO EDUCACIONAL"


def test_primavera_rejects_invalid_count(client):
    response = client.post("/api/v1/simulations/loja-primavera/days/generate", json={
        "date": "2026-08-12",
        "transaction_count": 9,
    })
    assert response.status_code == 422


def test_financial_continuity_accounts_and_scenario_version(client, scenario_id):
    scenarios = client.get("/api/v1/scenarios").json()
    scenario = next(item for item in scenarios if item["id"] == scenario_id)
    assert scenario["version"] == 1
    assert scenario["difficulty"] == "basic"

    first = client.post(f"/api/v1/scenarios/{scenario_id}/days/generate", json={
        "simulation_date": "2026-04-01", "transaction_count": 8,
    })
    assert first.status_code == 201
    first_day = first.json()
    expected_closing = first_day["opening_balance"]
    for transaction in first_day["transactions"]:
        if transaction["cash_effect"] == "in":
            expected_closing += transaction["amount"]
        elif transaction["cash_effect"] == "out":
            expected_closing -= transaction["amount"]
    assert first_day["closing_balance"] == pytest.approx(expected_closing)
    assert len(first_day["generation_hash"]) == 64

    second = client.post(f"/api/v1/scenarios/{scenario_id}/days/generate", json={
        "simulation_date": "2026-04-02", "transaction_count": 5,
    })
    assert second.status_code == 201
    assert second.json()["opening_balance"] == first_day["closing_balance"]

    retroactive = client.post(f"/api/v1/scenarios/{scenario_id}/days/generate", json={
        "simulation_date": "2026-03-31", "transaction_count": 3,
    })
    assert retroactive.status_code == 409

    payables = client.get(f"/api/v1/scenarios/{scenario_id}/accounts-payable")
    receivables = client.get(f"/api/v1/scenarios/{scenario_id}/accounts-receivable")
    assert payables.status_code == receivables.status_code == 200
    assert len(payables.json()) + len(receivables.json()) > 0

    published = client.post(f"/api/v1/scenarios/{scenario_id}/days/2026-04-01/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"


def test_due_accounts_can_be_settled_on_later_days(client, scenario_id):
    generated_days = []
    for simulation_date in ("2026-01-02", "2026-02-15", "2026-04-01", "2026-06-01"):
        response = client.post(f"/api/v1/scenarios/{scenario_id}/days/generate", json={
            "simulation_date": simulation_date, "transaction_count": 8,
        })
        assert response.status_code == 201
        generated_days.append(response.json())

    report = client.get(f"/api/v1/scenarios/{scenario_id}/reports").json()
    accounts = report["accounts_payable"] + report["accounts_receivable"]
    assert accounts
    assert any(account["status"] in {"paid", "overdue"} for account in accounts)

    settlement_kinds = {"customer_receipt", "supplier_payment"}
    assert any(transaction["transaction_kind"] in settlement_kinds
               for day in generated_days for transaction in day["transactions"])
