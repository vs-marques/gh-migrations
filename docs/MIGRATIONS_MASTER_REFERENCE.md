# 🎯 MIGRATIONS MASTER REFERENCE - NYOKA

## 📋 **VISÃO GERAL**

Este é o **ARQUIVO ÚNICO DE REFERÊNCIA** para todas as migrações do sistema NYOKA. **SEMPRE** consulte este arquivo antes de criar qualquer migration para evitar "migrations cagadas".

---

## **Bancos de destino e trilhas (NY / GE)**

| ID | Destino típico | Pasta de migrations | Observação |
|----|-----------------|---------------------|------------|
| **NY** | Banco transacional principal Nyoka (schemas `core`, `tenants`, `real_estate`, `chat`, etc.) | `migrations/core/{desenvolvimento,homologação,produção}/` | Identificador **NY** em runbooks, pipelines e comentários de pacote quando a execução for **explicitamente** no cluster principal. |
| **GE** | Banco dedicado a dados geográficos (PostGIS, `schema geography`, CEP Aberto, malhas) | `migrations/geography/{desenvolvimento,homologação,produção}/` | Identificador **GE** em comentários de SQL/README quando o `psql`/worker deve apontar para o **segundo** cluster (ex.: variável `GEOGRAPHY_DATABASE_URL` no backend). |

**Regra:** o nome físico do pacote continua no padrão `PKG_{ENV}_...`; o sufixo **GE** no código de ambiente (`PKG_DSV_GE_V1_*`) já indica trilha geography. Mencionar **NY** ou **GE** no cabeçalho da migration ou no README dispensa ambiguidade de qual `DATABASE_URL` usar na aplicação.

---

## 🚨 **REGRAS FUNDAMENTAIS**

### **1. CONSULTA OBRIGATÓRIA**
- **ANTES** de criar qualquer migration, **LEIA** este arquivo completo
- **NUNCA** crie migrations sem seguir os padrões estabelecidos
- **SEMPRE** valide sua migration com o modelo de validação

### **2. ESTRUTURA OBRIGATÓRIA**
Toda migration **DEVE** ter:
- ✅ **Arquivo(s) de execução** separados por schemas/afinidades/dependências
- ✅ **Arquivo(s) de rollback** correspondentes
- ✅ **README de execução** com documentação completa
- ✅ **Validações pós-execução** automáticas
- ✅ **Registro obrigatório** na tabela de histórico de migrations

---

## 🏗️ **ESTRUTURA DE MIGRATIONS**

### **Formato de Pacotes**
```
PKG_{ENV}_V{MAJOR}_{MINOR}_{SCHEMA}
```

**Exemplos:**
- `PKG_DSV_V1_00008_SUPERADMIN` - Desenvolvimento V1, versão 00008, schema SUPERADMIN
- `PKG_HMG_V1_00005_SUPERADMIN` - Homologação V1, versão 00005, schema SUPERADMIN
- `PKG_DSV_V1_00009_BATCH` - Desenvolvimento V1, versão 00009, schema BATCH
- `PKG_DSV_GE_V1_00002_GEOGRAPHY` - Desenvolvimento V1, trilha **GE**, schema GEOGRAPHY (pasta `migrations/geography/`)

**Regra**: O nome do schema no pacote deve ser o **schema principal afetado** pela migration.

### **Estrutura de Diretórios**
```
migrations/
├── core/                       # Trilha NY (banco transacional principal)
│   ├── desenvolvimento/
│   │   └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_DSV_V1_.../
│   ├── homologação/
│   │   └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_HMG_V1_.../
│   └── produção/
│       └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_PRD_V1_.../
└── geography/                  # Trilha GE (banco PostGIS / schema geography)
    ├── desenvolvimento/
    │   └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_DSV_GE_V1_.../
    ├── homologação/            # quando existir espelho HMG
    └── produção/
        └── [Ano]/[Mês]/[DD.MM.YYYY]/PKG_PRD_GE_V1_.../
            ├── [NUMERO]-[SCHEMA]-[AÇÃO].sql              # Execução
            ├── rollback/                                 # Pasta de rollbacks
            │   └── 9[NUMERO]-[SCHEMA]-[AÇÃO].sql        # Rollback (inicia com 9)
            └── README.md                                 # Documentação
```

