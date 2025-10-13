from fastapi import FastAPI, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config.settings import settings
from app.config.database import engine, Base
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
    title="GIVM - Gestão Inteligente de Vendas para Marketplace",
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
        
        # Iniciar scheduler
        print(f"🔧 [STARTUP] Scheduler rodando antes: {scheduler.running}")
        if not scheduler.running:
            print("🔧 [STARTUP] Iniciando scheduler...")
            scheduler.start()
            print(f"🔧 [STARTUP] Scheduler rodando depois: {scheduler.running}")
            print(f"🔧 [STARTUP] Jobs ativos: {len(scheduler.get_jobs())}")
            print("   📦 JOB 1: Pedidos novos - A cada 30 minutos")
            print("   🌙 JOB 2: Últimos 7 dias completos - INATIVO")
            print("   📊 JOB 3: Monitoramento de Catálogo - A cada 12 horas")
        else:
            print("🔄 Scheduler já está rodando")
        
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

# Rotas principais (sem prefixo para compatibilidade)
@app.get("/")
async def root():
    """Página inicial - Landing page do GIVM"""
    from app.views.template_renderer import render_template
    return render_template("home.html")



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
                ml_user_id=user_info["id"],
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
                ml_user_id=user_info["id"],
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
async def dashboard(session_token: str = Cookie(None)):
    """Dashboard do usuário"""
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
    
    return render_template("dashboard.html", user=result["user"])

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
