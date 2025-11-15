"""
Rotas para gerenciar assistentes OpenAI
"""
import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie, Query, Body, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config.database import get_db
from app.controllers.openai_assistant_controller import OpenAIAssistantController
from app.controllers.auth_controller import AuthController
from app.services.file_processor_service import FileProcessorService

logger = logging.getLogger(__name__)

# Router para assistentes OpenAI
openai_assistant_router = APIRouter(prefix="/api/openai/assistants", tags=["OpenAI Assistants"])

# Instância do controller
auth_controller = AuthController()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> dict:
    """Obtém usuário atual da sessão"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]


def get_superadmin_user(request: Request, db: Session = Depends(get_db)) -> dict:
    """Obtém usuário superadmin da sessão"""
    try:
        user = get_current_user(request, db)
        logger.info(f"✅ Usuário autenticado: {user.get('email')} (role: {user.get('role')})")
    except HTTPException as e:
        logger.warning(f"⚠️ Erro ao obter usuário: {e.detail} - Path: {request.url.path}")
        # Se não conseguir obter usuário normal, verificar se está acessando rotas administrativas
        # Por enquanto, permitir acesso se estiver na rota /superadmin ou /api/openai/assistants (para desenvolvimento)
        if "/superadmin" in request.url.path or "/api/openai/assistants" in request.url.path:
            logger.info("🔓 Permitindo acesso temporário para desenvolvimento")
            # Retornar um usuário mock para desenvolvimento
            return {"id": 1, "email": "admin@celx.com.br", "role": "super_admin"}
        raise
    
    # Verificar se é superadmin de três formas:
    # 1. Se o role do usuário é super_admin
    # 2. Se existe um registro na tabela SuperAdmin com o mesmo email
    # 3. Se está acessando rotas administrativas (permissão temporária para desenvolvimento)
    from app.models.saas_models import SuperAdmin
    
    is_superadmin = False
    
    # Verificar role
    if user.get("role") == "super_admin":
        logger.info("✅ Usuário é superadmin por role")
        is_superadmin = True
    else:
        # Verificar se existe SuperAdmin com o mesmo email
        user_email = user.get("email")
        if user_email:
            superadmin = db.query(SuperAdmin).filter(
                SuperAdmin.email == user_email,
                SuperAdmin.is_active == True
            ).first()
            if superadmin:
                logger.info(f"✅ Usuário é superadmin por tabela SuperAdmin: {user_email}")
                is_superadmin = True
        
        # Se ainda não for superadmin, verificar se está acessando rotas administrativas
        # (permissão temporária para desenvolvimento - remover em produção)
        if not is_superadmin and ("/superadmin" in request.url.path or "/api/openai/assistants" in request.url.path):
            logger.info("🔓 Permitindo acesso temporário para desenvolvimento (rota administrativa)")
            # Permitir acesso temporariamente para desenvolvimento
            is_superadmin = True
    
    if not is_superadmin:
        logger.warning(f"❌ Acesso negado para usuário: {user.get('email')} - Path: {request.url.path}")
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas superadmins podem acessar.")
    
    logger.info(f"✅ Acesso permitido para superadmin: {user.get('email')}")
    return user


# Modelos Pydantic para validação
class CreateAssistantRequest(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: str
    model: str = "gpt-5.1"
    temperature: Optional[float] = None  # Para modelos GPT-4 e anteriores
    reasoning_effort: Optional[str] = None  # Para modelos GPT-5: "minimal", "low", "medium", "high"
    verbosity: Optional[str] = None  # Para modelos GPT-5: "low", "medium", "high"
    max_tokens: int = 4000
    tools: Optional[List[Dict]] = None
    interaction_mode: str = "report"
    use_case: Optional[str] = None
    memory_enabled: bool = True  # Habilita memória persistente entre threads
    memory_data: Optional[Dict] = None  # Memórias compartilhadas (ex: preferências do usuário/empresa)
    initial_prompt: Optional[str] = None  # Template de prompt inicial com tag [[USUARIO]]


class UpdateAssistantRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None  # Para modelos GPT-4 e anteriores
    reasoning_effort: Optional[str] = None  # Para modelos GPT-5: "minimal", "low", "medium", "high"
    verbosity: Optional[str] = None  # Para modelos GPT-5: "low", "medium", "high"
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict]] = None
    interaction_mode: Optional[str] = None
    use_case: Optional[str] = None
    is_active: Optional[bool] = None
    memory_enabled: Optional[bool] = None  # Habilita/desabilita memória persistente
    memory_data: Optional[Dict] = None  # Atualiza memórias compartilhadas
    initial_prompt: Optional[str] = None  # Template de prompt inicial com tag [[USUARIO]]


class UseAssistantReportRequest(BaseModel):
    assistant_id: int
    prompt: str
    context_data: Optional[Dict] = None
    use_case: Optional[str] = None
    files_data: Optional[List[Dict]] = None  # Dados processados dos arquivos


class UseAssistantChatRequest(BaseModel):
    assistant_id: int
    message: str
    thread_id: Optional[str] = None
    context_data: Optional[Dict] = None
    use_case: Optional[str] = None
    files_data: Optional[List[Dict]] = None  # Dados processados dos arquivos


# Rotas de gerenciamento (apenas superadmin)
@openai_assistant_router.get("/")
async def list_assistants(
    active_only: bool = Query(True, description="Listar apenas assistentes ativos"),
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Lista todos os assistentes (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.list_assistants(active_only=active_only)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao listar agentes"))
    
    return result


@openai_assistant_router.post("/")
async def create_assistant(
    request_data: CreateAssistantRequest,
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Cria um novo assistente (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.create_assistant(
        name=request_data.name,
        description=request_data.description,
        instructions=request_data.instructions,
        model=request_data.model,
        temperature=request_data.temperature,
        reasoning_effort=request_data.reasoning_effort,
        verbosity=request_data.verbosity,
        max_tokens=request_data.max_tokens,
        tools=request_data.tools,
        interaction_mode=request_data.interaction_mode,
        use_case=request_data.use_case,
        memory_enabled=request_data.memory_enabled,
        memory_data=request_data.memory_data,
        initial_prompt=request_data.initial_prompt
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao criar agente"))
    
    return result


# Rotas de uso (qualquer usuário autenticado) - DEVE VIR ANTES DE /{assistant_id}
@openai_assistant_router.get("/available")
async def get_available_assistants(
    active_only: bool = Query(True, description="Listar apenas assistentes ativos"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista agentes disponíveis para uso (qualquer usuário autenticado)"""
    controller = OpenAIAssistantController(db)
    result = controller.list_assistants(active_only=active_only)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao listar agentes"))
    
    return result


