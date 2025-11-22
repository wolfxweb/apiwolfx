from fastapi import FastAPI, Cookie, Depends, HTTPException, Request
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional
from app.config.settings import settings
from app.config.database import engine, Base, get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, OperationalError, DisconnectionError
import psycopg2.errors
import time
from app.routes.main_routes import main_router
from app.routes.saas_routes import saas_router
from app.routes.auth_routes import auth_router
from app.routes.ml_routes import ml_router
from app.routes.ml_product_routes import ml_product_router
from app.routes.ml_orders_routes import ml_orders_router
from app.routes.ml_notifications_routes import ml_notifications_router, public_ml_notifications_router
from app.routes.ads_analytics_routes import ads_analytics_router
from app.routes.product_routes import product_router
from app.routes.pricing_analysis_routes import router as pricing_analysis_router
from app.routes.ml_pricing_routes import router as ml_pricing_router
from app.routes.sales_analysis_routes import router as sales_analysis_router
from app.routes.catalog_monitoring_routes import router as catalog_monitoring_router
from app.routes.superadmin_routes import superadmin_router
from app.routes.payment_routes import router as payment_router
from app.routes.asaas_routes import router as asaas_router
from app.routes.financial_routes import financial_router
from app.routes.fornecedores_routes import fornecedores_router
from app.routes.ordem_compra_routes import ordem_compra_router
from app.routes.ml_cash_routes import ml_cash_router
from app.routes.marketing_costs_routes import router as marketing_costs_router
from app.routes.advertising_full_routes import router as advertising_router
from app.routes.shipment_routes import router as shipment_router
from app.routes.highlights_routes import highlights_router
from app.routes.ml_questions_routes import ml_questions_router
from app.routes.ml_messages_routes import ml_messages_router
from app.routes.activity_routes import activity_router
from app.routes.openai_assistant_routes import openai_assistant_router, openai_chat_router, tools_router
from app.routes.stock_routes import stock_router
from app.routes.stock_projection_routes import stock_projection_router
from app.routes.internal_product_routes import internal_product_router
# from app.routes.settings_routes import router as settings_router  # Removido

# Scheduler para sincronização automática
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.services.auto_sync_service import AutoSyncService
from app.services.catalog_monitoring_service import CatalogMonitoringService
from app.services.asaas_sync_service import AsaasSyncService
from app.services.ml_cash_batch_service import MLCashBatchService
from app.config.database import SessionLocal
import atexit
import logging
import sys

# Configurar logging para aparecer no stdout/stderr (capturado pelo Docker)
# Verificar se já foi configurado antes de configurar novamente
root_logger = logging.getLogger()
if not root_logger.handlers:
    # Se não tem handlers, configurar basicConfig
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
else:
    # Se já tem handlers, apenas adiciona stdout handler se não existir
    has_stdout = any(
        isinstance(h, logging.StreamHandler) and getattr(h, 'stream', None) == sys.stdout
        for h in root_logger.handlers
    )
    if not has_stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(handler)

