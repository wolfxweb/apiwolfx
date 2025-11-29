"""
Rotas para sistema de Tarefas e Atividades
"""
from fastapi import APIRouter, Depends, Request, Cookie, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.task_controller import TaskController
from app.controllers.auth_controller import AuthController
from app.views.template_renderer import render_template
from typing import Optional
from datetime import date

task_router = APIRouter()
templates = Jinja2Templates(directory="app/views/templates")


def get_current_user_or_redirect(session_token: Optional[str], db: Session):
    """Obtém usuário atual ou retorna None"""
    if not session_token:
        return None
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return None
    
    return result.get("user")


@task_router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de lista de tarefas"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company_id")
    if not company_id:
        return render_template("error.html", request=request, error_message="Empresa não encontrada")
    
    # Obter usuários da empresa para o select de atribuição
    controller = TaskController(db)
    company_users = controller.get_company_users(company_id)
    
    return render_template(
        "tasks.html",
        request=request,
        user=user,
        company_users=company_users
    )


@task_router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_view_page(
    task_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de visualização de uma tarefa"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company_id")
    if not company_id:
        return render_template("error.html", request=request, error_message="Empresa não encontrada")
    
    controller = TaskController(db)
    result = controller.get_task(task_id, company_id)
    
    if not result.get("success"):
        return render_template("error.html", request=request, error_message=result.get("error", "Tarefa não encontrada"))
    
    task = result.get("task")
    company_users = controller.get_company_users(company_id)
    
    return render_template(
        "task_view.html",
        request=request,
        user=user,
        task=task,
        company_users=company_users
    )


# ========== API ROUTES ==========

@task_router.get("/api/tasks", response_class=JSONResponse)
async def list_tasks_api(
    request: Request,
    status: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    created_by: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    due_date_from: Optional[str] = Query(None),
    due_date_to: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar tarefas"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    company_id = user.get("company_id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    # Converter datas se fornecidas
    due_date_from_parsed = None
    due_date_to_parsed = None
    
    if due_date_from:
        try:
            due_date_from_parsed = date.fromisoformat(due_date_from)
        except ValueError:
            pass
    
    if due_date_to:
        try:
            due_date_to_parsed = date.fromisoformat(due_date_to)
        except ValueError:
            pass
    
    controller = TaskController(db)
    result = controller.list_tasks(
        company_id=company_id,
        status=status,
        assigned_to=assigned_to,
        created_by=created_by,
        category=category,
        search=search,
        due_date_from=due_date_from_parsed,
        due_date_to=due_date_to_parsed
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )


@task_router.post("/api/tasks", response_class=JSONResponse)
async def create_task_api(
    request: Request,
    task_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar tarefa"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    company_id = user.get("company_id")
    user_id = user.get("id")
    
    if not company_id or not user_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Dados do usuário incompletos"}
        )
    
    # Validar campos obrigatórios
    title = task_data.get("title")
    due_date_str = task_data.get("due_date")
    
    if not title:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Título é obrigatório"}
        )
    
    if not due_date_str:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Data de vencimento é obrigatória"}
        )
    
    try:
        due_date = date.fromisoformat(due_date_str)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Data de vencimento inválida"}
        )
    
    controller = TaskController(db)
    result = controller.create_task(
        company_id=company_id,
        user_id=user_id,
        title=title,
        due_date=due_date,
        assigned_to=task_data.get("assigned_to"),
        description=task_data.get("description"),
        status=task_data.get("status", "pending"),
        priority=task_data.get("priority", "medium"),
        category=task_data.get("category"),
        product_id=task_data.get("product_id")
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )


@task_router.get("/api/tasks/{task_id}", response_class=JSONResponse)
async def get_task_api(
    task_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter uma tarefa"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    company_id = user.get("company_id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = TaskController(db)
    result = controller.get_task(task_id, company_id)
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=404,
            content=result
        )


@task_router.patch("/api/tasks/{task_id}", response_class=JSONResponse)
async def update_task_api(
    task_id: int,
    request: Request,
    task_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar tarefa"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    company_id = user.get("company_id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    # Converter due_date se fornecido
    due_date = None
    if task_data.get("due_date"):
        try:
            due_date = date.fromisoformat(task_data.get("due_date"))
        except ValueError:
            pass
    
    controller = TaskController(db)
    result = controller.update_task(
        task_id=task_id,
        company_id=company_id,
        title=task_data.get("title"),
        description=task_data.get("description"),
        assigned_to=task_data.get("assigned_to"),
        due_date=due_date,
        priority=task_data.get("priority"),
        category=task_data.get("category"),
        product_id=task_data.get("product_id")
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )


@task_router.patch("/api/tasks/{task_id}/status", response_class=JSONResponse)
async def update_task_status_api(
    task_id: int,
    request: Request,
    status_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar status da tarefa"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    company_id = user.get("company_id")
    user_id = user.get("id")
    
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    status = status_data.get("status")
    if not status:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Status é obrigatório"}
        )
    
    controller = TaskController(db)
    result = controller.update_task_status(
        task_id=task_id,
        company_id=company_id,
        status=status,
        user_id=user_id
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )


@task_router.delete("/api/tasks/{task_id}", response_class=JSONResponse)
async def delete_task_api(
    task_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir tarefa"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    company_id = user.get("company_id")
    user_id = user.get("id")
    
    if not company_id or not user_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Dados do usuário incompletos"}
        )
    
    controller = TaskController(db)
    result = controller.delete_task(
        task_id=task_id,
        company_id=company_id,
        user_id=user_id
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )


@task_router.get("/api/tasks/users/list", response_class=JSONResponse)
async def list_company_users_api(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar usuários da empresa (para atribuição)"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    company_id = user.get("company_id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = TaskController(db)
    users = controller.get_company_users(company_id)
    
    return JSONResponse(content={"success": True, "users": users})