**Regra:** a raiz `migrations/` contém **somente** `core/` e `geography/`. Não criar `migrations/desenvolvimento/` (flat) na raiz — pacotes NY ficam sempre em `migrations/core/{ambiente}/`.

**Nota sobre estrutura com anos:**
- **Quando usar `[Ano]/[Mês]/`**: Quando há migrations de múltiplos anos (ex: 2025, 2026, 2027)
- **Quando usar apenas `[Mês]/`**: Quando todas as migrations são do mesmo ano (ex: todas de 2025)
- **Exemplos**:
  - `core/desenvolvimento/2026/Janeiro/25.01.2026/` - Migration NY de 2026
  - `geography/desenvolvimento/2026/Maio/15.05.2026/` - Migration GE de 2026

**Nota**: A pasta `rollback/` é obrigatória para migrations com rollbacks. Os arquivos de rollback devem seguir a mesma numeração do arquivo de execução, mas iniciando com `9` (ex: `01-CORE-CRE.sql` → `rollback/91-CORE-CRE.sql`).

---

## 📝 **PADRÕES DE NOMENCLATURA**

### **Arquivos SQL (Novo Padrão - a partir de 06/11/2025)**
```
[NUMERO]-[SCHEMA]-[AÇÃO].sql
```

**Formato:**
- `<Número do script>-<SCHEMA>-<AÇÃO>.sql`
- Rollbacks: `<9 + Número do script>-<SCHEMA>-<AÇÃO>.sql` (na pasta `rollback/`)

**Exemplos:**
- `01-CORE-CRE.sql` - Criação no schema CORE (arquivo 01)
- `02-SUPERADMIN-CRE.sql` - Criação no schema SUPERADMIN (arquivo 02)
- `03-PLATFORM-CRE.sql` - Criação no schema PLATFORM (arquivo 03)
- `04-SECURITY-CRE.sql` - Criação no schema SECURITY (arquivo 04)
- `05-SUPERADMIN-SEED.sql` - Seed de dados no schema SUPERADMIN (arquivo 05)

**Rollbacks (pasta `rollback/`):**
- `rollback/91-CORE-CRE.sql` - Rollback do arquivo 01
- `rollback/92-SUPERADMIN-CRE.sql` - Rollback do arquivo 02
- `rollback/93-PLATFORM-CRE.sql` - Rollback do arquivo 03
- `rollback/94-SECURITY-CRE.sql` - Rollback do arquivo 04

**Regras:**
- ✅ Números sequenciais começando em `01`, `02`, `03`, etc.
- ✅ Schema em UPPERCASE (CORE, SUPERADMIN, PLATFORM, SECURITY, etc.)
- ✅ Ação em UPPERCASE (CRE, FIX, DML, PRC, TRG, EXP, SEED, etc.)
- ✅ Rollbacks na pasta `rollback/` com numeração iniciando em `9` (91, 92, 93, etc.)
- ✅ Um arquivo = um schema (se precisar criar em múltiplos schemas, use arquivos separados)

### **Ações (AÇÃO)**
| Código | Descrição | Uso |
|--------|-----------|-----|
| `CRE` | CREATE | Criação de tabelas, schemas, índices, constraints, ENUMs |
| `FIX` | FIX | Correções, ajustes, comentários, documentação |
| `DML` | DML | Inserts, updates, deletes, migração de dados |
| `PRC` | PROCEDURE | Procedures, functions, views |
| `TRG` | TRIGGER | Triggers, eventos |
| `EXP` | EXPANSION | Expansão de tabelas existentes (ALTER TABLE) |
| `SEED` | SEED | Seed de dados iniciais (INSERTs) |
| `MULTI` | Múltiplas operações | Combinação de diferentes tipos (evitar quando possível) |

---

## 🔒 **SCHEMAS DISPONÍVEIS**

