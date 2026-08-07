# MIGRATIONS MASTER REFERENCE — GhostWritter (`gh-migrations`)

## VISÃO GERAL

Este é o **ARQUIVO ÚNICO DE REFERÊNCIA** para todas as migrações do **GhostWritter**. **SEMPRE** consulte este arquivo antes de criar qualquer migration.

Origem: adaptado de `nyoka-migrations/docs/MIGRATIONS_MASTER_REFERENCE.md`, com schemas e trilhas do domínio literário.

---

## Bancos de destino e trilhas (GH)

| ID | Destino típico | Pasta de migrations | Observação |
|----|-----------------|---------------------|------------|
| **GH** | Banco transacional principal GhostWritter (schemas `core`, `security`, `platform`, `superadmin`) | `migrations/core/{desenvolvimento,homologação,produção}/` | Identificador **GH** / trilha **core** em runbooks e cabeçalhos quando a execução for no cluster principal. |

**Regra:** o nome físico do pacote continua no padrão `PKG_{ENV}_...`. Mencionar **GH** no cabeçalho da migration ou no README remove ambiguidade de qual `DATABASE_URL` usar.

> Trilha `geography/` / sufixo `GE` **não** fazem parte do MVP GhostWritter. Não criar pasta `migrations/geography/` até haver necessidade explícita.

---

## REGRAS FUNDAMENTAIS

### 1. CONSULTA OBRIGATÓRIA
- **ANTES** de criar qualquer migration, **LEIA** este arquivo completo
- **NUNCA** crie migrations sem seguir os padrões estabelecidos
- **SEMPRE** valide sua migration com o modelo de validação

### 2. ESTRUTURA OBRIGATÓRIA
Toda migration **DEVE** ter:
- Arquivo(s) de execução separados por schemas/afinidades/dependências
- Arquivo(s) de rollback correspondentes
- README de execução com documentação completa
- Validações pós-execução automáticas
- Registro obrigatório na tabela de histórico de migrations

---

## ESTRUTURA DE MIGRATIONS

### Formato de Pacotes
```
PKG_{ENV}_V{MAJOR}_{MINOR}_{SCHEMA}
```

**Exemplos:**
- `PKG_DSV_V1_00001_SUPERADMIN` — Desenvolvimento V1, versão 00001, schema SUPERADMIN
- `PKG_DSV_V1_00002_CORE` — Desenvolvimento V1, versão 00002, schema CORE
- `PKG_HMG_V1_00002_CORE` — Homologação V1, versão 00002, schema CORE
- `PKG_PRD_V1_00002_CORE` — Produção V1, versão 00002, schema CORE

**Regra:** o nome do schema no pacote deve ser o **schema principal afetado** pela migration.

### Estrutura de Diretórios
```
migrations/
└── core/                       # Trilha GH (banco transacional principal)
    ├── desenvolvimento/
    │   └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_DSV_V1_.../
    ├── homologação/
    │   └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_HMG_V1_.../
    └── produção/
        └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_PRD_V1_.../
            ├── [NUMERO]-[SCHEMA]-[AÇÃO].sql              # Execução
            ├── rollback/                                 # Pasta de rollbacks
            │   └── 9[NUMERO]-[SCHEMA]-[AÇÃO].sql        # Rollback (inicia com 9)
            └── README.md                                 # Documentação
```

**Regra:** a raiz `migrations/` contém **somente** `core/` (MVP). Não criar `migrations/desenvolvimento/` (flat) na raiz.

**Nota sobre estrutura com anos:**
- **Quando usar `[Ano]/[Mês]/`**: quando há migrations de múltiplos anos
- **Quando usar apenas `[Mês]/`**: quando todas as migrations são do mesmo ano
- **Exemplo**: `core/desenvolvimento/2026/Agosto/07.08.2026/`

**Nota:** a pasta `rollback/` é obrigatória. Rollbacks: mesma numeração do arquivo de execução, iniciando com `9` (ex: `01-CORE-CRE.sql` → `rollback/91-CORE-CRE.sql`).

---

## PADRÕES DE NOMENCLATURA

### Arquivos SQL (padrão vigente)
```
[NUMERO]-[SCHEMA]-[AÇÃO].sql
```

**Formato:**
- `<Número do script>-<SCHEMA>-<AÇÃO>.sql`
- Rollbacks: `<9 + Número do script>-<SCHEMA>-<AÇÃO>.sql` (na pasta `rollback/`)

**Exemplos:**
- `01-CORE-CRE.sql` — Criação no schema CORE (arquivo 01)
- `02-SUPERADMIN-CRE.sql` — Criação no schema SUPERADMIN (arquivo 02)
- `03-PLATFORM-CRE.sql` — Criação no schema PLATFORM (arquivo 03)
- `04-SECURITY-CRE.sql` — Criação no schema SECURITY (arquivo 04)
- `05-SUPERADMIN-SEED.sql` — Seed no schema SUPERADMIN (arquivo 05)

