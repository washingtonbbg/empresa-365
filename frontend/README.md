# Painel do Professor — Empresa 365

Interface web para o professor gerar e acompanhar dias simulados da Loja Primavera.

## Requisitos

- Node.js 22.13 ou superior;
- pnpm 11;
- API FastAPI do Empresa 365 executando em `http://127.0.0.1:8000`.

## Execução

```powershell
pnpm install
pnpm run dev
```

Acesse `http://localhost:3000`.

## Validação

```powershell
pnpm run build
pnpm test
```

## Funcionalidades

- escolha da data da atividade;
- geração de seis movimentações do dia;
- indicadores de saldo, entradas e saídas;
- tabela de movimentações e classificações;
- acesso aos documentos HTML simulados;
- observações pedagógicas e sazonalidade;
- link para o relatório financeiro da API.

O projeto mantém a estrutura compatível com OpenAI Sites para uma etapa futura de hospedagem. A publicação integral depende de disponibilizar também a API FastAPI em uma URL acessível pelo frontend.