### **Schemas Principais**
- **`CORE`** - Tabelas fundamentais do sistema (users, companies, etc.)
- **`BATCH`** - Operações em lote e importação
- **`FINANCE`** - Sistema financeiro
- **`REWARDS`** - Sistema de recompensas e cashback
- **`SECURITY`** - Autenticação e autorização (invitations, sessions, etc.)
- **`GEOGRAPHY`** - Dados geográficos
- **`SUPERADMIN`** - Controle e auditoria de migrations (email_templates, etc.)
- **`PLATFORM`** - Dados da plataforma (email_logs, etc.)
- **`ANALYTICS`** - Analytics e métricas
- **`NYOKA`** - Tabelas específicas do sistema Nyoka

**Nota**: Schemas devem ser escritos em UPPERCASE nos nomes de arquivos.

### **Regras de Uso**
- **NUNCA** referenciar schemas inexistentes
- **SEMPRE** usar o schema correto para cada operação
- **VERIFICAR** dependências entre schemas antes de criar

---

## 📊 **MODELO DE VALIDAÇÃO OBRIGATÓRIO**

### **Registro Obrigatório na Tabela de Histórico**
**ANTES** de qualquer validação, **SEMPRE** registrar a migration na tabela `superadmin.migrations`:

```sql
-- =============================================================================
-- REGISTRO OBRIGATÓRIO NA TABELA DE HISTÓRICO
-- =============================================================================

-- Inserir registro desta migration para controle
INSERT INTO superadmin.migrations (
    package_name, 
    file_name, 
    environment, 
    notes,
    checksum
) VALUES (
    'PKG_{ENV}_V{MAJOR}_{MINOR}_{DESC}',
    '[SCHEMA]-[NUMERO]-[OBJETIVO].sql',
    '[desenvolvimento/homologacao/producao]',
    '[DESCRIÇÃO_DETALHADA_DA_MIGRATION]',
    encode(sha256('[NOME_DO_PACOTE]'::bytea), 'hex')
);
```

**⚠️ ATENÇÃO - CAMPOS OBRIGATÓRIOS:**
- **NUNCA** usar `created_at` ou `execution_date` - a tabela não possui esses campos
- **SEMPRE** usar apenas: `package_name`, `file_name`, `environment`, `notes`, `checksum`
- **VERIFICAR** estrutura da tabela antes de inserir: `\d superadmin.migrations`

### **🚨 PROBLEMAS COMUNS E SOLUÇÕES**

#### **1. Erro de Campos Inexistentes**
**Problema**: `column "created_at" of relation "migrations" does not exist`
**Causa**: Tentativa de usar campos que não existem na tabela
**Solução**: Usar apenas os campos corretos listados acima

#### **2. Erro de Sintaxe JSON em log_migration_step**
**Problema**: `invalid input syntax for type json`
**Causa**: Função `log_migration_step` recebendo parâmetros incorretos
**Solução**: Usar apenas 3 parâmetros: `(package_name, level, message)`

```sql
-- ❌ ERRADO - 4 parâmetros
SELECT superadmin.log_migration_step(
    'PKG_DSV_V1_00018_SECURITY',
    'SECURITY-01-DML.sql',  -- ❌ Este parâmetro não existe
    'INFO',
    'Mensagem de log'
);

-- ✅ CORRETO - 3 parâmetros
SELECT superadmin.log_migration_step(
    'PKG_DSV_V1_00018_SECURITY',
    'INFO',
    'Mensagem de log'
);
```

#### **3. Erro de Query em migration_logs**
**Problema**: `column "package_name" does not exist` em migration_logs
**Causa**: Tentativa de usar campos diretos em migration_logs
**Solução**: Sempre fazer JOIN com migrations

```sql
-- ❌ ERRADO - Query direta
SELECT COUNT(*) FROM superadmin.migration_logs 
WHERE package_name = 'PKG_DSV_V1_00018_SECURITY';

-- ✅ CORRETO - JOIN com migrations
SELECT COUNT(*) FROM superadmin.migration_logs ml
JOIN superadmin.migrations m ON ml.migration_id = m.id
WHERE m.package_name = 'PKG_DSV_V1_00018_SECURITY';
```

