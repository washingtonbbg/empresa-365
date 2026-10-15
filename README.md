# Empresa 365

Sistema educacional para simulação da rotina administrativa e financeira de empresas fictícias, voltado ao curso Técnico em Administração.

## Objetivo

Permitir a geração gradual de dias simulados de operação empresarial. A cada dia, os estudantes recebem movimentações e documentos para interpretar, classificar e registrar em planilhas de fluxo de caixa, contas a pagar, contas a receber, mini DRE e painel gerencial.

## Público-alvo

Professores e estudantes do Ensino Médio Técnico em Administração, especialmente nas disciplinas de Finanças, Gestão, Informática, Comunicação Profissional, Cálculos e Prática Profissional.

## Funcionalidades

- Cadastro e listagem de empresas fictícias;
- cenários mensais ou anuais, com semente para geração reproduzível;
- geração de exatamente um dia por chamada da API;
- receitas, despesas, operações à vista/a prazo e status em aberto/pago;
- sete documentos HTML imprimíveis: nota fiscal, cupom, boleto, recibo, comprovante, diária e passagem;
- fluxo de caixa, mini DRE, contas a pagar e contas a receber;
- exportação de movimentações em CSV e XLSX;
- documentação interativa automática (Swagger e ReDoc);
- testes automatizados dos principais fluxos.

## Tecnologias

- Python 3.11 ou superior;
- FastAPI e Uvicorn;
- SQLite e SQLAlchemy;
- Pydantic para contratos e validação;
- openpyxl para arquivos XLSX;
- módulo `csv` nativo do Python para arquivos CSV;
- HTML e CSS para documentos imprimíveis.

## Status

Projeto em desenvolvimento incremental. A base funcional do backend, o cenário Loja Primavera, continuidade entre dias, contas a pagar/receber, relatórios, exportações e os sete templates documentais já estão implementados e cobertos por testes automatizados.

## Continuidade financeira e versionamento

Cada dia persiste `opening_balance` e `closing_balance`. O fechamento do último dia torna-se a abertura do próximo, e a API rejeita geração retroativa para não invalidar dias posteriores. Cenários possuem `version` e `difficulty`; a versão participa da semente determinística junto com a data e a seed do cenário.

Vendas e compras a prazo criam registros próprios em contas a receber ou pagar. Em dias posteriores, títulos vencidos podem ser baixados de forma determinística, gerando `customer_receipt` ou `supplier_payment` sem repetir o efeito na DRE. Títulos não liquidados passam para `overdue` após o vencimento.

```text
GET  /api/v1/scenarios/{scenario_id}/accounts-payable
GET  /api/v1/scenarios/{scenario_id}/accounts-receivable
POST /api/v1/scenarios/{scenario_id}/days/{date}/publish
```

Dias nascem como `draft`. Ao publicar, tornam-se `published`, recebem data de publicação e o cenário passa a `active`. O `generation_hash` e o `generator_version` permitem identificar precisamente a regra usada na geração.

## Aviso de uso pedagógico

> Todos os dados são fictícios. Os documentos exibem **“SIMULAÇÃO EDUCACIONAL”** e **“USO EXCLUSIVO PARA FINS PEDAGÓGICOS”**, não possuem validade fiscal ou financeira e não incluem CPF, CNPJ, PIX ou código de barras funcional.

## Arquitetura

```text
app/
├── api/routes.py                 # endpoints HTTP
├── core/config.py                # configuração por ambiente
├── core/database.py              # engine e sessões SQLAlchemy
├── models/entities.py            # entidades persistidas
├── schemas/                      # contratos Pydantic
├── services/
│   ├── transaction_generator.py  # fatos financeiros reproduzíveis
│   ├── document_generator.py     # documentos pedagógicos em HTML
│   ├── simulation_service.py     # orquestração do dia
│   ├── report_service.py         # cálculos gerenciais
│   └── export_service.py         # CSV e XLSX
└── main.py                       # aplicação FastAPI
migrations/                       # evolução versionada do banco com Alembic
storage/                          # artefatos gerados (ignorados pelo Git)
tests/                            # testes de integração
README.md                         # documentação inicial e guia de uso
requirements.txt                 # dependências reproduzíveis
```

A separação entre rotas, regras, geradores e persistência facilita substituir SQLite por PostgreSQL, adicionar outros segmentos de empresa e versionar novos geradores nos próximos anos letivos.

## Instalação e execução

Requer Python 3.11 ou superior.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Acesse:

- Swagger: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Saúde da aplicação: <http://127.0.0.1:8000/health>

O Alembic cria ou atualiza o banco `empresa365.db`; as pastas de armazenamento são preparadas automaticamente pela aplicação. Execute `alembic upgrade head` sempre que receber uma nova versão do projeto.

## Fluxo de uso e exemplos

### Templates visuais de documentos

Os sete modelos ficam em `app/templates/documents/` e são combinados com um layout compartilhado pelo gerador. Os arquivos finais são HTML autocontidos, responsivos e preparados para impressão pelo navegador ou conversão futura em PDF/imagem.

```text
GET /api/v1/document-templates
```

Esse endpoint lista os tipos disponíveis e a finalidade de cada documento. Todos os layouts exibem data, valor, favorecido, descrição e forma de pagamento quando aplicáveis, além de marca d’água e aviso destacado de simulação. O boleto contém somente uma representação gráfica didática e uma linha explicitamente não digitável.

