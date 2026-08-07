# Changelog — gh-migrations

> Migrações de banco GhostWritter — pacotes DSV/HMG/PRD com rollback.

Baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).  
Convenção: ver `gh-docs/docs/CHANGELOG_CONVENTION.md`.

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