# Inicializar FastAPI
app = FastAPI(
    title="CELX - Gestão Inteligente de Vendas para Marketplace",
    description="Plataforma de gestão inteligente para marketplaces com Inteligência Artificial",
    version="2.0.0",
    docs_url="/docs"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar arquivos estáticos
app.mount("/static", StaticFiles(directory="public"), name="static")

# Inicializar scheduler
scheduler = BackgroundScheduler()
auto_sync_service = AutoSyncService()

def run_recent_sync():
    """JOB 1: Sincroniza pedidos RECENTES (últimas horas) - A cada 15 minutos"""
    try:
        print("📦 [AUTO-SYNC 15min] Iniciando...")
        result = auto_sync_service.sync_recent_orders()
        if result.get("success"):
            print(f"✅ Auto-sync 15min: {result.get('message', 'Concluído')}")
        else:
            print(f"❌ Auto-sync 15min falhou: {result.get('error', 'Erro desconhecido')}")
    except Exception as e:
        print(f"❌ Erro na auto-sync 15min: {e}")
        import traceback
        traceback.print_exc()

def run_daily_full_sync():
    """JOB 2: Sincroniza TODOS pedidos dos últimos 7 dias - À meia-noite"""
    try:
        result = auto_sync_service.sync_last_7_days_orders()
        if result.get("success"):
            print(f"🌙 Auto-sync meia-noite: {result.get('message', 'Concluído')}")
        else:
            print(f"❌ Auto-sync meia-noite falhou: {result.get('error', 'Erro desconhecido')}")
    except Exception as e:
        print(f"❌ Erro na auto-sync meia-noite: {e}")

# JOB 1: Sincronização rápida a cada 30 minutos (pedidos novos)
scheduler.add_job(
    func=run_recent_sync,
    trigger=IntervalTrigger(minutes=30),
    id='auto_sync_recent_orders',
    name='Sincronização automática - Pedidos novos (30min)',
    replace_existing=True
)

# JOB 2: Sincronização completa à meia-noite (últimos 7 dias) - INATIVO
# scheduler.add_job(
#     func=run_daily_full_sync,
#     trigger=CronTrigger(hour=0, minute=0),  # Todos os dias à meia-noite
#     id='auto_sync_7days_orders',
#     name='Sincronização automática - Últimos 7 dias (meia-noite)',
#     replace_existing=True
# )

# Função para monitoramento de catálogo
def run_catalog_monitoring():
    """Executa monitoramento de catálogos ativos"""
    try:
        print("📊 [CATALOG MONITORING] Iniciando...")
        db = SessionLocal()
        try:
            catalog_service = CatalogMonitoringService(db)
            catalog_service.collect_catalog_data_for_all_active()
            print("✅ Monitoramento de catálogo executado com sucesso")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Erro no monitoramento de catálogo: {e}")
        import traceback
        traceback.print_exc()

# JOB 3: Monitoramento de catálogo a cada 12 horas
scheduler.add_job(
    func=run_catalog_monitoring,
    trigger=IntervalTrigger(hours=12),
    id='catalog_monitoring_12h',
    name='Monitoramento de Catálogo ML (12h)',
    replace_existing=True
)

# Função para sincronização diária com Asaas
def run_asaas_daily_sync():
    """JOB 4: Sincronização diária com Asaas - Todos os dias às 3h da manhã"""
    try:
        print("🔄 [ASAAS SYNC] Iniciando sincronização diária com Asaas...")
        db = SessionLocal()
        try:
            sync_service = AsaasSyncService(db)
            result = sync_service.sync_all_subscriptions()
            if result.get("success"):
                stats = result.get("stats", {})
                print(f"✅ [ASAAS SYNC] Concluído: {stats.get('updated', 0)} atualizadas, {stats.get('inactivated', 0)} inativadas, {stats.get('errors', 0)} erros")
            else:
                print(f"❌ [ASAAS SYNC] Falhou: {result.get('error', 'Erro desconhecido')}")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Erro na sincronização diária com Asaas: {e}")
        import traceback
        traceback.print_exc()

# JOB 4: Sincronização diária com Asaas - Todos os dias às 3h da manhã
scheduler.add_job(
    func=run_asaas_daily_sync,
    trigger=CronTrigger(hour=3, minute=0),  # Todos os dias às 3h
    id='asaas_daily_sync',
    name='Sincronização diária com Asaas (3h)',
    replace_existing=True
)

def run_ml_cash_batch_processing():
    """JOB: Processamento de lançamentos ML Cash para todas as empresas - Todos os dias às 2h da manhã"""
    try:
        print("💰 [ML CASH BATCH] Iniciando processamento de lançamentos ML Cash para todas as empresas...")
        batch_service = MLCashBatchService()
        result = batch_service.process_all_companies()
        
        if result.get("success"):
            stats = result
            print(f"✅ [ML CASH BATCH] Concluído:")
            print(f"   - Empresas processadas: {stats.get('companies_processed', 0)}")
            print(f"   - Empresas puladas (sem conta): {stats.get('companies_skipped', 0)}")
            print(f"   - Lançamentos criados: {stats.get('total_processed', 0)}")
            print(f"   - Valor total: R$ {stats.get('total_amount', 0.0):.2f}")
            if stats.get('companies_with_errors', 0) > 0:
                print(f"   ⚠️ Empresas com erro: {stats.get('companies_with_errors', 0)}")
        else:
            print(f"❌ [ML CASH BATCH] Falhou: {result.get('error', 'Erro desconhecido')}")
    except Exception as e:
        print(f"❌ Erro no processamento em lote de ML Cash: {e}")
        import traceback
        traceback.print_exc()

# JOB 5: Processamento de lançamentos ML Cash para todas as empresas - Todos os dias às 2h da manhã
scheduler.add_job(
    func=run_ml_cash_batch_processing,
    trigger=CronTrigger(hour=2, minute=0),  # Todos os dias às 2h da manhã
    id='ml_cash_batch_processing',
    name='Processamento de lançamentos ML Cash (2h)',
    replace_existing=True
)

# Criar tabelas do banco de dados
@app.on_event("startup")
async def startup_event():
    """Evento de inicialização da aplicação"""
    try:
        print("🚀 [STARTUP] Iniciando aplicação...")
        
        # Criar tabelas se não existirem (com retry para conexões lentas)
        max_retries = 3
        retry_delay = 2
        
        # PRIMEIRO: Criar ENUMs necessários antes de criar tabelas
        try:
            from app.config.database import SessionLocal
            from sqlalchemy import text
            
            db_enum = SessionLocal()
            try:
                print("📋 [STARTUP] Criando ENUMs necessários...")
                create_enums_sql = text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'warehousetype') THEN
                            CREATE TYPE warehousetype AS ENUM ('fulfillment', 'custom');
                        END IF;
                        
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stockmovementtype') THEN
                            CREATE TYPE stockmovementtype AS ENUM ('in', 'out', 'adjustment', 'transfer', 'sale', 'purchase', 'reservation', 'release');
                        END IF;
                    END $$;
                """)
                db_enum.execute(create_enums_sql)
                db_enum.commit()
                print("✅ [STARTUP] ENUMs verificados/criados")
            except Exception as e:
                db_enum.rollback()
                print(f"⚠️ [STARTUP] ENUMs podem já existir: {e}")
            finally:
                db_enum.close()
        except Exception as e:
            print(f"⚠️ [STARTUP] Erro ao criar ENUMs (podem já existir): {e}")
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 [STARTUP] Tentando conectar ao banco de dados (tentativa {attempt + 1}/{max_retries})...")
                Base.metadata.create_all(bind=engine, checkfirst=True)
                print("✅ Banco de dados inicializado")
                break
            except (ProgrammingError, Exception) as db_error:
                # Ignorar erros de índices/tabelas duplicadas (já existem no banco)
                error_str = str(db_error)
                error_code = None
                
                # Verificar se é erro de duplicata do PostgreSQL
                if hasattr(db_error, 'orig') and hasattr(db_error.orig, 'pgcode'):
                    error_code = db_error.orig.pgcode
                
                is_duplicate = (
                    "already exists" in error_str.lower() or 
                    "duplicatetable" in error_str.lower() or 
                    "duplicateindex" in error_str.lower() or
                    error_code == psycopg2.errors.DuplicateTable.sqlstate or
                    error_code == psycopg2.errors.DuplicateIndex.sqlstate
                )
                
                if is_duplicate:
                    print(f"ℹ️ [STARTUP] Tabelas/índices já existem no banco, continuando...")
                    break
                
                if attempt < max_retries - 1:
                    print(f"⚠️ [STARTUP] Falha na conexão, tentando novamente em {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                else:
                    print(f"❌ [STARTUP] Falha ao conectar após {max_retries} tentativas")
                    # Se for erro de índice/tabela duplicada, não levantar exceção
                    if not is_duplicate:
                        raise db_error
                    else:
                        print(f"ℹ️ [STARTUP] Erro de duplicata ignorado, continuando inicialização...")
        
        # Executar migrações de banco de dados automaticamente
        print("🔄 [STARTUP] Executando migrações de banco de dados...")
        try:
            from app.config.database import SessionLocal
            from sqlalchemy import text
            
            # Função auxiliar para executar queries com retry
            def execute_with_retry(query_func, description, max_retries=3, retry_delay=2):
                """Executa uma função de query com retry em caso de erro de conexão"""
                for attempt in range(max_retries):
                    try:
                        db = SessionLocal()
                        try:
                            return query_func(db)
                        finally:
                            db.close()
                    except (OperationalError, DisconnectionError) as e:
                        error_str = str(e).lower()
                        # Verificar também no erro original (psycopg2)
                        orig_error_str = ""
                        if hasattr(e, 'orig') and e.orig:
                            orig_error_str = str(e.orig).lower()
                        
                        is_connection_error = (
                            "timeout" in error_str or
                            "connection" in error_str or
                            "server closed" in error_str or
                            "could not connect" in error_str or
                            "timeout" in orig_error_str or
                            "connection" in orig_error_str or
                            "server closed" in orig_error_str
                        )
                        
                        if is_connection_error and attempt < max_retries - 1:
                            print(f"⚠️ [STARTUP] Erro de conexão em {description} (tentativa {attempt + 1}/{max_retries}), tentando novamente em {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Backoff exponencial
                            continue
                        else:
                            print(f"❌ [STARTUP] Erro ao executar {description}: {e}")
                            if attempt == max_retries - 1:
                                print(f"⚠️ [STARTUP] Continuando apesar do erro (pode ser temporário)...")
                            return None
                    except Exception as e:
                        error_str = str(e).lower()
                        # Verificar se é erro de conexão mesmo sendo Exception genérica
                        is_connection_error = (
                            "timeout" in error_str or
                            "connection" in error_str or
                            "server closed" in error_str or
                            "could not connect" in error_str or
                            "operationalerror" in error_str
                        )
                        
                        if is_connection_error and attempt < max_retries - 1:
                            print(f"⚠️ [STARTUP] Erro de conexão em {description} (tentativa {attempt + 1}/{max_retries}), tentando novamente em {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Backoff exponencial
                            continue
                        else:
                            print(f"❌ [STARTUP] Erro ao executar {description}: {e}")
                            if attempt == max_retries - 1 and is_connection_error:
                                print(f"⚠️ [STARTUP] Continuando apesar do erro (pode ser temporário)...")
                            return None
                return None
            
            # 0. PRIMEIRO: Adicionar colunas Asaas na tabela subscriptions (CRÍTICO - deve ser antes de qualquer query)
            print("📋 [STARTUP] Executando migration: Adicionar colunas Asaas...")
            def migration_asaas(db):
                try:
                    # Verificar se as colunas já existem
                    check_query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'subscriptions' 
                        AND column_name IN ('asaas_subscription_id', 'asaas_customer_id', 'payment_provider', 'next_charge_date')
                    """)
                    existing_columns = [row[0] for row in db.execute(check_query).fetchall()]
                    
                    if 'asaas_subscription_id' not in existing_columns:
                        db.execute(text("ALTER TABLE subscriptions ADD COLUMN asaas_subscription_id VARCHAR(100)"))
                        print("✅ Coluna asaas_subscription_id adicionada")
                    
                    if 'asaas_customer_id' not in existing_columns:
                        db.execute(text("ALTER TABLE subscriptions ADD COLUMN asaas_customer_id VARCHAR(100)"))
                        print("✅ Coluna asaas_customer_id adicionada")
                    
                    if 'payment_provider' not in existing_columns:
                        db.execute(text("ALTER TABLE subscriptions ADD COLUMN payment_provider VARCHAR(20) DEFAULT 'asaas'"))
                        print("✅ Coluna payment_provider adicionada")
                    
                    if 'next_charge_date' not in existing_columns:
                        db.execute(text("ALTER TABLE subscriptions ADD COLUMN next_charge_date TIMESTAMP"))
                        print("✅ Coluna next_charge_date adicionada")
                    
                    # Criar índices
                    try:
                        db.execute(text("CREATE INDEX IF NOT EXISTS idx_subscriptions_asaas_subscription_id ON subscriptions(asaas_subscription_id)"))
                    except Exception:
                        pass  # Índice pode já existir
                    
                    db.commit()
                    print("✅ [STARTUP] Migration Asaas concluída")
                except Exception as e:
                    db.rollback()
                    raise  # Re-raise para ser capturado pelo retry
            
            execute_with_retry(migration_asaas, "migration Asaas")
            
            # 0.1. Adicionar campos de tokens de IA na tabela companies
            print("📋 [STARTUP] Executando migration: Adicionar campos de tokens de IA...")
            def migration_ai_tokens(db):
                try:
                    # Verificar se as colunas já existem
                    check_query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'companies' 
                        AND column_name IN ('ai_tokens_monthly', 'ai_tokens_purchased')
                    """)
                    existing_columns = [row[0] for row in db.execute(check_query).fetchall()]
                    
                    if 'ai_tokens_monthly' not in existing_columns:
                        db.execute(text("ALTER TABLE companies ADD COLUMN ai_tokens_monthly INTEGER DEFAULT 0"))
                        print("✅ Coluna ai_tokens_monthly adicionada")
                    
                    if 'ai_tokens_purchased' not in existing_columns:
                        db.execute(text("ALTER TABLE companies ADD COLUMN ai_tokens_purchased INTEGER DEFAULT 0"))
                        print("✅ Coluna ai_tokens_purchased adicionada")
                    
                    # Criar índices
                    try:
                        db.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_ai_tokens_monthly ON companies(ai_tokens_monthly)"))
                        db.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_ai_tokens_purchased ON companies(ai_tokens_purchased)"))
                    except Exception:
                        pass  # Índices podem já existir
                    
                    db.commit()
                    print("✅ [STARTUP] Migration de tokens de IA concluída")
                except Exception as e:
                    db.rollback()
                    raise  # Re-raise para ser capturado pelo retry
            
            execute_with_retry(migration_ai_tokens, "migration de tokens de IA")
            
            # 1. Criar tabelas OpenAI Assistants (se não existirem)
            db = SessionLocal()
            try:
                print("📋 [STARTUP] Verificando tabelas OpenAI Assistants...")
                try:
                    import importlib.util
                    import os
                    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                'database', 'fixes', 'create_openai_assistants_tables.py')
                    if os.path.exists(script_path):
                        spec = importlib.util.spec_from_file_location("create_openai_assistants_tables", script_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        module.create_openai_assistants_tables()
                        print("✅ [STARTUP] Tabelas OpenAI Assistants verificadas/criadas")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Tabelas podem já existir: {e}")
 
                # 1.0 Criar/garantir tabelas de Ferramentas reutilizáveis
                try:
                    import importlib.util
                    import os
                    tools_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_16_create_openai_tools_tables.py'
                    )
                    if os.path.exists(tools_path):
                        spec = importlib.util.spec_from_file_location("create_openai_tools_tables", tools_path)
                        tools_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(tools_module)
                        tools_module.run(db)
                        print("✅ [STARTUP] Tabelas de Ferramentas verificadas/criadas")
                    # Seed de ferramentas padrão para análise de produto
                    seed_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_16_seed_product_analysis_tools.py'
                    )
                    if os.path.exists(seed_path):
                        spec2 = importlib.util.spec_from_file_location("seed_product_analysis_tools", seed_path)
                        seed_module = importlib.util.module_from_spec(spec2)
                        spec2.loader.exec_module(seed_module)
                        seed_module.run(db)
                        print("✅ [STARTUP] Ferramentas de análise de produto seedadas")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar tabelas de Ferramentas: {e}")

                # 1.05 Criar agente "Analise produto" se não existir
                try:
                    import importlib.util
                    import os
                    agent_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_17_create_product_analysis_agent.py'
                    )
                    if os.path.exists(agent_path):
                        spec_agent = importlib.util.spec_from_file_location("create_product_analysis_agent", agent_path)
                        agent_module = importlib.util.module_from_spec(spec_agent)
                        spec_agent.loader.exec_module(agent_module)
                        agent_module.run(db)
                        print("✅ [STARTUP] Agente 'Analise produto' verificado/criado")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar agente 'Analise produto': {e}")

                # 1.06 Adicionar instrução de idioma português ao agente
                try:
                    import importlib.util
                    import os
                    portuguese_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_18_add_portuguese_instruction_agent.py'
                    )
                    if os.path.exists(portuguese_path):
                        spec_pt = importlib.util.spec_from_file_location("add_portuguese_instruction_agent", portuguese_path)
                        pt_module = importlib.util.module_from_spec(spec_pt)
                        spec_pt.loader.exec_module(pt_module)
                        pt_module.run(db)
                        print("✅ [STARTUP] Instrução de idioma português adicionada ao agente")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível adicionar instrução de idioma: {e}")

                # 1.1 Garantir índices de performance do chat (threads e mensagens)
                try:
                    import importlib.util
                    import os
                    idx_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_16_add_indexes_openai_chat.py'
                    )
                    if os.path.exists(idx_path):
                        spec = importlib.util.spec_from_file_location("add_indexes_openai_chat", idx_path)
                        idx_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(idx_module)
                        # Passar conexão atual para evitar abrir múltiplas sessões
                        idx_module.run(db)
                        print("✅ [STARTUP] Índices do chat verificados/criados")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar índices do chat: {e}")
                
                # 1.2 Atualizar instruções do agente 1 (regras de identificação do produto)
                try:
                    import importlib.util
                    import os
                    upd_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_16_update_agent_1_instructions.py'
                    )
                    if os.path.exists(upd_path):
                        spec3 = importlib.util.spec_from_file_location("update_agent_1_instructions", upd_path)
                        upd_module = importlib.util.module_from_spec(spec3)
                        spec3.loader.exec_module(upd_module)
                        upd_module.run(db)
                        print("✅ [STARTUP] Instruções do agente 1 verificadas/atualizadas")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível atualizar instruções do agente 1: {e}")
                
                # 1.3 Forçar atualização das instruções do agente de Análise de Produto (por nome)
                try:
                    import importlib.util
                    import os
                    upd2_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_16_force_update_product_analysis_instructions.py'
                    )
                    if os.path.exists(upd2_path):
                        spec4 = importlib.util.spec_from_file_location("force_update_product_analysis_instructions", upd2_path)
                        upd2_module = importlib.util.module_from_spec(spec4)
                        spec4.loader.exec_module(upd2_module)
                        upd2_module.run(db)
                        print("✅ [STARTUP] Instruções do agente de Análise de Produto verificadas/atualizadas")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível forçar atualização de instruções do agente de análise de produto: {e}")
                
                # 1.4 Atualizar schema da ferramenta get_orders (adicionar product_name, seller_sku, is_catalog)
                try:
                    import importlib.util
                    import os
                    schema_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_16_update_get_orders_schema.py'
                    )
                    if os.path.exists(schema_path):
                        spec5 = importlib.util.spec_from_file_location("update_get_orders_schema", schema_path)
                        schema_module = importlib.util.module_from_spec(spec5)
                        spec5.loader.exec_module(schema_module)
                        schema_module.run(db)
                        print("✅ [STARTUP] Schema da ferramenta get_orders atualizado")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível atualizar schema da ferramenta get_orders: {e}")

                # 1.5 Adicionar colunas de boas-vindas (welcome) no agente
                try:
                    import importlib.util
                    import os
                    welcome_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_16_add_welcome_fields_openai_assistants.py'
                    )
                    if os.path.exists(welcome_path):
                        specw = importlib.util.spec_from_file_location("add_welcome_fields_openai_assistants", welcome_path)
                        welcome_module = importlib.util.module_from_spec(specw)
                        specw.loader.exec_module(welcome_module)
                        welcome_module.run(db)
                        print("✅ [STARTUP] Campos de boas-vindas verificados/criados em openai_assistants")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar campos de boas-vindas: {e}")
                
                # 2. Adicionar colunas de memória (se não existirem)
                print("📋 [STARTUP] Verificando colunas de memória...")
                sql_memory = """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'openai_assistants' AND column_name = 'memory_enabled'
                    ) THEN
                        ALTER TABLE openai_assistants 
                        ADD COLUMN memory_enabled BOOLEAN DEFAULT TRUE NOT NULL;
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'openai_assistants' AND column_name = 'memory_data'
                    ) THEN
                        ALTER TABLE openai_assistants 
                        ADD COLUMN memory_data JSONB;
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'openai_assistant_threads' AND column_name = 'memory_data'
                    ) THEN
                        ALTER TABLE openai_assistant_threads 
                        ADD COLUMN memory_data JSONB;
                    END IF;
                END $$;
                """
                with db.begin():
                    db.execute(text(sql_memory))
                print("✅ [STARTUP] Colunas de memória verificadas/adicionadas")
                
                # 3. Adicionar coluna initial_prompt (se não existir)
                print("📋 [STARTUP] Verificando coluna initial_prompt...")
                sql_initial_prompt = """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'openai_assistants' AND column_name = 'initial_prompt'
                    ) THEN
                        ALTER TABLE openai_assistants 
                        ADD COLUMN initial_prompt TEXT;
                    END IF;
                END $$;
                """
                with db.begin():
                    db.execute(text(sql_initial_prompt))
                print("✅ [STARTUP] Coluna initial_prompt verificada/adicionada")
                
                # 4. Criar ENUMs e tabelas de estoque
                print("📋 [STARTUP] Verificando tabelas de estoque...")
                try:
                    # Criar ENUMs se não existirem
                    create_stock_enums_sql = text("""
                        DO $$ 
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'warehousetype') THEN
                                CREATE TYPE warehousetype AS ENUM ('fulfillment', 'custom');
                            END IF;
                            
                            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stockmovementtype') THEN
                                CREATE TYPE stockmovementtype AS ENUM ('in', 'out', 'adjustment', 'transfer', 'sale', 'purchase', 'reservation', 'release');
                            END IF;
                        END $$;
                    """)
                    db.execute(create_stock_enums_sql)
                    db.commit()
                    print("✅ [STARTUP] ENUMs de estoque verificados/criados")
                    
                    # Verificar se as tabelas já existem
                    check_tables_query = text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('warehouses', 'product_stocks', 'stock_movements', 'stock_projections')
                    """)
                    existing_tables = [row[0] for row in db.execute(check_tables_query).fetchall()]
                    
                    if 'warehouses' not in existing_tables:
                        print("📋 [STARTUP] Criando tabela warehouses...")
                        create_warehouses_sql = text("""
                            CREATE TABLE warehouses (
                                id SERIAL PRIMARY KEY,
                                company_id INTEGER,
                                name VARCHAR(255) NOT NULL,
                                type warehousetype NOT NULL,
                                is_shared BOOLEAN DEFAULT FALSE,
                                address TEXT,
                                contact_info JSONB,
                                status VARCHAR(50) DEFAULT 'active',
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT fk_warehouses_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                            );
                            
                            CREATE INDEX IF NOT EXISTS ix_warehouses_company_id ON warehouses(company_id);
                            CREATE INDEX IF NOT EXISTS ix_warehouses_type ON warehouses(type);
                            CREATE INDEX IF NOT EXISTS ix_warehouses_is_shared ON warehouses(is_shared);
                            CREATE INDEX IF NOT EXISTS ix_warehouses_status ON warehouses(status);
                            CREATE INDEX IF NOT EXISTS ix_warehouses_company_type ON warehouses(company_id, type);
                        """)
                        db.execute(create_warehouses_sql)
                        db.commit()
                        print("✅ [STARTUP] Tabela warehouses criada")
                    
                    if 'warehouses' in existing_tables or 'warehouses' not in existing_tables:
                        # Criar depósito fulfillment padrão se não existir
                        check_fulfillment = text("SELECT COUNT(*) FROM warehouses WHERE type = 'fulfillment' AND is_shared = TRUE")
                        fulfillment_count = db.execute(check_fulfillment).scalar()
                        if fulfillment_count == 0:
                            insert_fulfillment = text("""
                                INSERT INTO warehouses (name, type, is_shared, status, created_at, updated_at)
                                VALUES ('Fulfillment ML', 'fulfillment', TRUE, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """)
                            db.execute(insert_fulfillment)
                            db.commit()
                            print("✅ [STARTUP] Depósito Fulfillment padrão criado")
                    
                    if 'product_stocks' not in existing_tables:
                        print("📋 [STARTUP] Criando tabela product_stocks...")
                        create_product_stocks_sql = text("""
                            CREATE TABLE product_stocks (
                                id SERIAL PRIMARY KEY,
                                company_id INTEGER NOT NULL,
                                warehouse_id INTEGER NOT NULL,
                                internal_product_id INTEGER,
                                ml_item_id VARCHAR(50),
                                quantity NUMERIC(10, 2) DEFAULT 0 NOT NULL,
                                reserved_quantity NUMERIC(10, 2) DEFAULT 0 NOT NULL,
                                min_stock NUMERIC(10, 2),
                                max_stock NUMERIC(10, 2),
                                reorder_point NUMERIC(10, 2),
                                last_movement_date TIMESTAMP,
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT fk_product_stocks_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                CONSTRAINT fk_product_stocks_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
                                CONSTRAINT fk_product_stocks_internal_product FOREIGN KEY (internal_product_id) REFERENCES internal_products(id) ON DELETE CASCADE
                            );
                            
                            CREATE INDEX IF NOT EXISTS ix_product_stocks_company_id ON product_stocks(company_id);
                            CREATE INDEX IF NOT EXISTS ix_product_stocks_warehouse_id ON product_stocks(warehouse_id);
                            CREATE INDEX IF NOT EXISTS ix_product_stocks_internal_product_id ON product_stocks(internal_product_id);
                            CREATE INDEX IF NOT EXISTS ix_product_stocks_ml_item_id ON product_stocks(ml_item_id);
                            CREATE INDEX IF NOT EXISTS ix_product_stocks_warehouse_product ON product_stocks(warehouse_id, internal_product_id);
                            CREATE INDEX IF NOT EXISTS ix_product_stocks_warehouse_ml_item ON product_stocks(warehouse_id, ml_item_id);
                        """)
                        db.execute(create_product_stocks_sql)
                        db.commit()
                        print("✅ [STARTUP] Tabela product_stocks criada")
                    
                    if 'stock_movements' not in existing_tables:
                        print("📋 [STARTUP] Criando tabela stock_movements...")
                        create_stock_movements_sql = text("""
                            CREATE TABLE stock_movements (
                                id SERIAL PRIMARY KEY,
                                company_id INTEGER NOT NULL,
                                warehouse_id INTEGER NOT NULL,
                                product_stock_id INTEGER NOT NULL,
                                movement_type stockmovementtype NOT NULL,
                                quantity NUMERIC(10, 2) NOT NULL,
                                previous_quantity NUMERIC(10, 2) NOT NULL,
                                new_quantity NUMERIC(10, 2) NOT NULL,
                                reference_type VARCHAR(50),
                                reference_id INTEGER,
                                ml_order_id BIGINT,
                                notes TEXT,
                                created_by INTEGER,
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT fk_stock_movements_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                CONSTRAINT fk_stock_movements_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
                                CONSTRAINT fk_stock_movements_product_stock FOREIGN KEY (product_stock_id) REFERENCES product_stocks(id) ON DELETE CASCADE,
                                CONSTRAINT fk_stock_movements_ml_order FOREIGN KEY (ml_order_id) REFERENCES ml_orders(id) ON DELETE SET NULL,
                                CONSTRAINT fk_stock_movements_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                            );
                            
                            CREATE INDEX IF NOT EXISTS ix_stock_movements_company_id ON stock_movements(company_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_movements_warehouse_id ON stock_movements(warehouse_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_movements_product_stock_id ON stock_movements(product_stock_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_movements_movement_type ON stock_movements(movement_type);
                            CREATE INDEX IF NOT EXISTS ix_stock_movements_ml_order_id ON stock_movements(ml_order_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_movements_product_stock_date ON stock_movements(product_stock_id, created_at);
                            CREATE INDEX IF NOT EXISTS ix_stock_movements_company_date ON stock_movements(company_id, created_at);
                        """)
                        db.execute(create_stock_movements_sql)
                        db.commit()
                        print("✅ [STARTUP] Tabela stock_movements criada")
                    
                    if 'stock_projections' not in existing_tables:
                        print("📋 [STARTUP] Criando tabela stock_projections...")
                        create_stock_projections_sql = text("""
                            CREATE TABLE stock_projections (
                                id SERIAL PRIMARY KEY,
                                company_id INTEGER NOT NULL,
                                internal_product_id INTEGER NOT NULL,
                                warehouse_id INTEGER NOT NULL,
                                current_stock NUMERIC(10, 2) DEFAULT 0 NOT NULL,
                                average_daily_sales NUMERIC(10, 2),
                                days_of_stock NUMERIC(10, 2),
                                projected_stockout_date TIMESTAMP,
                                recommended_reorder_date TIMESTAMP,
                                recommended_quantity NUMERIC(10, 2),
                                turnover_rate NUMERIC(10, 4),
                                calculation_period_days INTEGER,
                                last_calculated_at TIMESTAMP,
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT fk_stock_projections_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                CONSTRAINT fk_stock_projections_internal_product FOREIGN KEY (internal_product_id) REFERENCES internal_products(id) ON DELETE CASCADE,
                                CONSTRAINT fk_stock_projections_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE
                            );
                            
                            CREATE INDEX IF NOT EXISTS ix_stock_projections_company_id ON stock_projections(company_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_projections_internal_product_id ON stock_projections(internal_product_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_projections_warehouse_id ON stock_projections(warehouse_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_projections_product_warehouse ON stock_projections(internal_product_id, warehouse_id);
                            CREATE INDEX IF NOT EXISTS ix_stock_projections_last_calculated ON stock_projections(last_calculated_at);
                        """)
                        db.execute(create_stock_projections_sql)
                        db.commit()
                        print("✅ [STARTUP] Tabela stock_projections criada")
                    
                    print("✅ [STARTUP] Tabelas de estoque verificadas/criadas")
                    
                except Exception as e:
                    db.rollback()
                    print(f"⚠️ [STARTUP] Erro ao criar tabelas de estoque (podem já existir): {e}")
                    import traceback
                    traceback.print_exc()
                
                print("✅ [STARTUP] Todas as migrações concluídas!")
                
            except Exception as e:
                print(f"⚠️ [STARTUP] Erro ao executar migrações (podem já estar aplicadas): {e}")
            finally:
                db.close()
                
        except Exception as e:
            print(f"⚠️ [STARTUP] Erro ao executar migrações automáticas: {e}")
            print("ℹ️ [STARTUP] Continuando inicialização...")
        
        # Scheduler comentado - Webhook orders_v2 mantém pedidos atualizados automaticamente
        # print(f"🔧 [STARTUP] Scheduler rodando antes: {scheduler.running}")
        # if not scheduler.running:
        #     print("🔧 [STARTUP] Iniciando scheduler...")
        #     scheduler.start()
        #     print(f"🔧 [STARTUP] Scheduler rodando depois: {scheduler.running}")
        #     print(f"🔧 [STARTUP] Jobs ativos: {len(scheduler.get_jobs())}")
        #     print("   📦 JOB 1: Pedidos novos - A cada 30 minutos")
        #     print("   🌙 JOB 2: Últimos 7 dias completos - INATIVO")
        #     print("   📊 JOB 3: Monitoramento de Catálogo - A cada 12 horas")
        # else:
        #     print("🔄 Scheduler já está rodando")
        
        print("🔄 [STARTUP] Scheduler desabilitado - Webhook orders_v2 ativo")
        
        print("✅ [STARTUP] Aplicação inicializada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao inicializar: {e}")
        import traceback
        traceback.print_exc()

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de encerramento da aplicação"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            print("🛑 Scheduler de sincronização automática parado")
    except Exception as e:
        print(f"❌ Erro ao parar scheduler: {e}")