### Geração direta: Loja Primavera

Para a atividade pronta da empresa fictícia **Loja Primavera**, basta informar a data. A empresa e o cenário anual são preparados automaticamente:

`POST /api/v1/simulations/loja-primavera/days/generate`

```json
{
  "date": "2026-12-10",
  "transaction_count": 6,
  "seed": 2026
}
```

`transaction_count` é opcional e aceita de 3 a 8 movimentações. A resposta contém `opening_balance`, `closing_balance`, sazonalidade, observações pedagógicas e uma lista `movements`. Cada item é classificado como `entrada`, `saida`, `conta_a_pagar` ou `conta_a_receber`, possui documento coerente e campos planos adequados à futura exportação para planilha. Operações PIX são identificadas como simulação não funcional.

Exemplo resumido de movimentação:

```json
{
  "classification": "conta_a_receber",
  "classification_label": "Conta a receber",
  "category": "Vendas",
  "description": "Venda de artigos de vestuário #1",
  "amount": 325.50,
  "payment_method": "a prazo",
  "due_date": "2026-12-25",
  "status": "open",
  "document": {
    "type": "cupom_fiscal",
    "educational_number": "EDU-00001-000001",
    "disclaimer": "SIMULAÇÃO EDUCACIONAL"
  },
  "pedagogical_observation": "Não aumenta o caixa hoje; acompanhar prazo e risco de inadimplência."
}
```

### 1. Cadastrar uma empresa fictícia

`POST /api/v1/companies`

```json
{
  "name": "Empresa Modelo Educacional Ltda.",
  "trade_name": "Empresa Modelo",
  "educational_id": "EDU-EMP-001",
  "business_type": "Comércio e serviços",
  "city": "Cuiabá",
  "state": "MT",
  "opening_balance": 12000.00
}
```

O `educational_id` deve começar com `EDU-`; ele substitui qualquer cadastro fiscal real.

### 2. Criar um cenário

`POST /api/v1/scenarios`

```json
{
  "company_id": 1,
  "name": "Ano letivo 2026",
  "period_type": "annual",
  "start_date": "2026-01-01",
  "seed": 365
}
```

Use `monthly` ou `annual`. A data é normalizada para o primeiro dia do mês/ano e a API calcula o encerramento. A mesma semente, data e quantidade produzem o mesmo conjunto didático.

### 3. Gerar um dia

`POST /api/v1/scenarios/1/days/generate`

```json
{
  "simulation_date": "2026-03-16",
  "transaction_count": 4
}
```

`transaction_count` é opcional (1 a 20). Sem ele, são criadas de 3 a 7 movimentações. O mesmo dia não pode ser gerado duas vezes no mesmo cenário.

Resposta resumida:

```json
{
  "id": 1,
  "scenario_id": 1,
  "simulation_date": "2026-03-16",
  "summary": "Rotina simulada com 4 movimentações administrativas e financeiras.",
  "transactions": [
    {
      "id": 1,
      "transaction_type": "income",
      "category": "Vendas",
      "description": "Venda de mercadorias #1",
      "counterparty": "Cliente Educacional Alfa",
      "amount": 1480.25,
      "issue_date": "2026-03-16",
      "due_date": "2026-03-31",
      "payment_date": null,
      "status": "open",
      "payment_method": null,
      "documents": [{
        "id": 1,
        "document_type": "nota_fiscal",
        "educational_number": "EDU-00001-000001",
        "file_path": "storage/documents/nota_fiscal-edu-00001-000001.html",
        "disclaimer": "SIMULAÇÃO EDUCACIONAL"
      }]
    }
  ]
}
```

### 4. Consultar relatórios e baixar dados

```text
GET /api/v1/scenarios/1/reports
GET /api/v1/scenarios/1/exports/csv
GET /api/v1/scenarios/1/exports/xlsx
GET /api/v1/scenarios/1/days/2026-03-16
```

No relatório, o fluxo de caixa considera apenas itens pagos; a mini DRE simplificada considera receitas e despesas emitidas (competência). Essa diferença é intencional e pode ser explorada em aula.

## Testes

```powershell
pytest -q
```

Os testes usam SQLite em memória e diretórios temporários; não alteram a base de desenvolvimento.

## Roadmap sugerido

1. Autenticação e perfis de professor/aluno/turma;
2. modelos de cenário por segmento e nível de dificuldade;
3. calendário com eventos sazonais, folha e tributos simulados;
4. liquidação posterior de títulos e conciliação bancária didática;
5. documentos em PDF, anexos e pacote diário para distribuição;
6. rubricas de avaliação e comparação com planilhas entregues;
7. dashboard web e importação de respostas dos alunos;
8. PostgreSQL, migrações Alembic, filas de tarefas e armazenamento de objetos;
9. versionamento dos geradores (`2026`, `2027`...) para preservar turmas históricas.

## Cuidados de evolução

- Nunca introduza geradores de CPF/CNPJ/PIX ou linhas digitáveis válidas.
- Mantenha o aviso pedagógico em toda nova saída visual ou exportação.
- Versione alterações que mudem os resultados de uma mesma semente.
- Use migrações antes de alterar modelos em ambientes com dados de turmas.
- Trate os valores como material de exercício, nunca como orientação contábil ou fiscal.