#### **4. Erro de Constraint em Environment**
**Problema**: `violation of constraint migrations_environment_check`
**Causa**: Usar acentos em valores de environment
**Solução**: Usar valores sem acentos

```sql
-- ❌ ERRADO - Com acento
environment = 'homologação'

-- ✅ CORRETO - Sem acento
environment = 'homologacao'
```

#### **5. Erro de ON CONFLICT sem Constraint**
**Problema**: `there is no unique or exclusion constraint matching the ON CONFLICT specification`
**Causa**: Tentativa de usar ON CONFLICT em tabela sem constraint única
**Solução**: Verificar constraints antes de usar ON CONFLICT

```sql
-- ❌ ERRADO - ON CONFLICT sem constraint
INSERT INTO superadmin.super_email_templates (...)
VALUES (...)
ON CONFLICT (template_type, is_default) DO NOTHING;

-- ✅ CORRETO - Sem ON CONFLICT se não há constraint
INSERT INTO superadmin.super_email_templates (...)
VALUES (...);
```

### **Campo Status para Auditoria**
A tabela `superadmin.migrations` possui campo `status` para controle de auditoria:

**Valores possíveis:**
- `success` - Migration aplicada com sucesso (padrão)
- `rolled_back` - Migration revertida via rollback
- `failed` - Migration falhou na execução
- `retry_pending` - Migration aguardando re-execução

**IMPORTANTE:** 
- ✅ **Rollback DEVE** atualizar status para `rolled_back`
- ✅ **Re-execução** deve criar novo pacote `PKG_XXX_FIX` (não reutilizar numeração)
- ✅ **Auditoria completa** mantida para rastreabilidade

### **Spool de Logs Locais**
**OBRIGATÓRIO** para todas as migrations - criar arquivo de log local para debug e auditoria:

```sql
-- =============================================================================
-- SPOOL DE LOGS LOCAIS
-- =============================================================================

-- Iniciar spool de logs
\o migration_[PACOTE]_[DATA].log

-- Log de início
SELECT 'MIGRATION INICIADA: ' || '[NOME_DO_PACOTE]' || ' - ' || NOW() as log_entry;

-- [EXECUÇÃO DA MIGRATION]

-- Log de fim
SELECT 'MIGRATION CONCLUÍDA: ' || '[NOME_DO_PACOTE]' || ' - ' || NOW() as log_entry;

-- Parar spool
\o
```

**IMPORTANTE:** 
- ✅ **Worker de Deploy** - Executa migrations via `psql` com suporte a `\o`
- ✅ **Logs automáticos** - Spool criado automaticamente na pasta do pacote
- ✅ **Auditoria completa** - Logs locais + tabelas de histórico

**Estrutura de diretórios para logs:**
```
migrations/desenvolvimento/Setembro/20.09.2025/PKG_DSV_V1_00012_SUPERADMIN/
├── SUPERADMIN-05-PRC.sql
├── SUPERADMIN-05-PRC_ROLLBACK.sql
├── README_MIGRATION_RBAC_SEED.md
└── migration_PKG_DSV_V1_00012_SUPERADMIN_2025-09-20.log
```

**IMPORTANTE:**
- ✅ **SEMPRE** criar log local antes da execução
- ✅ **Incluir** timestamp de início e fim
- ✅ **Manter** logs para auditoria e debug
- ✅ **Organizar** por data e pacote

### **Registro Obrigatório na Tabela de Logs**
**DURANTE** a execução da migration, **SEMPRE** registrar logs detalhados na tabela `superadmin.migration_logs`:

