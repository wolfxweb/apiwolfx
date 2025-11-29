"""
Rotas para suporte e documentação
"""
from fastapi import APIRouter, Depends, Request, Cookie, Query, Body, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from pathlib import Path

from app.config.database import get_db
from app.controllers.support_controller import SupportController
from app.controllers.auth_controller import AuthController
from app.views.template_renderer import render_template
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Router para suporte
support_router = APIRouter()


class CreateTicketRequest(BaseModel):
    subject: str
    description: str
    category: Optional[str] = None
    priority: str = "medium"


@support_router.get("/support/ticket/{ticket_id}", response_class=HTMLResponse)
async def view_ticket_page(
    ticket_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página para visualizar um chamado específico"""
    if not session_token:
        return RedirectResponse(url="/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/login", status_code=302)
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return RedirectResponse(url="/support", status_code=302)
    
    controller = SupportController(db)
    ticket_result = controller.get_ticket(ticket_id, company_id)
    
    if not ticket_result.get("success"):
        return RedirectResponse(url="/support", status_code=302)
    
    return render_template(
        "support_ticket_view.html",
        request=request,
        user=user_data,
        ticket=ticket_result.get("ticket")
    )


@support_router.get("/support", response_class=HTMLResponse)
async def support_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de suporte"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    # Preparar dados da página
    controller = SupportController(db)
    page_data = controller.get_support_page(user_data)
    
    return render_template("support.html", user=user_data, page_data=page_data)


@support_router.get("/api/support/manuals", response_class=JSONResponse)
async def get_manuals_api(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar manuais"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    controller = SupportController(db)
    response = controller.get_manuals()
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=500,
            content=response
        )


@support_router.get("/api/support/manuals/{filename}", response_class=JSONResponse)
async def get_manual_api(
    filename: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter conteúdo de um manual"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    controller = SupportController(db)
    response = controller.get_manual(filename)
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in response.get("error", "").lower() else 500,
            content=response
        )


@support_router.get("/api/support/search", response_class=JSONResponse)
async def search_manuals_api(
    request: Request,
    q: str = Query(..., description="Termo de busca"),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar nos manuais"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    controller = SupportController(db)
    response = controller.search_manuals(q)
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=500,
            content=response
        )


@support_router.post("/api/support/tickets", response_class=JSONResponse)
async def create_ticket_api(
    request: Request,
    ticket_data: CreateTicketRequest,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar um chamado de suporte"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    user_id = user_data.get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = SupportController(db)
    response = controller.create_ticket(
        company_id=company_id,
        user_id=user_id,
        subject=ticket_data.subject,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority
    )
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=500,
            content=response
        )


@support_router.get("/api/support/tickets", response_class=JSONResponse)
async def list_tickets_api(
    request: Request,
    status: Optional[str] = Query(None, description="Filtrar por status"),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar chamados de suporte"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    user_id = user_data.get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = SupportController(db)
    response = controller.list_tickets(
        company_id=company_id,
        user_id=user_id,
        status=status
    )
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=500,
            content=response
        )


@support_router.get("/api/support/tickets/{ticket_id}", response_class=JSONResponse)
async def get_ticket_api(
    ticket_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter um chamado específico"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = SupportController(db)
    response = controller.get_ticket(ticket_id, company_id)
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in response.get("error", "").lower() else 500,
            content=response
        )


@support_router.post("/api/support/tickets/{ticket_id}/attachments", response_class=JSONResponse)
async def upload_attachment_api(
    ticket_id: int,
    request: Request,
    files: List[UploadFile] = File(...),
    message_id: Optional[int] = Form(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para fazer upload de anexos em um chamado"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    user_id = user_data.get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = SupportController(db)
    uploaded_attachments = []
    
    for file in files:
        if not file.filename:
            continue
        
        # Ler conteúdo do arquivo
        file_content = await file.read()
        
        # Validar tamanho (máximo 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            continue
        
        # Fazer upload
        response = controller.upload_attachment(
            ticket_id=ticket_id,
            company_id=company_id,
            user_id=user_id,
            filename=file.filename,
            file_content=file_content,
            content_type=file.content_type or "application/octet-stream",
            message_id=message_id
        )
        
        if response.get("success"):
            uploaded_attachments.append(response.get("attachment"))
    
    if uploaded_attachments:
        return JSONResponse(content={
            "success": True,
            "attachments": uploaded_attachments,
            "message": f"{len(uploaded_attachments)} anexo(s) enviado(s) com sucesso"
        })
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Nenhum arquivo foi enviado ou todos foram rejeitados"}
        )


@support_router.get("/api/support/tickets/{ticket_id}/attachments", response_class=JSONResponse)
async def list_attachments_api(
    ticket_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar anexos de um chamado"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = SupportController(db)
    response = controller.get_ticket_attachments(ticket_id, company_id)
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in response.get("error", "").lower() else 500,
            content=response
        )


@support_router.post("/api/support/tickets/{ticket_id}/messages", response_class=JSONResponse)
async def add_message_api(
    ticket_id: int,
    request: Request,
    message_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para adicionar uma mensagem a um chamado"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    user_id = user_data.get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    message_content = message_data.get("message", "").strip()
    if not message_content:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Mensagem não pode estar vazia"}
        )
    
    controller = SupportController(db)
    response = controller.add_message_to_ticket(
        ticket_id=ticket_id,
        company_id=company_id,
        user_id=user_id,
        message_content=message_content,
        is_from_support=False
    )
    
    # Se houver anexos, fazer upload
    if response.get("success") and message_data.get("attachments"):
        # Upload será feito separadamente via endpoint de attachments
        pass
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in response.get("error", "").lower() else 500,
            content=response
        )


@support_router.patch("/api/support/tickets/{ticket_id}/status", response_class=JSONResponse)
async def update_ticket_status_api(
    ticket_id: int,
    request: Request,
    status_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar o status de um chamado"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    new_status = status_data.get("status", "").strip()
    if not new_status:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Status não pode estar vazio"}
        )
    
    controller = SupportController(db)
    response = controller.update_ticket_status(
        ticket_id=ticket_id,
        company_id=company_id,
        status=new_status
    )
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in response.get("error", "").lower() else 500,
            content=response
        )

