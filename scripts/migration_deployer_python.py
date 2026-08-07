#!/usr/bin/env python3
# Caminho: scripts/migration_deployer_python.py
# Descrição: Deploy automatizado de pacotes de migration (GH)
# Data: 2026-08-07
# Versão: 1.1.0
# Histórico de Modificações:
# - 2025-01-27: versão Nyoka / Pontua
# - 2026-08-07: v1.1.0 — modos full / lote / last / package + manifesto de deps

"""
GhostWritter Migration Deployer — conexão Python direta (psycopg2).

Modos CLI:
  full     — todos os pacotes pendentes (ordem NNNN)
  lote     — pacotes de uma data DD.MM.YYYY
  last     — maior NNNN pendente
  package  — pacote nominal (nome completo ou sufixo)
  list / test / deploy / dry-run — legado
"""

import argparse
import os
import sys
import psycopg2
import json
import datetime
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

class MigrationDeployerPython:
    def __init__(self, base_path: str = None):
        # Se base_path não for fornecido, usar o diretório pai do script (raiz do projeto)
        if base_path:
            self.base_path = Path(base_path)
        else:
            # scripts/migration_deployer_python.py -> scripts/ -> raiz do projeto
            self.base_path = Path(__file__).parent.parent
        
        # Preferir .env do repo; fallback env.local (legado Nyoka)
        env_dotenv = self.base_path / ".env"
        env_local = self.base_path / "env.local"
        if env_dotenv.exists():
            load_dotenv(env_dotenv, override=True)
        elif env_local.exists():
            load_dotenv(env_local, override=True)
        else:
            load_dotenv()
        
        self.migrations_path = self.base_path / "migrations"
        self.deps_manifest_path = self.base_path / "docs" / "deps.manifest.json"
        
        # Debug (desativado por padrão para evitar UnicodeEncodeError no console Windows)
        if os.environ.get("MIGRATION_DEPLOYER_DEBUG"):
            print(f"[Deployer] Base path: {self.base_path}")
            print(f"[Deployer] Migrations path: {self.migrations_path}")
            print(f"[Deployer] Migrations exists: {self.migrations_path.exists()}")
        
        # Configurações dos bancos via variáveis de ambiente
        self.db_configs = {
            'desenvolvimento': {
                'host': os.getenv('DB_DEV_HOST'),
                'port': int(os.getenv('DB_DEV_PORT', '5432')),
                'database': os.getenv('DB_DEV_DATABASE'),
                'user': os.getenv('DB_DEV_USER'),
                'password': os.getenv('DB_DEV_PASSWORD')
            },
            'homologação': {
                'host': os.getenv('DB_HMG_HOST'),
                'port': int(os.getenv('DB_HMG_PORT', '5432')),
                'database': os.getenv('DB_HMG_DATABASE'),
                'user': os.getenv('DB_HMG_USER'),
                'password': os.getenv('DB_HMG_PASSWORD')
            },
            'produção': {
                'host': os.getenv('DB_PRD_HOST'),
                'port': int(os.getenv('DB_PRD_PORT', '5432')),
                'database': os.getenv('DB_PRD_DATABASE'),
                'user': os.getenv('DB_PRD_USER'),
                'password': os.getenv('DB_PRD_PASSWORD')
            }
        }
    
    def test_connection(self, environment: str) -> Tuple[bool, str]:
        """Testa a conexão com o banco"""
        if environment not in self.db_configs:
            return False, f"ERR Ambiente '{environment}' não configurado"
            
        config = self.db_configs[environment]
        
        try:
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return True, f"OK Conexão OK: {version[:50]}..."
            
        except Exception as e:
            return False, f"ERR Erro de conexão: {str(e)}"
    
    def _normalize_foldername(self, name: str) -> str:
        """Normaliza nome de pasta para comparação (evita NFC/NFD no Windows)."""
        return unicodedata.normalize("NFC", name)
    
    def _env_to_slug(self, name: str) -> str:
        """Converte nome do ambiente para slug ASCII (homologação -> homologacao)."""
        n = unicodedata.normalize("NFD", name)
        return "".join(c for c in n if unicodedata.category(c) != "Mn")
    
    def _resolve_env_path(self, environment: str, track: str = "core") -> Optional[Path]:
        """Resolve o Path da pasta do ambiente (trilha core ou geography)."""
        candidates: List[Path] = []

        track_norm = (track or "core").strip().lower()
        if track_norm in {"core", "geography"}:
            candidates.append(self.migrations_path / track_norm / environment)

        # Compat legado: migrations/{ambiente} na raiz (pré-reorg core/geography)
        candidates.append(self.migrations_path / environment)

        slug = self._env_to_slug(environment)
        env_norm = self._normalize_foldername(environment)

        for direct in candidates:
            if direct.exists():
                return direct
            slug_path = direct.parent / slug if direct.parent != self.migrations_path else self.migrations_path / slug
            if slug_path.exists():
                return slug_path

        for base in (self.migrations_path / track_norm, self.migrations_path):
            if not base.exists():
                continue
            for d in base.iterdir():
                if not d.is_dir():
                    continue
                if self._normalize_foldername(d.name) == env_norm:
                    return d
                if self._env_to_slug(d.name) == slug:
                    return d
        return None
    
    def list_available_migrations(self, environment: str) -> List[Dict]:
        """Lista todas as migrations disponíveis para um ambiente"""
        env_path = self._resolve_env_path(environment)
        
        if not env_path or not env_path.exists():
            print(f"ERR Ambiente '{environment}' não encontrado em {self.migrations_path}")
            return []
            
        migrations = []
        
        # Buscar por diretórios de data (formato DD.MM.YYYY)
        # Suporta duas estruturas:
        # 1. Estrutura antiga: environment/mês/data/package
        # 2. Estrutura nova: environment/ano/mês/data/package
        for first_level_dir in env_path.iterdir():
            if not first_level_dir.is_dir():
                continue
                
            # Verificar se é um ano (4 dígitos numéricos) ou um mês
            if first_level_dir.name.isdigit() and len(first_level_dir.name) == 4:
                # Estrutura nova: environment/ano/mês/data/package
                for month_dir in first_level_dir.iterdir():
                    if month_dir.is_dir():
                        for date_dir in month_dir.iterdir():
                            if date_dir.is_dir() and self._is_date_directory(date_dir.name):
                                for package_dir in date_dir.iterdir():
                                    if package_dir.is_dir() and package_dir.name.startswith("PKG_"):
                                        migration_info = self._analyze_migration_package(package_dir)
                                        if migration_info:
                                            # Consultar status real no banco
                                            migration_info['status'] = self._get_migration_status(migration_info['package_name'], environment)
                                            migrations.append(migration_info)
            else:
                # Estrutura antiga: environment/mês/data/package
                for date_dir in first_level_dir.iterdir():
                    if date_dir.is_dir() and self._is_date_directory(date_dir.name):
                        for package_dir in date_dir.iterdir():
                            if package_dir.is_dir() and package_dir.name.startswith("PKG_"):
                                migration_info = self._analyze_migration_package(package_dir)
                                if migration_info:
                                    # Consultar status real no banco
                                    migration_info['status'] = self._get_migration_status(migration_info['package_name'], environment)
                                    migrations.append(migration_info)
                            
        # Ordenar por número de versão (extrair número do package_name)
        return sorted(migrations, key=lambda x: self._extract_version_number(x['package_name']))
    
    def _is_date_directory(self, dir_name: str) -> bool:
        """Verifica se o diretório é uma data no formato DD.MM.YYYY"""
        try:
            datetime.datetime.strptime(dir_name, "%d.%m.%Y")
            return True
        except ValueError:
            return False
    
    def _extract_version_number(self, package_name: str) -> int:
        """Extrai o número da versão do package_name para ordenação"""
        try:
            # Exemplo: PKG_DSV_V1_00012_SUPERADMIN -> extrair 00012
            # Exemplo: PKG_DSV_V1_00026_SIGNUP_FIX -> extrair 00026
            parts = package_name.split('_')
            if len(parts) >= 4:
                # parts[2] = "V1", parts[3] = "00026"
                version_num_str = parts[3]  # "00026"
                # Remover zeros à esquerda se necessário e converter para int
                return int(version_num_str)
            return 0
        except (ValueError, IndexError):
            return 0
    
    def _get_migration_status(self, package_name: str, environment: str) -> str:
        """Consulta o status real da migration no banco"""
        try:
            if environment not in self.db_configs:
                return 'unknown'
            
            # Mapear nome do ambiente para o formato do banco
            env_mapping = {
                'homologação': 'homologacao',  # Remove acento
                'desenvolvimento': 'desenvolvimento',
                'produção': 'producao'  # Remove acento
            }
            db_environment = env_mapping.get(environment, environment)
                
            config = self.db_configs[environment]
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            # Consultar se a migration foi aplicada
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM superadmin.migrations 
                WHERE package_name = %s AND environment = %s
                GROUP BY status
            """, (package_name, db_environment))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                status, count = result
                if count > 0:
                    # Pacotes GH registram INSERT com status=pending e muitas vezes
                    # nao fazem UPDATE final para completed — registro = ja aplicado.
                    st = (status or "").lower()
                    if st in ("completed", "success", "ok", "applied"):
                        return st
                    return "applied"
            else:
                return "pending"
                
        except Exception as e:
            # Se não conseguir conectar ou tabela não existir, retorna pending
            print(f"WARN Não foi possível consultar status no banco: {e}")
            return 'pending'
    
    def _analyze_migration_package(self, package_path: Path) -> Optional[Dict]:
        """Analisa um pacote de migration e extrai informações"""
        # Buscar arquivos SQL de execução (na raiz, excluindo pasta rollback)
        sql_files = [f for f in package_path.glob("*.sql") if f.is_file()]
        
        # Buscar arquivos de rollback na pasta rollback/ (novo padrão)
        rollback_dir = package_path / "rollback"
        rollback_files = []
        if rollback_dir.exists() and rollback_dir.is_dir():
            # Novo padrão: arquivos na pasta rollback/ começando com 9 (ex: 91-CORE-CRE.sql)
            rollback_files = [f for f in rollback_dir.glob("9*.sql") if f.is_file()]
        
        # Também suportar padrão antigo: arquivos *_ROLLBACK.sql na raiz (compatibilidade)
        old_rollback_files = [f for f in sql_files if f.name.endswith('_ROLLBACK.sql')]
        rollback_files.extend(old_rollback_files)
        
        # Arquivos de execução: excluir rollbacks antigos
        # Incluir todos os arquivos .sql que não sejam rollbacks
        execution_files = [
            f for f in sql_files 
            if not f.name.endswith('_ROLLBACK.sql')
        ]
        
        # Seeds também são arquivos de execução válidos
        seed_files = [f for f in execution_files if f.name.startswith('SEED-')]
        non_seed_files = [f for f in execution_files if not f.name.startswith('SEED-')]
        
        # Se não houver nenhum arquivo SQL válido (execução, rollback ou seed), retornar None
        if not execution_files and not rollback_files:
            return None
        
        # Buscar README
        readme_files = list(package_path.glob("README*.md"))
        
        # Extrair informações do nome do pacote
        package_name = package_path.name
        parts = package_name.split("_")
        
        if len(parts) >= 5:
            env = parts[1]  # DSV, HMG, PRD
            version = f"{parts[2]}_{parts[3]}"  # V1_00012
            # Schema pode ser a última parte ou várias partes (ex: SIGNUP_FIX -> SIGNUP_FIX, CORE -> CORE)
            # Se houver mais de 5 partes, pegar todas as partes restantes como schema
            if len(parts) > 5:
                schema = "_".join(parts[4:])  # Ex: SIGNUP_FIX
            else:
                schema = parts[4]  # SUPERADMIN, CORE, etc.
        else:
            env = "UNKNOWN"
            version = "UNKNOWN"
            schema = "UNKNOWN"
        
        # Converter Path objects para strings relativas ao package_path
        rollback_file_names = []
        for rb_file in rollback_files:
            if rb_file.parent == rollback_dir:
                # Novo padrão: incluir caminho relativo rollback/
                rollback_file_names.append(f"rollback/{rb_file.name}")
            else:
                # Padrão antigo: apenas o nome do arquivo
                rollback_file_names.append(rb_file.name)
            
        # Ordenar arquivos SQL por nome para garantir ordem consistente
        sorted_execution_files = sorted([f.name for f in execution_files])
        sorted_rollback_files = sorted(rollback_file_names)
        
        return {
            'package_name': package_name,
            'package_path': str(package_path),
            'environment': env,
            'version': version,
            'schema': schema,
            'date': package_path.parent.name,
            'sql_files': sorted_execution_files,
            'rollback_files': sorted_rollback_files,
            'readme_files': [f.name for f in readme_files],
            'status': 'pending'
        }
    
    def deploy_migration(self, package_path: str, environment: str, dry_run: bool = False) -> Tuple[bool, str]:
        """Executa o deploy de uma migration"""
        package_path = Path(package_path)
        
        if not package_path.exists():
            return False, f"ERR Pacote não encontrado: {package_path}"
            
        # Buscar arquivos SQL de execução (na raiz, excluindo pasta rollback e arquivos *_ROLLBACK.sql)
        sql_files = [f for f in package_path.glob("*.sql") 
                     if f.is_file() and not f.name.endswith('_ROLLBACK.sql')]
        
        if not sql_files:
            return False, f"ERR Nenhum arquivo SQL de execução encontrado em {package_path}"
            
        if dry_run:
            results = []
            for sql_file in sorted(sql_files):
                results.append(f" DRY RUN: Executaria {sql_file.name}")
            return True, "\n".join(results)
            
        # Testar conexão primeiro
        success, message = self.test_connection(environment)
        if not success:
            return False, message
            
        # Executar migrations
        results = []
        
        try:
            config = self.db_configs[environment]
            conn = psycopg2.connect(**config)
            conn.autocommit = True
            cursor = conn.cursor()
            
            for sql_file in sorted(sql_files):
                try:
                    # Ler arquivo SQL
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()

                    # Remover meta-comandos do psql (\o, \echo, \set, etc.) —
                    # psycopg2 so executa SQL puro.
                    cleaned_lines = []
                    for line in sql_content.splitlines():
                        stripped = line.lstrip()
                        if stripped.startswith("\\"):
                            continue
                        cleaned_lines.append(line)
                    sql_content = "\n".join(cleaned_lines)
                    if not sql_content.strip():
                        results.append(f"OK {sql_file.name} (vazio apos strip psql meta)")
                        continue
                    
                    # Executar SQL
                    cursor.execute(sql_content)
                    results.append(f"OK {sql_file.name} executado com sucesso")
                    
                except Exception as e:
                    results.append(f"ERR {sql_file.name} falhou: {str(e)}")
                    return False, "\n".join(results)
            
            cursor.close()
            conn.close()
            
            return True, "\n".join(results)
            
        except Exception as e:
            return False, f"ERR Erro de conexão: {str(e)}"

    def load_deps_manifest(self) -> Optional[Dict]:
        if not self.deps_manifest_path.exists():
            return None
        with open(self.deps_manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def find_package(self, environment: str, needle: str) -> Optional[Dict]:
        """Resolve pacote por nome completo, NNNN ou sufixo de schema."""
        needle = (needle or "").strip()
        if not needle:
            return None
        migrations = self.list_available_migrations(environment)
        exact = [m for m in migrations if m["package_name"] == needle]
        if exact:
            return exact[0]
        upper = needle.upper()
        # NNNN puro
        if upper.isdigit():
            n = int(upper)
            by_seq = [m for m in migrations if self._extract_version_number(m["package_name"]) == n]
            if len(by_seq) == 1:
                return by_seq[0]
            if by_seq:
                return by_seq[-1]
        # sufixo / contains
        matches = [m for m in migrations if upper in m["package_name"].upper()]
        if len(matches) == 1:
            return matches[0]
        if matches:
            # prefer ends-with schema
            ends = [m for m in matches if m["package_name"].upper().endswith("_" + upper) or m["schema"].upper() == upper]
            if len(ends) == 1:
                return ends[0]
            print(f"WARN Ambíguo ({len(matches)}): {[m['package_name'] for m in matches]}")
            return None
        return None

    def filter_by_date(self, migrations: List[Dict], date: str) -> List[Dict]:
        date = (date or "").strip()
        return [m for m in migrations if m.get("date") == date]

    def pending_only(self, migrations: List[Dict], force: bool = False) -> List[Dict]:
        if force:
            return list(migrations)
        done = {"completed", "success", "ok", "applied"}
        return [m for m in migrations if (m.get("status") or "pending").lower() not in done]

    def assert_deps(self, package: Dict, environment: str, force: bool = False, dry_run: bool = False) -> Tuple[bool, str]:
        """Valida deps via manifesto (seq) quando disponivel."""
        if force or dry_run:
            return True, "skip deps (force/dry-run)"
        manifest = self.load_deps_manifest()
        if not manifest:
            return True, "sem manifesto"
        seq = self._extract_version_number(package["package_name"])
        entry = next((x for x in manifest.get("sequence", []) if int(x["seq"]) == seq), None)
        if not entry:
            return True, "seq fora do manifesto"
        needed = [int(x) for x in entry.get("depends_on_seq", [])]
        if not needed:
            return True, "sem deps"
        all_pkgs = self.list_available_migrations(environment)
        by_seq = {self._extract_version_number(m["package_name"]): m for m in all_pkgs}
        done = {"completed", "success", "ok", "applied"}
        missing = []
        for n in needed:
            dep = by_seq.get(n)
            if not dep:
                missing.append(f"{n:05d} (ausente no disco)")
                continue
            st = (dep.get("status") or "pending").lower()
            if st not in done:
                missing.append(f"{dep['package_name']} (status={dep.get('status')})")
        if missing:
            return False, "deps nao satisfeitas: " + ", ".join(missing)
        return True, "deps ok"

    def deploy_many(
        self,
        packages: List[Dict],
        environment: str,
        dry_run: bool = False,
        force: bool = False,
    ) -> Tuple[bool, str]:
        if not packages:
            return True, "Nada a aplicar (lista vazia)."
        lines = []
        for pkg in packages:
            ok_deps, msg_deps = self.assert_deps(pkg, environment, force=force, dry_run=dry_run)
            lines.append(f"-> {pkg['package_name']} [{pkg.get('status', '?')}] deps: {msg_deps}")
            if not ok_deps:
                lines.append(f"ERR Abortado: {msg_deps}")
                return False, "\n".join(lines)
            ok, msg = self.deploy_migration(pkg["package_path"], environment, dry_run=dry_run)
            lines.append(msg)
            if not ok:
                lines.append(f"ERR Falha em {pkg['package_name']}")
                return False, "\n".join(lines)
            lines.append(f"OK {pkg['package_name']}")
            if dry_run:
                pkg["status"] = "applied"
        return True, "\n".join(lines)

    def deploy_full(self, environment: str, dry_run: bool = False, force: bool = False) -> Tuple[bool, str]:
        pkgs = self.pending_only(self.list_available_migrations(environment), force=force)
        return self.deploy_many(pkgs, environment, dry_run=dry_run, force=force)

    def deploy_lote(
        self, environment: str, date: str, dry_run: bool = False, force: bool = False
    ) -> Tuple[bool, str]:
        all_pkgs = self.list_available_migrations(environment)
        lote = self.filter_by_date(all_pkgs, date)
        if not lote:
            return False, f"ERR Nenhum pacote na data {date} para {environment}"
        pkgs = self.pending_only(lote, force=force)
        return self.deploy_many(pkgs, environment, dry_run=dry_run, force=force)

    def deploy_last(self, environment: str, dry_run: bool = False, force: bool = False) -> Tuple[bool, str]:
        all_pkgs = self.list_available_migrations(environment)
        if not all_pkgs:
            return False, f"ERR Nenhum pacote em {environment}"
        pending = self.pending_only(all_pkgs, force=False)
        if force and not pending:
            target = all_pkgs[-1]
        elif pending:
            target = pending[-1]
        else:
            return True, "Nada pendente (use --force para reaplicar o último do disco)."
        return self.deploy_many([target], environment, dry_run=dry_run, force=force)

    def deploy_package_named(
        self, environment: str, name: str, dry_run: bool = False, force: bool = False
    ) -> Tuple[bool, str]:
        pkg = self.find_package(environment, name)
        if not pkg:
            return False, f"ERR Pacote não encontrado: {name}"
        if not force and (pkg.get("status") or "pending").lower() in ("completed", "success", "ok", "applied"):
            return True, f"Ja aplicado: {pkg['package_name']} (use --force para reaplicar)"
        return self.deploy_many([pkg], environment, dry_run=dry_run, force=force)
    
    def interactive_deploy(self):
        """Interface interativa para deploy de migrations"""
        print("GhostWritter Migration Deployer")
        print("=" * 60)
        
        # Selecionar ambiente
        environments = ["desenvolvimento", "homologação", "produção"]
        print("\n Ambientes disponíveis:")
        for i, env in enumerate(environments, 1):
            print(f"  {i}. {env}")
            
        try:
            env_choice = int(input("\n Selecione o ambiente (1-3): ")) - 1
            if env_choice < 0 or env_choice >= len(environments):
                print("ERR Opção inválida")
                return
                
            environment = environments[env_choice]
        except ValueError:
            print("ERR Opção inválida")
            return
            
        # Testar conexão
        print(f"\n Testando conexão com {environment}...")
        success, message = self.test_connection(environment)
        print(message)
        
        if not success:
            print("ERR Não é possível continuar sem conexão com o banco")
            return
            
        # Listar migrations disponíveis
        migrations = self.list_available_migrations(environment)
        
        if not migrations:
            print(f"ERR Nenhuma migration encontrada para {environment}")
            return
            
        print(f"\n Migrations disponíveis para {environment}:")
        for i, migration in enumerate(migrations, 1):
            print(f"  {i}. {migration['package_name']} ({migration['date']})")
            print(f"     Schema: {migration['schema']} | Arquivos: {len(migration['sql_files'])}")
            
        try:
            migration_choice = int(input(f"\n Selecione a migration (1-{len(migrations)}): ")) - 1
            if migration_choice < 0 or migration_choice >= len(migrations):
                print("ERR Opção inválida")
                return
                
            selected_migration = migrations[migration_choice]
        except ValueError:
            print("ERR Opção inválida")
            return
            
        # Confirmar ação
        print(f"\n Migration selecionada:")
        print(f"  Pacote: {selected_migration['package_name']}")
        print(f"  Data: {selected_migration['date']}")
        print(f"  Arquivos: {', '.join(selected_migration['sql_files'])}")
        
        action = input("\n Ação (deploy/dry-run): ").lower().strip()
        
        if action == "deploy":
            success, message = self.deploy_migration(
                selected_migration['package_path'], 
                environment, 
                dry_run=False
            )
        elif action == "dry-run":
            success, message = self.deploy_migration(
                selected_migration['package_path'], 
                environment, 
                dry_run=True
            )
        else:
            print("ERR Ação inválida. Use: deploy ou dry-run")
            return
            
        print(f"\n Resultado:")
        print(message)
        
        if success:
            print("OK Operação concluída com sucesso!")
        else:
            print("ERR Operação falhou!")

def main():
    """Função principal"""
    deployer = MigrationDeployerPython()

    parser = argparse.ArgumentParser(
        description="GhostWritter Migration Deployer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/migration_deployer_python.py full -e desenvolvimento
  python scripts/migration_deployer_python.py lote -e desenvolvimento -d 07.08.2026
  python scripts/migration_deployer_python.py last
  python scripts/migration_deployer_python.py package PKG_DSV_V1_00004_PLATFORM
  python scripts/migration_deployer_python.py package 00003 --dry-run
  python scripts/migration_deployer_python.py list desenvolvimento
        """,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default=None,
        help="full | lote | last | package | list | test | deploy | dry-run",
    )
    parser.add_argument("args", nargs="*", help="Argumentos posicionais (legado / package name)")
    parser.add_argument("-e", "--env", default="desenvolvimento", help="Ambiente (default: desenvolvimento)")
    parser.add_argument("-d", "--date", default=None, help="Data do lote DD.MM.YYYY")
    parser.add_argument("-p", "--package", default=None, help="Nome / NNNN / schema do pacote")
    parser.add_argument("--dry-run", action="store_true", help="Não executa SQL")
    parser.add_argument("--force", action="store_true", help="Não pula completed; ignora gate de deps")

    # Compat: se argv legado sem subcomando reconhecido pelo argparse ambíguo,
    # manter fluxo antigo quando command em {test,list,deploy,dry-run} com paths.
    if len(sys.argv) <= 1:
        deployer.interactive_deploy()
        return

    ns = parser.parse_args()
    command = (ns.command or "").lower()
    environment = ns.env
    dry = ns.dry_run
    force = ns.force

    if command == "test":
        env = ns.args[0] if ns.args else environment
        ok, message = deployer.test_connection(env)
        print(message)
        sys.exit(0 if ok else 1)

    if command == "list":
        env = ns.args[0] if ns.args else environment
        migrations = deployer.list_available_migrations(env)
        print(f"Migrations ({env}):")
        for migration in migrations:
            print(
                f"  • {migration['package_name']} ({migration['date']}) "
                f"[{migration.get('status', '?')}]"
            )
        sys.exit(0)

    if command == "full":
        ok, message = deployer.deploy_full(environment, dry_run=dry, force=force)
        print(message)
        sys.exit(0 if ok else 1)

    if command == "lote":
        date = ns.date or (ns.args[0] if ns.args else None)
        if not date:
            print("ERR Informe a data: --date DD.MM.YYYY")
            sys.exit(2)
        ok, message = deployer.deploy_lote(environment, date, dry_run=dry, force=force)
        print(message)
        sys.exit(0 if ok else 1)

    if command == "last":
        ok, message = deployer.deploy_last(environment, dry_run=dry, force=force)
        print(message)
        sys.exit(0 if ok else 1)

    if command == "package":
        name = ns.package or (ns.args[0] if ns.args else None)
        if not name:
            print("ERR Informe o pacote: --package PKG_... | NNNN | SCHEMA")
            sys.exit(2)
        ok, message = deployer.deploy_package_named(environment, name, dry_run=dry, force=force)
        print(message)
        sys.exit(0 if ok else 1)

    if command == "deploy":
        if len(ns.args) < 2:
            print("ERR Uso: deploy <package_path> <environment>")
            sys.exit(2)
        package_path, env = ns.args[0], ns.args[1]
        ok, message = deployer.deploy_migration(package_path, env, dry_run=False)
        print(message)
        sys.exit(0 if ok else 1)

    if command == "dry-run":
        if len(ns.args) < 2:
            print("ERR Uso: dry-run <package_path> <environment>")
            sys.exit(2)
        package_path, env = ns.args[0], ns.args[1]
        ok, message = deployer.deploy_migration(package_path, env, dry_run=True)
        print(message)
        sys.exit(0 if ok else 1)

    print(f"ERR Comando inválido: {command}")
    parser.print_help()
    sys.exit(2)

if __name__ == "__main__":
    main()