# Garantir que o scheduler seja parado ao sair
atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)

# Incluir todas as rotas com prefixo /api
app.include_router(main_router, prefix="/api")
app.include_router(saas_router, prefix="/api")
app.include_router(auth_router, prefix="/auth")
app.include_router(ml_router, prefix="/ml")
app.include_router(ml_product_router, prefix="/ml")
app.include_router(ml_orders_router, prefix="/ml")
app.include_router(ml_notifications_router, prefix="/api")  # Para /api/notifications
app.include_router(public_ml_notifications_router)  # Para /notifications
app.include_router(ads_analytics_router)  # Sem prefixo para /analytics
app.include_router(product_router)  # Sem prefixo para /api/products
app.include_router(pricing_analysis_router, prefix="/api/pricing")  # Para /api/pricing/analysis
app.include_router(ml_pricing_router, prefix="/api/ml-pricing")  # Para /api/ml-pricing/fees
app.include_router(sales_analysis_router)  # Para /api/sales/analysis
app.include_router(catalog_monitoring_router)  # Para /api/catalog-monitoring
app.include_router(superadmin_router)  # Para /superadmin
app.include_router(payment_router)  # Para /api/payments
app.include_router(asaas_router)  # Para /api/asaas
app.include_router(financial_router)  # Para /financial e /api/financial
app.include_router(fornecedores_router)  # Para /fornecedores e /api/fornecedores
app.include_router(ordem_compra_router)  # Para /ordem-compra e /api/ordem-compra
app.include_router(ml_cash_router)  # Para /api/ml-cash
app.include_router(marketing_costs_router)  # Para /marketing
app.include_router(advertising_router)  # Para /ml/advertising
app.include_router(shipment_router, prefix="/api")  # Para /api/shipments
app.include_router(highlights_router)  # Para /ml/highlights e /api/ml/highlights
app.include_router(ml_questions_router)  # Para /questions (HTML) e /api/questions (API)
app.include_router(ml_messages_router)  # Para /messages (HTML) e /api/messages (API)
app.include_router(activity_router)  # Para /api/activity/summary
app.include_router(openai_assistant_router)  # Para /api/openai/assistants
app.include_router(openai_chat_router)  # Para /ai/chat (HTML)
app.include_router(tools_router)  # Para /api/openai/tools
app.include_router(stock_router, prefix="/api")  # Para /api/stock (API)
app.include_router(stock_projection_router, prefix="/api")  # Para /api/stock/projections

