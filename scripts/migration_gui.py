# Caminho: scripts/migration_gui.py
# Descrição: Interface gráfica para gerenciamento de migrations
# Data: 2025-01-27
# Versão: 1.0
# Histórico de Modificações:
# - 2025-01-27: Criação inicial da interface GUI para migrations
# - 2025-01-27: Integração com migration_deployer_python
# - 2025-01-27: Implementação de todas as funcionalidades do backend original

import streamlit as st
import pandas as pd
import json
import datetime
from pathlib import Path
from typing import List, Dict, Optional
import sys
import os
import psycopg2
from dotenv import load_dotenv

# Adicionar o diretório scripts ao path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

# Adicionar o diretório pai (raiz do projeto) ao path
project_root = os.path.dirname(scripts_dir)
sys.path.insert(0, project_root)

# Carregar variáveis de ambiente do arquivo env.local na raiz do projeto
env_file = Path(project_root) / "env.local"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Fallback para .env se env.local não existir
    load_dotenv()

from migration_deployer_python import MigrationDeployerPython

class MigrationGUI:
    def __init__(self):
        self.deployer = MigrationDeployerPython()
        
        # Inicializar configurações na session_state se não existirem
        if 'db_config_desenvolvimento' not in st.session_state:
            st.session_state['db_config_desenvolvimento'] = self.deployer.db_configs['desenvolvimento']
        if 'db_config_homologação' not in st.session_state:
            st.session_state['db_config_homologação'] = self.deployer.db_configs['homologação']
        if 'db_config_produção' not in st.session_state:
            st.session_state['db_config_produção'] = self.deployer.db_configs['produção']
        
        # Atualizar deployer com configurações da session
        self.deployer.db_configs['desenvolvimento'] = st.session_state['db_config_desenvolvimento']
        self.deployer.db_configs['homologação'] = st.session_state['db_config_homologação']
        self.deployer.db_configs['produção'] = st.session_state['db_config_produção']
        
    def run(self):
        st.set_page_config(
            page_title="Nyoka Migration Manager",
            page_icon="🐍",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # CSS customizado
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .status-success {
            background-color: #d4edda;
            color: #155724;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border: 1px solid #c3e6cb;
        }
        .status-error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border: 1px solid #f5c6cb;
        }
        .status-warning {
            background-color: #fff3cd;
            color: #856404;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border: 1px solid #ffeaa7;
        }
        .migration-card {
            border: 1px solid #ddd;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
            background-color: #f9f9f9;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header principal
        st.markdown('<div class="main-header">🐍 Nyoka Migration Manager</div>', unsafe_allow_html=True)
        
        # Sidebar para configurações
        with st.sidebar:
            st.header("⚙️ Configurações")
            
            # Seleção de ambiente
            self.selected_env = st.selectbox(
                "Ambiente",
                ["desenvolvimento", "homologação", "produção"],
                index=1  # Default para homologação
            )
            
            # Teste de conexão
            st.subheader("🔗 Teste de Conexão")
            if st.button("Testar Conexão", type="primary"):
                with st.spinner("Testando conexão..."):
                    success, message = self.deployer.test_connection(self.selected_env)
                    if success:
                        st.markdown(f'<div class="status-success">✅ {message}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="status-error">❌ {message}</div>', unsafe_allow_html=True)
        
        # Tabs principais
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📦 Migrations", "🚀 Deploy", "📊 Status", "📝 Registrar", "⚙️ Config"])
        
        with tab1:
            self.show_migrations_tab()
            
        with tab2:
            self.show_deploy_tab()
            
        with tab3:
            self.show_status_tab()
            
        with tab4:
            self.show_register_tab()
            
        with tab5:
            self.show_config_tab()
    
    def show_migrations_tab(self):
        st.header(f"📦 Migrations - {self.selected_env.title()}")
        
        # Buscar migrations
        with st.spinner("Carregando migrations..."):
            migrations = self.deployer.list_available_migrations(self.selected_env)
        
        if not migrations:
            st.warning(f"Nenhuma migration encontrada para {self.selected_env}")
            return
        
        # Filtrar migrations
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("🔍 Buscar migration", placeholder="Digite o nome da migration...")
        with col2:
            show_only_pending = st.checkbox("Apenas pendentes", value=True)
        
        # Filtrar lista
        filtered_migrations = migrations
        if search_term:
            filtered_migrations = [m for m in filtered_migrations if search_term.lower() in m['package_name'].lower()]
        
        if show_only_pending:
            filtered_migrations = [m for m in filtered_migrations if m['status'] == 'pending']
        
        # Mostrar migrations
        st.subheader(f"📋 {len(filtered_migrations)} migrations encontradas")
        
        for migration in filtered_migrations:
            with st.expander(f"📦 {migration['package_name']} - {migration['date']}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Schema:** {migration['schema']}")
                    st.write(f"**Versão:** {migration['version']}")
                    st.write(f"**Data:** {migration['date']}")
                
                    # Arquivos SQL
                    if migration['sql_files']:
                        st.write("**Arquivos de execução:**")
                        for sql_file in migration['sql_files']:
                            st.write(f"  • {sql_file}")
                
                    if migration['rollback_files']:
                        st.write("**Arquivos de rollback:**")
                        for rollback_file in migration['rollback_files']:
                            st.write(f"  • {rollback_file}")
                
                with col2:
                    # Status com cores
                    status_emoji = {
                        'success': "🟢",
                        'pending': "🟡", 
                        'failed': "🔴",
                        'rolled_back': "🟠",
                        'unknown': "⚪"
                    }
                    emoji = status_emoji.get(migration['status'], "⚪")
                    st.write(f"**Status:** {emoji} {migration['status']}")
                
                with col3:
                    # Botões de ação
                    if migration['status'] == 'pending':
                        if st.button(f"🚀 Deploy", key=f"deploy_{migration['package_name']}"):
                            self.deploy_migration(migration['package_path'], self.selected_env)
                    else:
                        if st.button(f"🔄 Rollback", key=f"rollback_{migration['package_name']}"):
                            st.warning("Funcionalidade de rollback será implementada")
    
    def show_deploy_tab(self):
        st.header("🚀 Deploy de Migrations")
        
        # Seleção de migration para deploy
        migrations = self.deployer.list_available_migrations(self.selected_env)
        pending_migrations = [m for m in migrations if m['status'] == 'pending']
        
        if not pending_migrations:
            st.info("Nenhuma migration pendente para deploy")
            return
        
        selected_migration = st.selectbox(
            "Selecionar migration para deploy:",
            options=pending_migrations,
            format_func=lambda x: f"{x['package_name']} - {x['date']}"
        )
        
        if selected_migration:
            st.subheader(f"📦 {selected_migration['package_name']}")
            
            # Informações da migration
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Informações:**")
                st.write(f"• Schema: {selected_migration['schema']}")
                st.write(f"• Versão: {selected_migration['version']}")
                st.write(f"• Data: {selected_migration['date']}")
                st.write(f"• Ambiente: {self.selected_env}")
            
            with col2:
                st.write("**Arquivos que serão executados:**")
                for sql_file in selected_migration['sql_files']:
                    st.write(f"• {sql_file}")
            
            # Confirmação de deploy
            st.markdown("---")
            st.warning("⚠️ **ATENÇÃO:** Esta ação irá executar a migration no banco de dados!")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("🚀 EXECUTAR DEPLOY", type="primary", use_container_width=True):
                    with st.spinner("Executando deploy..."):
                        self.deploy_migration(selected_migration['package_path'], self.selected_env)
    
    def show_status_tab(self):
        st.header("📊 Status dos Ambientes")
        
        environments = ["desenvolvimento", "homologação", "produção"]
        
        for env in environments:
            with st.expander(f"🌐 {env.title()}", expanded=(env == self.selected_env)):
                # Teste de conexão
                success, message = self.deployer.test_connection(env)
                
                if success:
                    st.markdown(f'<div class="status-success">✅ Conectado: {message[:50]}...</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="status-error">❌ Erro: {message}</div>', unsafe_allow_html=True)
                
                # Estatísticas das migrations
                migrations = self.deployer.list_available_migrations(env)
                if migrations:
                    total = len(migrations)
                    pending = len([m for m in migrations if m['status'] == 'pending'])
                    success = len([m for m in migrations if m['status'] == 'success'])
                    failed = len([m for m in migrations if m['status'] == 'failed'])
                    rolled_back = len([m for m in migrations if m['status'] == 'rolled_back'])
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total", total)
                    with col2:
                        st.metric("✅ Aplicadas", success, delta=None)
                    with col3:
                        st.metric("🟡 Pendentes", pending, delta=None)
                    with col4:
                        st.metric("❌ Com Erro", failed + rolled_back, delta=None)
    
    def show_register_tab(self):
        st.header("📝 Registrar Migration Manual")
        
        st.info("""
        **Esta funcionalidade permite registrar migrations que já foram aplicadas antes da estrutura de versionamento.**
        
        Use quando:
        - ✅ Migration já foi aplicada manualmente
        - ✅ Migration foi aplicada antes do sistema de controle
        - ✅ Precisa registrar histórico de migrations antigas
        """)
        
        # Formulário para registrar migration
        with st.form("register_migration_form"):
            st.subheader("📋 Dados da Migration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                package_name = st.text_input(
                    "Package Name",
                    placeholder="Ex: PKG_HMG_V1_00008_CORE",
                    help="Nome do pacote da migration"
                )
                
                file_name = st.text_input(
                    "File Name", 
                    placeholder="Ex: CORE-01-EXP.sql",
                    help="Nome do arquivo principal da migration"
                )
                
                environment = st.selectbox(
                    "Ambiente",
                    ["produção", "desenvolvimento", "homologação"],
                    index=0
                )
                
                status = st.selectbox(
                    "Status",
                    ["success", "failed", "rolled_back"],
                    index=0
                )
            
            with col2:
                applied_at = st.date_input(
                    "Data de Aplicação",
                    value=datetime.date.today(),
                    help="Data quando a migration foi aplicada"
                )
                
                applied_by = st.text_input(
                    "Aplicado Por",
                    value="admin",
                    help="Usuário que aplicou a migration"
                )
                
                execution_time_ms = st.number_input(
                    "Tempo de Execução (ms)",
                    min_value=0,
                    value=1000,
                    help="Tempo de execução em milissegundos"
                )
                
                checksum = st.text_input(
                    "Checksum (opcional)",
                    placeholder="SHA256 hash",
                    help="Hash de verificação da migration"
                )
            
            notes = st.text_area(
                "Notas",
                placeholder="Descrição da migration, observações, etc.",
                help="Informações adicionais sobre a migration"
            )
            
            # Botão de submit
            submitted = st.form_submit_button("📝 Registrar Migration", type="primary")
            
            if submitted:
                if package_name and file_name:
                    self.register_migration(
                        package_name=package_name,
                        file_name=file_name,
                        environment=environment,
                        status=status,
                        applied_at=applied_at,
                        applied_by=applied_by,
                        execution_time_ms=execution_time_ms,
                        checksum=checksum,
                        notes=notes
                    )
                else:
                    st.error("❌ Package Name e File Name são obrigatórios!")
        
        # Lista migrations já registradas
        st.markdown("---")
        st.subheader("📋 Migrations Já Registradas")
        
        try:
            migrations = self.get_registered_migrations()
            if migrations:
                # Criar DataFrame para exibição
                df = pd.DataFrame(migrations)
                df['applied_at'] = pd.to_datetime(df['applied_at']).dt.strftime('%d/%m/%Y %H:%M')
                
                # Filtrar por ambiente
                env_filter = st.selectbox("Filtrar por ambiente:", ["Todos"] + list(df['environment'].unique()))
                if env_filter != "Todos":
                    df = df[df['environment'] == env_filter]
                
                # Mostrar tabela
                st.dataframe(
                    df[['package_name', 'file_name', 'environment', 'status', 'applied_at', 'applied_by']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma migration registrada ainda.")
                
        except Exception as e:
            st.error(f"❌ Erro ao carregar migrations: {str(e)}")
    
    def register_migration(self, package_name: str, file_name: str, environment: str, 
                          status: str, applied_at: datetime.date, applied_by: str,
                          execution_time_ms: int, checksum: str = None, notes: str = None):
        """Registra uma migration na tabela superadmin.migrations"""
        try:
            # Mapear nome do ambiente
            env_mapping = {
                'produção': 'producao',
                'desenvolvimento': 'desenvolvimento',
                'homologação': 'homologacao'
            }
            db_environment = env_mapping.get(environment, environment)
            
            # Conectar ao banco
            config = self.deployer.db_configs[environment]
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            # Inserir registro
            cursor.execute("""
                INSERT INTO superadmin.migrations (
                    package_name, file_name, environment, status,
                    applied_at, applied_by, execution_time_ms,
                    checksum, notes
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
            """, (
                package_name, file_name, db_environment, status,
                applied_at, applied_by, execution_time_ms,
                checksum, notes
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            st.success(f"✅ Migration registrada com sucesso!")
            st.info(f"**Package:** {package_name}\n**Arquivo:** {file_name}\n**Ambiente:** {environment}\n**Status:** {status}")
            
            # Recarregar a página para mostrar a atualização
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao registrar migration: {str(e)}")
    
    def get_registered_migrations(self):
        """Busca migrations já registradas no banco"""
        try:
            config = self.deployer.db_configs[self.selected_env]
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT package_name, file_name, environment, status,
                       applied_at, applied_by, execution_time_ms, notes
                FROM superadmin.migrations
                ORDER BY applied_at DESC
                LIMIT 50
            """)
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Converter para lista de dicionários
            migrations = []
            for row in results:
                migrations.append({
                    'package_name': row[0],
                    'file_name': row[1], 
                    'environment': row[2],
                    'status': row[3],
                    'applied_at': row[4],
                    'applied_by': row[5],
                    'execution_time_ms': row[6],
                    'notes': row[7]
                })
            
            return migrations
            
        except Exception as e:
            st.error(f"❌ Erro ao buscar migrations: {str(e)}")
            return []
    
    def update_db_config(self, environment: str, new_config: dict):
        """Atualiza configuração de banco de dados"""
        self.deployer.db_configs[environment] = new_config
        st.session_state[f'db_config_{environment}'] = new_config
        
        # Forçar recarregamento da página para aplicar as mudanças
        st.rerun()
    
    def reset_db_config(self, environment: str):
        """Reseta configuração para padrão"""
        default_configs = {
            'desenvolvimento': {
                'host': 'centerbeam.proxy.rlwy.net',
                'port': 39503,
                'database': 'nyoka',
                'user': 'admin',
                'password': 'Wp7gS93mZfT2lX'
            },
            'homologação': {
                'host': 'centerbeam.proxy.rlwy.net',
                'port': 39503,
                'database': 'nyoka',
                'user': 'admin',
                'password': 'Wp7gS93mZfT2lX'
            },
            'produção': {
                'host': 'nyoka-prd.proxy.rlwy.net',
                'port': 5432,
                'database': 'nyoka-prd',
                'user': 'admin',
                'password': 'Wp7gS93mZfT2lX'
            }
        }
        self.deployer.db_configs[environment] = default_configs[environment]
        st.session_state[f'db_config_{environment}'] = default_configs[environment]
    
    def test_custom_connection(self, config: dict):
        """Testa conexão com configuração customizada"""
        try:
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return True, f"Conexão OK: {version[:50]}..."
        except Exception as e:
            return False, f"Erro de conexão: {str(e)}"

    def show_config_tab(self):
        st.header("⚙️ Configurações")
        
        st.subheader("🔗 Configurações de Banco")
        
        # Permitir edição das configurações
        st.info("💡 **Edite as configurações de conexão abaixo e teste a conexão antes de usar.**")
        
        for env, config in self.deployer.db_configs.items():
            with st.expander(f"⚙️ Configurar - {env.title()}", expanded=True):
                
                # Formulário para editar configurações
                with st.form(f"config_form_{env}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_host = st.text_input(
                            "Host",
                            value=config['host'],
                            key=f"host_{env}"
                        )
                        
                        new_port = st.number_input(
                            "Porta",
                            value=config['port'],
                            min_value=1,
                            max_value=65535,
                            key=f"port_{env}"
                        )
                        
                        new_database = st.text_input(
                            "Database",
                            value=config['database'],
                            key=f"database_{env}"
                        )
                    
                    with col2:
                        new_user = st.text_input(
                            "Usuário",
                            value=config['user'],
                            key=f"user_{env}"
                        )
                        
                        new_password = st.text_input(
                            "Senha",
                            value=config['password'],
                            type="password",
                            key=f"password_{env}"
                        )
                    
                    # Botões de ação
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    with col1:
                        if st.form_submit_button("💾 Salvar", key=f"save_{env}"):
                            self.update_db_config(env, {
                                'host': new_host,
                                'port': new_port,
                                'database': new_database,
                                'user': new_user,
                                'password': new_password
                            })
                            st.success(f"✅ Configuração de {env} salva!")
                    
                    with col2:
                        if st.form_submit_button("🔗 Testar", key=f"test_{env}"):
                            # Testar conexão com nova configuração
                            test_config = {
                                'host': new_host,
                                'port': new_port,
                                'database': new_database,
                                'user': new_user,
                                'password': new_password
                            }
                            success, message = self.test_custom_connection(test_config)
                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ {message}")
                    
                    with col3:
                        if st.form_submit_button("🔄 Resetar", key=f"reset_{env}"):
                            self.reset_db_config(env)
                            st.info(f"🔄 Configuração de {env} resetada para padrão!")
                            st.rerun()
        
        # Exportar/Importar configurações
        st.markdown("---")
        st.subheader("💾 Backup/Restore Configurações")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Exportar Configurações"):
                configs_export = {
                    'desenvolvimento': self.deployer.db_configs['desenvolvimento'],
                    'homologação': self.deployer.db_configs['homologação'],
                    'produção': self.deployer.db_configs['produção']
                }
                # Remover senhas para segurança
                safe_configs = {}
                for env, config in configs_export.items():
                    safe_configs[env] = {k: v for k, v in config.items() if k != 'password'}
                
                st.download_button(
                    label="💾 Baixar Configurações (sem senhas)",
                    data=json.dumps(safe_configs, indent=2),
                    file_name="migration_gui_config.json",
                    mime="application/json"
                )
        
        with col2:
            uploaded_file = st.file_uploader("📥 Importar Configurações", type=['json'])
            if uploaded_file is not None:
                try:
                    configs_import = json.load(uploaded_file)
                    if 'desenvolvimento' in configs_import:
                        st.success("✅ Configurações carregadas! Configure as senhas manualmente.")
                        st.json(configs_import)
                except Exception as e:
                    st.error(f"❌ Erro ao importar: {str(e)}")
        
        # Mostrar configurações atuais
        st.markdown("---")
        st.subheader("📋 Configurações Atuais")
        
        for env, config in self.deployer.db_configs.items():
            with st.expander(f"Visualizar - {env.title()}"):
                st.write(f"**Host:** {config['host']}")
                st.write(f"**Porta:** {config['port']}")
                st.write(f"**Database:** {config['database']}")
                st.write(f"**Usuário:** {config['user']}")
                st.write("**Senha:** [PROTEGIDA]")
        
        st.subheader("📁 Estrutura de Migrations")
        # Usar o mesmo path que o deployer está usando
        migrations_path = Path(self.deployer.migrations_path)
        if migrations_path.exists():
            st.write(f"**Caminho:** {migrations_path.absolute()}")
            
            # Mostrar estrutura
            envs = [d for d in migrations_path.iterdir() if d.is_dir()]
            st.write("**Ambientes encontrados:**")
            for env in envs:
                st.write(f"  • {env.name}")
        else:
            st.error("Diretório de migrations não encontrado!")
    
    def deploy_migration(self, package_path: str, environment: str):
        """Executa deploy de uma migration"""
        try:
            success, message = self.deployer.deploy_migration(package_path, environment)
            
            if success:
                st.success(f"✅ Deploy executado com sucesso!")
                st.write(f"**Resultado:** {message}")
                st.rerun()  # Recarregar a página para atualizar status
            else:
                st.error(f"❌ Erro no deploy: {message}")
            
        except Exception as e:
            st.error(f"❌ Erro inesperado: {str(e)}")

def main():
    """Função principal"""
    gui = MigrationGUI()
    gui.run()

if __name__ == "__main__":
    main()