```sql
-- =============================================================================
-- REGISTRO OBRIGATÓRIO NA TABELA DE LOGS
-- =============================================================================

-- Função auxiliar para registrar logs
CREATE OR REPLACE FUNCTION superadmin.log_migration_step(
    p_migration_package_name TEXT,
    p_log_level TEXT,
    p_message TEXT,
    p_additional_data JSONB DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_migration_id UUID;
BEGIN
    -- Buscar ID da migration
    SELECT id INTO v_migration_id 
    FROM superadmin.migrations 
    WHERE package_name = p_migration_package_name;
    
    -- Inserir log
    INSERT INTO superadmin.migration_logs (
        migration_id, 
        log_level, 
        message, 
        additional_data
    ) VALUES (
        v_migration_id, 
        p_log_level, 
        p_message, 
        p_additional_data
    );
END;
$$ LANGUAGE plpgsql;

-- Exemplos de uso durante a migration:
-- SELECT superadmin.log_migration_step('PKG_DSV_V1_00009_REWARDS', 'INFO', 'Iniciando backup das tabelas existentes');
-- SELECT superadmin.log_migration_step('PKG_DSV_V1_00009_REWARDS', 'INFO', 'Removendo relacionamentos antigos');
-- SELECT superadmin.log_migration_step('PKG_DSV_V1_00009_REWARDS', 'INFO', 'Criando novas tabelas refatoradas');
-- SELECT superadmin.log_migration_step('PKG_DSV_V1_00009_REWARDS', 'ERROR', 'Erro na criação da tabela rewards', '{"table": "rewards", "error": "duplicate key"}');
-- SELECT superadmin.log_migration_step('PKG_DSV_V1_00009_REWARDS', 'INFO', 'Migration concluída com sucesso');
```

### **Estrutura Base para Todas as Migrations**
```sql
-- =============================================================================
-- VALIDAÇÃO FINAL
-- =============================================================================

DO $$
DECLARE
    v_count INTEGER;
    v_success_count INTEGER := 0;
    v_total_checks INTEGER := 0;
BEGIN
    -- [VERIFICAÇÕES ESPECÍFICAS AQUI]
    
    -- Verificação obrigatória: Logs registrados
    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migration_logs ml
    JOIN superadmin.migrations m ON ml.migration_id = m.id
    WHERE m.package_name = 'PKG_{ENV}_V{MAJOR}_{MINOR}_{DESC}';
    
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE '✅ Logs registrados: % entradas', v_count;
    ELSE
        RAISE NOTICE '❌ FALHA - Nenhum log registrado na migration_logs';
    END IF;
    
    -- Resumo final
    RAISE NOTICE '📊 RESUMO DA VALIDAÇÃO:';
    RAISE NOTICE '   Verificações realizadas: %', v_total_checks;
    RAISE NOTICE '   Verificações com sucesso: %', v_success_count;
    RAISE NOTICE '   Verificações com falha: %', v_total_checks - v_success_count;
    
    IF v_success_count = v_total_checks THEN
        RAISE NOTICE '✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO TOTAL!';
    ELSE
        RAISE NOTICE '⚠️  VALIDAÇÃO CONCLUÍDA COM ALGUMAS FALHAS!';
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '❌ ERRO CRÍTICO NA VALIDAÇÃO: %', SQLERRM;
END $$;
```

### **Verificações Obrigatórias**
- [ ] **Registro**: Verificar se foi registrada na tabela de histórico
- [ ] **Logs**: Verificar se logs foram registrados na tabela migration_logs
- [ ] **Schemas**: Verificar criação de novos schemas
- [ ] **Tabelas**: Validar tabelas principais criadas
- [ ] **Campos**: Verificar colunas e alterações
- [ ] **Functions**: Contar rotinas criadas
- [ ] **Índices**: Validar estruturas de performance
- [ ] **Constraints**: Verificar integridade
- [ ] **Relacionamentos**: Validar foreign keys
- [ ] **Triggers**: Verificar automações

---

## 🚀 **PLANO DE AÇÃO PARA NOVAS MIGRATIONS**

### **1. Análise Prévia (OBRIGATÓRIO)**
- [ ] **Consultar** este arquivo de referência
- [ ] **Identificar** schema correto
- [ ] **Definir** objetivo (CRE/FIX/DML/PRC/TRG/EXP/MULTI)
- [ ] **Verificar** dependências entre schemas
- [ ] **Consultar** modelo de dados atual
- [ ] **Verificar** estrutura da tabela `superadmin.migrations`: `\d superadmin.migrations`
- [ ] **Verificar** estrutura da tabela `superadmin.migration_logs`: `\d superadmin.migration_logs`
- [ ] **Verificar** constraints das tabelas que serão modificadas
- [ ] **Testar** queries de validação antes de incluir na migration