**Rollbacks (pasta `rollback/`):**
- `rollback/91-CORE-CRE.sql`
- `rollback/92-SUPERADMIN-CRE.sql`
- `rollback/93-PLATFORM-CRE.sql`
- `rollback/94-SECURITY-CRE.sql`

**Regras:**
- Números sequenciais começando em `01`, `02`, `03`, etc.
- Schema em UPPERCASE (`CORE`, `SUPERADMIN`, `PLATFORM`, `SECURITY`)
- Ação em UPPERCASE (`CRE`, `FIX`, `DML`, `PRC`, `TRG`, `EXP`, `SEED`, etc.)
- Rollbacks na pasta `rollback/` com numeração iniciando em `9` (`91`, `92`, `93`, …)
- **Um arquivo = um schema** (se precisar criar em múltiplos schemas, use arquivos separados)

### Ações (AÇÃO)
| Código | Descrição | Uso |
|--------|-----------|-----|
| `CRE` | CREATE | Criação de tabelas, schemas, índices, constraints, ENUMs |
| `FIX` | FIX | Correções, ajustes, comentários |
| `DML` | DML | Inserts, updates, deletes, migração de dados |
| `PRC` | PROCEDURE | Procedures, functions, views |
| `TRG` | TRIGGER | Triggers, eventos |
| `EXP` | EXPANSION | Expansão de tabelas existentes (ALTER TABLE) |
| `SEED` | SEED | Seed de dados iniciais (INSERTs) |
| `MULTI` | Múltiplas operações | Combinação de tipos (evitar quando possível) |

---

## SCHEMAS DISPONÍVEIS (GhostWritter)

### Schemas principais
- **`SUPERADMIN`** — controle de migrations, `email_templates`
- **`CORE`** — users, companies (PF/PJ), workspaces, membros, config de IA
- **`SECURITY`** — RBAC, sessions, API keys, audit / traces
- **`PLATFORM`** — obra: projects, catalog, sparks, narrative, mural, feed
- **`public`** — apenas extensões Postgres (`pgcrypto`, etc.)

**Nota:** schemas em UPPERCASE nos **nomes de arquivos**. No SQL, usar lowercase (`core.users`).

### Regras de uso
- **NUNCA** referenciar schemas inexistentes
- **SEMPRE** usar o schema correto para cada operação
- **VERIFICAR** dependências entre schemas antes de criar

**Ordem canônica de bootstrap:**
1. `SUPERADMIN` → 2. `CORE` → 3. `SECURITY` → 4. `PLATFORM`

---

## MODELO DE VALIDAÇÃO OBRIGATÓRIO

### Registro obrigatório na tabela de histórico
**ANTES** de qualquer validação, **SEMPRE** registrar a migration em `superadmin.migrations`:

```sql
-- =============================================================================
-- REGISTRO OBRIGATÓRIO NA TABELA DE HISTÓRICO
-- =============================================================================

INSERT INTO superadmin.migrations (
    package_name,
    file_name,
    environment,
    notes,
    checksum
) VALUES (
    'PKG_{ENV}_V{MAJOR}_{MINOR}_{DESC}',
    '[NUMERO]-[SCHEMA]-[AÇÃO].sql',
    '[desenvolvimento/homologacao/producao]',
    '[DESCRIÇÃO_DETALHADA_DA_MIGRATION]',
    encode(sha256('[NOME_DO_PACOTE]'::bytea), 'hex')
);
```

**ATENÇÃO — CAMPOS OBRIGATÓRIOS:**
- **NUNCA** incluir `created_at` ou `execution_date` no INSERT (defaults da tabela)
- **SEMPRE** usar apenas: `package_name`, `file_name`, `environment`, `notes`, `checksum`
- **VERIFICAR** estrutura: `\d superadmin.migrations`

### PROBLEMAS COMUNS E SOLUÇÕES

#### 1. Campos inexistentes
**Problema:** `column "created_at" of relation "migrations" does not exist` (em INSERT explícito indevido)  
**Solução:** usar apenas os campos listados acima

#### 2. Sintaxe / arity de `log_migration_step`
**Problema:** parâmetros incorretos  
**Solução:** **somente 3 parâmetros:** `(package_name, level, message)`

```sql
-- ERRADO — 4 parâmetros
SELECT superadmin.log_migration_step(
    'PKG_DSV_V1_00003_SECURITY',
    '01-SECURITY-CRE.sql',
    'INFO',
    'Mensagem'
);

-- CORRETO — 3 parâmetros
SELECT superadmin.log_migration_step(
    'PKG_DSV_V1_00003_SECURITY',
    'INFO',
    'Mensagem'
);
```