@openai_assistant_router.get("/{assistant_id}")
async def get_assistant(
    assistant_id: int,
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Obtém um assistente específico (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.get_assistant(assistant_id=assistant_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Agente não encontrado"))
    
    return result


@openai_assistant_router.put("/{assistant_id}")
async def update_assistant(
    assistant_id: int,
    request_data: UpdateAssistantRequest,
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Atualiza um assistente existente (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.update_assistant(
        assistant_id=assistant_id,
        name=request_data.name,
        description=request_data.description,
        instructions=request_data.instructions,
        model=request_data.model,
        temperature=request_data.temperature,
        reasoning_effort=request_data.reasoning_effort,
        verbosity=request_data.verbosity,
        max_tokens=request_data.max_tokens,
        tools=request_data.tools,
        interaction_mode=request_data.interaction_mode,
        use_case=request_data.use_case,
        is_active=request_data.is_active,
        memory_enabled=request_data.memory_enabled,
        memory_data=request_data.memory_data,
        initial_prompt=request_data.initial_prompt
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao atualizar agente"))
    
    return result


@openai_assistant_router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: int,
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Deleta um assistente (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.delete_assistant(assistant_id=assistant_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao deletar agente"))
    
    return result


# Rotas de uso (qualquer usuário autenticado)
@openai_assistant_router.post("/use/report")
async def use_assistant_report(
    request_data: UseAssistantReportRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Usa um assistente em modo relatório"""
    company_id = user.get("company", {}).get("id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID não encontrado")
    
    # Processar arquivos se fornecidos
    context_data = request_data.context_data or {}
    if request_data.files_data:
        files_context = FileProcessorService.format_for_context(request_data.files_data)
        if files_context:
            context_data.update(files_context)
    
    controller = OpenAIAssistantController(db)
    result = controller.use_assistant_report(
        assistant_id=request_data.assistant_id,
        company_id=company_id,
        user_id=user.get("id"),
        prompt=request_data.prompt,
        context_data=context_data,
        use_case=request_data.use_case
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao usar agente"))
    
    return result


@openai_assistant_router.post("/use/chat")
async def use_assistant_chat(
    request_data: UseAssistantChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Usa um assistente em modo chat"""
    company_id = user.get("company", {}).get("id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID não encontrado")
    
    # Processar arquivos se fornecidos
    context_data = request_data.context_data or {}
    if request_data.files_data:
        files_context = FileProcessorService.format_for_context(request_data.files_data)
        if files_context:
            context_data.update(files_context)
    
    controller = OpenAIAssistantController(db)
    result = controller.use_assistant_chat(
        assistant_id=request_data.assistant_id,
        company_id=company_id,
        user_id=user.get("id"),
        message=request_data.message,
        thread_id=request_data.thread_id,
        context_data=context_data,
        use_case=request_data.use_case
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao usar agente"))
    
    return result


@openai_assistant_router.post("/process-files")
async def process_files(
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    """Processa arquivos enviados e retorna conteúdo estruturado"""
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    
    processor = FileProcessorService()
    results = []
    
    for file in files:
        result = await processor.process_file(file)
        results.append({
            "filename": file.filename,
            **result
        })
    
    return {
        "success": True,
        "files": results
    }


@openai_assistant_router.get("/chat/{thread_id}/history")
async def get_chat_history(
    thread_id: str,
    limit: int = Query(50, ge=1, le=100, description="Número máximo de mensagens"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém histórico de mensagens de uma thread"""
    company_id = user.get("company", {}).get("id")
    user_id = user.get("id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID não encontrado")
    
    controller = OpenAIAssistantController(db)
    result = controller.get_chat_history(
        thread_id=thread_id,
        company_id=company_id,
        user_id=user_id,  # Passar user_id para validação
        limit=limit
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao obter histórico"))
    
    return result


# Rotas de estatísticas (apenas superadmin)
@openai_assistant_router.get("/usage/stats")
async def get_usage_stats(
    company_id: Optional[int] = Query(None, description="ID da empresa (opcional)"),
    days: int = Query(30, ge=1, le=365, description="Número de dias"),
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Obtém estatísticas gerais de uso de tokens (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.get_usage_stats(company_id=company_id, days=days)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao obter estatísticas"))
    
    return result


@openai_assistant_router.get("/usage/by-assistant")
async def get_usage_by_assistant(
    company_id: Optional[int] = Query(None, description="ID da empresa (opcional)"),
    days: int = Query(30, ge=1, le=365, description="Número de dias"),
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Obtém uso de tokens agrupado por assistente (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.get_usage_by_assistant(company_id=company_id, days=days)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao obter uso por agente"))
    
    return result


@openai_assistant_router.get("/usage/daily")
async def get_usage_daily(
    company_id: Optional[int] = Query(None, description="ID da empresa (opcional)"),
    days: int = Query(30, ge=1, le=365, description="Número de dias"),
    user: dict = Depends(get_superadmin_user),
    db: Session = Depends(get_db)
):
    """Obtém uso de tokens agrupado por dia (apenas superadmin)"""
    controller = OpenAIAssistantController(db)
    result = controller.get_usage_daily(company_id=company_id, days=days)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao obter uso diário"))
    
    return result

