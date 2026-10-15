from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import AccountPayable, AccountReceivable, Company, Scenario, SimulationDay, Transaction
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.scenario import DayGenerateRequest, DayRead, PrimaveraDayRequest, ScenarioCreate, ScenarioRead
from app.services.export_service import export_csv, export_xlsx
from app.services.document_generator import template_catalog
from app.services.report_service import build_reports, scenario_transactions
from app.services.primavera_service import generate_primavera_day
from app.services.simulation_service import create_simulated_day, scenario_end

router = APIRouter(prefix="/api/v1")


@router.get("/document-templates", tags=["Documentos simulados"])
def list_document_templates():
    """Lista os modelos HTML disponíveis e sua finalidade pedagógica."""
    return {"templates": template_catalog(), "disclaimer": "SIMULAÇÃO EDUCACIONAL"}


def get_scenario_or_404(db: Session, scenario_id: int) -> Scenario:
    scenario = db.scalar(select(Scenario).options(selectinload(Scenario.company)).where(Scenario.id == scenario_id))
    if not scenario:
        raise HTTPException(404, "Cenário não encontrado.")
    return scenario


@router.post("/companies", response_model=CompanyRead, status_code=201, tags=["Empresas"])
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    values = payload.model_dump()
    values["state"] = payload.state.upper()
    company = Company(**values)
    db.add(company)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "O ID educacional já está cadastrado.")
    db.refresh(company)
    return company


@router.get("/companies", response_model=list[CompanyRead], tags=["Empresas"])
def list_companies(db: Session = Depends(get_db)):
    return list(db.scalars(select(Company).order_by(Company.name)))


@router.post("/scenarios", response_model=ScenarioRead, status_code=201, tags=["Cenários"])
def create_scenario(payload: ScenarioCreate, db: Session = Depends(get_db)):
    if not db.get(Company, payload.company_id):
        raise HTTPException(404, "Empresa não encontrada.")
    start = payload.start_date
    # Cenários didáticos sempre começam no primeiro dia do mês/ano escolhido.
    normalized_start = start.replace(month=1, day=1) if payload.period_type == "annual" else start.replace(day=1)
    scenario = Scenario(**payload.model_dump(exclude={"start_date"}), start_date=normalized_start,
                        end_date=scenario_end(normalized_start, payload.period_type))
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("/scenarios", response_model=list[ScenarioRead], tags=["Cenários"])
def list_scenarios(db: Session = Depends(get_db)):
    return list(db.scalars(select(Scenario).order_by(Scenario.created_at.desc())))


@router.post("/scenarios/{scenario_id}/days/generate", response_model=DayRead, status_code=201, tags=["Simulação diária"])
def generate_day(scenario_id: int, payload: DayGenerateRequest, db: Session = Depends(get_db)):
    return create_simulated_day(db, get_scenario_or_404(db, scenario_id), payload.simulation_date, payload.transaction_count)


@router.post("/simulations/loja-primavera/days/generate", status_code=201, tags=["Loja Primavera"])
def generate_primavera(payload: PrimaveraDayRequest, db: Session = Depends(get_db)):
    """Gera um dia completo e tabularizável da empresa didática Loja Primavera."""
    return generate_primavera_day(db, payload.date, payload.transaction_count, payload.seed)


@router.get("/scenarios/{scenario_id}/days/{simulation_date}", response_model=DayRead, tags=["Simulação diária"])
def read_day(scenario_id: int, simulation_date: str, db: Session = Depends(get_db)):
    day = db.scalar(select(SimulationDay).options(
        selectinload(SimulationDay.transactions).selectinload(Transaction.documents)
    ).where(SimulationDay.scenario_id == scenario_id, SimulationDay.simulation_date == simulation_date))
    if not day:
        raise HTTPException(404, "Dia simulado não encontrado.")
    return day


@router.post("/scenarios/{scenario_id}/days/{simulation_date}/publish", response_model=DayRead, tags=["Simulação diária"])
def publish_day(scenario_id: int, simulation_date: str, db: Session = Depends(get_db)):
    from app.models.entities import utc_now
    day = db.scalar(select(SimulationDay).options(
        selectinload(SimulationDay.transactions).selectinload(Transaction.documents)
    ).where(SimulationDay.scenario_id == scenario_id, SimulationDay.simulation_date == simulation_date))
    if not day:
        raise HTTPException(404, "Dia simulado não encontrado.")
    day.status = "published"
    day.published_at = utc_now()
    scenario = get_scenario_or_404(db, scenario_id)
    if scenario.status == "draft":
        scenario.status = "active"
    db.commit()
    return day


@router.get("/scenarios/{scenario_id}/accounts-payable", tags=["Contas"])
def accounts_payable(scenario_id: int, db: Session = Depends(get_db)):
    get_scenario_or_404(db, scenario_id)
    accounts = db.scalars(select(AccountPayable).where(AccountPayable.scenario_id == scenario_id)
                          .order_by(AccountPayable.due_date)).all()
    return [{"id": a.id, "source_transaction_id": a.source_transaction_id, "counterparty": a.supplier_name,
             "description": a.description, "original_amount": float(a.original_amount),
             "outstanding_amount": float(a.outstanding_amount), "issue_date": a.issue_date,
             "due_date": a.due_date, "status": a.status, "settled_date": a.settled_date} for a in accounts]


@router.get("/scenarios/{scenario_id}/accounts-receivable", tags=["Contas"])
def accounts_receivable(scenario_id: int, db: Session = Depends(get_db)):
    get_scenario_or_404(db, scenario_id)
    accounts = db.scalars(select(AccountReceivable).where(AccountReceivable.scenario_id == scenario_id)
                          .order_by(AccountReceivable.due_date)).all()
    return [{"id": a.id, "source_transaction_id": a.source_transaction_id, "counterparty": a.customer_name,
             "description": a.description, "original_amount": float(a.original_amount),
             "outstanding_amount": float(a.outstanding_amount), "issue_date": a.issue_date,
             "due_date": a.due_date, "status": a.status, "settled_date": a.settled_date} for a in accounts]


@router.get("/scenarios/{scenario_id}/reports", tags=["Relatórios"])
def reports(scenario_id: int, db: Session = Depends(get_db)):
    return build_reports(db, get_scenario_or_404(db, scenario_id))


@router.get("/scenarios/{scenario_id}/exports/{file_format}", tags=["Exportações"])
def export(scenario_id: int, file_format: str, db: Session = Depends(get_db)):
    get_scenario_or_404(db, scenario_id)
    transactions = scenario_transactions(db, scenario_id)
    if file_format == "csv":
        path, media = export_csv(scenario_id, transactions), "text/csv"
    elif file_format == "xlsx":
        path, media = export_xlsx(scenario_id, transactions), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise HTTPException(422, "Formato aceito: csv ou xlsx.")
    return FileResponse(path, media_type=media, filename=path.name)