# Rota HTML para página de estoque (sem prefixo /api)
@app.get("/estoque", response_class=HTMLResponse)
async def stock_page_html(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de gerenciamento de estoque"""
    from fastapi.responses import RedirectResponse
    from app.controllers.auth_controller import AuthController
    from app.views.template_renderer import render_template
    
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            return RedirectResponse(url="/auth/login", status_code=302)
        
        user_data = result["user"]
        return render_template("stock_management.html", user=user_data, request=request)
    except Exception as e:
        return RedirectResponse(url="/auth/login", status_code=302)

# Rota HTML para página de projeções de estoque
@app.get("/estoque/projecoes", response_class=HTMLResponse)
async def stock_projection_page_html(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de projeções de estoque"""
    from fastapi.responses import RedirectResponse
    from app.controllers.auth_controller import AuthController
    from app.views.template_renderer import render_template
    
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            return RedirectResponse(url="/auth/login", status_code=302)
        
        user_data = result["user"]
        return render_template("stock_projection.html", user=user_data, request=request)
    except Exception as e:
        return RedirectResponse(url="/auth/login", status_code=302)

app.include_router(internal_product_router, prefix="/api")  # Para /api/internal-products
# app.include_router(settings_router)  # Removido - usando /auth/profile

# Rota específica para página de edição da empresa
@app.get("/auth/company/edit", response_class=HTMLResponse)
async def edit_company_page(
    request: Request,
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de edição da empresa"""
    if not session_token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=302)
    
    from app.controllers.auth_controller import AuthController
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar informações completas da empresa
    from sqlalchemy import text
    from app.models.saas_models import Company, Subscription, MLAccount
    
    # Informações da empresa
    company_query = text("""
        SELECT c.*, 
               COUNT(DISTINCT u.id) as total_users,
               COUNT(DISTINCT ma.id) as total_ml_accounts
        FROM companies c
        LEFT JOIN users u ON u.company_id = c.id
        LEFT JOIN ml_accounts ma ON ma.company_id = c.id
        WHERE c.id = :company_id
        GROUP BY c.id
    """)
    
    result = db.execute(company_query, {"company_id": company_id}).fetchone()
    
    print(f"DEBUG: Carregando empresa ID: {company_id}")
    if result:
        print(f"DEBUG: Empresa encontrada: {result.name}")
        print(f"DEBUG: Dados carregados do banco:")
        print(f"  - Nome Fantasia: {getattr(result, 'nome_fantasia', None)}")
        print(f"  - CEP: {getattr(result, 'cep', None)}")
        print(f"  - Cidade: {getattr(result, 'cidade', None)}")
    else:
        print(f"DEBUG: Empresa não encontrada")
    
    if not result:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    company_data = {
        "id": result.id,
        "name": result.name,
        "slug": result.slug,
        "domain": result.domain,
        "status": result.status,
        "description": result.description,
        "created_at": result.created_at,
        "trial_ends_at": result.trial_ends_at,
        "ml_orders_as_receivables": result.ml_orders_as_receivables,
        "total_users": result.total_users,
        "total_ml_accounts": result.total_ml_accounts,
        # Campos adicionais
        "razao_social": getattr(result, 'razao_social', None),
        "nome_fantasia": getattr(result, 'nome_fantasia', None),
        "cnpj": getattr(result, 'cnpj', None),
        "inscricao_estadual": getattr(result, 'inscricao_estadual', None),
        "inscricao_municipal": getattr(result, 'inscricao_municipal', None),
        "regime_tributario": getattr(result, 'regime_tributario', None),
        "cep": getattr(result, 'cep', None),
        "endereco": getattr(result, 'endereco', None),
        "numero": getattr(result, 'numero', None),
        "complemento": getattr(result, 'complemento', None),
        "bairro": getattr(result, 'bairro', None),
        "cidade": getattr(result, 'cidade', None),
        "estado": getattr(result, 'estado', None),
        "pais": getattr(result, 'pais', None),
        # Campos de impostos
        "aliquota_simples": getattr(result, 'aliquota_simples', None),
        "faturamento_anual": getattr(result, 'faturamento_anual', None),
        "aliquota_ir": getattr(result, 'aliquota_ir', None),
        "aliquota_csll": getattr(result, 'aliquota_csll', None),
        "aliquota_pis": getattr(result, 'aliquota_pis', None),
        "aliquota_cofins": getattr(result, 'aliquota_cofins', None),
        "aliquota_icms": getattr(result, 'aliquota_icms', None),
        "aliquota_iss": getattr(result, 'aliquota_iss', None),
        "aliquota_ir_real": getattr(result, 'aliquota_ir_real', None),
        "aliquota_csll_real": getattr(result, 'aliquota_csll_real', None),
        "aliquota_pis_real": getattr(result, 'aliquota_pis_real', None),
        "aliquota_cofins_real": getattr(result, 'aliquota_cofins_real', None),
        "aliquota_icms_real": getattr(result, 'aliquota_icms_real', None),
        "aliquota_iss_real": getattr(result, 'aliquota_iss_real', None),
        "percentual_marketing": getattr(result, 'percentual_marketing', None),
        "custo_adicional_por_pedido": getattr(result, 'custo_adicional_por_pedido', None)
    }
    
    from app.views.template_renderer import render_template
    return render_template("edit_company.html", 
                         user=user_data, 
                         company=company_data)

# Rota específica para API de atualização da empresa
@app.put("/api/company/update")
async def api_update_company(
    company_data: dict,
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar dados da empresa do usuário logado"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    from app.controllers.auth_controller import AuthController
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário não possui empresa associada")
    
    try:
        # Buscar a empresa
        from app.models.saas_models import Company
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        print(f"DEBUG: Dados recebidos: {company_data}")
        print(f"DEBUG: Empresa encontrada: {company.name}")
        
        # Atualizar campos permitidos
        if 'name' in company_data:
            company.name = company_data['name']
            # Gerar slug automaticamente baseado no nome
            import re
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', company_data['name'])
            slug = re.sub(r'\s+', '-', slug).lower()
            company.slug = slug
            print(f"DEBUG: Nome atualizado para: {company.name}")
        
        if 'domain' in company_data:
            company.domain = company_data['domain']
        
        if 'description' in company_data:
            company.description = company_data['description']
        
        # Campos de identificação
        if 'razao_social' in company_data:
            company.razao_social = company_data['razao_social']
            print(f"DEBUG: Razão Social atualizada para: {company.razao_social}")
        if 'nome_fantasia' in company_data:
            company.nome_fantasia = company_data['nome_fantasia']
            print(f"DEBUG: Nome Fantasia atualizado para: {company.nome_fantasia}")
        if 'cnpj' in company_data:
            company.cnpj = company_data['cnpj']
            print(f"DEBUG: CNPJ atualizado para: {company.cnpj}")
        if 'inscricao_estadual' in company_data:
            company.inscricao_estadual = company_data['inscricao_estadual']
            print(f"DEBUG: Inscrição Estadual atualizada para: {company.inscricao_estadual}")
        if 'inscricao_municipal' in company_data:
            company.inscricao_municipal = company_data['inscricao_municipal']
            print(f"DEBUG: Inscrição Municipal atualizada para: {company.inscricao_municipal}")
        if 'regime_tributario' in company_data:
            company.regime_tributario = company_data['regime_tributario']
            print(f"DEBUG: Regime Tributário atualizado para: {company.regime_tributario}")
        
        # Campos de endereço
        if 'cep' in company_data:
            company.cep = company_data['cep']
            print(f"DEBUG: CEP atualizado para: {company.cep}")
        if 'endereco' in company_data:
            company.endereco = company_data['endereco']
            print(f"DEBUG: Endereço atualizado para: {company.endereco}")
        if 'numero' in company_data:
            company.numero = company_data['numero']
            print(f"DEBUG: Número atualizado para: {company.numero}")
        if 'complemento' in company_data:
            company.complemento = company_data['complemento']
            print(f"DEBUG: Complemento atualizado para: {company.complemento}")
        if 'bairro' in company_data:
            company.bairro = company_data['bairro']
            print(f"DEBUG: Bairro atualizado para: {company.bairro}")
        if 'cidade' in company_data:
            company.cidade = company_data['cidade']
            print(f"DEBUG: Cidade atualizada para: {company.cidade}")
        if 'estado' in company_data:
            company.estado = company_data['estado']
            print(f"DEBUG: Estado atualizado para: {company.estado}")
        if 'pais' in company_data:
            company.pais = company_data['pais']
            print(f"DEBUG: País atualizado para: {company.pais}")
        
        # Campos de impostos (convertendo strings vazias para None)
        if 'aliquota_simples' in company_data:
            company.aliquota_simples = float(company_data['aliquota_simples']) if company_data['aliquota_simples'] else None
        if 'faturamento_anual' in company_data:
            company.faturamento_anual = float(company_data['faturamento_anual']) if company_data['faturamento_anual'] else None
        if 'aliquota_ir' in company_data:
            company.aliquota_ir = float(company_data['aliquota_ir']) if company_data['aliquota_ir'] else None
        if 'aliquota_csll' in company_data:
            company.aliquota_csll = float(company_data['aliquota_csll']) if company_data['aliquota_csll'] else None
        if 'aliquota_pis' in company_data:
            company.aliquota_pis = float(company_data['aliquota_pis']) if company_data['aliquota_pis'] else None
        if 'aliquota_cofins' in company_data:
            company.aliquota_cofins = float(company_data['aliquota_cofins']) if company_data['aliquota_cofins'] else None
        if 'aliquota_icms' in company_data:
            company.aliquota_icms = float(company_data['aliquota_icms']) if company_data['aliquota_icms'] else None
        if 'aliquota_iss' in company_data:
            company.aliquota_iss = float(company_data['aliquota_iss']) if company_data['aliquota_iss'] else None
        if 'aliquota_ir_real' in company_data:
            company.aliquota_ir_real = float(company_data['aliquota_ir_real']) if company_data['aliquota_ir_real'] else None
        if 'aliquota_csll_real' in company_data:
            company.aliquota_csll_real = float(company_data['aliquota_csll_real']) if company_data['aliquota_csll_real'] else None
        if 'aliquota_pis_real' in company_data:
            company.aliquota_pis_real = float(company_data['aliquota_pis_real']) if company_data['aliquota_pis_real'] else None
        if 'aliquota_cofins_real' in company_data:
            company.aliquota_cofins_real = float(company_data['aliquota_cofins_real']) if company_data['aliquota_cofins_real'] else None
        if 'aliquota_icms_real' in company_data:
            company.aliquota_icms_real = float(company_data['aliquota_icms_real']) if company_data['aliquota_icms_real'] else None
        if 'aliquota_iss_real' in company_data:
            company.aliquota_iss_real = float(company_data['aliquota_iss_real']) if company_data['aliquota_iss_real'] else None
        
        # Campos de marketing e custos
        if 'percentual_marketing' in company_data:
            company.percentual_marketing = float(company_data['percentual_marketing']) if company_data['percentual_marketing'] else None
            print(f"DEBUG: Percentual Marketing atualizado para: {company.percentual_marketing}")
        if 'custo_adicional_por_pedido' in company_data:
            company.custo_adicional_por_pedido = float(company_data['custo_adicional_por_pedido']) if company_data['custo_adicional_por_pedido'] else None
            print(f"DEBUG: Custo Adicional por Pedido atualizado para: {company.custo_adicional_por_pedido}")
        
        if 'trial_ends_at' in company_data and company_data['trial_ends_at']:
            from datetime import datetime
            company.trial_ends_at = datetime.fromisoformat(company_data['trial_ends_at'])
        
        if 'ml_orders_as_receivables' in company_data:
            company.ml_orders_as_receivables = company_data['ml_orders_as_receivables']
        
        # Salvar alterações
        print(f"DEBUG: Salvando alterações no banco...")
        try:
            # Forçar flush antes do commit
            db.flush()
            print(f"DEBUG: Flush realizado")
            
            # Commit explícito
            db.commit()
            print(f"DEBUG: Commit realizado")
            
            # Refresh para garantir que os dados estão atualizados
            db.refresh(company)
            print(f"DEBUG: Refresh realizado")
            
            # Verificar se os dados foram realmente salvos
            print(f"DEBUG: Verificando dados salvos:")
            print(f"  - Nome Fantasia: {company.nome_fantasia}")
            print(f"  - CEP: {company.cep}")
            print(f"  - Cidade: {company.cidade}")
            
            # Testar com uma nova sessão para verificar se os dados foram persistidos
            from app.config.database import SessionLocal
            from sqlalchemy import text
            new_db = SessionLocal()
            try:
                result = new_db.execute(text("SELECT nome_fantasia, cep, cidade FROM companies WHERE id = :company_id"), {"company_id": company_id}).fetchone()
                if result:
                    print(f"DEBUG: Verificação com nova sessão:")
                    print(f"  - Nome Fantasia no banco: {result.nome_fantasia}")
                    print(f"  - CEP no banco: {result.cep}")
                    print(f"  - Cidade no banco: {result.cidade}")
                else:
                    print(f"DEBUG: Erro - não foi possível verificar no banco")
            finally:
                new_db.close()
            
            print(f"DEBUG: Alterações salvas com sucesso!")
        except Exception as e:
            print(f"DEBUG: Erro ao salvar: {str(e)}")
            db.rollback()
            raise e
        
        return {
            "success": True,
            "message": "Empresa atualizada com sucesso",
            "company": {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "domain": company.domain,
                "status": company.status,
                "description": company.description,
                "trial_ends_at": company.trial_ends_at.isoformat() if company.trial_ends_at else None,
                "ml_orders_as_receivables": company.ml_orders_as_receivables
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar empresa: {str(e)}")

# Rotas principais (sem prefixo para compatibilidade)
@app.get("/")
async def root(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Página inicial - Landing page do CELX com menus do usuário se logado"""
    from app.views.template_renderer import render_template
    from app.controllers.auth_controller import AuthController
    from app.models.saas_models import Subscription
    
    user_data = None
    
    # Verificar se o usuário está logado para exibir menus
    if session_token:
        controller = AuthController()
        result = controller.get_user_by_session(session_token, db)
        if not result.get("error"):
            user_data = result.get("user")
    
    # Buscar planos templates do banco de dados
    try:
        plans = db.query(Subscription).filter(
            Subscription.status == "template"
        ).order_by(Subscription.price).all()
        
        # Converter para dict para passar ao template
        plans_data = []
        for plan in plans:
            plans_data.append({
                "id": plan.id,
                "plan_name": plan.plan_name,
                "description": plan.description,
                "price": float(plan.price) if plan.price else 0,
                "promotional_price": float(plan.promotional_price) if plan.promotional_price else None,
                "currency": plan.currency,
                "billing_cycle": plan.billing_cycle,
                "max_users": plan.max_users,
                "max_ml_accounts": plan.max_ml_accounts,
                "storage_gb": plan.storage_gb,
                "ai_analysis_monthly": plan.ai_analysis_monthly,
                "catalog_monitoring_slots": plan.catalog_monitoring_slots,
                "product_mining_slots": plan.product_mining_slots,
                "product_monitoring_slots": plan.product_monitoring_slots,
                "trial_days": plan.trial_days
            })
    except Exception as e:
        # Se houver erro ao buscar planos, continuar sem eles
        plans_data = []
    
    # Renderizar landing page com user_data (se logado, os menus aparecerão automaticamente)
    return render_template("home.html", request=request, user=user_data, plans=plans_data)



@app.get("/login")
async def login(state: str = None):
    """Redireciona para o login do Mercado Livre"""
    from app.controllers.auth_controller import AuthController
    from fastapi.responses import RedirectResponse
    controller = AuthController()
    result = controller.redirect_to_login(state)
    return RedirectResponse(url=result["auth_url"], status_code=302)


@app.get("/api/callback")
async def api_callback(code: str = None, error: str = None, state: str = None):
    """Recebe o callback do Mercado Livre via /api/callback"""
    from fastapi.responses import RedirectResponse
    from app.config.database import get_db
    from sqlalchemy.orm import Session
    from app.models.saas_models import MLAccount, UserMLAccount, Token, MLAccountStatus
    from datetime import datetime, timedelta
    import requests
    
    if error:
        return RedirectResponse(url=f"/ml/accounts?error={error}", status_code=302)
    
    if not code:
        return RedirectResponse(url="/ml/accounts?error=no_code", status_code=302)
    
    try:
        # Trocar code por access_token
        from app.config.settings import settings
        
        url = f"{settings.ml_token_url}"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.ml_app_id,
            "client_secret": settings.ml_client_secret,
            "code": code,
            "redirect_uri": settings.ml_redirect_uri
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        
        # Obter informações do usuário ML
        user_info_url = "https://api.mercadolibre.com/users/me"
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        user_response = requests.get(user_info_url, headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()
        
        # Buscar usuário pelo state (que contém o user_id)
        from app.models.saas_models import Company, User
        db = next(get_db())
        
        if not state:
            return RedirectResponse(url="/ml/accounts?error=State não fornecido", status_code=302)
        
        try:
            user_id_from_state = int(state)  # State contém o user_id
            user = db.query(User).filter(User.id == user_id_from_state, User.is_active == True).first()
            if not user:
                return RedirectResponse(url="/ml/accounts?error=Usuário não encontrado", status_code=302)
        except (ValueError, TypeError):
            return RedirectResponse(url="/ml/accounts?error=State inválido", status_code=302)
        
        company_id = user.company_id
        user_id = user.id
        
  
        
        # Verificar se a conta ML já existe
        existing_account = db.query(MLAccount).filter(
            MLAccount.ml_user_id == str(user_info["id"]),
            MLAccount.company_id == company_id
        ).first()
        
        if existing_account:
            # ATUALIZAR conta existente
            existing_account.nickname = user_info["nickname"]
            existing_account.email = user_info.get("email", existing_account.email)
            existing_account.first_name = user_info.get("first_name", existing_account.first_name)
            existing_account.last_name = user_info.get("last_name", existing_account.last_name)
            existing_account.country_id = user_info.get("country_id", existing_account.country_id)
            existing_account.site_id = user_info.get("site_id", existing_account.site_id)
            existing_account.permalink = user_info.get("permalink", existing_account.permalink)
            existing_account.status = MLAccountStatus.ACTIVE
            existing_account.updated_at = datetime.utcnow()
            
            # Desativar tokens antigos
            db.query(Token).filter(
                Token.ml_account_id == existing_account.id,
                Token.is_active == True
            ).update({"is_active": False})
            
            # Salvar novos tokens
            access_token = Token(
                user_id=user_id,  # Usar usuário logado
                ml_account_id=existing_account.id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type="bearer",
                expires_in=token_data.get("expires_in", 21600),
                scope=token_data.get("scope", ""),
                expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                is_active=True
            )
            db.add(access_token)
            
            action = "atualizada"
        else:
            # CRIAR nova conta ML
            ml_account = MLAccount(
                company_id=company_id,
                ml_user_id=str(user_info["id"]),  # IMPORTANTE: Sempre salvar como string
                nickname=user_info["nickname"],
                email=user_info.get("email", ""),
                first_name=user_info.get("first_name", ""),
                last_name=user_info.get("last_name", ""),
                country_id=user_info.get("country_id", ""),
                site_id=user_info.get("site_id", ""),
                permalink=user_info.get("permalink", ""),
                status=MLAccountStatus.ACTIVE,
                is_primary=False,
                settings={}
            )
            db.add(ml_account)
            db.flush()
            
            # Salvar tokens
            access_token = Token(
                user_id=user_id,  # Usar usuário logado
                ml_account_id=ml_account.id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type="bearer",
                expires_in=token_data.get("expires_in", 21600),
                scope=token_data.get("scope", ""),
                expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                is_active=True
            )
            db.add(access_token)
            
            action = "conectada"
        
        db.commit()
        db.close()
        
        # Redirecionar para página de contas com sucesso
        return RedirectResponse(url=f"/ml/accounts?success={action}", status_code=302)
        
    except Exception as e:
        return RedirectResponse(url=f"/ml/accounts?error=Erro interno: {str(e)}", status_code=302)

@app.get("/callback")
async def callback(code: str = None, error: str = None, state: str = None):
    """Recebe o callback do Mercado Livre (compatibilidade)"""
    from fastapi.responses import RedirectResponse
    from app.config.database import get_db
    from sqlalchemy.orm import Session
    from app.models.saas_models import MLAccount, UserMLAccount, Token, MLAccountStatus
    from datetime import datetime, timedelta
    import requests
    
    if error:
        return RedirectResponse(url=f"/ml/accounts?error={error}", status_code=302)
    
    if not code:
        return RedirectResponse(url="/ml/accounts?error=no_code", status_code=302)
    
    try:
        # Trocar code por access_token
        from app.config.settings import settings
        
        url = f"{settings.ml_token_url}"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.ml_app_id,
            "client_secret": settings.ml_client_secret,
            "code": code,
            "redirect_uri": settings.ml_redirect_uri
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        
        # Obter informações do usuário ML
        user_info_url = "https://api.mercadolibre.com/users/me"
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        user_response = requests.get(user_info_url, headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()
        
        # Para este callback, vamos assumir que é para a empresa padrão
        # Em um sistema real, você precisaria identificar o usuário/empresa
        db = next(get_db())
        
        # Buscar usuário pelo state (que contém o user_id)
        from app.models.saas_models import Company, User
        if not state:
            return RedirectResponse(url="/ml/accounts?error=State não fornecido", status_code=302)
        
        try:
            user_id_from_state = int(state)  # State contém o user_id
            user = db.query(User).filter(User.id == user_id_from_state, User.is_active == True).first()
            if not user:
                return RedirectResponse(url="/ml/accounts?error=Usuário não encontrado", status_code=302)
        except (ValueError, TypeError):
            return RedirectResponse(url="/ml/accounts?error=State inválido", status_code=302)
        
        company_id = user.company_id
        user_id = user.id
        
        # Verificar se a conta ML já existe
        existing_account = db.query(MLAccount).filter(
            MLAccount.ml_user_id == str(user_info["id"]),
            MLAccount.company_id == company_id
        ).first()
        
        if existing_account:
            # ATUALIZAR conta existente
            existing_account.nickname = user_info["nickname"]
            existing_account.email = user_info.get("email", existing_account.email)
            existing_account.first_name = user_info.get("first_name", existing_account.first_name)
            existing_account.last_name = user_info.get("last_name", existing_account.last_name)
            existing_account.country_id = user_info.get("country_id", existing_account.country_id)
            existing_account.site_id = user_info.get("site_id", existing_account.site_id)
            existing_account.permalink = user_info.get("permalink", existing_account.permalink)
            existing_account.status = MLAccountStatus.ACTIVE
            existing_account.updated_at = datetime.utcnow()
            
            # Desativar tokens antigos
            db.query(Token).filter(
                Token.ml_account_id == existing_account.id,
                Token.is_active == True
            ).update({"is_active": False})
            
            # Salvar novos tokens
            access_token = Token(
                user_id=user_id,  # Usar usuário logado
                ml_account_id=existing_account.id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type="bearer",
                expires_in=token_data.get("expires_in", 21600),
                scope=token_data.get("scope", ""),
                expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                is_active=True
            )
            db.add(access_token)
            
            action = "atualizada"
        else:
            # CRIAR nova conta ML
            ml_account = MLAccount(
                company_id=company_id,
                ml_user_id=str(user_info["id"]),  # IMPORTANTE: Sempre salvar como string
                nickname=user_info["nickname"],
                email=user_info.get("email", ""),
                first_name=user_info.get("first_name", ""),
                last_name=user_info.get("last_name", ""),
                country_id=user_info.get("country_id", ""),
                site_id=user_info.get("site_id", ""),
                permalink=user_info.get("permalink", ""),
                status=MLAccountStatus.ACTIVE,
                is_primary=False,
                settings={}
            )
            db.add(ml_account)
            db.flush()
            
            # Salvar tokens
            access_token = Token(
                user_id=user_id,  # Usar usuário logado
                ml_account_id=ml_account.id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type="bearer",
                expires_in=token_data.get("expires_in", 21600),
                scope=token_data.get("scope", ""),
                expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                is_active=True
            )
            db.add(access_token)
            
            action = "conectada"
        
        db.commit()
        db.close()
        
        # Redirecionar para página de contas com sucesso
        return RedirectResponse(url=f"/ml/accounts?success={action}", status_code=302)
        
    except Exception as e:
        return RedirectResponse(url=f"/ml/accounts?error=Erro interno: {str(e)}", status_code=302)


@app.get("/user")
async def get_user_info(access_token: str = None):
    """Obtém informações do usuário (compatibilidade)"""
    from app.controllers.auth_controller import AuthController
    controller = AuthController()
    return await controller.get_user_info(access_token)



@app.get("/dashboard")
async def dashboard(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Dashboard de gestão do usuário"""
    from app.views.template_renderer import render_template
    from app.controllers.auth_controller import AuthController
    from fastapi.responses import RedirectResponse
    
    # Verificar autenticação
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    controller = AuthController()
    result = controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result.get("user")
    # Tentar pegar company_id diretamente ou do objeto company
    company_id = user_data.get("company_id") if user_data else None
    if not company_id and user_data and user_data.get("company"):
        company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return render_template("dashboard_simple.html", request=request, user=user_data)
    
    return render_template("auth_dashboard.html", request=request, user=user_data)

@app.get("/api/dashboard/data")
async def get_dashboard_data_api(
    period: Optional[str] = "30days",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter dados do dashboard de gestão (rota alternativa)"""
    from fastapi.responses import JSONResponse
    from app.controllers.auth_controller import AuthController
    
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    controller = AuthController()
    result = controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result.get("user")
    # Tentar pegar company_id diretamente ou do objeto company
    company_id = user_data.get("company_id") if user_data else None
    if not company_id and user_data and user_data.get("company"):
        company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Empresa não encontrada"}
        )
    
    dashboard_data = controller.get_management_dashboard_data(
        company_id, 
        db, 
        period=period,
        date_from=date_from,
        date_to=date_to
    )
    return JSONResponse(content=dashboard_data)

@app.get("/health")
async def health_check():
    """Verifica saúde da API"""
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "architecture": "MVC"
    }

@app.get("/pricing-analysis")
async def pricing_analysis_page(session_token: str = Cookie(None)):
    """Página de análise de preços e taxas"""
    from app.controllers.auth_controller import AuthController
    from app.config.database import get_db
    from app.views.template_renderer import render_template
    from fastapi.responses import RedirectResponse
    
    # Se não há session_token como parâmetro, redirecionar para login
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    controller = AuthController()
    db = next(get_db())
    result = controller.get_user_by_session(session_token, db)
    
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return render_template("pricing_analysis.html", user=result["user"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