#### 3. Query em `migration_logs`
**Problema:** `column "package_name" does not exist`  
**Solução:** sempre JOIN com `migrations`

```sql
SELECT COUNT(*) FROM superadmin.migration_logs ml
JOIN superadmin.migrations m ON ml.migration_id = m.id
WHERE m.package_name = 'PKG_DSV_V1_00003_SECURITY';
```

#### 4. Constraint de environment
**Problema:** acentos em `environment`  
**Solução:** sem acento

```sql
-- ERRADO
environment = 'homologação'
-- CORRETO
environment = 'homologacao'
```

Valores aceitos na prática: `desenvolvimento`, `homologacao`, `producao`.

#### 5. ON CONFLICT sem constraint
**Problema:** `there is no unique or exclusion constraint matching the ON CONFLICT specification`  
**Solução:** verificar constraints antes de usar `ON CONFLICT`

### Campo Status para auditoria
Valores possíveis em `superadmin.migrations.status`:
- `success` — aplicada com sucesso
- `rolled_back` — revertida via rollback
- `failed` — falhou
- `retry_pending` — aguardando re-execução
- `pending` — registrada, ainda não concluída (default do bootstrap)

**IMPORTANTE:**
- Rollback **DEVE** atualizar status para `rolled_back`
- Re-execução deve criar novo pacote `PKG_XXX_FIX` (não reutilizar numeração)

### Spool de logs locais
**OBRIGATÓRIO** — criar arquivo de log local:

```sql
\o migration_[PACOTE]_[DATA].log

SELECT 'MIGRATION INICIADA: ' || '[NOME_DO_PACOTE]' || ' - ' || NOW() as log_entry;

-- [EXECUÇÃO]

SELECT 'MIGRATION CONCLUÍDA: ' || '[NOME_DO_PACOTE]' || ' - ' || NOW() as log_entry;

\o
```

### Registro obrigatório em `migration_logs`
Durante a execução, usar `superadmin.log_migration_step(package, level, message)`.

### Estrutura base — validação final
```sql
DO $$
DECLARE
    v_count INTEGER;
    v_success_count INTEGER := 0;
    v_total_checks INTEGER := 0;
BEGIN
    -- [VERIFICAÇÕES ESPECÍFICAS]

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migration_logs ml
    JOIN superadmin.migrations m ON ml.migration_id = m.id
    WHERE m.package_name = 'PKG_{ENV}_V{MAJOR}_{MINOR}_{DESC}';

    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Logs registrados: % entradas', v_count;
    ELSE
        RAISE NOTICE 'FALHA - Nenhum log registrado na migration_logs';
    END IF;

    RAISE NOTICE 'RESUMO: % / %', v_success_count, v_total_checks;

    IF v_success_count = v_total_checks THEN
        RAISE NOTICE 'VALIDAÇÃO CONCLUÍDA COM SUCESSO';
    ELSE
        RAISE NOTICE 'VALIDAÇÃO COM FALHAS';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'ERRO CRÍTICO NA VALIDAÇÃO: %', SQLERRM;
END $$;
```

### Verificações obrigatórias
- [ ] Registro em `superadmin.migrations`
- [ ] Logs em `superadmin.migration_logs`
- [ ] Schemas / tabelas / índices / constraints / FKs / triggers / functions conforme o pacote

---

## PLANO DE AÇÃO PARA NOVAS MIGRATIONS

### 1. Análise prévia (OBRIGATÓRIO)
- [ ] Consultar este arquivo
- [ ] Identificar schema correto
- [ ] Definir objetivo (CRE/FIX/DML/PRC/TRG/EXP/SEED/MULTI)
- [ ] Verificar dependências entre schemas
- [ ] Verificar `\d superadmin.migrations` e `\d superadmin.migration_logs`

### 2. Criação da estrutura
- [ ] Diretório `migrations/core/{ambiente}/[Ano]/[Mês]/[DD.MM.YYYY]/PKG_.../`
- [ ] Nome do pacote `PKG_{ENV}_V{MAJOR}_{MINOR}_{SCHEMA}`

### 3. Criação dos arquivos
- [ ] Execução `[NUMERO]-[SCHEMA]-[AÇÃO].sql`
- [ ] Rollback `rollback/9[NUMERO]-[SCHEMA]-[AÇÃO].sql`
- [ ] README completo
- [ ] Validações + registro no histórico

### 4. Padrões de arquivos

