from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config.settings import settings
from app.config.database import engine, Base
from app.routes.main_routes import main_router

# Inicializar FastAPI
app = FastAPI(
    title="API Mercado Livre - MVC",
    description="API para integração com o Mercado Livre usando arquitetura MVC",
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

# Criar tabelas do banco de dados
@app.on_event("startup")
async def startup_event():
    """Evento de inicialização da aplicação"""
    try:
        # Criar tabelas se não existirem
        Base.metadata.create_all(bind=engine)
        print("✅ Banco de dados inicializado")
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")

# Incluir todas as rotas com prefixo /api
app.include_router(main_router, prefix="/api")

# Rotas principais (sem prefixo para compatibilidade)
@app.get("/")
async def root():
    """Página inicial"""
    from app.controllers.auth_controller import AuthController
    controller = AuthController()
    return controller.get_login_page()


@app.get("/login")
async def login(state: str = None):
    """Redireciona para o login do Mercado Livre"""
    from app.controllers.auth_controller import AuthController
    controller = AuthController()
    return controller.redirect_to_login(state)


@app.get("/callback")
async def callback(code: str = None, error: str = None, state: str = None):
    """Recebe o callback do Mercado Livre (compatibilidade)"""
    from app.controllers.auth_controller import AuthController
    controller = AuthController()
    return await controller.handle_callback(code, error, state)


@app.get("/user")
async def get_user_info(access_token: str = None):
    """Obtém informações do usuário (compatibilidade)"""
    from app.controllers.auth_controller import AuthController
    controller = AuthController()
    return await controller.get_user_info(access_token)


@app.get("/health")
async def health_check():
    """Verifica saúde da API"""
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "architecture": "MVC"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
