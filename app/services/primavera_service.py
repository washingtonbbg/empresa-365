from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Company, Scenario, SimulationDay, Transaction
from app.services.simulation_service import create_simulated_day
from app.services.transaction_generator import movement_classification


COMPANY_EDUCATIONAL_ID = "EDU-LOJA-PRIMAVERA"


def _get_or_create_context(db: Session, simulation_date: date, seed: int) -> Scenario:
    company = db.scalar(select(Company).where(Company.educational_id == COMPANY_EDUCATIONAL_ID))
    if not company:
        company = Company(
            name="Loja Primavera Comércio Educacional Ltda.",
            trade_name="Loja Primavera",
            educational_id=COMPANY_EDUCATIONAL_ID,
            business_type="Comércio varejista fictício de vestuário e acessórios",
            city="Cuiabá",
            state="MT",
            opening_balance=Decimal("15000.00"),
        )
        db.add(company)
        db.flush()

    scenario = db.scalar(select(Scenario).options(selectinload(Scenario.company)).where(
        Scenario.company_id == company.id,
        Scenario.name == f"Loja Primavera — {simulation_date.year}",
    ))
    if not scenario:
        scenario = Scenario(
            company_id=company.id,
            name=f"Loja Primavera — {simulation_date.year}",
            period_type="annual",
            start_date=date(simulation_date.year, 1, 1),
            end_date=date(simulation_date.year, 12, 31),
            seed=seed,
        )
        db.add(scenario)
        db.commit()
        scenario = db.scalar(select(Scenario).options(selectinload(Scenario.company)).where(Scenario.id == scenario.id))
    return scenario


def _opening_balance(db: Session, scenario: Scenario, simulation_date: date) -> Decimal:
    previous = list(db.scalars(
        select(Transaction).join(SimulationDay).where(
            SimulationDay.scenario_id == scenario.id,
            SimulationDay.simulation_date < simulation_date,
            Transaction.status == "paid",
        )
    ))
    inflows = sum((t.amount for t in previous if t.transaction_type == "income"), Decimal("0"))
    outflows = sum((t.amount for t in previous if t.transaction_type == "expense"), Decimal("0"))
    return scenario.company.opening_balance + inflows - outflows


def _seasonality(simulation_date: date) -> tuple[str, str]:
    if simulation_date.month == 12:
        return "alta", "Compras de fim de ano podem elevar vendas e exigir controle de estoque."
    if simulation_date.month in (1, 2):
        return "baixa", "Período pós-festas: atenção à queda de demanda e ao capital de giro."
    if simulation_date.month in (5, 6):
        return "moderada", "Datas comemorativas podem justificar promoções e reforço de estoque."
    return "normal", "Dia sem pico sazonal; compare o desempenho com a média do cenário."


def generate_primavera_day(db: Session, simulation_date: date, count: int | None, seed: int) -> dict:
    scenario = _get_or_create_context(db, simulation_date, seed)
    day = create_simulated_day(db, scenario, simulation_date, count)
    seasonality, seasonal_note = _seasonality(simulation_date)
    movements = []
    opening = day.opening_balance
    closing = day.closing_balance

    for transaction in day.transactions:
        classification = movement_classification(transaction.transaction_type, transaction.status)
        observation = {
            "entrada": "Registrar no fluxo de caixa como ingresso realizado.",
            "saida": "Registrar no fluxo de caixa e conferir o documento de quitação.",
            "conta_a_pagar": "Não reduz o caixa hoje; lançar no controle de obrigações.",
            "conta_a_receber": "Não aumenta o caixa hoje; acompanhar prazo e risco de inadimplência.",
        }[classification]
        classification_label = {
            "entrada": "Entrada",
            "saida": "Saída",
            "conta_a_pagar": "Conta a pagar",
            "conta_a_receber": "Conta a receber",
        }[classification]
        document = transaction.documents[0]
        movements.append({
            "id": transaction.id,
            "classification": classification,
            "classification_label": classification_label,
            "category": transaction.category,
            "transaction_kind": transaction.transaction_kind,
            "cash_effect": transaction.cash_effect,
            "dre_effect": transaction.dre_effect,
            "description": transaction.description,
            "counterparty": transaction.counterparty,
            "amount": float(transaction.amount),
            "payment_method": transaction.payment_method or "a prazo",
            "issue_date": transaction.issue_date.isoformat(),
            "due_date": transaction.due_date.isoformat(),
            "payment_date": transaction.payment_date.isoformat() if transaction.payment_date else None,
            "status": transaction.status,
            "document": {
                "type": document.document_type,
                "educational_number": document.educational_number,
                "file_path": document.file_path,
                "disclaimer": document.disclaimer,
            },
            "pedagogical_observation": observation,
        })

    open_receivables = sum(Decimal(str(m["amount"])) for m in movements if m["classification"] == "conta_a_receber")
    open_payables = sum(Decimal(str(m["amount"])) for m in movements if m["classification"] == "conta_a_pagar")
    risks = []
    if open_payables > opening * Decimal("0.20"):
        risks.append("Obrigações do dia superam 20% do saldo inicial; discutir liquidez e priorização.")
    if open_receivables > Decimal("0"):
        risks.append("Há vendas a prazo; avaliar prazo médio, cobrança e possível inadimplência.")
    if not risks:
        risks.append("Risco financeiro baixo no dia; verificar se o caixa realizado sustenta as operações.")

    return {
        "company": {"name": scenario.company.trade_name, "educational_id": scenario.company.educational_id},
        "scenario_id": scenario.id,
        "simulation_day_id": day.id,
        "date": simulation_date.isoformat(),
        "opening_balance": float(opening),
        "closing_balance": float(closing),
        "seasonality": {"level": seasonality, "pedagogical_note": seasonal_note},
        "movements_count": len(movements),
        "movements": movements,
        "pedagogical_observations": [
            "Compare saldo contábil, caixa realizado e valores ainda a vencer.",
            "Avalie se promoções aumentam receita sem comprometer margem e estoque.",
            *risks,
        ],
        "spreadsheet_compatibility": {
            "one_row_per_movement": True,
            "suggested_columns": [
                "date", "classification", "category", "description", "counterparty", "amount",
                "payment_method", "due_date", "payment_date", "status", "document.type",
                "document.educational_number", "pedagogical_observation",
            ],
        },
        "disclaimer": "SIMULAÇÃO EDUCACIONAL — USO EXCLUSIVO PARA FINS PEDAGÓGICOS",
    }
