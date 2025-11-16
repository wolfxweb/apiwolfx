"""
Rotas para gerenciar assistentes OpenAI
"""
import logging
import json
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie, Query, Body, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config.database import get_db
from app.controllers.openai_assistant_controller import OpenAIAssistantController
from app.controllers.auth_controller import AuthController
from app.services.file_processor_service import FileProcessorService

logger = logging.getLogger(__name__)

# Router para assistentes OpenAI (API)
openai_assistant_router = APIRouter(prefix="/api/openai/assistants", tags=["OpenAI Assistants"])
tools_router = APIRouter(prefix="/api/openai/tools", tags=["OpenAI Tools"])

# Router para páginas HTML de assistentes OpenAI
openai_chat_router = APIRouter(tags=["OpenAI Chat"])

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
    user = get_current_user(request, db)
    logger.info(f"✅ Usuário autenticado: {user.get('email')} (role: {user.get('role')})")
    
    # Verificar se é superadmin de duas formas:
    # 1. Se o role do usuário é super_admin
    # 2. Se existe um registro na tabela SuperAdmin com o mesmo email
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
        
        # Não permitir bypass por rota em produção; exige autenticação e papel
    
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
    request: Request,
    active_only: bool = Query(True, description="Listar apenas assistentes ativos"),
    db: Session = Depends(get_db)
):
    """Lista todos os assistentes (superadmin)"""
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


# ========== THREADS E MENSAGENS (DEVEM VIR ANTES DE /{assistant_id}) ==========

