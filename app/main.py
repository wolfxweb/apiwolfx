from fastapi import FastAPI, Cookie, Depends, HTTPException, Request
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config.settings import settings
from app.config.database import engine, Base, get_db
from sqlalchemy.orm import Session
from app.routes.main_routes import main_router
from app.routes.saas_routes import saas_router
from app.routes.auth_routes import auth_router
from app.routes.ml_routes import ml_router
from app.routes.ml_product_routes import ml_product_router
from app.routes.ml_orders_routes import ml_orders_router
from app.routes.ml_notifications_routes import ml_notifications_router
from app.routes.ads_analytics_routes import ads_analytics_router
from app.routes.product_routes import product_router
from app.routes.pricing_analysis_routes import router as pricing_analysis_router
from app.routes.ml_pricing_routes import router as ml_pricing_router
from app.routes.sales_analysis_routes import router as sales_analysis_router
from app.routes.catalog_monitoring_routes import router as catalog_monitoring_router
from app.routes.superadmin_routes import superadmin_router
from app.routes.payment_routes import router as payment_router
from app.routes.financial_routes import financial_router
from app.routes.fornecedores_routes import fornecedores_router
from app.routes.ordem_compra_routes import ordem_compra_router
from app.routes.ml_cash_routes import ml_cash_router
from app.routes.marketing_costs_routes import router as marketing_costs_router
from app.routes.advertising_full_routes import router as advertising_router
from app.routes.shipment_routes import router as shipment_router
from app.routes.highlights_routes import highlights_router
from app.routes.ml_questions_routes import ml_questions_router
# from app.routes.settings_routes import router as settings_router  # Removido

# Scheduler para sincronização automática
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.services.auto_sync_service import AutoSyncService
from app.services.catalog_monitoring_service import CatalogMonitoringService
from app.config.database import SessionLocal
import atexit

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

# Criar tabelas do banco de dados
@app.on_event("startup")
async def startup_event():
    """Evento de inicialização da aplicação"""
    try:
        print("🚀 [STARTUP] Iniciando aplicação...")
        
        # Criar tabelas se não existirem
        Base.metadata.create_all(bind=engine)
        print("✅ Banco de dados inicializado")
        
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
app.include_router(ads_analytics_router)  # Sem prefixo para /analytics
app.include_router(product_router)  # Sem prefixo para /api/products
app.include_router(pricing_analysis_router, prefix="/api/pricing")  # Para /api/pricing/analysis
app.include_router(ml_pricing_router, prefix="/api/ml-pricing")  # Para /api/ml-pricing/fees
app.include_router(sales_analysis_router)  # Para /api/sales/analysis
app.include_router(catalog_monitoring_router)  # Para /api/catalog-monitoring
app.include_router(superadmin_router)  # Para /superadmin
app.include_router(payment_router)  # Para /api/payments
app.include_router(financial_router)  # Para /financial e /api/financial
app.include_router(fornecedores_router)  # Para /fornecedores e /api/fornecedores
app.include_router(ordem_compra_router)  # Para /ordem-compra e /api/ordem-compra
app.include_router(ml_cash_router)  # Para /api/ml-cash
app.include_router(marketing_costs_router)  # Para /marketing
app.include_router(advertising_router)  # Para /ml/advertising
app.include_router(shipment_router, prefix="/api")  # Para /api/shipments
app.include_router(highlights_router)  # Para /ml/highlights e /api/ml/highlights
app.include_router(ml_questions_router, prefix="/ml")  # Para /ml/questions e /api/ml/questions
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
async def root():
    """Página inicial - Landing page do CELX"""
    from app.views.template_renderer import render_template
    from app.models.saas_models import Subscription
    from app.config.database import SessionLocal
    
    # Buscar planos templates do banco de dados
    db = SessionLocal()
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
    finally:
        db.close()
    
    return render_template("home.html", plans=plans_data)



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
    """Dashboard do usuário"""
    from app.views.template_renderer import render_template
    from app.controllers.auth_controller import AuthController
    
    # Se o usuário estiver logado, buscar seus dados
    user_data = None
    if session_token:
        controller = AuthController()
        result = controller.get_user_by_session(session_token, db)
        if "error" not in result:
            user_data = result.get("user")
    
    return render_template("dashboard_simple.html", request=request, user=user_data)

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
