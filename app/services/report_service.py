from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountPayable, AccountReceivable, Scenario, SimulationDay, Transaction


def scenario_transactions(db: Session, scenario_id: int) -> list[Transaction]:
    return list(db.scalars(select(Transaction).join(SimulationDay)
        .where(SimulationDay.scenario_id == scenario_id)
        .order_by(Transaction.issue_date, Transaction.id)))


def build_reports(db: Session, scenario: Scenario) -> dict:
    transactions = scenario_transactions(db, scenario.id)
    days = list(db.scalars(select(SimulationDay).where(SimulationDay.scenario_id == scenario.id)
                           .order_by(SimulationDay.simulation_date)))
    cash_in = sum((t.amount for t in transactions if t.cash_effect == "in"), Decimal("0"))
    cash_out = sum((t.amount for t in transactions if t.cash_effect == "out"), Decimal("0"))
    revenue = sum((t.amount for t in transactions if t.dre_effect == "revenue"), Decimal("0"))
    costs = sum((t.amount for t in transactions if t.dre_effect == "cost"), Decimal("0"))
    expenses = sum((t.amount for t in transactions if t.dre_effect == "expense"), Decimal("0"))
    payables = list(db.scalars(select(AccountPayable).where(AccountPayable.scenario_id == scenario.id)
                               .order_by(AccountPayable.due_date)))
    receivables = list(db.scalars(select(AccountReceivable).where(AccountReceivable.scenario_id == scenario.id)
                                  .order_by(AccountReceivable.due_date)))

    def account_item(account, counterparty: str) -> dict:
        return {"id": account.id, "source_transaction_id": account.source_transaction_id,
                "description": account.description, "counterparty": counterparty,
                "original_amount": float(account.original_amount),
                "outstanding_amount": float(account.outstanding_amount),
                "issue_date": account.issue_date, "due_date": account.due_date,
                "status": account.status, "settled_date": account.settled_date}

    return {
        "scenario_id": scenario.id, "scenario_version": scenario.version,
        "currency": "BRL (valores fictícios)",
        "cash_flow": {"opening_balance": float(scenario.company.opening_balance),
                      "cash_in": float(cash_in), "cash_out": float(cash_out),
                      "closing_balance": float(days[-1].closing_balance if days else scenario.company.opening_balance)},
        "mini_dre": {"gross_revenue": float(revenue), "costs": float(costs),
                     "gross_profit": float(revenue - costs), "operating_expenses": float(expenses),
                     "simulated_result": float(revenue - costs - expenses)},
        "accounts_payable": [account_item(a, a.supplier_name) for a in payables],
        "accounts_receivable": [account_item(a, a.customer_name) for a in receivables],
        "days": [{"date": d.simulation_date, "opening_balance": float(d.opening_balance),
                  "closing_balance": float(d.closing_balance), "status": d.status} for d in days],
    }