### **2. Criação da Estrutura**
- [ ] **Criar** diretório seguindo padrão estabelecido
- [ ] **Definir** nome do pacote (PKG_{ENV}_V{MAJOR}_{MINOR}_{DESC})
- [ ] **Organizar** por ambiente (desenvolvimento/homologação)
- [ ] **Separar** por data (DD.MM.YYYY)

### **3. Criação dos Arquivos**
- [ ] **Arquivo de execução** principal
- [ ] **Arquivo de rollback** correspondente
- [ ] **README** com documentação completa
- [ ] **Validações** pós-execução
- [ ] **Registro na tabela de histórico** (superadmin.migrations)

### **4. Padrões de Arquivos**

#### **Arquivo de Execução**
```sql
-- =====================================================
-- Migration: [NOME_DO_PACOTE]
-- Arquivo: [NUMERO]-[SCHEMA]-[AÇÃO].sql
-- Data: [DD/MM/YYYY]
-- Descrição: [DESCRIÇÃO_CLARA]
-- =====================================================

-- =====================================================
-- OBJETIVO: [OBJETIVO_DETALHADO]
-- =====================================================

-- [CÓDIGO DA MIGRATION]

-- =====================================================
-- REGISTRO OBRIGATÓRIO NA TABELA DE HISTÓRICO
-- =====================================================

-- [REGISTRO_NA_TABELA_SUPERADMIN_MIGRATIONS]

-- =====================================================
-- VALIDAÇÃO FINAL
-- =====================================================

-- [BLOCO DE VALIDAÇÃO]

-- =====================================================
-- Status: ✅ Migration aplicada com sucesso
-- =====================================================
```

**Exemplo**: `01-CORE-CRE.sql`

#### **Arquivo de Rollback (pasta `rollback/`)**
```sql
-- =====================================================
-- Rollback: [NOME_DO_PACOTE]
-- Arquivo: rollback/9[NUMERO]-[SCHEMA]-[AÇÃO].sql
-- Data: [DD/MM/YYYY]
-- Descrição: Reversão da migration [NUMERO]-[SCHEMA]-[AÇÃO].sql
-- =====================================================

-- [CÓDIGO DE REVERSÃO]

-- =====================================================
-- ATUALIZAR STATUS DA MIGRATION PARA ROLLED_BACK
-- =====================================================

-- Marcar migration como rolled_back para auditoria
UPDATE superadmin.migrations 
SET 
    status = 'rolled_back',
    updated_at = NOW(),
    notes = notes || ' | ROLLBACK APLICADO'
WHERE package_name = '[NOME_DO_PACOTE]' 
  AND file_name = '[NUMERO]-[SCHEMA]-[AÇÃO].sql'
  AND environment = '[AMBIENTE]';

-- =====================================================
-- Status: ✅ Rollback aplicado com sucesso
-- =====================================================
```

**Exemplo**: `rollback/91-CORE-CRE.sql` (rollback de `01-CORE-CRE.sql`)

**⚠️ IMPORTANTE**: 
- Rollbacks sempre na pasta `rollback/`
- Numeração do rollback = `9` + número do arquivo original
- Ex: `01-CORE-CRE.sql` → `rollback/91-CORE-CRE.sql`
- Ex: `02-SUPERADMIN-CRE.sql` → `rollback/92-SUPERADMIN-CRE.sql`

#### **README de Execução**
```markdown
# 📋 Migration: [NOME_DO_PACOTE]

## 📊 **Informações Gerais**
- **Pacote**: [NOME_DO_PACOTE]
- **Arquivo**: [NOME_DO_ARQUIVO]
- **Data**: [DD/MM/YYYY]
- **Ambiente**: [Desenvolvimento/Homologação/Produção]
- **Versão**: [X.X]

## 🎯 **Objetivo**
[DESCRIÇÃO_DO_OBJETIVO]

## 🔍 **Problema Identificado**
[LISTA_DE_PROBLEMAS]

## ✅ **Solução Implementada**
[LISTA_DE_SOLUÇÕES]

## 📝 **Scripts Executados**
[LISTA_DE_SCRIPTS]

## 🔄 **Dependências**
[LISTA_DE_DEPENDÊNCIAS]

## ⚠️ **Observações Importantes**
[OBSERVAÇÕES]

## 📊 **Status**
[STATUS_ATUAL]

## 🚀 **Próximos Passos**
[PRÓXIMOS_PASSOS]
```

