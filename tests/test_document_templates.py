from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.document_generator import DOCUMENT_CATALOG, render_document_html


@pytest.fixture()
def template_data():
    company = SimpleNamespace(trade_name="Loja Primavera", educational_id="EDU-LOJA-PRIMAVERA")
    transaction = SimpleNamespace(
        issue_date=date(2026, 10, 15), due_date=date(2026, 10, 30), payment_date=date(2026, 10, 15),
        counterparty="Favorecido Fictício", description="Operação exclusivamente pedagógica",
        category="Despesas operacionais", amount=Decimal("245.90"),
        payment_method="PIX SIMULADO — NÃO FUNCIONAL", status="paid",
    )
    return transaction, company


@pytest.mark.parametrize("document_type", DOCUMENT_CATALOG.keys())
def test_all_visual_templates_render_required_fields(document_type, template_data):
    transaction, company = template_data
    html = render_document_html(transaction, company, document_type, "EDU-TESTE-0001")
    assert html.startswith("<!doctype html>")
    assert "SIMULAÇÃO EDUCACIONAL" in html
    assert "SEM VALIDADE FISCAL OU FINANCEIRA" in html
    assert "Favorecido Fictício" in html
    assert "15/10/2026" in html
    assert "R$ 245,90" in html
    assert "PIX SIMULADO — NÃO FUNCIONAL" in html
    assert "CPF, CNPJ, PIX ou código de barras funcional" in html


def test_document_template_catalog_endpoint(client):
    response = client.get("/api/v1/document-templates")
    assert response.status_code == 200
    assert len(response.json()["templates"]) == 7
    assert {item["type"] for item in response.json()["templates"]} == set(DOCUMENT_CATALOG)
