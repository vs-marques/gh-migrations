# GhostWritter Migrations (`gh-migrations`)

Migrations Postgres do GhostWritter — pacotes versionados **DSV / HMG / PRD** com rollback.

> Tooling e convenções herdados de **nyoka-migrations**. Pacotes SQL da Nyoka **não** foram trazidos — só a estrutura.

## Estrutura

```
gh-migrations/
├── migrations/
│   ├── core/
│   │   ├── desenvolvimento/
│   │   ├── homologação/
│   │   └── produção/
│   └── templates/
│       └── PKG_DSV_V1_00001_BOOTSTRAP/
├── scripts/          # deployer + GUI (Streamlit)
├── docs/             # master reference (adaptar nomes)
├── config.env.example
└── requirements.txt
```

## Naming de pacote

`PKG_{DSV|HMG|PRD}_V1_{NNNN}_{DOMINIO}`

Ex.: `PKG_DSV_V1_00001_BOOTSTRAP`

Pasta tipica:

`migrations/core/desenvolvimento/2026/Agosto/07.08.2026/PKG_DSV_V1_00001_BOOTSTRAP/`

## Setup

```bash
cd gh-migrations
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
cp config.env.example .env   # ajustar hosts/DB ghostwritter
```

```bash
streamlit run scripts/migration_gui.py
# ou
python scripts/migration_deployer_python.py list desenvolvimento
```

## Relacionados

- Hub: [`gh-docs`](https://github.com/vs-marques/gh-docs)
- Infra DB: `gh-infra`