---

## 📋 **CHECKLIST OBRIGATÓRIO**

### **Antes de Criar**
- [ ] **Consultou** este arquivo de referência?
- [ ] **Identificou** schema correto?
- [ ] **Definiu** objetivo da migration?
- [ ] **Verificou** dependências?
- [ ] **Consultou** modelo de dados?

### **Durante Criação**
- [ ] **Usou** estrutura de diretórios correta?
- [ ] **Seguiu** nomenclatura exata? (`[NUMERO]-[SCHEMA]-[AÇÃO].sql`)
- [ ] **Criou** pasta `rollback/` para rollbacks?
- [ ] **Numerou** rollbacks começando com `9`? (`9[NUMERO]-[SCHEMA]-[AÇÃO].sql`)
- [ ] **Incluiu** cabeçalho completo?
- [ ] **Usou** transações?
- [ ] **Adicionou** comentários?
- [ ] **Incluiu** índices quando necessário?
- [ ] **Verificou** campos da tabela `superadmin.migrations` antes de inserir?
- [ ] **Usou** apenas 3 parâmetros em `log_migration_step`?
- [ ] **Fez** JOIN correto com `migration_logs`?
- [ ] **Evitou** acentos em valores de `environment`?
- [ ] **Verificou** constraints antes de usar `ON CONFLICT`?

### **Após Criação**
- [ ] **Criou** arquivo de rollback na pasta `rollback/`?
- [ ] **Numerou** rollback corretamente? (`9` + número do arquivo original)
- [ ] **Criou** README completo?
- [ ] **Incluiu** validações pós-execução?
- [ ] **Registrou** na tabela de histórico?
- [ ] **Incluiu** logs na migration_logs?
- [ ] **Configurou** spool de logs locais?
- [ ] **Testou** em ambiente de desenvolvimento?
- [ ] **Documentou** mudanças?

---

## 🔍 **EXEMPLOS DE IMPLEMENTAÇÃO**

### **Exemplo 1: Criação de Schema (Padrão Antigo)**
**Pacote**: `PKG_DSV_V1_00008_SUPERADMIN`
**Arquivo**: `SUPERADMIN-01-CRE.sql`
**Objetivo**: Criação do schema superadmin com tabelas de controle

### **Exemplo 2: Criação de Tabelas (Novo Padrão - a partir de 06/11/2025)**
**Pacote**: `PKG_DSV_V1_00025_SIGNUP`
**Arquivos**:
- `01-CORE-CRE.sql` - Criação de ENUMs e extensão de core.users
- `02-SUPERADMIN-CRE.sql` - Criação de superadmin.email_templates
- `03-PLATFORM-CRE.sql` - Criação de platform.email_logs
- `04-SECURITY-CRE.sql` - Criação de security.invitations
- `05-SUPERADMIN-SEED.sql` - Seed de templates de email
**Rollbacks** (pasta `rollback/`):
- `rollback/91-CORE-CRE.sql`
- `rollback/92-SUPERADMIN-CRE.sql`
- `rollback/93-PLATFORM-CRE.sql`
- `rollback/94-SECURITY-CRE.sql`
**Objetivo**: Sistema completo de signup

**Estrutura criada:**
- Schema `superadmin`
- Tabela `migrations`
- Tabela `migration_logs`
- Índices otimizados
- Constraints de integridade

**Registro obrigatório:**
- Migration registrada na tabela `superadmin.migrations`
- Logs de execução na tabela `superadmin.migration_logs`

### **Exemplo 3: Correção de Foreign Keys**
**Pacote**: `PKG_DSV_V1_00007_BATCH`
**Arquivo**: `01-BATCH-FIX.sql` (novo padrão) ou `BATCH-01-FIX.sql` (padrão antigo)
**Rollback**: `rollback/91-BATCH-FIX.sql`
**Objetivo**: Correção de foreign keys incorretas

