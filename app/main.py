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
from app.routes.ml_claims_routes import ml_claims_router
from app.routes.activity_routes import activity_router
from app.routes.openai_assistant_routes import openai_assistant_router, openai_chat_router, tools_router
from app.routes.stock_routes import stock_router
from app.routes.stock_projection_routes import stock_projection_router
from app.routes.internal_product_routes import internal_product_router
from app.routes.support_routes import support_router
from app.routes.hr_routes import hr_router
from app.routes.task_routes import task_router
from app.routes.content_routes import content_router
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
    title="SELVEZ - Gestão Inteligente de Vendas para Marketplace",
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

# JOB 1: Sincronização rápida a cada 30 minutos (pedidos novos) - DESABILITADO
# Webhook orders_v2 mantém pedidos atualizados automaticamente
# scheduler.add_job(
#     func=run_recent_sync,
#     trigger=IntervalTrigger(minutes=30),
#     id='auto_sync_recent_orders',
#     name='Sincronização automática - Pedidos novos (30min)',
#     replace_existing=True
# )

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
                        
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'supportticketstatus') THEN
                            CREATE TYPE supportticketstatus AS ENUM ('open', 'in_progress', 'waiting_user', 'resolved', 'closed');
                        END IF;
                        
                        -- Criar/atualizar enum userrole se não existir
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                            CREATE TYPE userrole AS ENUM ('super_admin', 'company_admin', 'manager', 'analyst', 'viewer');
                        ELSE
                            -- Se o enum já existe, adicionar valores que faltam
                            IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole') AND enumlabel = 'analyst') THEN
                                ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'analyst';
                            END IF;
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
                    
                    # Adicionar suporte a múltiplos providers (CRÍTICO - deve ser antes de criar agentes)
                    print("📋 [STARTUP] Adicionando suporte a múltiplos providers...")
                    provider_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                'database', 'fixes', 'add_provider_support_to_agents.py')
                    # Tentar caminho alternativo
                    if not os.path.exists(provider_script_path):
                        provider_script_path = os.path.join('/app', 'database', 'fixes', 'add_provider_support_to_agents.py')
                    
                    if os.path.exists(provider_script_path):
                        try:
                            provider_spec = importlib.util.spec_from_file_location("add_provider_support_to_agents", provider_script_path)
                            provider_module = importlib.util.module_from_spec(provider_spec)
                            provider_spec.loader.exec_module(provider_module)
                            # Passar a sessão db atual para o script
                            result = provider_module.add_provider_support(db)
                            if result.get("success"):
                                print("✅ [STARTUP] Suporte a múltiplos providers adicionado")
                            else:
                                print(f"⚠️ [STARTUP] Providers: {result.get('message', 'já configurado ou erro')}")
                                if result.get("error"):
                                    print(f"❌ [STARTUP] Erro ao adicionar providers: {result.get('error')}")
                                    import traceback
                                    traceback.print_exc()
                        except Exception as e:
                            print(f"❌ [STARTUP] Erro ao executar script de providers: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"⚠️ [STARTUP] Script de providers não encontrado. Tentou: {provider_script_path}")
                    
                    # Tornar company_id nullable em briefings (para superadmin)
                    briefing_nullable_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                'database', 'fixes', 'make_company_id_nullable_in_briefings.py')
                    if not os.path.exists(briefing_nullable_path):
                        briefing_nullable_path = os.path.join('/app', 'database', 'fixes', 'make_company_id_nullable_in_briefings.py')
                    
                    if os.path.exists(briefing_nullable_path):
                        try:
                            nullable_spec = importlib.util.spec_from_file_location("make_company_id_nullable_in_briefings", briefing_nullable_path)
                            nullable_module = importlib.util.module_from_spec(nullable_spec)
                            nullable_spec.loader.exec_module(nullable_module)
                            result = nullable_module.make_company_id_nullable()
                            if result.get("success"):
                                print("✅ [STARTUP] company_id nullable em briefings configurado")
                            else:
                                print(f"ℹ️ [STARTUP] company_id nullable: {result.get('message', 'já configurado ou erro')}")
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro ao tornar company_id nullable: {e}")
                    
                    # Criar tabelas de suporte
                    support_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                            'database', 'fixes', 'create_support_tickets_tables.py')
                    if os.path.exists(support_script_path):
                        support_spec = importlib.util.spec_from_file_location("create_support_tickets_tables", support_script_path)
                        support_module = importlib.util.module_from_spec(support_spec)
                        support_spec.loader.exec_module(support_module)
                        support_module.create_support_tickets_tables()
                        print("✅ [STARTUP] Tabelas de suporte verificadas/criadas")
                    
                    # Criar tabelas de RH
                    print("📋 [STARTUP] Verificando tabelas de RH...")
                    hr_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            'database', 'fixes', 'create_hr_tables.py')
                    # Tentar caminho alternativo se não encontrar
                    if not os.path.exists(hr_script_path):
                        hr_script_path = os.path.join('/app', 'database', 'fixes', 'create_hr_tables.py')
                    if os.path.exists(hr_script_path):
                        print(f"📋 [STARTUP] Script encontrado: {hr_script_path}")
                        hr_spec = importlib.util.spec_from_file_location("create_hr_tables", hr_script_path)
                        hr_module = importlib.util.module_from_spec(hr_spec)
                        hr_spec.loader.exec_module(hr_module)
                        hr_module.create_hr_tables()
                        print("✅ [STARTUP] Tabelas de RH verificadas/criadas")
                    else:
                        print(f"⚠️ [STARTUP] Script de RH não encontrado. Tentou: {hr_script_path}")
                    
                    # Criar tabelas de Tarefas
                    print("📋 [STARTUP] Verificando tabelas de Tarefas...")
                    task_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            'database', 'fixes', 'create_tasks_tables.py')
                    # Tentar caminho alternativo se não encontrar
                    if not os.path.exists(task_script_path):
                        task_script_path = os.path.join('/app', 'database', 'fixes', 'create_tasks_tables.py')
                    if os.path.exists(task_script_path):
                        print(f"📋 [STARTUP] Script encontrado: {task_script_path}")
                        task_spec = importlib.util.spec_from_file_location("create_tasks_tables", task_script_path)
                        task_module = importlib.util.module_from_spec(task_spec)
                        task_spec.loader.exec_module(task_module)
                        task_module.create_tasks_tables()
                        print("✅ [STARTUP] Tabelas de Tarefas verificadas/criadas")
                    else:
                        print(f"⚠️ [STARTUP] Script de tarefas não encontrado. Tentou: {task_script_path}")
                    
                    # Criar tabelas de Planejamento de Conteúdo
                    print("📋 [STARTUP] Verificando tabelas de Planejamento de Conteúdo...")
                    content_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            'database', 'fixes', 'create_content_tables.py')
                    # Tentar caminho alternativo se não encontrar
                    if not os.path.exists(content_script_path):
                        content_script_path = os.path.join('/app', 'database', 'fixes', 'create_content_tables.py')
                    if os.path.exists(content_script_path):
                        print(f"📋 [STARTUP] Script encontrado: {content_script_path}")
                        content_spec = importlib.util.spec_from_file_location("create_content_tables", content_script_path)
                        content_module = importlib.util.module_from_spec(content_spec)
                        content_spec.loader.exec_module(content_module)
                        content_module.create_content_tables()
                        print("✅ [STARTUP] Tabelas de Planejamento de Conteúdo verificadas/criadas")
                    else:
                        print(f"⚠️ [STARTUP] Script de conteúdo não encontrado. Tentou: {content_script_path}")
                    
                    # Criar tabela de Briefings de Marketing
                    print("📋 [STARTUP] Verificando tabela de Briefings...")
                    briefing_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            'database', 'fixes', 'create_content_briefings_table.py')
                    # Tentar caminho alternativo se não encontrar
                    if not os.path.exists(briefing_script_path):
                        briefing_script_path = os.path.join('/app', 'database', 'fixes', 'create_content_briefings_table.py')
                    if os.path.exists(briefing_script_path):
                        print(f"📋 [STARTUP] Script encontrado: {briefing_script_path}")
                        try:
                            briefing_spec = importlib.util.spec_from_file_location("create_content_briefings_table", briefing_script_path)
                            briefing_module = importlib.util.module_from_spec(briefing_spec)
                            briefing_spec.loader.exec_module(briefing_module)
                            briefing_module.create_content_briefings_table()
                            print("✅ [STARTUP] Tabela de Briefings verificada/criada")
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro ao criar tabela de Briefings: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"⚠️ [STARTUP] Script de briefings não encontrado. Tentou: {briefing_script_path}")
                    
                    # Tornar company_id nullable em openai_assistant_usage (para superadmin)
                    print("🔓 [STARTUP] Verificando company_id nullable em openai_assistant_usage...")
                    usage_nullable_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            'database', 'fixes', 'make_company_id_nullable_in_openai_assistant_usage.py')
                    if not os.path.exists(usage_nullable_path):
                        usage_nullable_path = os.path.join('/app', 'database', 'fixes', 'make_company_id_nullable_in_openai_assistant_usage.py')
                    
                    if os.path.exists(usage_nullable_path):
                        try:
                            usage_nullable_spec = importlib.util.spec_from_file_location("make_company_id_nullable_in_openai_assistant_usage", usage_nullable_path)
                            usage_nullable_module = importlib.util.module_from_spec(usage_nullable_spec)
                            usage_nullable_spec.loader.exec_module(usage_nullable_module)
                            usage_nullable_module.run(db)
                            print("✅ [STARTUP] company_id nullable em openai_assistant_usage configurado")
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro ao tornar company_id nullable em openai_assistant_usage: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"⚠️ [STARTUP] Script de usage nullable não encontrado. Tentou: {usage_nullable_path}")
                    
                    # Tornar company_id nullable em openai_assistant_threads (para superadmin)
                    print("🔓 [STARTUP] Verificando company_id nullable em openai_assistant_threads...")
                    threads_nullable_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            'database', 'fixes', 'make_company_id_nullable_in_openai_assistant_threads.py')
                    if not os.path.exists(threads_nullable_path):
                        threads_nullable_path = os.path.join('/app', 'database', 'fixes', 'make_company_id_nullable_in_openai_assistant_threads.py')
                    
                    if os.path.exists(threads_nullable_path):
                        try:
                            threads_nullable_spec = importlib.util.spec_from_file_location("make_company_id_nullable_in_openai_assistant_threads", threads_nullable_path)
                            threads_nullable_module = importlib.util.module_from_spec(threads_nullable_spec)
                            threads_nullable_spec.loader.exec_module(threads_nullable_module)
                            threads_nullable_module.run(db)
                            print("✅ [STARTUP] company_id nullable em openai_assistant_threads configurado")
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro ao tornar company_id nullable em openai_assistant_threads: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"⚠️ [STARTUP] Script de threads nullable não encontrado. Tentou: {threads_nullable_path}")
                    
                    # Adicionar coluna hide_product_data
                    print("🔒 [STARTUP] Verificando coluna hide_product_data...")
                    hide_data_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                'database', 'fixes', 'add_hide_product_data_column.py')
                    if not os.path.exists(hide_data_script_path):
                        hide_data_script_path = os.path.join('/app', 'database', 'fixes', 'add_hide_product_data_column.py')
                    if os.path.exists(hide_data_script_path):
                        print(f"🔒 [STARTUP] Script encontrado: {hide_data_script_path}")
                        hide_data_spec = importlib.util.spec_from_file_location("add_hide_product_data_column", hide_data_script_path)
                        hide_data_module = importlib.util.module_from_spec(hide_data_spec)
                        hide_data_spec.loader.exec_module(hide_data_module)
                        hide_data_module.add_hide_product_data_column()
                        print("✅ [STARTUP] Coluna hide_product_data verificada/criada")
                    else:
                        print(f"⚠️ [STARTUP] Script hide_product_data não encontrado. Tentou: {hide_data_script_path}")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Tabelas podem já existir: {e}")
                finally:
                    db.close()
 
                # 1.0 Criar/garantir tabelas de Ferramentas reutilizáveis
                try:
                    import importlib.util
                    import os
                    print("🔄 [STARTUP] Iniciando setup de ferramentas...")
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
                    else:
                        print(f"⚠️ [STARTUP] Arquivo de tabelas não encontrado: {tools_path}")
                    # Primeiro, remover/desativar ferramentas antigas
                    cleanup_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_11_23_remove_deprecated_tools.py'
                    )
                    cleanup_executed = False
                    if os.path.exists(cleanup_path):
                        try:
                            print(f"🔄 [STARTUP] Executando limpeza de ferramentas antigas...")
                            spec_cleanup = importlib.util.spec_from_file_location("remove_deprecated_tools", cleanup_path)
                            cleanup_module = importlib.util.module_from_spec(spec_cleanup)
                            spec_cleanup.loader.exec_module(cleanup_module)
                            cleanup_result = cleanup_module.run(db)
                            if cleanup_result.get("success"):
                                print(f"✅ [STARTUP] {cleanup_result.get('tools_deactivated', 0)} ferramentas antigas desativadas")
                                cleanup_executed = True
                            else:
                                print(f"⚠️ [STARTUP] Erro na limpeza: {cleanup_result.get('error', 'Erro desconhecido')}")
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro ao executar script de limpeza: {e}")
                    
                    # Fallback: executar SQL diretamente se script não foi encontrado ou falhou
                    if not cleanup_executed:
                        print(f"🔄 [STARTUP] Executando limpeza via SQL direto (fallback)...")
                        try:
                            deprecated_tools = ["get_ml_order_status", "get_product_info"]
                            for tool_name in deprecated_tools:
                                db.execute(
                                    text("UPDATE openai_tools SET is_active = FALSE WHERE name = :name"),
                                    {"name": tool_name}
                                )
                                db.execute(
                                    text("""
                                        UPDATE openai_tool_handlers 
                                        SET is_active = FALSE 
                                        WHERE tool_id IN (SELECT id FROM openai_tools WHERE name = :name)
                                    """),
                                    {"name": tool_name}
                                )
                            db.commit()
                            print(f"✅ [STARTUP] Limpeza via SQL concluída")
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro na limpeza via SQL: {e}")
                            db.rollback()
                    
                    # Seed de TODAS as ferramentas do agente IA
                    # Tentar múltiplos caminhos possíveis
                    possible_seed_paths = [
                        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'fixes', '2025_11_23_seed_all_ai_tools.py'),
                        '/app/database/fixes/2025_11_23_seed_all_ai_tools.py',
                        os.path.join(os.getcwd(), 'database', 'fixes', '2025_11_23_seed_all_ai_tools.py'),
                    ]
                    
                    seed_executed = False
                    seed_path = None
                    for path in possible_seed_paths:
                        if os.path.exists(path):
                            seed_path = path
                            break
                    
                    if seed_path:
                        try:
                            print(f"🔄 [STARTUP] Executando seed de ferramentas de {seed_path}...")
                            spec2 = importlib.util.spec_from_file_location("seed_all_ai_tools", seed_path)
                            seed_module = importlib.util.module_from_spec(spec2)
                            spec2.loader.exec_module(seed_module)
                            result = seed_module.run(db)
                            if result.get("success"):
                                # Garantir que o commit foi efetivado
                                try:
                                    db.commit()
                                    # Verificar quantas ferramentas foram realmente criadas
                                    tool_count = db.execute(text("SELECT COUNT(*) FROM openai_tools WHERE is_active = TRUE")).scalar()
                                    print(f"✅ [STARTUP] {result.get('tools_registered', 0)} ferramentas registradas. Total ativo no banco: {tool_count}")
                                    seed_executed = True
                                except Exception as commit_error:
                                    print(f"⚠️ [STARTUP] Erro ao confirmar commit: {commit_error}")
                                    db.rollback()
                            else:
                                print(f"⚠️ [STARTUP] Erro ao registrar ferramentas: {result.get('error', 'Erro desconhecido')}")
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro ao executar script de seed: {e}")
                            import traceback
                            traceback.print_exc()
                            try:
                                db.rollback()
                            except Exception:
                                pass
                    
                    # Fallback: tentar importar diretamente se estiver no PYTHONPATH
                    if not seed_executed:
                        try:
                            print(f"🔄 [STARTUP] Tentando importar seed_all_ai_tools diretamente...")
                            import sys
                            # Adicionar caminhos possíveis ao sys.path
                            for base_path in [
                                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                '/app',
                                os.getcwd()
                            ]:
                                db_fixes_path = os.path.join(base_path, 'database', 'fixes')
                                if db_fixes_path not in sys.path and os.path.exists(db_fixes_path):
                                    sys.path.insert(0, db_fixes_path)
                                    print(f"📁 [STARTUP] Adicionado ao path: {db_fixes_path}")
                            
                            # Tentar importar usando importlib com caminho absoluto
                            import importlib.util
                            for base_path in [
                                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                '/app',
                                os.getcwd()
                            ]:
                                potential_path = os.path.join(base_path, 'database', 'fixes', '2025_11_23_seed_all_ai_tools.py')
                                if os.path.exists(potential_path):
                                    print(f"📁 [STARTUP] Tentando importar de: {potential_path}")
                                    spec = importlib.util.spec_from_file_location("seed_all_ai_tools_fallback", potential_path)
                                    if spec and spec.loader:
                                        seed_module = importlib.util.module_from_spec(spec)
                                        spec.loader.exec_module(seed_module)
                                        result = seed_module.run(db)
                                        if result.get("success"):
                                            print(f"✅ [STARTUP] {result.get('tools_registered', 0)} ferramentas do agente IA registradas (via import direto)")
                                            seed_executed = True
                                            break
                        except Exception as e:
                            print(f"⚠️ [STARTUP] Erro ao importar seed diretamente: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    if not seed_executed:
                        print(f"❌ [STARTUP] IMPORTANTE: Não foi possível executar seed de ferramentas!")
                        print(f"❌ [STARTUP] Verifique se os arquivos estão em /app/database/fixes/")
                        print(f"❌ [STARTUP] Caminhos testados:")
                        for path in possible_seed_paths:
                            exists = "✅" if os.path.exists(path) else "❌"
                            print(f"   {exists} {path}")
                        print(f"❌ [STARTUP] Execute manualmente: python database/fixes/2025_11_23_seed_all_ai_tools.py")
                        # Fallback para o script antigo se o novo não existir
                        old_seed_path = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            'database', 'fixes', '2025_11_16_seed_product_analysis_tools.py'
                        )
                        if os.path.exists(old_seed_path):
                            spec2 = importlib.util.spec_from_file_location("seed_product_analysis_tools", old_seed_path)
                            seed_module = importlib.util.module_from_spec(spec2)
                            spec2.loader.exec_module(seed_module)
                            seed_module.run(db)
                            print("✅ [STARTUP] Ferramentas de análise de produto seedadas (script antigo)")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar tabelas de Ferramentas: {e}")
                finally:
                    # IMPORTANTE: Fechar sessão e garantir que commits foram efetivados
                    try:
                        db.commit()
                        # Verificar quantas ferramentas estão realmente no banco
                        tool_count = db.execute(text("SELECT COUNT(*) FROM openai_tools WHERE is_active = TRUE")).scalar()
                        print(f"📊 [STARTUP] Total de ferramentas ativas no banco após seed: {tool_count}")
                    except Exception as commit_error:
                        print(f"⚠️ [STARTUP] Erro ao fazer commit final: {commit_error}")
                        try:
                            db.rollback()
                        except Exception:
                            pass
                    finally:
                        db.close()

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

                # 1.05.1 Criar agente "Analise cadastro produto" se não existir
                try:
                    import importlib.util
                    import os
                    agent_registration_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_12_01_create_product_registration_analysis_agent.py'
                    )
                    # Tentar caminho alternativo
                    if not os.path.exists(agent_registration_path):
                        agent_registration_path = os.path.join('/app', 'database', 'fixes', '2025_12_01_create_product_registration_analysis_agent.py')
                    
                    if os.path.exists(agent_registration_path):
                        spec_registration = importlib.util.spec_from_file_location("create_product_registration_analysis_agent", agent_registration_path)
                        registration_module = importlib.util.module_from_spec(spec_registration)
                        spec_registration.loader.exec_module(registration_module)
                        result = registration_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Agente 'Analise cadastro produto' verificado/criado")
                        else:
                            print(f"ℹ️ [STARTUP] Agente 'Analise cadastro produto': {result.get('message', 'já existe ou erro')}")
                    else:
                        print(f"⚠️ [STARTUP] Script de criação do agente 'Analise cadastro produto' não encontrado em: {agent_registration_path}")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar agente 'Analise cadastro produto': {e}")
                    import traceback
                    traceback.print_exc()

                # 1.05.2 Atualizar instructions e initial_prompt do agente "Analise cadastro produto"
                # Este script atualiza tanto instructions quanto initial_prompt com todas as instruções completas
                try:
                    import importlib.util
                    import os
                    update_instructions_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_12_01_update_product_registration_analysis_agent_instructions.py'
                    )
                    # Tentar caminho alternativo
                    if not os.path.exists(update_instructions_path):
                        update_instructions_path = os.path.join('/app', 'database', 'fixes', '2025_12_01_update_product_registration_analysis_agent_instructions.py')
                    
                    if os.path.exists(update_instructions_path):
                        spec_update = importlib.util.spec_from_file_location("update_product_registration_analysis_agent_instructions", update_instructions_path)
                        update_module = importlib.util.module_from_spec(spec_update)
                        spec_update.loader.exec_module(update_module)
                        result = update_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Instructions e initial_prompt do agente 'Analise cadastro produto' atualizados")
                        else:
                            print(f"⚠️ [STARTUP] Erro ao atualizar agente: {result.get('error', 'Erro desconhecido')}")
                    else:
                        print(f"⚠️ [STARTUP] Script de atualização do agente 'Analise cadastro produto' não encontrado em: {update_instructions_path}")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível atualizar instructions do agente 'Analise cadastro produto': {e}")
                    import traceback
                    traceback.print_exc()

                # 1.05.3 Atualizar max_tokens do agente "Analise cadastro produto" (se necessário)
                try:
                    import importlib.util
                    import os
                    update_tokens_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_12_01_update_product_registration_analysis_agent_max_tokens.py'
                    )
                    # Tentar caminho alternativo
                    if not os.path.exists(update_tokens_path):
                        update_tokens_path = os.path.join('/app', 'database', 'fixes', '2025_12_01_update_product_registration_analysis_agent_max_tokens.py')
                    
                    if os.path.exists(update_tokens_path):
                        spec_tokens = importlib.util.spec_from_file_location("update_product_registration_analysis_agent_max_tokens", update_tokens_path)
                        tokens_module = importlib.util.module_from_spec(spec_tokens)
                        spec_tokens.loader.exec_module(tokens_module)
                        result = tokens_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Max tokens do agente 'Analise cadastro produto' atualizado para 16000")
                        else:
                            print(f"ℹ️ [STARTUP] Max tokens: {result.get('message', 'já atualizado ou erro')}")
                    else:
                        print(f"⚠️ [STARTUP] Script de atualização de max_tokens não encontrado em: {update_tokens_path}")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível atualizar max_tokens do agente 'Analise cadastro produto': {e}")

                # 1.06 Criar agente "Criar Descrição de Produto" se não existir
                try:
                    import importlib.util
                    import os
                    agent_description_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'database', 'fixes', '2025_12_01_create_product_description_agent.py'
                    )
                    if not os.path.exists(agent_description_path):
                        agent_description_path = os.path.join('/app', 'database', 'fixes', '2025_12_01_create_product_description_agent.py')
                    
                    if os.path.exists(agent_description_path):
                        spec_description = importlib.util.spec_from_file_location("create_product_description_agent", agent_description_path)
                        description_module = importlib.util.module_from_spec(spec_description)
                        spec_description.loader.exec_module(description_module)
                        result = description_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Agente 'Criar Descrição de Produto' verificado/criado")
                        else:
                            print(f"ℹ️ [STARTUP] Agente 'Criar Descrição de Produto': {result.get('message', 'já existe ou erro')}")
                    else:
                        print(f"⚠️ [STARTUP] Script de criação do agente 'Criar Descrição de Produto' não encontrado")
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar agente 'Criar Descrição de Produto': {e}")
                    import traceback
                    traceback.print_exc()
                
                # Criar agentes multi-provider
                try:
                    # Perplexity - Pesquisa
                    perplexity_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        'database', 'fixes', 'create_perplexity_research_agent.py')
                    if not os.path.exists(perplexity_path):
                        perplexity_path = os.path.join('/app', 'database', 'fixes', 'create_perplexity_research_agent.py')
                    if os.path.exists(perplexity_path):
                        spec_perplexity = importlib.util.spec_from_file_location("create_perplexity_research_agent", perplexity_path)
                        perplexity_module = importlib.util.module_from_spec(spec_perplexity)
                        spec_perplexity.loader.exec_module(perplexity_module)
                        result = perplexity_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Agente 'Pesquisa de Conteúdo' (Perplexity) verificado/criado")
                        else:
                            print(f"ℹ️ [STARTUP] Agente 'Pesquisa de Conteúdo': {result.get('message', 'já existe ou erro')}")
                    
                    # Anthropic - Texto
                    anthropic_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        'database', 'fixes', 'create_anthropic_text_agent.py')
                    if not os.path.exists(anthropic_path):
                        anthropic_path = os.path.join('/app', 'database', 'fixes', 'create_anthropic_text_agent.py')
                    if os.path.exists(anthropic_path):
                        spec_anthropic = importlib.util.spec_from_file_location("create_anthropic_text_agent", anthropic_path)
                        anthropic_module = importlib.util.module_from_spec(spec_anthropic)
                        spec_anthropic.loader.exec_module(anthropic_module)
                        result = anthropic_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Agente 'Criação de Texto' (Anthropic) verificado/criado")
                        else:
                            print(f"ℹ️ [STARTUP] Agente 'Criação de Texto': {result.get('message', 'já existe ou erro')}")
                    
                    # Google - Vídeo
                    google_video_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        'database', 'fixes', 'create_google_video_agent.py')
                    if not os.path.exists(google_video_path):
                        google_video_path = os.path.join('/app', 'database', 'fixes', 'create_google_video_agent.py')
                    if os.path.exists(google_video_path):
                        spec_google_video = importlib.util.spec_from_file_location("create_google_video_agent", google_video_path)
                        google_video_module = importlib.util.module_from_spec(spec_google_video)
                        spec_google_video.loader.exec_module(google_video_module)
                        result = google_video_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Agente 'Geração de Vídeo' (Google VEO) verificado/criado")
                        else:
                            print(f"ℹ️ [STARTUP] Agente 'Geração de Vídeo': {result.get('message', 'já existe ou erro')}")
                    
                    # Google - Imagem
                    google_image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        'database', 'fixes', 'create_google_image_agent.py')
                    if not os.path.exists(google_image_path):
                        google_image_path = os.path.join('/app', 'database', 'fixes', 'create_google_image_agent.py')
                    if os.path.exists(google_image_path):
                        spec_google_image = importlib.util.spec_from_file_location("create_google_image_agent", google_image_path)
                        google_image_module = importlib.util.module_from_spec(spec_google_image)
                        spec_google_image.loader.exec_module(google_image_module)
                        result = google_image_module.run(db)
                        if result.get("success"):
                            print("✅ [STARTUP] Agente 'Geração de Imagem' (Google Imagen) verificado/criado")
                        else:
                            print(f"ℹ️ [STARTUP] Agente 'Geração de Imagem': {result.get('message', 'já existe ou erro')}")
                    
                    # Agentes de Briefing de Marketing
                    briefing_agents = [
                        ('create_briefing_generator_agent.py', 'Gerador de Briefing'),
                        ('create_briefing_orchestrator_agent.py', 'Orquestrador de Briefing'),
                        ('create_seo_optimization_agent.py', 'Otimização SEO'),
                        ('create_social_copy_agent.py', 'Copy para Redes Sociais'),
                        ('create_email_marketing_agent.py', 'Email Marketing'),
                        ('create_video_script_agent.py', 'Scripts de Vídeo')
                    ]
                    
                    for script_name, agent_name in briefing_agents:
                        try:
                            agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            'database', 'fixes', script_name)
                            if not os.path.exists(agent_path):
                                agent_path = os.path.join('/app', 'database', 'fixes', script_name)
                            if os.path.exists(agent_path):
                                print(f"📋 [STARTUP] Executando script: {script_name}")
                                module_name = script_name.replace('.py', '')
                                spec_agent = importlib.util.spec_from_file_location(module_name, agent_path)
                                agent_module = importlib.util.module_from_spec(spec_agent)
                                spec_agent.loader.exec_module(agent_module)
                                result = agent_module.run(db)
                                if result.get("success"):
                                    print(f"✅ [STARTUP] Agente '{agent_name}' verificado/criado")
                                else:
                                    print(f"ℹ️ [STARTUP] Agente '{agent_name}': {result.get('message', 'já existe ou erro')}")
                                    if result.get("error"):
                                        print(f"❌ [STARTUP] Erro detalhado: {result.get('error')}")
                            else:
                                print(f"⚠️ [STARTUP] Script não encontrado: {script_name} (tentou: {agent_path})")
                        except Exception as e:
                            print(f"❌ [STARTUP] Erro ao criar agente '{agent_name}': {e}")
                            import traceback
                            traceback.print_exc()
                            
                except Exception as e:
                    print(f"⚠️ [STARTUP] Não foi possível criar agentes multi-provider: {e}")
                    import traceback
                    traceback.print_exc()

                # 1.07 Adicionar instrução de idioma português ao agente
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
                try:
                    db.execute(text(sql_memory))
                    db.commit()
                except Exception as e:
                    error_msg = str(e)
                    # Tentar rollback apenas se não houver erro de transação
                    if "transaction is already begun" not in error_msg.lower():
                        try:
                            db.rollback()
                        except:
                            pass
                    print(f"⚠️ [STARTUP] Erro ao adicionar colunas de memória (podem já existir): {error_msg}")
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
                try:
                    db.execute(text(sql_initial_prompt))
                    db.commit()
                except Exception as e:
                    error_msg = str(e)
                    # Tentar rollback apenas se não houver erro de transação
                    if "transaction is already begun" not in error_msg.lower():
                        try:
                            db.rollback()
                        except:
                            pass
                    print(f"⚠️ [STARTUP] Erro ao adicionar coluna initial_prompt (pode já existir): {error_msg}")
                print("✅ [STARTUP] Coluna initial_prompt verificada/adicionada")
                
                # 4. Criar ENUMs e tabelas de estoque
                print("📋 [STARTUP] ========== INICIANDO CRIAÇÃO DE TABELAS DE ESTOQUE E CLAIMS ==========")
                print("📋 [STARTUP] Verificando tabelas de estoque...")
                print(f"📋 [STARTUP] DEBUG: db session status - {db.is_active if hasattr(db, 'is_active') else 'N/A'}")
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
                    try:
                        db.execute(create_stock_enums_sql)
                        db.commit()
                        print("✅ [STARTUP] ENUMs de estoque verificados/criados")
                    except Exception as e:
                        error_msg = str(e)
                        # Tentar rollback apenas se não houver erro de transação
                        if "transaction is already begun" not in error_msg.lower():
                            try:
                                db.rollback()
                            except:
                                pass
                        print(f"⚠️ [STARTUP] Erro ao criar ENUMs de estoque (podem já existir): {error_msg}")
                    
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
                    
                    # Verificar e criar tabelas de pacotes de tokens
                    check_token_packages_query = text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('token_packages', 'token_package_purchases')
                    """)
                    existing_token_tables = [row[0] for row in db.execute(check_token_packages_query).fetchall()]
                    
                    if 'token_packages' not in existing_token_tables:
                        print("📋 [STARTUP] Criando tabela token_packages...")
                        create_token_packages_sql = text("""
                            CREATE TABLE token_packages (
                                id SERIAL PRIMARY KEY,
                                name VARCHAR(255) NOT NULL,
                                description TEXT,
                                tokens_amount INTEGER NOT NULL,
                                price VARCHAR(50) NOT NULL,
                                currency VARCHAR(10) DEFAULT 'BRL',
                                is_active BOOLEAN DEFAULT TRUE,
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                            );
                            
                            CREATE INDEX IF NOT EXISTS ix_token_packages_is_active ON token_packages(is_active);
                        """)
                        db.execute(create_token_packages_sql)
                        db.commit()
                        print("✅ [STARTUP] Tabela token_packages criada")
                    
                    if 'token_package_purchases' not in existing_token_tables:
                        print("📋 [STARTUP] Criando tabela token_package_purchases...")
                        create_token_package_purchases_sql = text("""
                            CREATE TABLE token_package_purchases (
                                id SERIAL PRIMARY KEY,
                                company_id INTEGER NOT NULL,
                                package_id INTEGER NOT NULL,
                                tokens_amount INTEGER NOT NULL,
                                price VARCHAR(50) NOT NULL,
                                currency VARCHAR(10) DEFAULT 'BRL',
                                payment_method VARCHAR(50),
                                payment_status VARCHAR(50) DEFAULT 'pending',
                                asaas_payment_id VARCHAR(100),
                                invoice_url VARCHAR(500),
                                purchased_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                confirmed_at TIMESTAMP WITH TIME ZONE,
                                CONSTRAINT fk_token_package_purchases_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                CONSTRAINT fk_token_package_purchases_package FOREIGN KEY (package_id) REFERENCES token_packages(id) ON DELETE CASCADE
                            );
                            
                            CREATE INDEX IF NOT EXISTS ix_token_package_purchases_company_id ON token_package_purchases(company_id);
                            CREATE INDEX IF NOT EXISTS ix_token_package_purchases_package_id ON token_package_purchases(package_id);
                            CREATE INDEX IF NOT EXISTS ix_token_package_purchases_payment_status ON token_package_purchases(payment_status);
                            CREATE INDEX IF NOT EXISTS ix_token_package_purchases_asaas_payment_id ON token_package_purchases(asaas_payment_id);
                            CREATE INDEX IF NOT EXISTS ix_token_package_purchases_purchased_at ON token_package_purchases(purchased_at);
                        """)
                        db.execute(create_token_package_purchases_sql)
                        db.commit()
                        print("✅ [STARTUP] Tabela token_package_purchases criada")
                    
                    # Verificar e criar tabelas de claims (pós-venda)
                    print("📋 [STARTUP] ========== INICIANDO CRIAÇÃO DE TABELAS DE CLAIMS ==========")
                    print("📋 [STARTUP] Verificando tabelas de claims (pós-venda)...")
                    try:
                        check_claims_query = text("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name IN ('ml_claims', 'ml_claim_messages', 'ml_claim_evidences')
                        """)
                        existing_claims_tables = [row[0] for row in db.execute(check_claims_query).fetchall()]
                        print(f"📋 [STARTUP] Tabelas de claims existentes: {existing_claims_tables}")
                    except Exception as e:
                        print(f"⚠️ [STARTUP] Erro ao verificar tabelas de claims: {e}")
                        existing_claims_tables = []
                    
                    if 'ml_claims' not in existing_claims_tables:
                        print("📋 [STARTUP] Criando tabela ml_claims...")
                        print(f"📋 [STARTUP] DEBUG: existing_claims_tables = {existing_claims_tables}")
                        try:
                            create_ml_claims_sql = text("""
                                CREATE TABLE ml_claims (
                                    id SERIAL PRIMARY KEY,
                                    company_id INTEGER NOT NULL,
                                    ml_account_id INTEGER NOT NULL,
                                    ml_claim_id VARCHAR(50) UNIQUE NOT NULL,
                                    ml_order_id VARCHAR(50),
                                    ml_buyer_id VARCHAR(50),
                                    ml_seller_id VARCHAR(50) NOT NULL,
                                    claim_type VARCHAR(20) NOT NULL,
                                    status VARCHAR(20) NOT NULL,
                                    resolution_reason VARCHAR(50),
                                    resolution_status VARCHAR(50),
                                    resolution_date TIMESTAMP WITH TIME ZONE,
                                    date_created TIMESTAMP WITH TIME ZONE NOT NULL,
                                    date_updated TIMESTAMP WITH TIME ZONE,
                                    date_closed TIMESTAMP WITH TIME ZONE,
                                    buyer_nickname VARCHAR(255),
                                    claim_data JSONB,
                                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                    last_sync TIMESTAMP WITH TIME ZONE,
                                    CONSTRAINT fk_ml_claims_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                    CONSTRAINT fk_ml_claims_ml_account FOREIGN KEY (ml_account_id) REFERENCES ml_accounts(id) ON DELETE CASCADE
                                );
                                
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_company_id ON ml_claims(company_id);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_ml_account_id ON ml_claims(ml_account_id);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_ml_claim_id ON ml_claims(ml_claim_id);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_status ON ml_claims(status);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_claim_type ON ml_claims(claim_type);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_date_created ON ml_claims(date_created);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_ml_order_id ON ml_claims(ml_order_id);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_company_status ON ml_claims(company_id, status);
                                CREATE INDEX IF NOT EXISTS ix_ml_claims_company_type ON ml_claims(company_id, claim_type);
                            """)
                            db.execute(create_ml_claims_sql)
                            db.commit()
                            print("✅ [STARTUP] Tabela ml_claims criada com sucesso")
                            # Verificar se foi criada
                            verify_query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'ml_claims'")
                            verify_result = db.execute(verify_query).fetchall()
                            if verify_result:
                                print("✅ [STARTUP] CONFIRMADO: Tabela ml_claims existe no banco")
                            else:
                                print("⚠️ [STARTUP] AVISO: Tabela ml_claims não foi encontrada após criação")
                        except Exception as e:
                            db.rollback()
                            print(f"❌ [STARTUP] ERRO CRÍTICO ao criar tabela ml_claims: {e}")
                            import traceback
                            traceback.print_exc()
                            # Não re-raise para não bloquear startup, mas loga o erro detalhadamente
                    
                    if 'ml_claim_messages' not in existing_claims_tables:
                        print("📋 [STARTUP] Criando tabela ml_claim_messages...")
                        try:
                            create_ml_claim_messages_sql = text("""
                                CREATE TABLE ml_claim_messages (
                                    id SERIAL PRIMARY KEY,
                                    claim_id INTEGER NOT NULL,
                                    ml_message_id VARCHAR(50) UNIQUE NOT NULL,
                                    from_type VARCHAR(20) NOT NULL,
                                    message_text TEXT NOT NULL,
                                    date_created TIMESTAMP WITH TIME ZONE NOT NULL,
                                    message_data JSONB,
                                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                    CONSTRAINT fk_ml_claim_messages_claim FOREIGN KEY (claim_id) REFERENCES ml_claims(id) ON DELETE CASCADE
                                );
                                
                                CREATE INDEX IF NOT EXISTS ix_ml_claim_messages_claim_id ON ml_claim_messages(claim_id);
                                CREATE INDEX IF NOT EXISTS ix_ml_claim_messages_ml_message_id ON ml_claim_messages(ml_message_id);
                                CREATE INDEX IF NOT EXISTS ix_ml_claim_messages_date_created ON ml_claim_messages(date_created);
                            """)
                            db.execute(create_ml_claim_messages_sql)
                            db.commit()
                            print("✅ [STARTUP] Tabela ml_claim_messages criada com sucesso")
                        except Exception as e:
                            db.rollback()
                            print(f"❌ [STARTUP] ERRO ao criar tabela ml_claim_messages: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    if 'ml_claim_evidences' not in existing_claims_tables:
                        print("📋 [STARTUP] Criando tabela ml_claim_evidences...")
                        try:
                            create_ml_claim_evidences_sql = text("""
                                CREATE TABLE ml_claim_evidences (
                                    id SERIAL PRIMARY KEY,
                                    claim_id INTEGER NOT NULL,
                                    ml_evidence_id VARCHAR(50) UNIQUE NOT NULL,
                                    evidence_type VARCHAR(20),
                                    evidence_url VARCHAR(500),
                                    evidence_data JSONB,
                                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                    CONSTRAINT fk_ml_claim_evidences_claim FOREIGN KEY (claim_id) REFERENCES ml_claims(id) ON DELETE CASCADE
                                );
                                
                                CREATE INDEX IF NOT EXISTS ix_ml_claim_evidences_claim_id ON ml_claim_evidences(claim_id);
                            """)
                            db.execute(create_ml_claim_evidences_sql)
                            db.commit()
                            print("✅ [STARTUP] Tabela ml_claim_evidences criada com sucesso")
                        except Exception as e:
                            db.rollback()
                            print(f"❌ [STARTUP] ERRO ao criar tabela ml_claim_evidences: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    print("✅ [STARTUP] Tabelas de claims verificadas/criadas")
                    print("✅ [STARTUP] Tabelas de estoque verificadas/criadas")
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️ [STARTUP] Erro ao criar tabelas de estoque/claims: {error_msg}")
                    # Tentar fazer rollback apenas se não houver erro de transação
                    if "transaction is already begun" not in error_msg.lower():
                        try:
                            db.rollback()
                        except:
                            pass  # Ignorar erro de rollback se já houver problema de transação
                    import traceback
                    traceback.print_exc()
                    # Continuar mesmo com erro - as tabelas podem já existir
                    print("ℹ️ [STARTUP] Continuando inicialização apesar do erro (tabelas podem já existir)...")
                
                print("✅ [STARTUP] Todas as migrações concluídas!")
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ [STARTUP] Erro ao executar migrações: {error_msg}")
                # Tentar fazer rollback apenas se não houver erro de transação
                if "transaction is already begun" not in error_msg.lower():
                    try:
                        db.rollback()
                    except:
                        pass  # Ignorar erro de rollback se já houver problema de transação
                print("ℹ️ [STARTUP] Continuando inicialização apesar do erro...")
            finally:
                db.close()
                
        except Exception as e:
            print(f"⚠️ [STARTUP] Erro ao executar migrações automáticas: {e}")
            print("ℹ️ [STARTUP] Continuando inicialização...")
        
        # Scheduler: Habilitar apenas para jobs que não dependem de webhook
        # JOB 1 (sync pedidos): Desabilitado - Webhook orders_v2 mantém pedidos atualizados
        # JOB 3 (catálogo): Habilitado - Monitoramento de catálogo
        # JOB 4 (Asaas): Habilitado - Sincronização com Asaas
        # JOB 5 (ML Cash): Habilitado - Processamento de lançamentos ML Cash
        
        print(f"🔧 [STARTUP] Scheduler rodando antes: {scheduler.running}")
        if not scheduler.running:
            print("🔧 [STARTUP] Iniciando scheduler...")
            scheduler.start()
            print(f"✅ [STARTUP] Scheduler iniciado")
            print(f"📋 [STARTUP] Jobs ativos: {len(scheduler.get_jobs())}")
            for job in scheduler.get_jobs():
                next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'N/A'
                print(f"   - {job.name} (ID: {job.id}) - Próxima execução: {next_run}")
        else:
            print("🔄 [STARTUP] Scheduler já está rodando")
        
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
app.include_router(ml_claims_router)  # Para /api/ml/claims (API)
app.include_router(activity_router)  # Para /api/activity/summary
app.include_router(openai_assistant_router)  # Para /api/openai/assistants
app.include_router(openai_chat_router)  # Para /ai/chat (HTML)
app.include_router(support_router)  # Para /support (HTML) e /api/support (API)
app.include_router(hr_router)  # Para /hr (HTML) e /api/hr (API)
app.include_router(task_router)  # Para /tasks (HTML) e /api/tasks (API)
app.include_router(content_router)  # Para /content (HTML) e /api/content (API)
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
        
        # Verificar se plano está inativo e redirecionar para profile
        if result.get("should_redirect_to_profile"):
            return RedirectResponse(url="/auth/profile", status_code=302)
        
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
        
        # Verificar se plano está inativo e redirecionar para profile
        if result.get("should_redirect_to_profile"):
            return RedirectResponse(url="/auth/profile", status_code=302)
        
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
        "hide_product_data": getattr(result, 'hide_product_data', False),
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
        
        if 'hide_product_data' in company_data:
            # Garantir que seja boolean
            hide_data_value = company_data['hide_product_data']
            if isinstance(hide_data_value, str):
                hide_data_value = hide_data_value.lower() in ('true', '1', 'yes')
            company.hide_product_data = bool(hide_data_value)
            print(f"DEBUG: Hide Product Data atualizado para: {company.hide_product_data} (tipo: {type(company.hide_product_data)})")
        
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
                "ml_orders_as_receivables": company.ml_orders_as_receivables,
                "hide_product_data": company.hide_product_data
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar empresa: {str(e)}")

# Endpoint para comprar plano
@app.post("/api/company/purchase-plan")
async def api_purchase_plan(
    purchase_data: dict,
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para empresa comprar um plano de assinatura"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    from app.controllers.auth_controller import AuthController
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    user_id = user_data.get("id")
    
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário não possui empresa associada")
    
    plan_id = purchase_data.get("plan_id")
    payment_method = purchase_data.get("payment_method", "PIX")
    
    if not plan_id:
        raise HTTPException(status_code=400, detail="ID do plano é obrigatório")
    
    try:
        from app.models.saas_models import Company, Subscription, User
        from app.controllers.asaas_controller import AsaasController
        
        # Buscar empresa e usuário
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Buscar plano template
        plan = db.query(Subscription).filter(
            Subscription.id == plan_id,
            Subscription.company_id.is_(None),
            Subscription.status == "template"
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plano não encontrado")
        
        # Criar assinatura via Asaas
        asaas_controller = AsaasController(db)
        
        # Mapear método de pagamento
        billing_type_map = {
            "PIX": "PIX",
            "BOLETO": "BOLETO",
            "CREDIT_CARD": "CREDIT_CARD"
        }
        billing_type = billing_type_map.get(payment_method, "PIX")
        
        # Preparar dados do assinante
        subscriber_data = {
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            "email": user.email,
            "cpf": company.cnpj if company.cnpj and len(company.cnpj) == 11 else None,
            "billing_type": billing_type
        }
        
        # Criar assinatura no Asaas
        asaas_result = asaas_controller.create_subscription(
            plan_id=str(plan_id),
            company_id=company_id,
            user_id=user_id,
            subscriber_data=subscriber_data
        )
        
        invoice_url = (
            asaas_result.get("invoice_url") or 
            asaas_result.get("invoiceUrl") or 
            asaas_result.get("invoiceURL")
        )
        
        # Verificar e processar automaticamente o pagamento inicial da assinatura
        asaas_subscription_id = asaas_result.get("id") or asaas_result.get("subscription_id")
        if asaas_subscription_id:
            logger.info(f"🔍 Verificando pagamento inicial da assinatura {asaas_subscription_id}...")
            
            def check_and_process_subscription_payment():
                """Função helper para verificar e processar pagamento da assinatura"""
                try:
                    from app.services.asaas_service import asaas_service, is_payment_confirmed
                    
                    # Buscar pagamentos da assinatura
                    subscription_payments = asaas_service.get_subscription_payments(asaas_subscription_id)
                    
                    if subscription_payments and len(subscription_payments) > 0:
                        # Verificar o primeiro pagamento (pagamento inicial)
                        first_payment = subscription_payments[0]
                        payment_id = first_payment.get("id")
                        
                        # Buscar detalhes completos do pagamento
                        payment_info = asaas_service._make_request("GET", f"/payments/{payment_id}")
                        
                        # Usar função helper para verificar se está confirmado
                        is_confirmed, final_status = is_payment_confirmed(payment_info)
                        
                        logger.info(f"📊 Verificação do pagamento inicial {payment_id}:")
                        logger.info(f"   - status: {payment_info.get('status')}")
                        logger.info(f"   - confirmedDate: {payment_info.get('confirmedDate')}")
                        logger.info(f"   - paymentDate: {payment_info.get('paymentDate')}")
                        logger.info(f"   - netValue: {payment_info.get('netValue')}")
                        logger.info(f"   - value: {payment_info.get('value')}")
                        logger.info(f"   - billingType: {payment_info.get('billingType')}")
                        logger.info(f"   - Está confirmado? {is_confirmed}, Status final: {final_status}")
                        
                        if is_confirmed:
                            logger.info(f"✅ Pagamento inicial confirmado! Processando assinatura automaticamente...")
                            
                            # Se não tem paymentDate do Asaas, usar data atual de São Paulo
                            payment_date = payment_info.get("paymentDate") or payment_info.get("confirmedDate")
                            if not payment_date:
                                try:
                                    from zoneinfo import ZoneInfo
                                    sao_paulo_tz = ZoneInfo('America/Sao_Paulo')
                                    now_sp = dt.now(sao_paulo_tz)
                                except ImportError:
                                    # Fallback para Python < 3.9
                                    from datetime import timedelta
                                    offset_hours = -3
                                    now_utc = dt.utcnow()
                                    now_sp = now_utc + timedelta(hours=offset_hours)
                                payment_date = now_sp.strftime("%Y-%m-%d")
                                logger.info(f"📅 Usando data atual de São Paulo para pagamento confirmado: {payment_date}")
                            
                            # Processar como webhook
                            notification_data = {
                                "event": "PAYMENT_CONFIRMED",
                                "payment": {
                                    "id": payment_id,
                                    "status": final_status,
                                    "paymentDate": payment_date,
                                    "externalReference": payment_info.get("externalReference", "")
                                },
                                "subscription": {
                                    "id": asaas_subscription_id
                                }
                            }
                            
                            webhook_result = asaas_controller.process_webhook_notification(notification_data)
                            logger.info(f"✅ Webhook processado automaticamente: {webhook_result}")
                            return True
                        else:
                            logger.info(f"ℹ️ Pagamento inicial ainda não confirmado, aguardando webhook do Asaas...")
                            return False
                    else:
                        logger.info(f"ℹ️ Nenhum pagamento encontrado na assinatura ainda")
                        return False
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao verificar pagamento inicial: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())
                    return False
            
            # Verificação imediata
            processed = check_and_process_subscription_payment()
            
            # Se não foi processado, fazer retry após 3 segundos (para sandbox)
            if not processed:
                import time
                import threading
                
                def delayed_check():
                    time.sleep(3)
                    logger.info(f"🔄 Retry: Verificando novamente pagamento inicial da assinatura {asaas_subscription_id}...")
                    check_and_process_subscription_payment()
                
                # Executar retry em thread separada para não bloquear resposta
                threading.Thread(target=delayed_check, daemon=True).start()
        
        return {
            "success": True,
            "message": "Plano contratado com sucesso",
            "invoice_url": invoice_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao comprar plano: {str(e)}")

# Endpoint para comprar pacote de tokens
@app.post("/api/company/purchase-package")
async def api_purchase_package(
    purchase_data: dict,
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para empresa comprar um pacote de tokens"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    from app.controllers.auth_controller import AuthController
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    user_id = user_data.get("id")
    
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário não possui empresa associada")
    
    package_id = purchase_data.get("package_id")
    payment_method = purchase_data.get("payment_method", "PIX")
    
    if not package_id:
        raise HTTPException(status_code=400, detail="ID do pacote é obrigatório")
    
    try:
        from app.models.saas_models import Company, TokenPackage, TokenPackagePurchase, User
        from app.controllers.asaas_controller import AsaasController
        from app.services.asaas_service import AsaasService
        from app.config.settings import settings
        from datetime import datetime as dt
        
        # Buscar empresa e usuário
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Buscar pacote
        package = db.query(TokenPackage).filter(
            TokenPackage.id == package_id,
            TokenPackage.is_active == True
        ).first()
        
        if not package:
            raise HTTPException(status_code=404, detail="Pacote não encontrado ou inativo")
        
        # Criar registro de compra
        purchase = TokenPackagePurchase(
            company_id=company_id,
            package_id=package.id,
            tokens_amount=package.tokens_amount,
            price=package.price,
            currency=package.currency,
            payment_method=payment_method,
            payment_status="pending",
            purchased_at=dt.now()
        )
        db.add(purchase)
        db.flush()  # Para obter o ID
        
        # Criar pagamento no Asaas
        asaas_service = AsaasService()
        asaas_controller = AsaasController(db)
        
        # Buscar ou criar cliente no Asaas
        subscriber_data = {
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            "email": user.email,
            "cpf": company.cnpj if company.cnpj and len(company.cnpj) == 11 else None
        }
        
        asaas_customer_id = asaas_controller._get_or_create_customer(
            company_id=company_id,
            user_id=user_id,
            subscriber_data=subscriber_data
        )
        
        if asaas_customer_id:
            # Mapear método de pagamento
            billing_type_map = {
                "PIX": "PIX",
                "BOLETO": "BOLETO",
                "CREDIT_CARD": "CREDIT_CARD"
            }
            billing_type = billing_type_map.get(payment_method, "PIX")
            
            # Converter preço para float
            price_str = package.price.replace("R$", "").replace(" ", "").replace(",", ".")
            try:
                price_float = float(price_str)
            except:
                price_float = 0.0
            
            # Criar pagamento único
            payment_data = {
                "customer": asaas_customer_id,
                "billingType": billing_type,
                "value": price_float,
                "dueDate": dt.now().strftime("%Y-%m-%d"),
                "description": f"Pacote de Tokens: {package.name} ({package.tokens_amount} tokens)",
                "externalReference": f"package_{purchase.id}_company_{company_id}"
            }
            
            payment_result = asaas_service.create_payment(payment_data)
            
            # Atualizar compra com dados do pagamento
            payment_id_from_asaas = payment_result.get("id")
            purchase.asaas_payment_id = payment_id_from_asaas
            purchase.invoice_url = (
                payment_result.get("invoiceUrl") or 
                payment_result.get("invoice_url") or 
                payment_result.get("invoiceURL")
            )
            
            # Log para debug
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"📦 Compra de pacote criada:")
            logger.info(f"   - Purchase ID: {purchase.id}")
            logger.info(f"   - Company ID: {company_id}")
            logger.info(f"   - Package ID: {package.id}")
            logger.info(f"   - Asaas Payment ID: {payment_id_from_asaas}")
            logger.info(f"   - External Reference: package_{purchase.id}_company_{company_id}")
            logger.info(f"   - Payment Status: {purchase.payment_status}")
            
            db.commit()
            
            # Verificar status do pagamento imediatamente e após alguns segundos (para sandbox)
            # No sandbox, pagamentos podem ser confirmados automaticamente
            logger.info(f"🔍 Verificando status do pagamento {payment_id_from_asaas}...")
            
            def check_and_process_payment():
                """Função helper para verificar e processar pagamento"""
                try:
                    payment_info = asaas_service._make_request("GET", f"/payments/{payment_id_from_asaas}")
                    
                    # Usar função helper para verificar se está confirmado
                    from app.services.asaas_service import is_payment_confirmed
                    is_confirmed, final_status = is_payment_confirmed(payment_info)
                    
                    logger.info(f"📊 Verificação do pagamento {payment_id_from_asaas}:")
                    logger.info(f"   - status: {payment_info.get('status')}")
                    logger.info(f"   - confirmedDate: {payment_info.get('confirmedDate')}")
                    logger.info(f"   - paymentDate: {payment_info.get('paymentDate')}")
                    logger.info(f"   - netValue: {payment_info.get('netValue')}")
                    logger.info(f"   - value: {payment_info.get('value')}")
                    logger.info(f"   - billingType: {payment_info.get('billingType')}")
                    logger.info(f"   - Está confirmado? {is_confirmed}, Status final: {final_status}")
                    
                    if is_confirmed:
                        logger.info(f"✅ Pagamento confirmado! Processando tokens automaticamente...")
                        
                        # Se não tem paymentDate do Asaas, usar data atual de São Paulo
                        payment_date = payment_info.get("paymentDate") or payment_info.get("confirmedDate")
                        if not payment_date:
                            try:
                                from zoneinfo import ZoneInfo
                                sao_paulo_tz = ZoneInfo('America/Sao_Paulo')
                                now_sp = dt.now(sao_paulo_tz)
                            except ImportError:
                                # Fallback para Python < 3.9
                                from datetime import timedelta
                                offset_hours = -3
                                now_utc = dt.utcnow()
                                now_sp = now_utc + timedelta(hours=offset_hours)
                            payment_date = now_sp.strftime("%Y-%m-%d")
                            logger.info(f"📅 Usando data atual de São Paulo para pagamento confirmado: {payment_date}")
                        
                        # Processar como webhook
                        notification_data = {
                            "event": "PAYMENT_CONFIRMED",
                            "payment": {
                                "id": payment_id_from_asaas,
                                "status": final_status,
                                "paymentDate": payment_date,
                                "externalReference": f"package_{purchase.id}_company_{company_id}"
                            }
                        }
                        
                        webhook_result = asaas_controller.process_webhook_notification(notification_data)
                        logger.info(f"✅ Webhook processado automaticamente: {webhook_result}")
                        return True
                    else:
                        logger.info(f"ℹ️ Pagamento ainda não confirmado, aguardando webhook do Asaas...")
                        return False
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao verificar status do pagamento: {e}")
                    return False
            
            # Verificação imediata
            processed = check_and_process_payment()
            
            # Se não foi processado, fazer retry após 3 segundos (para sandbox)
            if not processed:
                import time
                import threading
                
                def delayed_check():
                    time.sleep(3)
                    logger.info(f"🔄 Retry: Verificando novamente status do pagamento {payment_id_from_asaas}...")
                    check_and_process_payment()
                
                # Executar retry em thread separada para não bloquear resposta
                threading.Thread(target=delayed_check, daemon=True).start()
            
            return {
                "success": True,
                "message": "Pacote selecionado com sucesso",
                "invoice_url": purchase.invoice_url,
                "package_purchase": {
                    "id": purchase.id,
                    "package_name": package.name,
                    "tokens_amount": package.tokens_amount,
                    "price": package.price
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Erro ao criar cliente no Asaas")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao comprar pacote: {str(e)}")

# Endpoint público para listar planos disponíveis
@app.get("/api/plans")
async def api_list_plans(db: Session = Depends(get_db)):
    """API pública: Lista planos disponíveis (templates)"""
    try:
        from app.models.saas_models import Subscription
        
        plans = db.query(Subscription).filter(
            Subscription.company_id.is_(None),
            Subscription.status == "template"
        ).all()
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                "id": plan.id,
                "plan_name": plan.plan_name,
                "price": plan.price,
                "currency": plan.currency,
                "billing_cycle": plan.billing_cycle,
                "ai_tokens_monthly": plan.ai_tokens_monthly,
                "description": plan.description
            })
        
        return {
            "success": True,
            "plans": plans_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao listar planos: {str(e)}")

# Endpoint público para listar pacotes de tokens disponíveis
@app.get("/api/token-packages")
async def api_list_token_packages(db: Session = Depends(get_db)):
    """API pública: Lista pacotes de tokens disponíveis"""
    try:
        from app.models.saas_models import TokenPackage
        
        packages = db.query(TokenPackage).filter(
            TokenPackage.is_active == True
        ).all()
        
        packages_data = []
        for package in packages:
            packages_data.append({
                "id": package.id,
                "name": package.name,
                "description": package.description,
                "tokens_amount": package.tokens_amount,
                "price": package.price,
                "currency": package.currency
            })
        
        return {
            "success": True,
            "packages": packages_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao listar pacotes: {str(e)}")

# Rotas principais (sem prefixo para compatibilidade)
@app.get("/")
async def root(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Página inicial - Landing page do SELVEZ com menus do usuário se logado"""
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


@app.get("/paginatrial")
async def trial_capture(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Página de captura exclusiva para o trial de 7 dias"""
    from app.views.template_renderer import render_template
    from app.controllers.auth_controller import AuthController

    user_data = None

    if session_token:
        controller = AuthController()
        result = controller.get_user_by_session(session_token, db)
        if not result.get("error"):
            user_data = result.get("user")

    return render_template("paginatrial.html", request=request, user=user_data)


@app.get("/paginacalculadora")
async def calculator_capture(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Página de captura da calculadora de margem"""
    from app.views.template_renderer import render_template
    from app.controllers.auth_controller import AuthController

    user_data = None

    if session_token:
        controller = AuthController()
        result = controller.get_user_by_session(session_token, db)
        if not result.get("error"):
            user_data = result.get("user")

    return render_template("paginacalculadora.html", request=request, user=user_data)


@app.get("/obrigadacalculadora")
async def calculator_thanks(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Página de obrigado após download da calculadora"""
    from app.views.template_renderer import render_template
    from app.controllers.auth_controller import AuthController

    user_data = None

    if session_token:
        controller = AuthController()
        result = controller.get_user_by_session(session_token, db)
        if not result.get("error"):
            user_data = result.get("user")

    return render_template("paginaobrigadacalculadora.html", request=request, user=user_data)


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
