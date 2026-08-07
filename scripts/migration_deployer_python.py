#!/usr/bin/env python3
"""
🚀 PONTUA MIGRATION DEPLOYER - Python Version
Tool para deploy automatizado de migrations usando conexão Python direta
"""

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
        
        # Carregar variáveis de ambiente do arquivo env.local na raiz do projeto
        env_file = self.base_path / "env.local"
        if env_file.exists():
            load_dotenv(env_file)
        else:
            # Fallback para .env se env.local não existir
            load_dotenv()
        
        self.migrations_path = self.base_path / "migrations"
        
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
            return False, f"❌ Ambiente '{environment}' não configurado"
            
        config = self.db_configs[environment]
        
        try:
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return True, f"✅ Conexão OK: {version[:50]}..."
            
        except Exception as e:
            return False, f"❌ Erro de conexão: {str(e)}"
    
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
            print(f"❌ Ambiente '{environment}' não encontrado em {self.migrations_path}")
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
                return status if count > 0 else 'pending'
            else:
                return 'pending'
                
        except Exception as e:
            # Se não conseguir conectar ou tabela não existir, retorna pending
            print(f"⚠️ Não foi possível consultar status no banco: {e}")
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
            return False, f"❌ Pacote não encontrado: {package_path}"
            
        # Buscar arquivos SQL de execução (na raiz, excluindo pasta rollback e arquivos *_ROLLBACK.sql)
        sql_files = [f for f in package_path.glob("*.sql") 
                     if f.is_file() and not f.name.endswith('_ROLLBACK.sql')]
        
        if not sql_files:
            return False, f"❌ Nenhum arquivo SQL de execução encontrado em {package_path}"
            
        if dry_run:
            results = []
            for sql_file in sorted(sql_files):
                results.append(f"🔍 DRY RUN: Executaria {sql_file.name}")
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
                    
                    # Executar SQL
                    cursor.execute(sql_content)
                    results.append(f"✅ {sql_file.name} executado com sucesso")
                    
                except Exception as e:
                    results.append(f"❌ {sql_file.name} falhou: {str(e)}")
                    return False, "\n".join(results)
            
            cursor.close()
            conn.close()
            
            return True, "\n".join(results)
            
        except Exception as e:
            return False, f"❌ Erro de conexão: {str(e)}"
    
    def interactive_deploy(self):
        """Interface interativa para deploy de migrations"""
        print("🚀 PONTUA MIGRATION DEPLOYER - Python Version")
        print("=" * 60)
        
        # Selecionar ambiente
        environments = ["desenvolvimento", "homologação", "produção"]
        print("\n📋 Ambientes disponíveis:")
        for i, env in enumerate(environments, 1):
            print(f"  {i}. {env}")
            
        try:
            env_choice = int(input("\n🎯 Selecione o ambiente (1-3): ")) - 1
            if env_choice < 0 or env_choice >= len(environments):
                print("❌ Opção inválida")
                return
                
            environment = environments[env_choice]
        except ValueError:
            print("❌ Opção inválida")
            return
            
        # Testar conexão
        print(f"\n🔍 Testando conexão com {environment}...")
        success, message = self.test_connection(environment)
        print(message)
        
        if not success:
            print("❌ Não é possível continuar sem conexão com o banco")
            return
            
        # Listar migrations disponíveis
        migrations = self.list_available_migrations(environment)
        
        if not migrations:
            print(f"❌ Nenhuma migration encontrada para {environment}")
            return
            
        print(f"\n📦 Migrations disponíveis para {environment}:")
        for i, migration in enumerate(migrations, 1):
            print(f"  {i}. {migration['package_name']} ({migration['date']})")
            print(f"     Schema: {migration['schema']} | Arquivos: {len(migration['sql_files'])}")
            
        try:
            migration_choice = int(input(f"\n🎯 Selecione a migration (1-{len(migrations)}): ")) - 1
            if migration_choice < 0 or migration_choice >= len(migrations):
                print("❌ Opção inválida")
                return
                
            selected_migration = migrations[migration_choice]
        except ValueError:
            print("❌ Opção inválida")
            return
            
        # Confirmar ação
        print(f"\n📋 Migration selecionada:")
        print(f"  Pacote: {selected_migration['package_name']}")
        print(f"  Data: {selected_migration['date']}")
        print(f"  Arquivos: {', '.join(selected_migration['sql_files'])}")
        
        action = input("\n🎯 Ação (deploy/dry-run): ").lower().strip()
        
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
            print("❌ Ação inválida. Use: deploy ou dry-run")
            return
            
        print(f"\n📊 Resultado:")
        print(message)
        
        if success:
            print("✅ Operação concluída com sucesso!")
        else:
            print("❌ Operação falhou!")

def main():
    """Função principal"""
    deployer = MigrationDeployerPython()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            env = sys.argv[2] if len(sys.argv) > 2 else "homologação"
            success, message = deployer.test_connection(env)
            print(message)
            
        elif command == "list":
            env = sys.argv[2] if len(sys.argv) > 2 else "desenvolvimento"
            migrations = deployer.list_available_migrations(env)
            print(f"📦 Migrations disponíveis para {env}:")
            for migration in migrations:
                print(f"  • {migration['package_name']} ({migration['date']})")
                
        elif command == "deploy":
            if len(sys.argv) < 4:
                print("❌ Uso: python migration_deployer_python.py deploy <package_path> <environment>")
                return
            package_path, environment = sys.argv[2], sys.argv[3]
            success, message = deployer.deploy_migration(package_path, environment)
            print(message)
            
        elif command == "dry-run":
            if len(sys.argv) < 4:
                print("❌ Uso: python migration_deployer_python.py dry-run <package_path> <environment>")
                return
            package_path, environment = sys.argv[2], sys.argv[3]
            success, message = deployer.deploy_migration(package_path, environment, dry_run=True)
            print(message)
                
        else:
            print("❌ Comando inválido. Use: test, list, deploy, dry-run ou execute sem parâmetros para modo interativo")
    else:
        deployer.interactive_deploy()

if __name__ == "__main__":
    main()

