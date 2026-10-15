from html import escape
from pathlib import Path
from string import Template

from app.core.config import settings
from app.models import Company, Transaction

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "documents"
DOCUMENT_CATALOG = {
    "nota_fiscal": {"label": "Nota fiscal simulada", "purpose": "Venda de mercadoria ou serviço"},
    "cupom_fiscal": {"label": "Cupom fiscal simulado", "purpose": "Venda ao consumidor"},
    "boleto": {"label": "Boleto didático — não pagável", "purpose": "Obrigação com vencimento"},
    "recibo": {"label": "Recibo simulado", "purpose": "Declaração de recebimento"},
    "comprovante": {"label": "Comprovante de pagamento simulado", "purpose": "Liquidação de valor"},
    "diaria": {"label": "Diária de colaborador simulada", "purpose": "Despesa de atividade externa"},
    "passagem": {"label": "Passagem de viagem simulada", "purpose": "Deslocamento pedagógico"},
}

BASE_HTML = Template("""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>$title</title><style>
*{box-sizing:border-box}body{font-family:Arial,Helvetica,sans-serif;background:#e9eef3;margin:0;padding:28px;color:#17202a}
.document{--accent:$accent;max-width:820px;min-height:520px;margin:auto;background:#fff;border:1px solid #9aa6b2;box-shadow:0 8px 24px #17202a22;position:relative;overflow:hidden}
.document:before{content:"SIMULAÇÃO EDUCACIONAL";position:absolute;top:46%;left:8%;transform:rotate(-27deg);font-size:50px;font-weight:800;color:#25374610;letter-spacing:3px;white-space:nowrap;z-index:0}
.warning{background:#7b241c;color:#fff;padding:9px 24px;text-align:center;font-size:12px;font-weight:700;letter-spacing:.8px}
.header{display:flex;justify-content:space-between;gap:24px;padding:24px 28px 18px;border-bottom:4px solid var(--accent)}
.brand{font-size:20px;font-weight:800}.eyebrow,.label{font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:#566573;font-weight:700}
h1{margin:5px 0 0;font-size:26px;color:var(--accent)}.document-no{text-align:right;font:700 15px Consolas,monospace}
.content{position:relative;z-index:1;padding:22px 28px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.grid.three{grid-template-columns:repeat(3,1fr)}
.field{border:1px solid #c8d0d8;border-radius:4px;padding:10px 12px;min-height:58px;background:#ffffffdd}.field.wide{grid-column:1/-1}.value{display:block;margin-top:5px;font-size:14px;font-weight:600}.amount{font-size:25px;color:var(--accent)}
.items{width:100%;border-collapse:collapse;margin:16px 0}.items th{background:var(--accent);color:#fff;font-size:11px;text-align:left;padding:8px}.items td{border:1px solid #ccd3da;padding:9px;font-size:13px}
.total{display:flex;justify-content:flex-end;align-items:center;gap:16px;margin:14px 0;font-weight:700}.total strong{font-size:25px;color:var(--accent)}
.fake-code{font:700 16px Consolas,monospace;letter-spacing:2px;background:#f2f4f4;border:2px dashed #7f8c8d;padding:12px;text-align:center}.route{display:flex;align-items:center;justify-content:space-between;margin:18px 0}.city{font-size:18px;font-weight:800}.arrow{font-size:28px;color:var(--accent)}
.signature{margin:28px auto 0;padding-top:10px;border-top:1px solid #566573;text-align:center;width:55%;font-size:11px}.footer{position:relative;z-index:1;margin:4px 28px 22px;padding-top:12px;border-top:1px solid #d5d8dc;font-size:10px;color:#5d6d7e;display:flex;justify-content:space-between;gap:20px}
.badge{display:inline-block;background:#f4f6f7;border:1px solid #aeb6bf;border-radius:20px;padding:5px 10px;font-size:11px;font-weight:700}
@media(max-width:620px){body{padding:8px}.header{display:block}.document-no{text-align:left;margin-top:12px}.grid,.grid.three{grid-template-columns:1fr}.document:before{font-size:30px}.field.wide{grid-column:auto}}
@media print{body{background:#fff;padding:0}.document{box-shadow:none;border:0;max-width:none}.warning{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style></head><body><main class="document"><div class="warning">SIMULAÇÃO EDUCACIONAL • USO EXCLUSIVO PARA FINS PEDAGÓGICOS • SEM VALIDADE FISCAL OU FINANCEIRA</div>
<header class="header"><div><div class="eyebrow">Empresa fictícia</div><div class="brand">$company</div><h1>$title</h1></div><div class="document-no"><span class="label">Documento</span><br>$number</div></header>
<section class="content">$body</section><footer class="footer"><span>Não contém CPF, CNPJ, PIX ou código de barras funcional.</span><span>Gerado pelo Empresa 365</span></footer></main></body></html>""")


def _money(value) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _context(transaction: Transaction, company: Company, educational_number: str) -> dict[str, str]:
    return {"company": escape(company.trade_name), "company_id": escape(company.educational_id),
            "number": educational_number, "issue_date": transaction.issue_date.strftime("%d/%m/%Y"),
            "due_date": transaction.due_date.strftime("%d/%m/%Y"),
            "payment_date": transaction.payment_date.strftime("%d/%m/%Y") if transaction.payment_date else "Não liquidado",
            "counterparty": escape(transaction.counterparty), "description": escape(transaction.description),
            "category": escape(transaction.category), "amount": _money(transaction.amount),
            "payment_method": escape(transaction.payment_method or "A prazo"),
            "status": "PAGO" if transaction.status == "paid" else "EM ABERTO",
            "origin": "Loja / unidade educacional", "destination": "Destino fictício"}


def render_document_html(transaction: Transaction, company: Company, document_type: str, educational_number: str) -> str:
    if document_type not in DOCUMENT_CATALOG:
        raise ValueError(f"Tipo de documento não suportado: {document_type}")
    context = _context(transaction, company, educational_number)
    body = Template((TEMPLATE_DIR / f"{document_type}.html").read_text(encoding="utf-8")).substitute(context)
    colors = {"nota_fiscal": "#1f618d", "cupom_fiscal": "#424949", "boleto": "#154360",
              "recibo": "#196f3d", "comprovante": "#117864", "diaria": "#6c3483", "passagem": "#b03a2e"}
    return BASE_HTML.substitute(title=DOCUMENT_CATALOG[document_type]["label"], accent=colors[document_type],
                                company=context["company"], number=educational_number, body=body)


def generate_document(transaction: Transaction, company: Company, document_type: str) -> tuple[str, str]:
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    type_code = document_type.replace("_", "-").upper()[:12]
    educational_number = f"EDU-{transaction.day_id:05d}-{transaction.id:06d}-{type_code}"
    path = settings.documents_dir / f"{document_type}-{educational_number.lower()}.html"
    path.write_text(render_document_html(transaction, company, document_type, educational_number), encoding="utf-8")
    return educational_number, str(path.as_posix())


def template_catalog() -> list[dict[str, str]]:
    return [{"type": key, **value, "format": "text/html", "educational_only": True}
            for key, value in DOCUMENT_CATALOG.items()]
