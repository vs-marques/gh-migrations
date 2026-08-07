# GhostWritter Migrations (`gh-migrations`)

Migrations Postgres do GhostWritter — pacotes versionados **DSV / HMG / PRD** com rollback.

> Convenções: **`docs/MIGRATIONS_MASTER_REFERENCE.md`** (fonte de verdade). Tooling herdado de nyoka-migrations.

## Estrutura

```
gh-migrations/
├── migrations/
│   ├── core/
│   │   ├── desenvolvimento/
│   │   ├── homologação/
│   │   └── produção/
│   └── templates/
├── scripts/          # deployer + GUI (Streamlit)
├── docs/MIGRATIONS_MASTER_REFERENCE.md
├── config.env.example
└── requirements.txt
```

## Bootstrap DSV (ordem)

| # | Pacote | Schema |
|---|--------|--------|
| 1 | `PKG_DSV_V1_00001_SUPERADMIN` | superadmin |
| 2 | `PKG_DSV_V1_00002_CORE` | core (users, companies PF/PJ, workspaces) |
| 3 | `PKG_DSV_V1_00003_SECURITY` | security (RBAC, sessions, audit) |
| 4 | `PKG_DSV_V1_00004_PLATFORM` | platform (obra) |

Path: `migrations/core/desenvolvimento/2026/Agosto/07.08.2026/`

## Naming

`PKG_{DSV|HMG|PRD}_V1_{NNNN}_{SCHEMA}`  
Arquivos: `[NUMERO]-[SCHEMA]-[AÇÃO].sql` · Rollback: `rollback/9[NUMERO]-…`

## Setup

```bash
cd gh-migrations
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
cp config.env.example .env
```

```bash
streamlit run scripts/migration_gui.py
# ou
python scripts/migration_deployer_python.py list desenvolvimento
```

## Relacionados

- Hub: [`gh-docs`](https://github.com/vs-marques/gh-docs)
- Infra DB: `gh-infra`
