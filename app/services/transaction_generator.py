import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class GeneratedTransaction:
    transaction_type: str
    transaction_kind: str
    cash_effect: str
    dre_effect: str
    category: str
    description: str
    counterparty: str
    amount: Decimal
    issue_date: date
    due_date: date
    payment_date: date | None
    status: str
    payment_method: str | None
    document_type: str


REVENUES = [
    ("Vendas", "Venda de artigos de vestuário", "Cliente Fictício", 80, 850, "cupom_fiscal"),
    ("Vendas", "Venda de acessórios", "Consumidor Simulado", 45, 420, "cupom_fiscal"),
    ("Promoções", "Venda em campanha promocional", "Cliente da Promoção Educacional", 70, 650, "nota_fiscal"),
    ("Vendas", "Venda de mercadorias para cliente cadastrado", "Cliente Educacional Alfa", 350, 2800, "nota_fiscal"),
]

EXPENSES = [
    ("Fornecedores", "Compra de estoque para revenda", "Confecções Horizonte Fictícia", 300, 2200, "boleto"),
    ("Despesas operacionais", "Material de embalagem", "Suprimentos Primavera Simulada", 60, 600, "cupom_fiscal"),
    ("Utilidades", "Conta mensal de serviço", "Concessionária Educacional", 180, 950, "boleto"),
    ("Transporte", "Passagem para visita técnica", "Viação Modelo", 90, 480, "passagem"),
    ("Viagens", "Diária para atividade externa", "Colaborador Fictício", 180, 650, "diaria"),
    ("Serviços", "Serviço de manutenção", "Manutenção Exemplo ME", 150, 1200, "recibo"),
]

PAYMENT_METHODS = ["PIX SIMULADO — NÃO FUNCIONAL", "cartão simulado", "dinheiro fictício"]


def generate_transactions(simulation_date: date, seed: int, count: int | None = None, scenario_version: int = 1) -> list[GeneratedTransaction]:
    """Gera lançamentos reproduzíveis sem usar identificadores financeiros reais."""
    rng = random.Random(seed + simulation_date.toordinal() + scenario_version * 1_000_003)
    total = count or rng.randint(3, 8)
    generated: list[GeneratedTransaction] = []

    for index in range(total):
        is_revenue = rng.random() < 0.48
        source = rng.choice(REVENUES if is_revenue else EXPENSES)
        category, description, counterparty, minimum, maximum, document_type = source
        amount = Decimal(str(round(rng.uniform(minimum, maximum), 2)))
        on_credit = rng.random() < (0.38 if is_revenue else 0.45)
        due_date = simulation_date + timedelta(days=rng.choice([7, 15, 20, 30])) if on_credit else simulation_date
        paid = not on_credit or rng.random() < 0.18
        payment_date = simulation_date if paid else None
        status = "paid" if paid else "open"
        payment_method = rng.choice(PAYMENT_METHODS) if paid else None

        generated.append(
            GeneratedTransaction(
                transaction_type="income" if is_revenue else "expense",
                transaction_kind=("credit_sale" if on_credit else "cash_sale") if is_revenue else ("credit_purchase" if on_credit else "cash_purchase"),
                cash_effect="in" if is_revenue and paid else ("out" if not is_revenue and paid else "none"),
                dre_effect="revenue" if is_revenue else ("cost" if category == "Fornecedores" else "expense"),
                category=category,
                description=f"{description} #{index + 1}",
                counterparty=counterparty,
                amount=amount,
                issue_date=simulation_date,
                due_date=due_date,
                payment_date=payment_date,
                status=status,
                payment_method=payment_method,
                document_type=document_type,
            )
        )
    return generated


def movement_classification(transaction_type: str, status: str) -> str:
    """Converte atributos contábeis na classificação usada pelos alunos."""
    if transaction_type == "income":
        return "entrada" if status == "paid" else "conta_a_receber"
    return "saida" if status == "paid" else "conta_a_pagar"
