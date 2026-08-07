# Changelog — gh-migrations

> Migrações de banco GhostWritter — pacotes DSV/HMG/PRD com rollback.

Baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).  
Convenção: ver `gh-docs/docs/CHANGELOG_CONVENTION.md`.

---

## [0.2.0.202608.0] — 2026-08-07

**Autor:** Victor · **Resumo:** estrutura inicial de schemas/tabelas + referência de migrations GhostWritter.

### Added

- `docs/MIGRATIONS_MASTER_REFERENCE.md` adaptado para GhostWritter (padrão Nyoka).
- `PKG_DSV_V1_00001_SUPERADMIN` — controle de migrations + `email_templates`.
- `PKG_DSV_V1_00002_CORE` — users, companies (PF/PJ), workspaces, members, AI config.
- `PKG_DSV_V1_00003_SECURITY` — RBAC, sessions, API keys, audit.
- `PKG_DSV_V1_00004_PLATFORM` — projects, catalog, sparks, narrative, mural, feed.

### Notes

- Ordem: SUPERADMIN → CORE → SECURITY → PLATFORM.
- Path: `migrations/core/desenvolvimento/2026/Agosto/07.08.2026/`.

---

## [0.1.0.202608.0] — 2026-08-07

**Autor:** Victor · **Resumo:** bootstrap do repo de migrations (estrutura Nyoka, sem pacotes de domínio Nyoka).

### Added

- Tooling: `scripts/migration_deployer_python.py`, `migration_gui.py`, `requirements.txt`.
- Árvore vazia `migrations/core/{desenvolvimento,homologação,produção}/`.
- Template `migrations/templates/PKG_DSV_V1_00001_BOOTSTRAP/`.
- `docs/MIGRATIONS_MASTER_REFERENCE.md` (origem Nyoka — adaptar).

### Notes

- Primeiro pacote real de schema GhostWritter ainda não aplicado.
- `config.env.example` aponta para DBs `ghostwritter_*`.