@openai_assistant_router.get("/threads")
async def list_user_threads(
    request: Request,
    assistant_id: Optional[str] = Query(None, description="Filtrar por assistente específico"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todas as conversas (threads) do usuário logado"""
    company_id = user.get("company", {}).get("id")
    user_id = user.get("id")
    
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID não encontrado")
    
    # Converter assistant_id para inteiro somente se válido
    assistant_id_int = None
    if isinstance(assistant_id, str) and assistant_id.strip() != "":
        try:
            assistant_id_int = int(assistant_id)
        except ValueError:
            assistant_id_int = None
    
    controller = OpenAIAssistantController(db)
    result = controller.list_user_threads(
        company_id=company_id,
        user_id=user_id,
        assistant_id=assistant_id_int
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao listar conversas"))
    
    return result


@openai_assistant_router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    request: Request,
    thread_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Busca todas as mensagens de uma conversa específica"""
    company_id = user.get("company", {}).get("id")
    user_id = user.get("id")
    
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID não encontrado")
    
    controller = OpenAIAssistantController(db)
    result = controller.get_thread_messages(
        thread_id=thread_id,
        company_id=company_id,
        user_id=user_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao buscar mensagens"))
    
    return result


@openai_assistant_router.delete("/threads/{thread_id}")
async def delete_thread(
    request: Request,
    thread_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deleta uma conversa (marca como inativa)"""
    company_id = user.get("company", {}).get("id")
    user_id = user.get("id")
    
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID não encontrado")
    
    controller = OpenAIAssistantController(db)
    result = controller.delete_thread(
        thread_id=thread_id,
        company_id=company_id,
        user_id=user_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao deletar conversa"))
    
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


# ================== TOOLS CRUD (SuperAdmin) ==================

@tools_router.get("")
async def list_tools(
    request: Request,
    db: Session = Depends(get_db)
):
    from sqlalchemy import text as sql_text
    try:
        rows = db.execute(sql_text("SELECT id, name, description, is_active, created_at, json_schema FROM openai_tools ORDER BY created_at DESC")).fetchall()
    except Exception:
        # Tabela pode não existir: criar via migração e tentar novamente
        # Limpar estado de transação abortada
        try:
            db.rollback()
        except Exception:
            pass
        import importlib.util, os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # /app
        tools_path = os.path.join(base_dir, 'database', 'fixes', '2025_11_16_create_openai_tools_tables.py')
        spec = importlib.util.spec_from_file_location("create_openai_tools_tables", tools_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.run(db)
        # Garantir novo estado limpo
        try:
            db.rollback()
        except Exception:
            pass
        rows = db.execute(sql_text("SELECT id, name, description, is_active, created_at, json_schema FROM openai_tools ORDER BY created_at DESC")).fetchall()
    tools = []
    for r in rows:
        tools.append({
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "is_active": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
            "json_schema": r[5]
        })
    return {"success": True, "tools": tools}


class SaveTool(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    json_schema: dict
    handler_name: str | None = None
    python_module: str | None = None
    python_function: str | None = None


@tools_router.post("")
async def create_tool(
    body: SaveTool,
    request: Request,
    db: Session = Depends(get_db)
):
    from sqlalchemy import text as sql_text
    try:
        with db.begin():
            row = db.execute(sql_text(
                """
                INSERT INTO openai_tools (name, description, json_schema, is_active)
                VALUES (:name, :description, CAST(:schema AS JSONB), :active)
                RETURNING id
                """
            ), {"name": body.name, "description": body.description, "schema": json.dumps(body.json_schema), "active": body.is_active}).fetchone()
            tool_id = row[0]
            if body.handler_name:
                db.execute(sql_text(
                    """
                    INSERT INTO openai_tool_handlers (tool_id, handler_name, python_module, python_function, is_active)
                    VALUES (:tool_id, :handler_name, :python_module, :python_function, TRUE)
                    """
                ), {"tool_id": tool_id, "handler_name": body.handler_name, "python_module": body.python_module, "python_function": body.python_function})
        return {"success": True, "id": tool_id}
    except Exception as e:
        logger.error(f"Erro ao criar ferramenta: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tools_router.get("/{tool_id}")
async def get_tool(tool_id: int, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import text as sql_text
    r = db.execute(sql_text("SELECT id, name, description, is_active, created_at, json_schema FROM openai_tools WHERE id=:id"), {"id": tool_id}).fetchone()
    if not r:
        return {"success": False, "error": "Ferramenta não encontrada"}
    handler = db.execute(sql_text("SELECT handler_name, python_module, python_function FROM openai_tool_handlers WHERE tool_id=:id AND is_active=TRUE LIMIT 1"), {"id": tool_id}).fetchone()
    return {
        "success": True,
        "tool": {
            "id": r[0], "name": r[1], "description": r[2], "is_active": r[3], "created_at": r[4].isoformat() if r[4] else None, "json_schema": r[5],
            "handler": {"handler_name": handler[0], "python_module": handler[1], "python_function": handler[2]} if handler else None
        }
    }


@tools_router.put("/{tool_id}")
async def update_tool(tool_id: int, body: SaveTool, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import text as sql_text
    try:
        with db.begin():
            db.execute(sql_text(
                """
                UPDATE openai_tools SET name=:name, description=:description, json_schema=CAST(:schema AS JSONB), is_active=:active WHERE id=:id
                """
            ), {"id": tool_id, "name": body.name, "description": body.description, "schema": json.dumps(body.json_schema), "active": body.is_active})
            # Upsert handler
            if body.handler_name:
                db.execute(sql_text(
                    """
                    INSERT INTO openai_tool_handlers (tool_id, handler_name, python_module, python_function, is_active)
                    VALUES (:tool_id, :handler_name, :python_module, :python_function, TRUE)
                    ON CONFLICT (tool_id, handler_name) DO UPDATE SET python_module=EXCLUDED.python_module, python_function=EXCLUDED.python_function, is_active=TRUE
                    """
                ), {"tool_id": tool_id, "handler_name": body.handler_name, "python_module": body.python_module, "python_function": body.python_function})
        return {"success": True}
    except Exception as e:
        logger.error(f"Erro ao atualizar ferramenta: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tools_router.delete("/{tool_id}")
async def delete_tool(tool_id: int, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import text as sql_text
    try:
        with db.begin():
            db.execute(sql_text("DELETE FROM openai_agent_tools WHERE tool_id=:id"), {"id": tool_id})
            db.execute(sql_text("DELETE FROM openai_tool_handlers WHERE tool_id=:id"), {"id": tool_id})
            db.execute(sql_text("DELETE FROM openai_tools WHERE id=:id"), {"id": tool_id})
        return {"success": True}
    except Exception as e:
        logger.error(f"Erro ao deletar ferramenta: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ========== ROTAS HTML PARA PÁGINA DE CHAT ==========

@openai_chat_router.get("/ai/chat", response_class=HTMLResponse)
async def ai_chat_page(
    request: Request,
    thread_id: Optional[str] = None,
    assistant_id: Optional[int] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de chat com IA (estilo ChatGPT)"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("ai_chat.html", 
                         request=request,
                         user=user_data,
                         thread_id=thread_id,
                         assistant_id=assistant_id)