**Correções aplicadas:**
- Foreign key `import_history.rule_set_id` → `batch.rule_sets.id`
- Foreign key `import_history.validation_rule_id` → `batch.validation_rules.id`

**Registro obrigatório:**
- Migration registrada na tabela `superadmin.migrations`
- Logs de execução na tabela `superadmin.migration_logs`

---

## 📊 **STATUS DAS MIGRATIONS ATUAIS**

### **Desenvolvimento**
| Sequência | Pacote | Schema | Ação | Data | Status |
|-----------|--------|--------|------|------|--------|
| 00007 | `PKG_DSV_V1_00007_BATCH` | BATCH | FIX | 22.08.2025 | ✅ Aplicada |
| 00008 | `PKG_DSV_V1_00008_SUPERADMIN` | SUPERADMIN | CRE | 22.08.2025 | ⏳ Pendente |

### **Homologação**
| Sequência | Pacote | Schema | Ação | Data | Status |
|-----------|--------|--------|------|------|--------|
| 00004 | `PKG_HMG_V1_00004_BATCH` | BATCH | FIX | 22.08.2025 | ⏳ Pendente |
| 00005 | `PKG_HMG_V1_00005_SUPERADMIN` | SUPERADMIN | CRE | 22.08.2025 | ⏳ Pendente |

---

## 🚨 **PROIBIÇÕES ABSOLUTAS**

### **1. NUNCA Faça**
- ❌ **Criar** migrations sem consultar este arquivo
- ❌ **Referenciar** schemas inexistentes
- ❌ **Editar** migrations consolidadas antigas
- ❌ **Criar** migrations sem validações
- ❌ **Esquecer** de criar arquivo de rollback
- ❌ **Pular** a criação do README
- ❌ **Executar** migrations sem registrar na tabela de histórico

### **2. SEMPRE Faça**
- ✅ **Consultar** este arquivo antes de criar
- ✅ **Seguir** padrões estabelecidos
- ✅ **Criar** validações pós-execução
- ✅ **Registrar** na tabela de histórico
- ✅ **Testar** em desenvolvimento primeiro
- ✅ **Documentar** todas as mudanças
- ✅ **Criar** rollback correspondente

---

## 📞 **SUPORTE E CONTATOS**

### **Equipe Responsável**
- **Desenvolvimento**: Implementação de migrations
- **DBA**: Validação de estruturas de banco
- **DevOps**: Integração com pipelines
- **QA**: Testes de validação

### **Contatos**
- **Email**: api@nyoka.com.br
- **Slack**: #migrations-nyoka

---

## 📅 **HISTÓRICO DE ATUALIZAÇÕES**

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 22/08/2025 | Criação inicial do arquivo consolidado |
| 1.1.0 | 22/08/2025 | Adicionado plano de ação obrigatório |
| 1.2.0 | 22/08/2025 | Incluído modelo de validação obrigatório |
| 1.3.0 | 22/08/2025 | Adicionado registro obrigatório na tabela de histórico |
| 1.4.0 | 22/09/2025 | Adicionada seção de problemas comuns e soluções |
| 1.6.0 | 17/05/2026 | Bancos NY/GE; árvore `migrations/geography/` no diagrama de diretórios |
| 1.5.0 | 22/09/2025 | Incluído checklist específico para evitar erros |

---

## ✅ **CONCLUSÃO**

Este arquivo é a **ÚNICA FONTE DE VERDADE** para todas as migrações do sistema NYOKA. **SEMPRE** consulte-o antes de criar qualquer migration para garantir:

1. **Consistência** com padrões estabelecidos
2. **Qualidade** das implementações
3. **Rastreabilidade** de todas as mudanças
4. **Segurança** na execução
5. **Facilidade** de manutenção

**🎯 LEMBRE-SE**: Consultar este arquivo não é opcional, é **OBRIGATÓRIO**!

---

**📅 Última atualização:** 17/05/2026  
**✅ Status:** ARQUIVO CONSOLIDADO E ATIVO  
**🚀 Próximo passo:** Implementar este padrão em todas as migrations futuras