#### Arquivo de execução
```sql
-- =====================================================
-- Migration: [NOME_DO_PACOTE]
-- Arquivo: [NUMERO]-[SCHEMA]-[AÇÃO].sql
-- Data: [DD/MM/YYYY]
-- Banco: GH (trilha core)
-- Descrição: [DESCRIÇÃO_CLARA]
-- =====================================================

-- =====================================================
-- OBJETIVO: [OBJETIVO_DETALHADO]
-- =====================================================

\o migration_[PACOTE]_[DATA].log
SELECT 'MIGRATION INICIADA: ' || '[NOME_DO_PACOTE]' || ' - ' || NOW() as log_entry;

-- [CÓDIGO]

-- =====================================================
-- REGISTRO OBRIGATÓRIO NA TABELA DE HISTÓRICO
-- =====================================================
-- [INSERT superadmin.migrations ...]

-- =====================================================
-- VALIDAÇÃO FINAL
-- =====================================================
-- [BLOCO DO $$]

SELECT 'MIGRATION CONCLUÍDA: ' || '[NOME_DO_PACOTE]' || ' - ' || NOW() as log_entry;
\o

-- =====================================================
-- Status: Migration aplicada com sucesso
-- =====================================================
```

#### Arquivo de rollback (`rollback/`)
```sql
-- =====================================================
-- Rollback: [NOME_DO_PACOTE]
-- Arquivo: rollback/9[NUMERO]-[SCHEMA]-[AÇÃO].sql
-- Data: [DD/MM/YYYY]
-- Descrição: Reversão de [NUMERO]-[SCHEMA]-[AÇÃO].sql
-- =====================================================

-- [CÓDIGO DE REVERSÃO]

UPDATE superadmin.migrations
SET
    status = 'rolled_back',
    updated_at = NOW(),
    notes = COALESCE(notes, '') || ' | ROLLBACK APLICADO'
WHERE package_name = '[NOME_DO_PACOTE]'
  AND file_name = '[NUMERO]-[SCHEMA]-[AÇÃO].sql'
  AND environment = '[AMBIENTE]';

-- =====================================================
-- Status: Rollback aplicado com sucesso
-- =====================================================
```

#### README de execução
```markdown
# Migration: [NOME_DO_PACOTE]

## Informações Gerais
- **Pacote**: …
- **Arquivo(s)**: …
- **Data**: …
- **Ambiente**: …
- **Banco**: GH (trilha core)
- **Versão**: …

## Objetivo
…

## Problema Identificado
…

## Solução Implementada
…

## Scripts Executados
…

## Dependências
…

## Observações Importantes
…

## Status
…

## Próximos Passos
…
```

---

## CHECKLIST OBRIGATÓRIO

### Antes de criar
- [ ] Consultou este arquivo?
- [ ] Identificou schema correto?
- [ ] Definiu objetivo?
- [ ] Verificou dependências?

### Durante criação
- [ ] Estrutura de diretórios correta?
- [ ] Nomenclatura `[NUMERO]-[SCHEMA]-[AÇÃO].sql`?
- [ ] Pasta `rollback/` + numeração `9…`?
- [ ] Cabeçalho completo + spool `\o`?
- [ ] `log_migration_step` com 3 parâmetros?
- [ ] JOIN correto em validações de logs?
- [ ] `environment` sem acento?
- [ ] Um arquivo = um schema?

### Após criação
- [ ] Rollback atualiza `status = 'rolled_back'`?
- [ ] README completo?
- [ ] Registro + logs + validação final?

---

## STATUS DAS MIGRATIONS (GhostWritter)

### Desenvolvimento
| Sequência | Pacote | Schema | Ação | Data | Status |
|-----------|--------|--------|------|------|--------|
| 00001 | `PKG_DSV_V1_00001_SUPERADMIN` | SUPERADMIN | CRE | 07.08.2026 | Pronto |
| 00002 | `PKG_DSV_V1_00002_CORE` | CORE | CRE | 07.08.2026 | Pronto |
| 00003 | `PKG_DSV_V1_00003_SECURITY` | SECURITY | CRE | 07.08.2026 | Pronto |
| 00004 | `PKG_DSV_V1_00004_PLATFORM` | PLATFORM | CRE | 07.08.2026 | Pronto |

---

## PROIBIÇÕES ABSOLUTAS

### NUNCA
- Criar migrations sem consultar este arquivo
- Referenciar schemas inexistentes
- Editar migrations consolidadas antigas
- Criar migrations sem validações / rollback / README
- Executar sem registrar no histórico
- Misturar múltiplos schemas no mesmo arquivo SQL

### SEMPRE
- Consultar este arquivo antes de criar
- Seguir padrões de nomenclatura e pasta
- Validar pós-execução
- Registrar histórico + logs
- Testar em desenvolvimento primeiro

---

## HISTÓRICO DE ATUALIZAÇÕES

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 07/08/2026 | Adaptação GhostWritter a partir da referência Nyoka; schemas SUPERADMIN/CORE/SECURITY/PLATFORM |

---

**Última atualização:** 07/08/2026  
**Status:** ARQUIVO CONSOLIDADO E ATIVO  
**Fonte de verdade:** este arquivo em `gh-migrations/docs/MIGRATIONS_MASTER_REFERENCE.md`
