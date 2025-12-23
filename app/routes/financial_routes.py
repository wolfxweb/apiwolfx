"""
Rotas para o módulo financeiro SaaS
Seguindo o padrão do sistema
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Cookie, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text, literal
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, date, timedelta

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.models.financial_models import (
    FinancialAccount, FinancialCategory, CostCenter, FinancialCustomer,
    AccountReceivable, FinancialSupplier, AccountPayable, FinancialTransaction
)
from app.models.saas_models import MLOrder, Fornecedor, OrdemCompra

# Configurar logging
logger = logging.getLogger(__name__)

# Criar router
financial_router = APIRouter()

# Instanciar controller
auth_controller = AuthController()

# Funções auxiliares para operações com banco de dados
def get_company_id_from_user(user_data: dict) -> int:
    """Extrai o company_id do usuário logado"""
    company_id = user_data.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID não encontrado")
    return company_id

# =====================================================
# ROTAS DE INTERFACE (TEMPLATES)
# =====================================================

@financial_router.get("/financial/categories", response_class=HTMLResponse)
async def financial_categories(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de categorias financeiras"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    logger.info(f"🔍 DEBUG - user_data keys: {list(user_data.keys()) if user_data else 'None'}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_categories.html", user=user_data)

@financial_router.get("/financial/payables", response_class=HTMLResponse)
async def financial_payables(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de contas a pagar"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("financial_payables.html", user=user_data)

@financial_router.get("/financial/payables/nova", response_class=HTMLResponse)
async def nova_conta_pagar(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de nova conta a pagar"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("nova_conta_pagar.html", user=user_data)

@financial_router.get("/financial/payables/editar/{payable_id}", response_class=HTMLResponse)
async def editar_conta_pagar(
    payable_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de edição de conta a pagar"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a pagar
    payable = db.query(AccountPayable).filter(
        AccountPayable.id == payable_id,
        AccountPayable.company_id == company_id
    ).first()
    
    if not payable:
        return RedirectResponse(url="/financial/payables", status_code=302)
    
    # Preparar dados para o template
    payable_data = {
        "id": payable.id,
        "supplier_name": payable.supplier_name,
        "fornecedor_id": payable.fornecedor_id,
        "ordem_compra_id": payable.ordem_compra_id,
        "invoice_number": payable.invoice_number,
        "description": payable.description,
        "amount": float(payable.amount),
        "due_date": payable.due_date.isoformat() if payable.due_date else None,
        "category_id": payable.category_id,
        "cost_center_id": payable.cost_center_id,
        "account_id": payable.account_id,
        "is_fixed": payable.is_fixed,
        "expense_type": "single",  # Default
        "recurring_frequency": payable.recurring_frequency,
        "recurring_end_date": payable.recurring_end_date.isoformat() if payable.recurring_end_date else None,
        "total_installments": payable.total_installments,
        "installment_due_date": None,  # Será calculado se necessário
        "notes": payable.notes
    }
    
    from app.views.template_renderer import render_template
    return render_template("editar_conta_pagar.html", user=user_data, payable_data=payable_data)

@financial_router.get("/financial/cost-centers", response_class=HTMLResponse)
async def financial_cost_centers(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de centros de custo"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_cost_centers.html", user=user_data)

@financial_router.get("/financial/accounts", response_class=HTMLResponse)
async def financial_accounts(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de contas bancárias"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_accounts.html", user=user_data)

@financial_router.get("/financial/account-transactions/{account_id}", response_class=HTMLResponse)
async def financial_account_transactions(
    account_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de movimentações de uma conta específica"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    # Buscar dados da conta
    from app.models.financial_models import FinancialAccount
    account = db.query(FinancialAccount).filter(
        and_(
            FinancialAccount.id == account_id,
            FinancialAccount.company_id == user_data["company_id"]
        )
    ).first()
    
    if not account:
        return RedirectResponse(url="/financial/accounts", status_code=302)
    
    from app.views.template_renderer import render_template
    return render_template("financial_account_transactions.html", 
                         user=user_data, account=account)

@financial_router.get("/financial/receivables", response_class=HTMLResponse)
async def financial_receivables(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de contas a receber"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_receivables.html", user=user_data)

@financial_router.get("/financial/cashflow", response_class=HTMLResponse)
async def financial_cashflow(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de fluxo de caixa"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_cashflow.html", user=user_data)

@financial_router.get("/financial/dashboard", response_class=HTMLResponse)
async def financial_dashboard(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página do dashboard financeiro"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_dashboard.html", user=user_data)

@financial_router.get("/financial/reports", response_class=HTMLResponse)
async def financial_reports(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de planejamento financeiro"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("financial_reports.html", user=user_data)

@financial_router.get("/financial/planning/create", response_class=HTMLResponse)
async def create_planning_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página para criar novo planejamento financeiro"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("create_planning.html", user=user_data)

@financial_router.get("/financial/planning/edit/{year}", response_class=HTMLResponse)
async def edit_planning_page(
    year: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página para editar planejamento financeiro existente"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("edit_planning.html", user=user_data, year=year)

# =====================================================
# ROTAS DE API
# =====================================================

@financial_router.get("/api/financial/categories")
async def get_financial_categories(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter categorias financeiras"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    logger.info(f"🔍 DEBUG - Buscando categorias para company_id: {company_id}")
    
    # Buscar categorias no banco de dados
    categories = db.query(FinancialCategory).filter(
        FinancialCategory.company_id == company_id
    ).order_by(FinancialCategory.name).all()
    
    logger.info(f"🔍 DEBUG - Encontradas {len(categories)} categorias")
    
    return {
        "categories": [
            {
                "id": cat.id,
                "code": cat.code,
                "name": cat.name,
                "type": cat.type.value if cat.type else None,
                "monthly_limit": float(cat.monthly_limit) if cat.monthly_limit else None,
                "description": cat.description,
                "is_active": cat.is_active,
                "created_at": cat.created_at,
                "company_id": cat.company_id
            }
            for cat in categories
        ]
    }

@financial_router.post("/api/financial/categories")
async def create_financial_category(
    category_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar categoria financeira"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Validar dados obrigatórios
    if not category_data.get("name"):
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    if not category_data.get("type"):
        raise HTTPException(status_code=400, detail="Tipo é obrigatório")
    
    # Gerar código automaticamente se não fornecido
    code = category_data.get("code", "").strip()
    if not code:
        # Buscar o último código gerado para esta empresa
        last_category = db.query(FinancialCategory).filter(
            FinancialCategory.company_id == company_id,
            FinancialCategory.code.like("CT-%")
        ).order_by(FinancialCategory.code.desc()).first()
        
        if last_category and last_category.code:
            # Extrair número do último código e incrementar
            try:
                last_number = int(last_category.code.split("-")[1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        # Gerar novo código no formato CT-001, CT-002, etc.
        code = f"CT-{next_number:03d}"
    
    # Criar nova categoria no banco
    from app.models.financial_models import CategoryType
    
    new_category = FinancialCategory(
        company_id=company_id,
        code=code,
        name=category_data.get("name"),
        type=CategoryType(category_data.get("type")),
        monthly_limit=float(category_data.get("monthly_limit", 0)) if category_data.get("monthly_limit") else None,
        description=category_data.get("description", ""),
        is_active=category_data.get("is_active", True)
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    logger.info(f"✅ Categoria criada: {new_category.name} (ID: {new_category.id})")
    return {"message": "Categoria criada com sucesso", "id": new_category.id}

@financial_router.put("/api/financial/categories/{category_id}")
async def update_financial_category(
    category_id: int,
    category_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar categoria financeira"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar categoria existente
    category = db.query(FinancialCategory).filter(
        FinancialCategory.id == category_id,
        FinancialCategory.company_id == company_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Validar dados obrigatórios
    if not category_data.get("name"):
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    if not category_data.get("type"):
        raise HTTPException(status_code=400, detail="Tipo é obrigatório")
    
    # Atualizar categoria
    from app.models.financial_models import CategoryType
    from datetime import datetime
    
    category.code = category_data.get("code", category.code)
    category.name = category_data.get("name")
    category.type = CategoryType(category_data.get("type"))
    category.monthly_limit = float(category_data.get("monthly_limit", 0)) if category_data.get("monthly_limit") else None
    category.description = category_data.get("description", category.description)
    category.is_active = category_data.get("is_active", category.is_active)
    category.updated_at = datetime.now()
    
    db.commit()
    db.refresh(category)
    
    logger.info(f"✅ Categoria atualizada: {category.name} (ID: {category_id})")
    return {"message": "Categoria atualizada com sucesso"}

@financial_router.delete("/api/financial/categories/{category_id}")
async def delete_financial_category(
    category_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir categoria financeira"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar categoria existente
    category = db.query(FinancialCategory).filter(
        FinancialCategory.id == category_id,
        FinancialCategory.company_id == company_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    category_name = category.name
    
    # Verificar se a categoria está sendo usada em contas a pagar
    from app.models.financial_models import AccountPayable
    payables_using_category = db.query(AccountPayable).filter(
        AccountPayable.category_id == category_id,
        AccountPayable.company_id == company_id
    ).count()
    
    if payables_using_category > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Não é possível excluir a categoria '{category_name}' pois ela está sendo usada em {payables_using_category} conta(s) a pagar"
        )
    
    # Excluir categoria
    db.delete(category)
    db.commit()
    
    logger.info(f"✅ Categoria excluída: {category_name} (ID: {category_id})")
    return {"message": "Categoria excluída com sucesso"}

# =====================================================
# ROTAS DE API PARA CENTROS DE CUSTO
# =====================================================

@financial_router.get("/api/financial/cost-centers")
async def get_cost_centers(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter centros de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    logger.info(f"🔍 DEBUG - Buscando centros de custo para company_id: {company_id}")
    
    # Buscar centros de custo no banco de dados
    cost_centers = db.query(CostCenter).filter(
        CostCenter.company_id == company_id
    ).order_by(CostCenter.name).all()
    
    logger.info(f"🔍 DEBUG - Encontrados {len(cost_centers)} centros de custo")
    
    return [
        {
            "id": cc.id,
            "code": cc.code,
            "name": cc.name,
            "description": cc.description,
            "is_active": cc.is_active,
            "created_at": cc.created_at,
            "company_id": cc.company_id
        }
        for cc in cost_centers
    ]

@financial_router.post("/api/financial/cost-centers")
async def create_cost_center(
    cost_center_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar centro de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Validar dados obrigatórios
    if not cost_center_data.get("name"):
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    
    # Gerar código automaticamente se não fornecido
    code = cost_center_data.get("code", "").strip()
    if not code:
        # Buscar o último código gerado para esta empresa
        last_cost_center = db.query(CostCenter).filter(
            CostCenter.company_id == company_id,
            CostCenter.code.like("CC-%")
        ).order_by(CostCenter.code.desc()).first()
        
        if last_cost_center and last_cost_center.code:
            # Extrair número do último código e incrementar
            try:
                last_number = int(last_cost_center.code.split("-")[1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        # Gerar novo código no formato CC-001, CC-002, etc.
        code = f"CC-{next_number:03d}"
    
    # Criar novo centro de custo no banco
    new_cost_center = CostCenter(
        company_id=company_id,
        code=code,
        name=cost_center_data.get("name"),
        description=cost_center_data.get("description", ""),
        is_active=cost_center_data.get("is_active", True)
    )
    
    db.add(new_cost_center)
    db.commit()
    db.refresh(new_cost_center)
    
    logger.info(f"✅ Centro de custo criado: {new_cost_center.name} (ID: {new_cost_center.id})")
    return {"message": "Centro de custo criado com sucesso", "id": new_cost_center.id}

@financial_router.put("/api/financial/cost-centers/{cost_center_id}")
async def update_cost_center(
    cost_center_id: int,
    cost_center_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar centro de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar centro de custo existente
    cost_center = db.query(CostCenter).filter(
        CostCenter.id == cost_center_id,
        CostCenter.company_id == company_id
    ).first()
    
    if not cost_center:
        raise HTTPException(status_code=404, detail="Centro de custo não encontrado")
    
    # Atualizar campos
    if cost_center_data.get("code") is not None:
        cost_center.code = cost_center_data.get("code")
    if cost_center_data.get("name"):
        cost_center.name = cost_center_data.get("name")
    if cost_center_data.get("description") is not None:
        cost_center.description = cost_center_data.get("description")
    if cost_center_data.get("color") is not None:
        cost_center.color = cost_center_data.get("color")
    if cost_center_data.get("is_active") is not None:
        cost_center.is_active = cost_center_data.get("is_active")
    
    db.commit()
    
    logger.info(f"✅ Centro de custo atualizado: {cost_center.name} (ID: {cost_center_id})")
    return {"message": "Centro de custo atualizado com sucesso"}

@financial_router.delete("/api/financial/cost-centers/{cost_center_id}")
async def delete_cost_center(
    cost_center_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir centro de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar centro de custo existente
    cost_center = db.query(CostCenter).filter(
        CostCenter.id == cost_center_id,
        CostCenter.company_id == company_id
    ).first()
    
    if not cost_center:
        raise HTTPException(status_code=404, detail="Centro de custo não encontrado")
    
    # Verificação de centros filhos removida (coluna parent_id não existe)
    
    # Remover centro de custo
    db.delete(cost_center)
    db.commit()
    
    logger.info(f"✅ Centro de custo excluído: {cost_center.name} (ID: {cost_center_id})")
    return {"message": "Centro de custo excluído com sucesso"}

# =====================================================
# ROTAS DE API PARA CONTAS BANCÁRIAS
# =====================================================

@financial_router.get("/api/financial/accounts")
async def get_bank_accounts(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter contas bancárias"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    logger.info(f"🔍 DEBUG - Buscando contas bancárias para company_id: {company_id}")
    
    # Buscar contas bancárias no banco de dados
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.company_id == company_id
    ).order_by(FinancialAccount.bank_name, FinancialAccount.account_name).all()
    
    logger.info(f"🔍 DEBUG - Encontradas {len(accounts)} contas bancárias")
    
    return [
        {
            "id": acc.id,
            "bank_name": acc.bank_name,
            "account_name": acc.account_name,
            "account_type": acc.account_type,
            "agency": acc.agency,
            "account_number": acc.account_number,
            "initial_balance": float(acc.initial_balance),
            "current_balance": float(acc.current_balance),
            "is_active": acc.is_active,
            "is_main_account": acc.is_main_account,  # Adicionado campo is_main_account
            "description": acc.description,
            "created_at": acc.created_at,
            "company_id": acc.company_id,
            # Campos específicos para cartão de crédito
            "limit_amount": float(acc.limit_amount) if acc.limit_amount else None,
            "card_number": acc.card_number,
            "invoice_due_day": acc.invoice_due_day,
            "holder_name": acc.holder_name,
            "holder_document": acc.holder_document
        }
        for acc in accounts
    ]

@financial_router.get("/api/financial/account-transactions/{account_id}")
async def get_account_transactions(
    account_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter transações de uma conta específica"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Verificar se a conta pertence à empresa
    from app.models.financial_models import FinancialAccount, FinancialTransaction
    account = db.query(FinancialAccount).filter(
        and_(
            FinancialAccount.id == account_id,
            FinancialAccount.company_id == company_id
        )
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Buscar transações da conta (filtradas por company_id)
    transactions = db.query(FinancialTransaction).filter(
        and_(
            FinancialTransaction.account_id == account_id,
            FinancialTransaction.company_id == company_id
        )
    ).order_by(FinancialTransaction.created_at.desc()).all()
    
    # Calcular estatísticas
    total_credits = sum(float(t.amount) for t in transactions if t.transaction_type == "credit")
    total_debits = sum(float(t.amount) for t in transactions if t.transaction_type == "debit")
    net_balance = total_credits - total_debits
    
    return {
        "account": {
            "id": account.id,
            "bank_name": account.bank_name,
            "account_name": account.account_name,
            "current_balance": float(account.current_balance or 0)
        },
        "transactions": [
            {
                "id": t.id,
                "transaction_type": t.transaction_type,
                "amount": float(t.amount),
                "description": t.description,
                "reference_type": t.reference_type,
                "reference_id": t.reference_id,
                "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in transactions
        ],
        "statistics": {
            "total_credits": total_credits,
            "total_debits": total_debits,
            "net_balance": net_balance,
            "total_transactions": len(transactions)
        }
    }

@financial_router.post("/api/financial/transfer")
async def process_transfer(
    transfer_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para processar transferência entre contas"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Validar dados obrigatórios
    from_account_id = transfer_data.get("from_account_id")
    to_account_id = transfer_data.get("to_account_id")
    amount = transfer_data.get("amount")
    description = transfer_data.get("description", "Transferência entre contas")
    
    if not from_account_id or not to_account_id or not amount:
        raise HTTPException(status_code=400, detail="Dados obrigatórios não fornecidos")
    
    if from_account_id == to_account_id:
        raise HTTPException(status_code=400, detail="Conta de origem e destino não podem ser iguais")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")
    
    try:
        # Buscar contas
        from_account = db.query(FinancialAccount).filter(
            and_(
                FinancialAccount.id == from_account_id,
                FinancialAccount.company_id == company_id
            )
        ).first()
        
        to_account = db.query(FinancialAccount).filter(
            and_(
                FinancialAccount.id == to_account_id,
                FinancialAccount.company_id == company_id
            )
        ).first()
        
        if not from_account:
            raise HTTPException(status_code=404, detail="Conta de origem não encontrada")
        
        if not to_account:
            raise HTTPException(status_code=404, detail="Conta de destino não encontrada")
        
        # Verificar saldo suficiente (considerando tipo de conta)
        current_balance = float(from_account.current_balance or 0)
        is_from_credit_card = from_account.account_type == "credit"
        
        # Para cartão de crédito, saldo negativo é permitido (dívida)
        # Para outras contas, verificar saldo suficiente
        if not is_from_credit_card and amount > current_balance:
            raise HTTPException(status_code=400, detail="Saldo insuficiente")
        
        # Criar transações
        # Transação de débito na conta de origem
        debit_transaction = FinancialTransaction(
            company_id=company_id,
            account_id=from_account_id,
            transaction_type="debit",
            amount=amount,
            description=f"Débito - {description} - Enviado para {to_account.bank_name} - {to_account.account_name}",
            transaction_date=datetime.now().date(),
            reference_type="transfer",
            reference_id=f"transfer_{from_account_id}_to_{to_account_id}"
        )
        
        # Transação de crédito na conta de destino
        credit_transaction = FinancialTransaction(
            company_id=company_id,
            account_id=to_account_id,
            transaction_type="credit",
            amount=amount,
            description=f"Crédito - {description} - Recebido de {from_account.bank_name} - {from_account.account_name}",
            transaction_date=datetime.now().date(),
            reference_type="transfer",
            reference_id=f"transfer_{from_account_id}_to_{to_account_id}"
        )
        
        # Atualizar saldos considerando tipo de conta
        from_account.current_balance = current_balance - amount
        to_account.current_balance = float(to_account.current_balance or 0) + amount
        
        # Salvar no banco
        db.add(debit_transaction)
        db.add(credit_transaction)
        db.commit()
        
        logger.info(f"💰 Transferência realizada: R$ {amount:.2f} da conta {from_account.account_name} para {to_account.account_name}")
        
        return {
            "success": True,
            "message": "Transferência realizada com sucesso",
            "transfer_id": f"transfer_{from_account_id}_to_{to_account_id}",
            "amount": amount,
            "from_account": from_account.account_name,
            "to_account": to_account.account_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar transferência: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@financial_router.delete("/api/financial/transaction/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para remover transação e ajustar saldo da conta"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    try:
        # Buscar transação
        transaction = db.query(FinancialTransaction).filter(
            and_(
                FinancialTransaction.id == transaction_id,
                FinancialTransaction.company_id == company_id
            )
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        
        # Buscar conta
        account = db.query(FinancialAccount).filter(
            and_(
                FinancialAccount.id == transaction.account_id,
                FinancialAccount.company_id == company_id
            )
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Conta não encontrada")
        
        # Ajustar saldo da conta (reverter a transação)
        current_balance = float(account.current_balance or 0)
        if transaction.transaction_type == "credit":
            # Se era crédito, subtrair do saldo
            new_balance = current_balance - float(transaction.amount)
        else:
            # Se era débito, somar ao saldo
            new_balance = current_balance + float(transaction.amount)
        
        # Atualizar saldo da conta
        account.current_balance = new_balance
        
        # Remover transação
        db.delete(transaction)
        db.commit()
        
        logger.info(f"🗑️ Transação {transaction_id} removida. Saldo da conta {account.account_name} ajustado de R$ {current_balance:.2f} para R$ {new_balance:.2f}")
        
        return {
            "success": True,
            "message": "Transação removida com sucesso",
            "transaction_id": transaction_id,
            "account_name": account.account_name,
            "old_balance": current_balance,
            "new_balance": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover transação: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@financial_router.post("/api/financial/transaction")
async def create_transaction(
    transaction_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar nova movimentação manual"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    try:
        # Validar dados
        account_id = transaction_data.get("account_id")
        transaction_type = transaction_data.get("transaction_type")
        reference_type = transaction_data.get("reference_type")
        amount = float(transaction_data.get("amount", 0))
        description = transaction_data.get("description", "")
        transaction_date = transaction_data.get("transaction_date")
        
        if not all([account_id, transaction_type, reference_type, amount, description, transaction_date]):
            raise HTTPException(status_code=400, detail="Todos os campos são obrigatórios")
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")
        
        # Verificar se a conta pertence à empresa
        account = db.query(FinancialAccount).filter(
            and_(
                FinancialAccount.id == account_id,
                FinancialAccount.company_id == company_id
            )
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Conta não encontrada")
        
        # Criar transação
        transaction = FinancialTransaction(
            company_id=company_id,
            account_id=account_id,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            transaction_date=datetime.strptime(transaction_date, '%Y-%m-%d').date(),
            reference_type=reference_type,
            reference_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        db.add(transaction)
        
        # Atualizar saldo da conta considerando tipo de conta
        current_balance = float(account.current_balance or 0)
        is_credit_card = account.account_type == "credit"
        
        # Para cartões de crédito, a lógica é inversa:
        # - Crédito aumenta dívida (diminui saldo disponível)
        # - Débito diminui dívida (aumenta saldo disponível)
        if is_credit_card:
            if transaction_type == "credit":
                new_balance = current_balance - amount  # Crédito aumenta dívida
            else:
                new_balance = current_balance + amount  # Débito diminui dívida
        else:
            # Para contas normais, lógica tradicional
            if transaction_type == "credit":
                new_balance = current_balance + amount
            else:
                new_balance = current_balance - amount
        
        account.current_balance = new_balance
        
        db.commit()
        
        logger.info(f"💰 Movimentação criada: {transaction_type} R$ {amount:.2f} - {description}")
        
        return {
            "success": True,
            "message": "Movimentação criada com sucesso",
            "transaction_id": transaction.id,
            "new_balance": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar movimentação: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@financial_router.post("/api/financial/accounts")
async def create_bank_account(
    account_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar conta bancária"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Validar dados obrigatórios
    if not account_data.get("bank_name"):
        raise HTTPException(status_code=400, detail="Nome do banco é obrigatório")
    if not account_data.get("account_name"):
        raise HTTPException(status_code=400, detail="Nome da conta é obrigatório")
    if not account_data.get("account_type"):
        raise HTTPException(status_code=400, detail="Tipo da conta é obrigatório")
    
    # Log dos dados recebidos
    logger.info(f"🔍 Dados recebidos para criação de conta: {account_data}")
    logger.info(f"🔍 Campo is_main_account: {account_data.get('is_main_account')}")
    
    # Criar nova conta bancária no banco
    new_account = FinancialAccount(
        company_id=company_id,
        bank_name=account_data.get("bank_name"),
        account_name=account_data.get("account_name"),
        account_type=account_data.get("account_type"),
        agency=account_data.get("agency"),
        account_number=account_data.get("account_number"),
        initial_balance=float(account_data.get("initial_balance", 0)),
        current_balance=float(account_data.get("initial_balance", 0)), # Saldo atual começa com o saldo inicial
        is_active=account_data.get("is_active", True),
        is_main_account=account_data.get("is_main_account", False),
        description=account_data.get("description"),
        # Campos específicos para cartão de crédito
        limit_amount=float(account_data.get("limit_amount", 0)) if account_data.get("limit_amount") else None,
        card_number=account_data.get("card_number"),
        invoice_due_day=int(account_data.get("invoice_due_day")) if account_data.get("invoice_due_day") else None,
        holder_name=account_data.get("holder_name"),
        holder_document=account_data.get("holder_document")
    )
    
    logger.info(f"✅ Nova conta criada com is_main_account: {new_account.is_main_account}")
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    logger.info(f"✅ Conta bancária criada: {new_account.account_name} (ID: {new_account.id})")
    return {"message": "Conta bancária criada com sucesso", "id": new_account.id}

@financial_router.put("/api/financial/accounts/{account_id}")
async def update_bank_account(
    account_id: int,
    account_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar conta bancária"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar conta bancária existente
    account = db.query(FinancialAccount).filter(
        FinancialAccount.id == account_id,
        FinancialAccount.company_id == company_id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada")
    
    # Log dos dados recebidos
    logger.info(f"🔍 Dados recebidos para atualização da conta {account_id}: {account_data}")
    logger.info(f"🔍 Campo is_main_account: {account_data.get('is_main_account')}")
    
    # Atualizar campos
    if account_data.get("bank_name"):
        account.bank_name = account_data.get("bank_name")
    if account_data.get("account_name"):
        account.account_name = account_data.get("account_name")
    if account_data.get("account_type"):
        account.account_type = account_data.get("account_type")
    if account_data.get("agency") is not None:
        account.agency = account_data.get("agency")
    if account_data.get("account_number") is not None:
        account.account_number = account_data.get("account_number")
    # Campos de cartão temporariamente desativados no modelo
    if account_data.get("initial_balance") is not None:
        account.initial_balance = float(account_data.get("initial_balance"))
    if account_data.get("current_balance") is not None:
        account.current_balance = float(account_data.get("current_balance"))
    if account_data.get("is_active") is not None:
        account.is_active = account_data.get("is_active")
    # Sempre atualizar is_main_account (mesmo se for False)
    if "is_main_account" in account_data:
        account.is_main_account = account_data.get("is_main_account", False)
        logger.info(f"✅ Campo is_main_account atualizado para: {account.is_main_account}")
    else:
        logger.warning("⚠️ Campo is_main_account não encontrado nos dados recebidos")
    if account_data.get("description") is not None:
        account.description = account_data.get("description")
    
    # Campos específicos para cartão de crédito
    if account_data.get("limit_amount") is not None:
        account.limit_amount = float(account_data.get("limit_amount")) if account_data.get("limit_amount") else None
    if account_data.get("card_number") is not None:
        account.card_number = account_data.get("card_number")
    if account_data.get("invoice_due_day") is not None:
        account.invoice_due_day = int(account_data.get("invoice_due_day")) if account_data.get("invoice_due_day") else None
    if account_data.get("holder_name") is not None:
        account.holder_name = account_data.get("holder_name")
    if account_data.get("holder_document") is not None:
        account.holder_document = account_data.get("holder_document")
    
    db.commit()
    
    logger.info(f"✅ Conta bancária atualizada: {account.account_name} (ID: {account_id})")
    return {"message": "Conta bancária atualizada com sucesso"}

@financial_router.delete("/api/financial/accounts/{account_id}")
async def delete_bank_account(
    account_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir conta bancária"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar conta bancária existente
    account = db.query(FinancialAccount).filter(
        FinancialAccount.id == account_id,
        FinancialAccount.company_id == company_id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada")
    
    # Verificação de conta principal removida (coluna is_main não existe)
    
    # Remover conta bancária
    db.delete(account)
    db.commit()
    
    logger.info(f"✅ Conta bancária excluída: {account.account_name} (ID: {account_id})")
    return {"message": "Conta bancária excluída com sucesso"}

# =====================================================
# ROTAS DE API PARA CONTAS A RECEBER
# =====================================================

@financial_router.get("/api/financial/receivables")
async def get_accounts_receivable(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter contas a receber (incluindo pedidos ML)"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar empresa para verificar se ML orders está ativado
    from app.models.saas_models import Company, MLOrder, OrderStatus
    from datetime import timedelta
    
    company = db.query(Company).filter(Company.id == company_id).first()
    
    # Lista para armazenar todos os receivables
    all_receivables = []
    
    # 1. Buscar contas a receber normais
    normal_receivables = db.query(AccountReceivable).filter(
        AccountReceivable.company_id == company_id
    ).all()
    
    for rec in normal_receivables:
        all_receivables.append({
            "id": f"normal_{rec.id}",
            "type": "normal",
            "customer_name": rec.customer_name,
            "description": rec.description,
            "amount": float(rec.amount),
            "due_date": rec.due_date.isoformat() if rec.due_date else None,
            "status": rec.status,
            "installment_number": rec.installment_number,
            "total_installments": rec.total_installments,
            "invoice_number": rec.invoice_number,
            "notes": rec.notes,
            "created_at": rec.created_at,
            "updated_at": rec.updated_at
        })
    
    # 2. Se ML orders está ativado, buscar pedidos ML finalizados
    if company and company.ml_orders_as_receivables:
        logger.info(f"DEBUG: Buscando pedidos ML para company_id={company_id}, ml_orders_as_receivables={company.ml_orders_as_receivables}")
        ml_orders = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED]),
            MLOrder.date_closed.isnot(None)
        ).all()
        logger.info(f"DEBUG: Encontrados {len(ml_orders)} pedidos ML")
        
        for order in ml_orders:
            # Calcular data de recebimento baseada no método de pagamento
            payment_date = calculate_ml_payment_date(order)
            
            # Calcular valor líquido (total - taxas)
            net_amount = float(order.total_amount or 0) - float(order.total_fees or 0)
            
            # Criar descrição detalhada
            description = f"Mercado Livre - Pedido #{order.ml_order_id}"
            
            # Definir status baseado no status do pedido ML e shipping
            # Se shipping_status = "delivered" ou status = DELIVERED = received (entregue)
            # Mas se foi entregue há menos de 7 dias, continua como pending
            from datetime import datetime, timedelta
            
            is_delivered = (
                order.status == OrderStatus.DELIVERED or 
                (order.shipping_status and order.shipping_status.lower() == "delivered")
            )
            
            # Se foi entregue, verificar se já passou 7 dias
            if is_delivered:
                # Tentar extrair data de entrega do shipping_details
                delivery_date = None
                if order.shipping_details and isinstance(order.shipping_details, dict):
                    status_history = order.shipping_details.get('status_history', {})
                    if status_history and 'date_delivered' in status_history:
                        try:
                            delivery_date_str = status_history['date_delivered']
                            # Converter string para datetime
                            delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                        except:
                            pass
                
                # Se não conseguiu extrair a data ou foi entregue há menos de 7 dias, continua pending
                if delivery_date:
                    days_since_delivery = (datetime.now() - delivery_date.replace(tzinfo=None)).days
                    if days_since_delivery < 7:
                        is_delivered = False
            
            ml_status = "received" if is_delivered else "pending"
            
            # Debug log para o pedido específico
            if order.ml_order_id == 2000009656360792:
                logger.info(f"DEBUG Pedido {order.ml_order_id}: status={order.status}, shipping_status={order.shipping_status}, is_delivered={is_delivered}, ml_status={ml_status}")
            
            all_receivables.append({
                "id": f"ml_{order.ml_order_id}",
                "type": "ml_order",
                "customer_name": order.buyer_nickname or order.buyer_first_name or "Cliente ML",
                "description": description,
                "amount": net_amount,
                "due_date": payment_date.isoformat() if payment_date else None,
                "status": ml_status,
                "installment_number": None,
                "total_installments": None,
                "invoice_number": f"ML-{order.ml_order_id}",
                "notes": None,
                "created_at": order.date_created,
                "updated_at": order.last_updated,
                "ml_order_id": order.ml_order_id,
                "total_amount": float(order.total_amount or 0),
                "total_fees": float(order.total_fees or 0)
            })
    
    # Ordenar por data de vencimento (mais recente primeiro)
    all_receivables.sort(key=lambda x: x['due_date'] or '9999-12-31', reverse=True)
    
    return all_receivables

def calculate_ml_payment_date(order):
    """Calcula quando receberemos o pagamento do pedido ML"""
    from datetime import timedelta
    
    if not order.date_closed:
        return None
    
    base_date = order.date_closed
    
    # Verificar método de envio e pagamento
    shipping_method = (order.shipping_method or '').lower()
    payment_method = (order.payment_method_id or '').lower()
    
    if 'mercadoenvios' in shipping_method:
        # Mercado Envios: 7 dias
        return base_date + timedelta(days=7)
    elif 'mercadopago' in payment_method:
        # Mercado Pago: 1-2 dias
        return base_date + timedelta(days=2)
    else:
        # Vendas normais: 14 dias
        return base_date + timedelta(days=14)

@financial_router.post("/api/financial/receivables")
async def create_account_receivable(
    receivable_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar conta a receber"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Validar dados obrigatórios
    if not receivable_data.get("customer_name"):
        raise HTTPException(status_code=400, detail="Nome do cliente é obrigatório")
    if not receivable_data.get("description"):
        raise HTTPException(status_code=400, detail="Descrição é obrigatória")
    if not receivable_data.get("amount"):
        raise HTTPException(status_code=400, detail="Valor é obrigatório")
    if not receivable_data.get("due_date"):
        raise HTTPException(status_code=400, detail="Data de vencimento é obrigatória")
    
    # Criar nova conta a receber no banco
    new_receivable = AccountReceivable(
        company_id=company_id,
        customer_name=receivable_data.get("customer_name"),  # Campo de texto livre
        category_id=receivable_data.get("category_id"),
        cost_center_id=receivable_data.get("cost_center_id"),
        account_id=receivable_data.get("account_id"),
        invoice_number=receivable_data.get("invoice_number"),
        description=receivable_data.get("description"),
        amount=receivable_data.get("amount"),
        due_date=datetime.strptime(receivable_data.get("due_date"), "%Y-%m-%d").date(),
        status="pending",
        installment_number=receivable_data.get("installment_number"),
        total_installments=receivable_data.get("total_installments"),
        parent_receivable_id=receivable_data.get("parent_receivable_id"),
        is_recurring=receivable_data.get("is_recurring", False),
        recurring_frequency=receivable_data.get("recurring_frequency"),
        recurring_end_date=datetime.strptime(receivable_data.get("recurring_end_date"), "%Y-%m-%d").date() if receivable_data.get("recurring_end_date") else None,
        notes=receivable_data.get("notes")
    )
    
    db.add(new_receivable)
    db.commit()
    db.refresh(new_receivable)
    
    logger.info(f"✅ Conta a receber criada: {new_receivable.description} (ID: {new_receivable.id})")
    return {"message": "Conta a receber criada com sucesso", "id": new_receivable.id}

@financial_router.put("/api/financial/receivables/{receivable_id}")
async def update_account_receivable(
    receivable_id: int,
    receivable_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar conta a receber"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a receber existente
    receivable = db.query(AccountReceivable).filter(
        AccountReceivable.id == receivable_id,
        AccountReceivable.company_id == company_id
    ).first()
    
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    
    # Atualizar campos
    if receivable_data.get("customer_name") is not None:
        receivable.customer_name = receivable_data.get("customer_name")
    if receivable_data.get("category_id") is not None:
        receivable.category_id = receivable_data.get("category_id")
    if receivable_data.get("cost_center_id") is not None:
        receivable.cost_center_id = receivable_data.get("cost_center_id")
    if receivable_data.get("account_id") is not None:
        receivable.account_id = receivable_data.get("account_id")
    if receivable_data.get("invoice_number") is not None:
        receivable.invoice_number = receivable_data.get("invoice_number")
    if receivable_data.get("description"):
        receivable.description = receivable_data.get("description")
    if receivable_data.get("amount"):
        receivable.amount = receivable_data.get("amount")
    if receivable_data.get("due_date"):
        receivable.due_date = datetime.strptime(receivable_data.get("due_date"), "%Y-%m-%d").date()
    if receivable_data.get("is_recurring") is not None:
        receivable.is_recurring = receivable_data.get("is_recurring")
    if receivable_data.get("recurring_frequency"):
        receivable.recurring_frequency = receivable_data.get("recurring_frequency")
    if receivable_data.get("recurring_end_date"):
        receivable.recurring_end_date = datetime.strptime(receivable_data.get("recurring_end_date"), "%Y-%m-%d").date()
    if receivable_data.get("notes") is not None:
        receivable.notes = receivable_data.get("notes")
    
    db.commit()
    
    logger.info(f"✅ Conta a receber atualizada: {receivable.description} (ID: {receivable_id})")
    return {"message": "Conta a receber atualizada com sucesso"}

@financial_router.delete("/api/financial/receivables/{receivable_id}")
async def delete_account_receivable(
    receivable_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir conta a receber"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a receber existente
    receivable = db.query(AccountReceivable).filter(
        AccountReceivable.id == receivable_id,
        AccountReceivable.company_id == company_id
    ).first()
    
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    
    # Verificar se tem parcelas filhas
    has_installments = db.query(AccountReceivable).filter(
        AccountReceivable.parent_receivable_id == receivable_id
    ).count() > 0
    
    if has_installments:
        raise HTTPException(status_code=400, detail="Não é possível excluir uma conta a receber que possui parcelas")
    
    # Remover conta a receber
    db.delete(receivable)
    db.commit()
    
    logger.info(f"✅ Conta a receber excluída: {receivable.description} (ID: {receivable_id})")
    return {"message": "Conta a receber excluída com sucesso"}

# =====================================================
# ROTAS DE API PARA CONTAS A PAGAR
# =====================================================

@financial_router.get("/api/financial/payables")
async def get_accounts_payable(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter contas a pagar"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar contas a pagar no banco de dados
    payables = db.query(AccountPayable).filter(
        AccountPayable.company_id == company_id
    ).order_by(AccountPayable.due_date).all()
    
    # Buscar categorias para incluir nomes
    categories = db.query(FinancialCategory).filter(
        FinancialCategory.company_id == company_id
    ).all()
    category_dict = {cat.id: cat.name for cat in categories}
    
    # Buscar ordens de compra para incluir números
    ordens_compra = db.query(OrdemCompra).filter(
        OrdemCompra.company_id == company_id
    ).all()
    ordem_dict = {ordem.id: ordem.numero_ordem for ordem in ordens_compra}
    
    return [
                {
                    "id": pay.id,
                    "supplier_name": pay.supplier_name,  # Campo texto livre
                    "category_id": pay.category_id,
                    "category_name": category_dict.get(pay.category_id, "N/A"),
                    "cost_center_id": pay.cost_center_id,
                    "account_id": pay.account_id,
                    "invoice_number": pay.invoice_number,
                    "description": pay.description,
                    "amount": float(pay.amount),
                    "due_date": pay.due_date.isoformat() if pay.due_date else None,
                    "paid_date": pay.paid_date.isoformat() if pay.paid_date else None,
                    "paid_amount": float(pay.paid_amount) if pay.paid_amount else None,
                    "status": pay.status,
                    "installment_number": pay.installment_number,
                    "total_installments": pay.total_installments,
                    "parent_payable_id": pay.parent_payable_id,
                    "is_recurring": pay.is_recurring,
                    "recurring_frequency": pay.recurring_frequency,
                    "recurring_end_date": pay.recurring_end_date.isoformat() if pay.recurring_end_date else None,
                    "is_fixed": pay.is_fixed,
                    "notes": pay.notes,
                    "ordem_compra_id": pay.ordem_compra_id,
                    "ordem_compra_numero": ordem_dict.get(pay.ordem_compra_id, None),
                    "created_at": pay.created_at,
                    "updated_at": pay.updated_at
                }
                for pay in payables
            ]

@financial_router.post("/api/financial/payables")
async def create_account_payable(
    payable_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar conta a pagar"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Validar dados obrigatórios
    if not payable_data.get("description"):
        raise HTTPException(status_code=400, detail="Descrição é obrigatória")
    if not payable_data.get("amount"):
        raise HTTPException(status_code=400, detail="Valor é obrigatório")
    if not payable_data.get("due_date"):
        raise HTTPException(status_code=400, detail="Data de vencimento é obrigatória")
    
    # Validar se os IDs pertencem à empresa do usuário
    if payable_data.get("category_id"):
        category = db.query(FinancialCategory).filter(
            FinancialCategory.id == payable_data.get("category_id"),
            FinancialCategory.company_id == company_id
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Categoria não encontrada ou não pertence à sua empresa")
    
    if payable_data.get("cost_center_id"):
        cost_center = db.query(CostCenter).filter(
            CostCenter.id == payable_data.get("cost_center_id"),
            CostCenter.company_id == company_id
        ).first()
        if not cost_center:
            raise HTTPException(status_code=400, detail="Centro de custo não encontrado ou não pertence à sua empresa")
    
    if payable_data.get("account_id"):
        account = db.query(FinancialAccount).filter(
            FinancialAccount.id == payable_data.get("account_id"),
            FinancialAccount.company_id == company_id
        ).first()
        if not account:
            raise HTTPException(status_code=400, detail="Conta bancária não encontrada ou não pertence à sua empresa")
    
    if payable_data.get("fornecedor_id"):
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == payable_data.get("fornecedor_id"),
            Fornecedor.company_id == company_id
        ).first()
        if not fornecedor:
            raise HTTPException(status_code=400, detail="Fornecedor não encontrado ou não pertence à sua empresa")
    
    if payable_data.get("ordem_compra_id"):
        ordem_compra = db.query(OrdemCompra).filter(
            OrdemCompra.id == payable_data.get("ordem_compra_id"),
            OrdemCompra.company_id == company_id
        ).first()
        if not ordem_compra:
            raise HTTPException(status_code=400, detail="Ordem de compra não encontrada ou não pertence à sua empresa")
    
    # Verificar se é parcelamento
    total_installments = payable_data.get("total_installments") or 1
    if total_installments is None:
        total_installments = 1
    is_recurring = payable_data.get("is_recurring", False)
    recurring_frequency = payable_data.get("recurring_frequency")
    installment_due_date = payable_data.get("installment_due_date")
    
    # Se for despesa recorrente, criar múltiplas entradas baseadas na frequência
    if is_recurring and recurring_frequency:
        from dateutil.relativedelta import relativedelta
        
        # Calcular quantas entradas criar baseado na frequência e data de término
        start_date = datetime.strptime(payable_data.get("due_date"), "%Y-%m-%d").date()
        end_date = datetime.strptime(payable_data.get("recurring_end_date"), "%Y-%m-%d").date()
        
        # Calcular número de entradas baseado na frequência
        if recurring_frequency == "monthly":
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            total_entries = months_diff + 1
        elif recurring_frequency == "quarterly":
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            total_entries = (months_diff // 3) + 1
        elif recurring_frequency == "yearly":
            years_diff = end_date.year - start_date.year
            total_entries = years_diff + 1
        else:
            total_entries = 1
        
        # Limitar a um máximo razoável (ex: 60 entradas)
        total_entries = min(total_entries, 60)
        
        created_entries = []
        base_description = payable_data.get("description")
        base_invoice = payable_data.get("invoice_number")
        
        for i in range(total_entries):
            # Calcular data de vencimento baseada na frequência
            if recurring_frequency == "monthly":
                due_date = start_date + relativedelta(months=i)
            elif recurring_frequency == "quarterly":
                due_date = start_date + relativedelta(months=i*3)
            elif recurring_frequency == "yearly":
                due_date = start_date + relativedelta(years=i)
            else:
                due_date = start_date
            
            # Se a data calculada ultrapassar a data de término, parar
            if due_date > end_date:
                break
            
            # Criar entrada recorrente
            recurring_payable = AccountPayable(
                company_id=company_id,
                supplier_name=payable_data.get("supplier_name"),  # Campo texto livre
                fornecedor_id=payable_data.get("fornecedor_id"),  # FK para fornecedores
                ordem_compra_id=payable_data.get("ordem_compra_id"),  # FK para ordens de compra
                category_id=payable_data.get("category_id"),
                cost_center_id=payable_data.get("cost_center_id"),
                account_id=payable_data.get("account_id"),
                payment_method_id=payable_data.get("payment_method_id"),
                invoice_number=f"{base_invoice}-{i+1}" if base_invoice else None,
                description=f"{base_description} - Recorrência {i+1}" if i > 0 else base_description,
                amount=payable_data.get("amount"),
                due_date=due_date,
                status="pending",
                installment_number=i+1,
                total_installments=total_entries,
                is_recurring=True,
                recurring_frequency=recurring_frequency,
                recurring_end_date=end_date,
                is_fixed=payable_data.get("is_fixed", False),
                notes=payable_data.get("notes")
            )
            
            db.add(recurring_payable)
            created_entries.append(recurring_payable)
        
        db.commit()
        
        # Refresh para obter os IDs
        for entry in created_entries:
            db.refresh(entry)
        
        # Se for cartão de crédito, diminuir saldo para cada entrada recorrente criada
        # Buscar account novamente após commit para garantir dados atualizados
        account_id = payable_data.get("account_id")
        if account_id:
            account = db.query(FinancialAccount).filter(
                FinancialAccount.id == account_id,
                FinancialAccount.company_id == company_id
            ).first()
            
        if account:
            logger.info(f"🔍 DEBUG: Account encontrado - ID: {account.id}, Tipo: '{account.account_type}', Nome: {account.account_name}")
            logger.info(f"🔍 DEBUG: Comparando account_type: '{account.account_type}' == 'credit' ? {account.account_type == 'credit'}")
            if account.account_type == "credit":
            # Fazer refresh do account para garantir dados atualizados
            db.refresh(account)
            
            total_amount = 0
            for entry in created_entries:
                total_amount += float(entry.amount)
            
            current_balance = float(account.current_balance or 0)
            # Para cartão de crédito, crédito aumenta dívida (diminui saldo disponível)
            account.current_balance = current_balance - total_amount
            
            # Criar transação para registrar a movimentação
            transaction = FinancialTransaction(
                company_id=company_id,
                account_id=account.id,
                transaction_type="credit",  # Crédito aumenta dívida no cartão
                amount=total_amount,
                description=f"{base_description} - Recorrências ({len(created_entries)}x) (Criação)",
                transaction_date=datetime.now().date(),
                reference_type="payable_creation",
                reference_id=f"payable_recurring_{created_entries[0].id}"
            )
            db.add(transaction)
            db.commit()
            
            logger.info(f"💳 Saldo do cartão atualizado: -R$ {total_amount:.2f} ({len(created_entries)} recorrências)")
        
        logger.info(f"✅ {len(created_entries)} despesas recorrentes criadas: {base_description}")
        return {"message": f"{len(created_entries)} despesas recorrentes criadas com sucesso", "count": len(created_entries)}
    
    # Se for parcelamento, criar múltiplas entradas
    elif total_installments > 1:
        # Não criar conta principal - apenas as parcelas numeradas
        
        # Criar parcelas
        value_type = payable_data.get("value_type", "total")
        base_amount = float(payable_data.get("amount"))
        
        if value_type == "total":
            # Se for valor total, dividir igualmente entre as parcelas
            installment_amount = base_amount / total_installments
        else:
            # Se for valor da parcela, usar o valor para cada parcela
            installment_amount = base_amount
        
        # Usar data de vencimento da primeira parcela se fornecida, senão usar due_date
        if installment_due_date:
            base_due_date = datetime.strptime(installment_due_date, "%Y-%m-%d").date()
        else:
            base_due_date = datetime.strptime(payable_data.get("due_date"), "%Y-%m-%d").date()
        
        # Criar todas as parcelas
        created_installments = []
        for i in range(1, total_installments + 1):
            # Calcular data de vencimento da parcela (mensal)
            # Adicionar (i-1) meses à data base
            from dateutil.relativedelta import relativedelta
            due_date = base_due_date + relativedelta(months=i-1)
            
            installment = AccountPayable(
                company_id=company_id,
                supplier_name=payable_data.get("supplier_name"),  # Campo texto livre
                fornecedor_id=payable_data.get("fornecedor_id"),  # FK para fornecedores
                ordem_compra_id=payable_data.get("ordem_compra_id"),  # FK para ordens de compra
                category_id=payable_data.get("category_id"),
                cost_center_id=payable_data.get("cost_center_id"),
                account_id=payable_data.get("account_id"),
                payment_method_id=payable_data.get("payment_method_id"),
                invoice_number=f"{payable_data.get('invoice_number', '')}-{i}" if payable_data.get("invoice_number") else None,
                description=f"{payable_data.get('description')} - Parcela {i}/{total_installments}",
                amount=installment_amount,
                due_date=due_date,
                status="pending",
                installment_number=i,
                total_installments=total_installments,
                parent_payable_id=None,  # Será definido depois
                is_fixed=payable_data.get("is_fixed", False),
                notes=payable_data.get("notes")
            )
            
            db.add(installment)
            created_installments.append(installment)
        
        db.commit()
        
        # Definir parent_payable_id para todas as parcelas (apontando para a primeira)
        first_installment_id = created_installments[0].id
        for installment in created_installments:
            installment.parent_payable_id = first_installment_id
        
        db.commit()
        
        # Se for cartão de crédito, diminuir saldo imediatamente (valor total de uma vez)
        # Buscar account novamente após commit para garantir dados atualizados
        account_id = payable_data.get("account_id")
        logger.info(f"🔍 DEBUG: account_id recebido (parcelamento): {account_id}")
        if account_id:
            account = db.query(FinancialAccount).filter(
                FinancialAccount.id == account_id,
                FinancialAccount.company_id == company_id
            ).first()
            
        if account:
            logger.info(f"🔍 DEBUG: Account encontrado - ID: {account.id}, Tipo: '{account.account_type}', Nome: {account.account_name}")
            logger.info(f"🔍 DEBUG: Comparando account_type: '{account.account_type}' == 'credit' ? {account.account_type == 'credit'}")
            if account.account_type == "credit":
                logger.info(f"💳 Cartão de crédito detectado! Atualizando saldo...")
                # Fazer refresh do account para garantir dados atualizados
                db.refresh(account)
                
                total_amount = base_amount if value_type == "total" else (base_amount * total_installments)
                current_balance = float(account.current_balance or 0)
                logger.info(f"💳 Saldo atual: R$ {current_balance:.2f}, Valor a deduzir: R$ {total_amount:.2f}")
                
                # Para cartão de crédito, crédito aumenta dívida (diminui saldo disponível)
                account.current_balance = current_balance - total_amount
                
                # Criar transação para registrar a movimentação
                transaction = FinancialTransaction(
                    company_id=company_id,
                    account_id=account.id,
                    transaction_type="credit",  # Crédito aumenta dívida no cartão
                    amount=total_amount,
                    description=f"{payable_data.get('description')} - Parcelamento {total_installments}x (Criação)",
                    transaction_date=datetime.now().date(),
                    reference_type="payable_creation",
                    reference_id=f"payable_installment_{first_installment_id}"
                )
                db.add(transaction)
                db.commit()
                
                logger.info(f"💳 Saldo do cartão atualizado: -R$ {total_amount:.2f} (Novo saldo: R$ {account.current_balance:.2f}) (Parcelamento {total_installments}x)")
            else:
                logger.info(f"⚠️ Conta não é cartão de crédito. Tipo: {account.account_type}")
        else:
            logger.warning(f"⚠️ Account não encontrado para account_id: {payable_data.get('account_id')}")
        
        logger.info(f"✅ Parcelamento criado: {payable_data.get('description')} - {total_installments} parcelas")
        return {"message": f"Parcelamento criado com sucesso - {total_installments} parcelas", "id": first_installment_id}
    
    # Despesa única
    else:
        new_payable = AccountPayable(
            company_id=company_id,
            supplier_name=payable_data.get("supplier_name"),  # Campo texto livre
            fornecedor_id=payable_data.get("fornecedor_id"),  # FK para fornecedores
            ordem_compra_id=payable_data.get("ordem_compra_id"),  # FK para ordens de compra
            category_id=payable_data.get("category_id"),
            cost_center_id=payable_data.get("cost_center_id"),
            account_id=payable_data.get("account_id"),
            payment_method_id=payable_data.get("payment_method_id"),
            invoice_number=payable_data.get("invoice_number"),
            description=payable_data.get("description"),
            amount=payable_data.get("amount"),
            due_date=datetime.strptime(payable_data.get("due_date"), "%Y-%m-%d").date(),
            status="pending",
            installment_number=1,
            total_installments=1,
            is_fixed=payable_data.get("is_fixed", False),
            notes=payable_data.get("notes")
        )
        
        db.add(new_payable)
        db.commit()
        db.refresh(new_payable)
        
        # Se for cartão de crédito, diminuir saldo imediatamente
        # Buscar account novamente após commit para garantir dados atualizados
        account_id = payable_data.get("account_id")
        logger.info(f"🔍 DEBUG: account_id recebido: {account_id}")
        if account_id:
            account = db.query(FinancialAccount).filter(
                FinancialAccount.id == account_id,
                FinancialAccount.company_id == company_id
            ).first()
            
        if account:
            logger.info(f"🔍 DEBUG: Account encontrado - ID: {account.id}, Tipo: '{account.account_type}', Nome: {account.account_name}")
            logger.info(f"🔍 DEBUG: Comparando account_type: '{account.account_type}' == 'credit' ? {account.account_type == 'credit'}")
            if account.account_type == "credit":
                logger.info(f"💳 Cartão de crédito detectado! Atualizando saldo...")
                # Fazer refresh do account para garantir dados atualizados
                db.refresh(account)
                
                amount_value = float(new_payable.amount)
                current_balance = float(account.current_balance or 0)
                logger.info(f"💳 Saldo atual: R$ {current_balance:.2f}, Valor a deduzir: R$ {amount_value:.2f}")
                
                # Para cartão de crédito, crédito aumenta dívida (diminui saldo disponível)
                account.current_balance = current_balance - amount_value
                
                # Criar transação para registrar a movimentação
                transaction = FinancialTransaction(
                    company_id=company_id,
                    account_id=account.id,
                    transaction_type="credit",  # Crédito aumenta dívida no cartão
                    amount=amount_value,
                    description=f"{new_payable.description} (Criação)",
                    transaction_date=datetime.now().date(),
                    reference_type="payable_creation",
                    reference_id=f"payable_{new_payable.id}"
                )
                db.add(transaction)
                db.commit()
                
                logger.info(f"💳 Saldo do cartão atualizado: -R$ {amount_value:.2f} (Novo saldo: R$ {account.current_balance:.2f})")
            else:
                logger.info(f"⚠️ Conta não é cartão de crédito. Tipo: {account.account_type}")
        else:
            logger.warning(f"⚠️ Account não encontrado para account_id: {payable_data.get('account_id')}")
        
        logger.info(f"✅ Conta a pagar criada: {new_payable.description} (ID: {new_payable.id})")
        return {"message": "Conta a pagar criada com sucesso", "id": new_payable.id}

@financial_router.put("/api/financial/payables/{payable_id}")
async def update_account_payable(
    payable_id: int,
    payable_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar conta a pagar"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a pagar existente
    payable = db.query(AccountPayable).filter(
        AccountPayable.id == payable_id,
        AccountPayable.company_id == company_id
    ).first()
    
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    
    # Validar se os IDs pertencem à empresa do usuário
    if payable_data.get("category_id"):
        category = db.query(FinancialCategory).filter(
            FinancialCategory.id == payable_data.get("category_id"),
            FinancialCategory.company_id == company_id
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Categoria não encontrada ou não pertence à sua empresa")
    
    if payable_data.get("cost_center_id"):
        cost_center = db.query(CostCenter).filter(
            CostCenter.id == payable_data.get("cost_center_id"),
            CostCenter.company_id == company_id
        ).first()
        if not cost_center:
            raise HTTPException(status_code=400, detail="Centro de custo não encontrado ou não pertence à sua empresa")
    
    if payable_data.get("account_id"):
        account = db.query(FinancialAccount).filter(
            FinancialAccount.id == payable_data.get("account_id"),
            FinancialAccount.company_id == company_id
        ).first()
        if not account:
            raise HTTPException(status_code=400, detail="Conta bancária não encontrada ou não pertence à sua empresa")
    
    if payable_data.get("fornecedor_id"):
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == payable_data.get("fornecedor_id"),
            Fornecedor.company_id == company_id
        ).first()
        if not fornecedor:
            raise HTTPException(status_code=400, detail="Fornecedor não encontrado ou não pertence à sua empresa")
    
    if payable_data.get("ordem_compra_id"):
        ordem_compra = db.query(OrdemCompra).filter(
            OrdemCompra.id == payable_data.get("ordem_compra_id"),
            OrdemCompra.company_id == company_id
        ).first()
        if not ordem_compra:
            raise HTTPException(status_code=400, detail="Ordem de compra não encontrada ou não pertence à sua empresa")
    
    # Atualizar campos
    if payable_data.get("supplier_name") is not None:
        payable.supplier_name = payable_data.get("supplier_name")
    if payable_data.get("fornecedor_id") is not None:
        payable.fornecedor_id = payable_data.get("fornecedor_id")
    if payable_data.get("ordem_compra_id") is not None:
        payable.ordem_compra_id = payable_data.get("ordem_compra_id")
    if payable_data.get("category_id") is not None:
        payable.category_id = payable_data.get("category_id")
    if payable_data.get("cost_center_id") is not None:
        payable.cost_center_id = payable_data.get("cost_center_id")
    if payable_data.get("account_id") is not None:
        payable.account_id = payable_data.get("account_id")
    if payable_data.get("invoice_number") is not None:
        payable.invoice_number = payable_data.get("invoice_number")
    if payable_data.get("description"):
        payable.description = payable_data.get("description")
    if payable_data.get("amount"):
        payable.amount = payable_data.get("amount")
    if payable_data.get("due_date"):
        payable.due_date = datetime.strptime(payable_data.get("due_date"), "%Y-%m-%d").date()
    if payable_data.get("status"):
        payable.status = payable_data.get("status")
    if payable_data.get("installment_number") is not None:
        payable.installment_number = payable_data.get("installment_number")
    if payable_data.get("total_installments") is not None:
        payable.total_installments = payable_data.get("total_installments")
    if payable_data.get("parent_payable_id") is not None:
        payable.parent_payable_id = payable_data.get("parent_payable_id")
    if payable_data.get("is_recurring") is not None:
        payable.is_recurring = payable_data.get("is_recurring")
    if payable_data.get("is_fixed") is not None:
        payable.is_fixed = payable_data.get("is_fixed")
    if payable_data.get("recurring_frequency") is not None:
        payable.recurring_frequency = payable_data.get("recurring_frequency")
    if payable_data.get("recurring_end_date"):
        payable.recurring_end_date = datetime.strptime(payable_data.get("recurring_end_date"), "%Y-%m-%d").date()
    if payable_data.get("notes") is not None:
        payable.notes = payable_data.get("notes")
    
    db.commit()
    
    logger.info(f"✅ Conta a pagar atualizada: {payable.description} (ID: {payable_id})")
    return {"message": "Conta a pagar atualizada com sucesso"}

@financial_router.delete("/api/financial/payables/{payable_id}")
async def delete_account_payable(
    payable_id: int,
    delete_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir conta a pagar"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a pagar existente
    payable = db.query(AccountPayable).filter(
        AccountPayable.id == payable_id,
        AccountPayable.company_id == company_id
    ).first()
    
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    
    remove_future_entries = delete_data.get("remove_future_entries", False)
    deleted_count = 1
    
    # Se deve remover lançamentos futuros
    if remove_future_entries:
        if payable.total_installments > 1:
            # É uma conta parcelada - remover todas as parcelas
            # Se a conta atual tem parent_payable_id, usar ele, senão ela é a principal
            if payable.parent_payable_id:
                # Esta é uma parcela, buscar pela parcela principal
                parent_id = payable.parent_payable_id
                all_installments = db.query(AccountPayable).filter(
                    or_(
                        AccountPayable.id == parent_id,
                        AccountPayable.parent_payable_id == parent_id
                    ),
                    AccountPayable.company_id == company_id
                ).all()
            else:
                # Esta é a parcela principal, buscar todas as parcelas desta série
                all_installments = db.query(AccountPayable).filter(
                    or_(
                        AccountPayable.id == payable_id,
                        AccountPayable.parent_payable_id == payable_id
                    ),
                    AccountPayable.company_id == company_id
                ).all()
            
            deleted_count = len(all_installments)
            logger.info(f"🔍 DEBUG: Encontradas {deleted_count} parcelas para exclusão")
            for installment in all_installments:
                logger.info(f"🔍 DEBUG: Excluindo parcela {installment.installment_number}/{installment.total_installments} - {installment.description}")
                db.delete(installment)
                
        elif payable.is_recurring:
            # É uma despesa recorrente - remover todas as recorrências futuras
            # Buscar todas as recorrências relacionadas pela descrição base e frequência
            base_description = payable.description
            # Remover sufixo "- Recorrência X" se existir para obter a descrição base
            if " - Recorrência " in base_description:
                base_description = base_description.split(" - Recorrência ")[0]
            
            # Buscar todas as recorrências relacionadas
            related_recurring = db.query(AccountPayable).filter(
                AccountPayable.company_id == company_id,
                AccountPayable.is_recurring == True,
                AccountPayable.recurring_frequency == payable.recurring_frequency,
                or_(
                    AccountPayable.description == base_description,
                    AccountPayable.description.like(f"{base_description} - Recorrência %")
                )
            ).all()
            
            deleted_count = len(related_recurring)
            for recurring in related_recurring:
                db.delete(recurring)
    
    # Remover a conta atual apenas se não foi removida na lógica acima
    if not remove_future_entries:
        db.delete(payable)
    
    db.commit()
    
    if remove_future_entries and deleted_count > 1:
        logger.info(f"✅ Conta a pagar e {deleted_count - 1} lançamentos futuros excluídos: {payable.description} (ID: {payable_id})")
        return {"message": f"Conta e {deleted_count - 1} lançamentos futuros excluídos com sucesso", "deleted_count": deleted_count}
    else:
        logger.info(f"✅ Conta a pagar excluída: {payable.description} (ID: {payable_id})")
        return {"message": "Conta a pagar excluída com sucesso", "deleted_count": deleted_count}

@financial_router.put("/api/financial/payables/{payable_id}/mark-paid")
async def mark_payable_as_paid(
    payable_id: int,
    payment_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para marcar conta a pagar como paga"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a pagar existente
    payable = db.query(AccountPayable).filter(
        AccountPayable.id == payable_id,
        AccountPayable.company_id == company_id
    ).first()
    
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    
    if payable.status == "paid":
        raise HTTPException(status_code=400, detail="Conta já está marcada como paga")
    
    # Marcar como paga
    payable.status = "paid"
    payable.paid_date = datetime.strptime(payment_data.get("paid_date"), "%Y-%m-%d").date()
    
    # Se não foi informado valor pago, usar o valor original
    if payment_data.get("paid_amount"):
        payable.paid_amount = float(payment_data.get("paid_amount"))
    else:
        payable.paid_amount = float(payable.amount)
    
    db.commit()
    
    logger.info(f"✅ Conta a pagar marcada como paga: {payable.description} (ID: {payable_id})")
    return {"message": "Conta marcada como paga com sucesso"}

@financial_router.put("/api/financial/payables/{payable_id}/mark-pending")
async def mark_payable_as_pending(
    payable_id: int,
    payment_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para marcar conta a pagar como pendente"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a pagar existente
    payable = db.query(AccountPayable).filter(
        AccountPayable.id == payable_id,
        AccountPayable.company_id == company_id
    ).first()
    
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    
    if payable.status == "pending":
        raise HTTPException(status_code=400, detail="Conta já está marcada como pendente")
    
    # Marcar como pendente
    payable.status = "pending"
    payable.paid_date = None
    payable.paid_amount = None
    
    db.commit()
    
    logger.info(f"✅ Conta a pagar marcada como pendente: {payable.description} (ID: {payable_id})")
    return {"message": "Conta marcada como pendente com sucesso"}

@financial_router.put("/api/financial/payables/{payable_id}/status")
async def update_payable_status(
    payable_id: int,
    status_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar status de conta a pagar"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a pagar existente
    payable = db.query(AccountPayable).filter(
        AccountPayable.id == payable_id,
        AccountPayable.company_id == company_id
    ).first()
    
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar não encontrada")
    
    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status é obrigatório")
    
    if new_status not in ["pending", "paid", "overdue", "cancelled"]:
        raise HTTPException(status_code=400, detail="Status inválido")
    
    # Atualizar status
    payable.status = new_status

    # Valor base da operação
    amount_value = float(payable.paid_amount or payable.amount or 0)

    # Conta vinculada: prioriza vinda do payload, senão da própria conta a pagar (se existir)
    account_id = status_data.get("account_id") or getattr(payable, "account_id", None)

    # Se marcando como pago, definir data/valor e lançar saída na conta
    if new_status == "paid":
        payable.paid_date = datetime.now().date()
        if status_data.get("paid_amount") is not None:
            payable.paid_amount = float(status_data.get("paid_amount"))
            amount_value = float(payable.paid_amount)

        # Lançar transação na conta vinculada (se houver)
        if account_id:
            account = db.query(FinancialAccount).filter(
                FinancialAccount.id == account_id,
                FinancialAccount.company_id == company_id
            ).first()
            if account:
                # Para cartões de crédito, o pagamento aumenta o saldo (reduz a dívida)
                # Para outros tipos de conta, o pagamento diminui o saldo (saída de dinheiro)
                is_credit_card = account.account_type == "credit"
                
                if is_credit_card:
                    # Cartão de crédito: pagamento aumenta saldo (reduz dívida)
                    account.current_balance = float(account.current_balance or 0) + amount_value
                    transaction_type = "credit"
                    description_prefix = "Pagamento de fatura"
                else:
                    # Conta corrente/poupança: pagamento diminui saldo (saída de dinheiro)
                    account.current_balance = float(account.current_balance or 0) - amount_value
                    transaction_type = "debit"
                    description_prefix = "Pagamento de conta"
                
                # Cria transação
                tx = FinancialTransaction(
                    company_id=company_id,
                    account_id=account.id,
                    transaction_type=transaction_type,
                    amount=amount_value,
                    description=f"{description_prefix} - {payable.description}",
                    transaction_date=datetime.now().date(),
                    reference_type="payable",
                    reference_id=str(payable.id),
                    supplier_id=getattr(payable, "supplier_id", None),
                    category_id=getattr(payable, "category_id", None),
                    cost_center_id=getattr(payable, "cost_center_id", None)
                )
                db.add(tx)

    else:
        # Reversão: se voltando para pendente, limpar dados e estornar eventual transação associada
        if new_status == "pending":
            # Limpar dados de pagamento
            payable.paid_date = None
            payable.paid_amount = None

            # Estornar transação de referência, se existir
            existing_tx = db.query(FinancialTransaction).filter(
                FinancialTransaction.company_id == company_id,
                FinancialTransaction.reference_type == "payable",
                FinancialTransaction.reference_id == str(payable.id)
            ).first()
            if existing_tx and existing_tx.account_id:
                account = db.query(FinancialAccount).filter(
                    FinancialAccount.id == existing_tx.account_id,
                    FinancialAccount.company_id == company_id
                ).first()
                if account:
                    # Para cartões de crédito, estorno diminui saldo (volta a dívida)
                    # Para outros tipos de conta, estorno aumenta saldo (volta o dinheiro)
                    is_credit_card = account.account_type == "credit"
                    
                    if is_credit_card:
                        # Cartão de crédito: estorno diminui saldo (volta a dívida)
                        account.current_balance = float(account.current_balance or 0) - float(existing_tx.amount or 0)
                    else:
                        # Conta corrente/poupança: estorno aumenta saldo (volta o dinheiro)
                        account.current_balance = float(account.current_balance or 0) + float(existing_tx.amount or 0)
                # Remove transação
                db.delete(existing_tx)
        else:
            # Outros status: apenas limpar datas/valores se não for pago
            payable.paid_date = None
            payable.paid_amount = None

    db.commit()

    logger.info(f"✅ Status da conta a pagar atualizado: {payable.description} -> {new_status} (ID: {payable_id})")
    return {"message": f"Status atualizado para {new_status} com sucesso"}

@financial_router.put("/api/financial/receivables/{receivable_id}/mark-received")
async def mark_receivable_as_received(
    receivable_id: int,
    payment_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para marcar conta a receber como recebida"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a receber existente
    receivable = db.query(AccountReceivable).filter(
        AccountReceivable.id == receivable_id,
        AccountReceivable.company_id == company_id
    ).first()
    
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    
    if receivable.status == "paid":
        raise HTTPException(status_code=400, detail="Conta já está marcada como recebida")
    
    # Marcar como recebida (usar 'paid' no banco, mas mostrar 'received' na interface)
    receivable.status = "paid"
    receivable.paid_date = datetime.strptime(payment_data.get("received_date"), "%Y-%m-%d").date()
    
    # Se não foi informado valor recebido, usar o valor original
    if payment_data.get("received_amount"):
        receivable.paid_amount = float(payment_data.get("received_amount"))
    else:
        receivable.paid_amount = float(receivable.amount)
    
    db.commit()
    
    logger.info(f"✅ Conta a receber marcada como recebida: {receivable.description} (ID: {receivable_id})")
    return {"message": "Conta a receber marcada como recebida com sucesso"}

@financial_router.put("/api/financial/receivables/{receivable_id}/mark-pending")
async def mark_receivable_as_pending(
    receivable_id: int,
    payment_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para marcar conta a receber como pendente"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar conta a receber existente
    receivable = db.query(AccountReceivable).filter(
        AccountReceivable.id == receivable_id,
        AccountReceivable.company_id == company_id
    ).first()
    
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada")
    
    if receivable.status == "pending":
        raise HTTPException(status_code=400, detail="Conta já está marcada como pendente")
    
    # Marcar como pendente
    receivable.status = "pending"
    receivable.paid_date = None
    receivable.paid_amount = None
    
    db.commit()
    
    logger.info(f"✅ Conta a receber marcada como pendente: {receivable.description} (ID: {receivable_id})")
    return {"message": "Conta marcada como pendente com sucesso"}

# =====================================================
# ROTAS DE API PARA CLIENTES
# =====================================================

@financial_router.get("/api/financial/customers")
async def get_financial_customers(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter clientes financeiros"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar clientes no banco de dados
    customers = db.query(FinancialCustomer).filter(
        FinancialCustomer.company_id == company_id,
        FinancialCustomer.is_active == True
    ).order_by(FinancialCustomer.name).all()
    
    return [
        {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "document": customer.document,
            "address": customer.address,
            "city": customer.city,
            "state": customer.state,
            "zip_code": customer.zip_code,
            "is_active": customer.is_active,
            "notes": customer.notes,
            "created_at": customer.created_at
        }
        for customer in customers
    ]

@financial_router.get("/api/financial/cashflow")
async def get_cashflow_data(
    period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter dados do fluxo de caixa"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar empresa para verificar se ML orders está ativado
    from app.models.saas_models import Company, MLOrder, OrderStatus
    from datetime import timedelta, datetime
    
    company = db.query(Company).filter(Company.id == company_id).first()
    
    # Lista para armazenar todos os itens do fluxo de caixa
    cashflow_items = []
    period_start = None
    period_end = None

    # Calcular período, se informado
    try:
        from datetime import datetime, timedelta
        today = datetime.now()
        if period:
            if period == "today":
                period_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "this_week":
                days_since_monday = today.weekday()
                period_start = (today - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = (period_start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "this_month":
                period_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                period_end = period_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "last_month":
                period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                period_end = today.replace(day=1) - timedelta(days=1)
                period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_end.replace(hour=23, minute=59, second=0, microsecond=0)
            elif period == "next_month":
                next_month = today.replace(day=1) + timedelta(days=32)
                period_start = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                period_end = period_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "next_30_days":
                period_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = (today + timedelta(days=30)).replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "next_60_days":
                period_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = (today + timedelta(days=60)).replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "next_90_days":
                period_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = (today + timedelta(days=90)).replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "this_year":
                period_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        if date_from and date_to:
            # Sobrescreve se período personalizado foi informado
            period_start = datetime.fromisoformat(date_from)
            period_end = datetime.fromisoformat(date_to)
    except Exception:
        # Em caso de erro de parsing, ignora filtro de período
        period_start = None
        period_end = None
    
    # 1. Buscar contas a receber (todas, incluindo pagas)
    receivables = db.query(AccountReceivable).filter(
        AccountReceivable.company_id == company_id
    ).all()
    
    for rec in receivables:
        # Se já foi pago/recebido, usar a data de pagamento, senão data de vencimento
        transaction_date = rec.paid_date.isoformat() if rec.paid_date else (rec.due_date.isoformat() if rec.due_date else None)
        
        cashflow_items.append({
            "id": f"rec_{rec.id}",
            "date": transaction_date,
            "description": f"Conta a Receber - {rec.customer_name}",
            "type": "receivable",
            "flow_type": "inflow",
            "amount": float(rec.paid_amount) if rec.paid_amount else float(rec.amount),
            "status": rec.status,
            "customer_name": rec.customer_name,
            "invoice_number": rec.invoice_number,
            "is_paid": rec.status in ['paid', 'received']
        })
    
    # 2. Buscar contas a pagar (todas, incluindo pagas)
    payables = db.query(AccountPayable).filter(
        AccountPayable.company_id == company_id
    ).all()
    
    for pay in payables:
        # Se já foi pago, usar a data de pagamento, senão data de vencimento
        transaction_date = pay.paid_date.isoformat() if pay.paid_date else (pay.due_date.isoformat() if pay.due_date else None)
        
        cashflow_items.append({
            "id": f"pay_{pay.id}",
            "date": transaction_date,
            "description": f"Conta a Pagar - {pay.supplier_name}",
            "type": "payable",
            "flow_type": "outflow",
            "amount": float(pay.paid_amount) if pay.paid_amount else float(pay.amount),
            "status": pay.status,
            "supplier_name": pay.supplier_name,
            "invoice_number": pay.invoice_number,
            "is_paid": pay.status in ['paid']
        })
    
    # 3. Se ML orders está ativado, buscar pedidos ML (todos, incluindo recebidos)
    if company and company.ml_orders_as_receivables:
        ml_orders = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED]),
            MLOrder.date_closed.isnot(None)
        ).all()
        
        for order in ml_orders:
            # Calcular data de recebimento baseada no método de pagamento
            payment_date = calculate_ml_payment_date(order)
            
            # Calcular valor líquido (total - taxas)
            net_amount = float(order.total_amount or 0) - float(order.total_fees or 0)
            
            # Definir status baseado no status do pedido ML e shipping
            is_delivered = (
                order.status == OrderStatus.DELIVERED or 
                (order.shipping_status and order.shipping_status.lower() == "delivered")
            )
            
            # Se foi entregue, verificar se já passou 7 dias
            if is_delivered:
                delivery_date = None
                if order.shipping_details and isinstance(order.shipping_details, dict):
                    status_history = order.shipping_details.get('status_history', {})
                    if status_history and 'date_delivered' in status_history:
                        try:
                            delivery_date_str = status_history['date_delivered']
                            delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                        except:
                            pass
                
                if delivery_date:
                    days_since_delivery = (datetime.now() - delivery_date.replace(tzinfo=None)).days
                    if days_since_delivery < 7:
                        is_delivered = False
            
            ml_status = "received" if is_delivered else "pending"
            
            # Se foi recebido, usar data de entrega + 7 dias, senão data de pagamento prevista
            if is_delivered and delivery_date:
                actual_payment_date = delivery_date + timedelta(days=7)
                transaction_date = actual_payment_date.isoformat()
            else:
                transaction_date = payment_date.isoformat() if payment_date else None
            
            cashflow_items.append({
                "id": f"ml_{order.ml_order_id}",
                "date": transaction_date,
                "description": f"Mercado Livre - Pedido #{order.ml_order_id}",
                "type": "ml_order",
                "flow_type": "inflow",
                "amount": net_amount,
                "status": ml_status,
                "ml_order_id": order.ml_order_id,
                "buyer_name": order.buyer_nickname or order.buyer_first_name or "Cliente ML",
                "is_paid": ml_status == "received"
            })
    
    # Aplicar filtro por período (servidor) se definido
    if period_start or period_end:
        def in_range(item_date_str: Optional[str]) -> bool:
            if not item_date_str:
                return False
            try:
                d = datetime.fromisoformat(item_date_str.replace('Z', '+00:00'))
                # Normalizar para naive (sem timezone) para comparação consistente
                if d.tzinfo is not None:
                    d = d.astimezone(tz=None).replace(tzinfo=None)
            except Exception:
                return False
            # Garantir que limites também sejam naive
            ps = period_start.replace(tzinfo=None) if period_start else None
            pe = period_end.replace(tzinfo=None) if period_end else None
            if ps and d < ps:
                return False
            if pe and d > pe:
                return False
            return True
        cashflow_items = [it for it in cashflow_items if in_range(it.get('date'))]

    # Ordenar por data
    cashflow_items.sort(key=lambda x: x['date'] or '9999-12-31')
    
    # Calcular saldo atual real das contas bancárias
    bank_accounts = db.query(FinancialAccount).filter(
        FinancialAccount.company_id == company_id,
        FinancialAccount.is_active == True
    ).all()
    
    total_current_balance = sum(float(acc.current_balance) for acc in bank_accounts)
    
    return {
        "cashflow_items": cashflow_items,
        "total_current_balance": total_current_balance
    }

@financial_router.get("/api/financial/dashboard")
async def get_dashboard_data(
    period: str = "this_month",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter dados do dashboard financeiro com KPIs otimizados"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    from datetime import datetime, timedelta
    from sqlalchemy import extract, func, and_, or_
    
    # Calcular período baseado no filtro
    today = datetime.now()
    
    if period == "today":
        month_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_week":
        days_since_monday = today.weekday()
        month_start = (today - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_month":
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period == "last_month":
        month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        month_end = today.replace(day=1) - timedelta(days=1)
    elif period == "custom" and date_from and date_to:
        month_start = datetime.fromisoformat(date_from)
        month_end = datetime.fromisoformat(date_to)
    else:
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # CONSULTA ÚNICA: Receitas (normais + Mercado Livre) com regra dos 7 dias
    from app.models.financial_models import AccountReceivable, AccountPayable, FinancialAccount
    from app.models.saas_models import Company, MLOrder, OrderStatus
    from sqlalchemy import text
    
    # 1. Receitas normais pagas no período
    receivables_paid = db.query(func.sum(AccountReceivable.paid_amount)).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status.in_(['paid', 'received']),
        AccountReceivable.paid_date >= month_start,
        AccountReceivable.paid_date <= month_end
    ).scalar() or 0
    
    # 2. Receitas normais pendentes no período
    receivables_pending = db.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status == 'pending',
        AccountReceivable.due_date >= month_start,
        AccountReceivable.due_date <= month_end
    ).scalar() or 0
    
    # 3. Pedidos ML com regra dos 7 dias
    ml_received_revenue = 0
    ml_pending_revenue = 0
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if company and company.ml_orders_as_receivables:
        # Buscar pedidos ML do período (usando data de criação)
        ml_orders = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED]),
            MLOrder.date_created >= month_start,
            MLOrder.date_created <= month_end
        ).all()
        
        for order in ml_orders:
            # Usar receita BRUTA (sem desconto das taxas)
            gross_amount = float(order.total_amount or 0)
            
            # Aplicar regra dos 7 dias
            is_delivered = (
                order.status == OrderStatus.DELIVERED or 
                (order.shipping_status and order.shipping_status.lower() == "delivered")
            )
            
            if is_delivered:
                delivery_date = None
                if order.shipping_details and isinstance(order.shipping_details, dict):
                    status_history = order.shipping_details.get('status_history', {})
                    if status_history and 'date_delivered' in status_history:
                        try:
                            delivery_date_str = status_history['date_delivered']
                            delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                        except:
                            pass
                
                if delivery_date:
                    days_since_delivery = (datetime.now() - delivery_date.replace(tzinfo=None)).days
                    if days_since_delivery >= 7:
                        ml_received_revenue += gross_amount
                    else:
                        ml_pending_revenue += gross_amount
                else:
                    ml_pending_revenue += gross_amount
            else:
                ml_pending_revenue += gross_amount
    
    # 4. Totais combinados (normais + ML) - convertendo para float
    total_received_revenue = float(receivables_paid) + float(ml_received_revenue)
    total_pending_revenue = float(receivables_pending) + float(ml_pending_revenue)
    
    # Despesas pagas no período - incluindo diferentes status
    try:
        payables_paid = db.query(func.sum(AccountPayable.amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status.in_(['paid', 'received', 'completed'])
        ).scalar() or 0
    except Exception as e:
        print(f"Erro ao consultar despesas pagas: {e}")
        payables_paid = 0
    
    # Despesas pendentes no período - incluindo diferentes status
    try:
        payables_pending = db.query(func.sum(AccountPayable.amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status.in_(['pending', 'overdue', 'unpaid']),
            AccountPayable.due_date >= month_start,
            AccountPayable.due_date <= month_end
        ).scalar() or 0
    except Exception as e:
        print(f"Erro ao consultar despesas pendentes: {e}")
        payables_pending = 0
    
    # Debug: Log dos valores
    print(f"DEBUG - Despesas pagas: {payables_paid}")
    print(f"DEBUG - Despesas pendentes: {payables_pending}")
    print(f"DEBUG - Company ID: {company_id}")
    print(f"DEBUG - Período: {month_start} a {month_end}")
    
    # Debug: Verificar todos os status das despesas
    all_status = db.query(AccountPayable.status, func.count(AccountPayable.id)).filter(
        AccountPayable.company_id == company_id
    ).group_by(AccountPayable.status).all()
    print(f"DEBUG - Status das despesas: {all_status}")
    
    # Debug: Verificar despesas com paid_date no período
    paid_in_period = db.query(func.count(AccountPayable.id), func.sum(AccountPayable.paid_amount)).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.paid_date >= month_start,
        AccountPayable.paid_date <= month_end
    ).first()
    print(f"DEBUG - Despesas com paid_date no período: {paid_in_period}")
    
    # Debug: Verificar despesas pagas - detalhes
    paid_details = db.query(AccountPayable.id, AccountPayable.amount, AccountPayable.paid_amount, AccountPayable.status).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status.in_(['paid', 'received', 'completed'])
    ).all()
    print(f"DEBUG - Detalhes das despesas pagas: {paid_details}")
    
    # Debug: Verificar se paid_amount está NULL
    paid_amount_check = db.query(func.count(AccountPayable.id), func.sum(AccountPayable.amount)).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status.in_(['paid', 'received', 'completed'])
    ).first()
    print(f"DEBUG - Despesas pagas (usando amount): {paid_amount_check}")
    
    # Saldo das contas bancárias
    current_balance = db.query(func.sum(FinancialAccount.current_balance)).filter(
        FinancialAccount.company_id == company_id,
        FinancialAccount.is_active == True
    ).scalar() or 0
    
    # Calcular totais finais (incluindo ML) - convertendo tudo para float
    monthly_revenue = float(total_received_revenue) + float(total_pending_revenue)
    monthly_expenses = float(payables_paid) + float(payables_pending)
    monthly_profit = float(monthly_revenue) - float(monthly_expenses)
    cash_projection = float(current_balance) + float(total_pending_revenue) - float(payables_pending)
    cash_flow = float(total_received_revenue) - float(payables_paid)
    
    # Definir variáveis para o retorno (convertendo para float)
    received_revenue = float(total_received_revenue)
    pending_revenue = float(total_pending_revenue)
    paid_expenses = float(payables_paid)
    pending_expenses = float(payables_pending)
    
    # Seção removida: Código duplicado dos pedidos ML
    # Código duplicado removido
    
    # Seção removida: Dados históricos (últimos 6 meses)
    
    # Seções removidas: Top categorias, Contas a receber recentes, Contas a pagar recentes
    
    return {
        "monthly_revenue": float(monthly_revenue),
        "monthly_expenses": float(monthly_expenses),
        "monthly_profit": float(monthly_profit),
        "current_balance": float(cash_projection),
        "received_revenue": float(received_revenue),
        "pending_revenue": float(pending_revenue),
        "paid_expenses": float(paid_expenses),
        "pending_expenses": float(pending_expenses),
        "cash_flow": float(cash_flow),
        "ml_received_revenue": float(ml_received_revenue),
        "ml_pending_revenue": float(ml_pending_revenue),
        "filters_applied": {
            "period": period,
            "date_from": date_from,
            "date_to": date_to
        }
    }

@financial_router.get("/financial/dre")
async def dre_report_page():
    """Página do relatório DRE"""
    from app.views.template_renderer import render_template
    return render_template("dre_report.html", {})

@financial_router.get("/api/financial/dre")
async def get_dre_report(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Gera relatório DRE agrupado por centro de custo com 12 meses"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        # Calcular período dos últimos 12 meses
        from datetime import timedelta
        today = datetime.now()
        
        # Gerar lista dos próximos 3 meses + últimos 12 meses (total: 15 meses)
        months_data = []
        
        # Próximos 3 meses (futuro) - PRIMEIRO (do mais próximo para o mais distante)
        for i in range(3, 0, -1):
            future_month = today.month + i
            future_year = today.year
            
            if future_month > 12:
                future_month -= 12
                future_year += 1
            
            month_date = datetime(future_year, future_month, 1)
            
            # Calcular o último dia do mês
            if future_month == 12:
                next_month = datetime(future_year + 1, 1, 1)
            else:
                next_month = datetime(future_year, future_month + 1, 1)
            
            last_day = next_month - timedelta(days=1)
            
            months_data.append({
                'year': future_year,
                'month': future_month,
                'name': month_date.strftime('%m/%Y'),
                'start_date': month_date,
                'end_date': last_day,
                'is_future': True
            })
        
        # Últimos 12 meses (histórico) - do mais recente para o mais antigo
        for i in range(12):  # 0, 1, 2, ..., 11
            # Calcular mês atual - i meses
            current_month = today.month - i
            current_year = today.year
            
            if current_month <= 0:
                current_month += 12
                current_year -= 1
            
            month_date = datetime(current_year, current_month, 1)
            
            # Calcular o último dia do mês
            if current_month == 12:
                next_month = datetime(current_year + 1, 1, 1)
            else:
                next_month = datetime(current_year, current_month + 1, 1)
            
            last_day = next_month - timedelta(days=1)
            
            months_data.append({
                'year': current_year,
                'month': current_month,
                'name': month_date.strftime('%m/%Y'),
                'start_date': month_date,
                'end_date': last_day,
                'is_future': False
            })
        
        # Inicializar estrutura de dados para o DRE consolidado
        dre_report = {
            'months': [m['name'] for m in months_data],
            'data': {
                'RECEITAS': {
                    'total': {m['name']: 0.0 for m in months_data},
                    'Contas a Receber': {m['name']: 0.0 for m in months_data},
                    'Mercado Livre': {m['name']: 0.0 for m in months_data},
                },
                'DESPESAS': {
                    'total': {m['name']: 0.0 for m in months_data},
                    'Taxas Mercado Livre': {m['name']: 0.0 for m in months_data},
                },
                'RESULTADO': {
                    'total': {m['name']: 0.0 for m in months_data},
                }
            },
            'cost_centers': {},
            'categories': {},
            'cost_center_categories': {}
        }

        # OTIMIZAÇÃO: Buscar todos os dados de uma vez e processar em memória
        print("DEBUG DRE - Buscando todos os dados de uma vez...")
        
        # Buscar todas as receitas de uma vez (sem filtro de status para incluir todas)
        all_receivables = db.query(AccountReceivable).filter(
            AccountReceivable.company_id == company_id
        ).all()
        print(f"DEBUG DRE - Total receitas encontradas: {len(all_receivables)}")
        
        # Buscar todos os pedidos ML de uma vez (sem filtro de status para incluir todos)
        all_ml_orders = db.query(MLOrder).filter(
            MLOrder.company_id == company_id
        ).all()
        print(f"DEBUG DRE - Total pedidos ML encontrados: {len(all_ml_orders)}")
        
        # OTIMIZAÇÃO: Consulta SQL consolidada para despesas
        print("DEBUG DRE - Executando consulta SQL consolidada para despesas...")
        
        # Definir período de busca (últimos 12 meses + próximos 3 meses)
        start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        end_date = (today + timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Consulta SQL consolidada para despesas (pagas + pendentes)
        expenses_query = text("""
            -- Despesas pagas
            SELECT 
                TO_CHAR(ap.paid_date, 'MM/YYYY') as month_key,
                COALESCE(cc.name, 'Sem Centro de Custo') as cost_center_name,
                'paid' as expense_type,
                SUM(ap.amount) as total_amount,
                COUNT(*) as record_count
            FROM accounts_payable ap 
            LEFT JOIN cost_centers cc ON cc.id = ap.cost_center_id
            WHERE ap.company_id = :company_id
                AND ap.status IN ('paid', 'received', 'completed')
                AND ap.paid_date IS NOT NULL
                AND ap.paid_date >= :start_date 
                AND ap.paid_date <= :end_date
            GROUP BY 
                TO_CHAR(ap.paid_date, 'MM/YYYY'),
                cc.name

            UNION ALL

            -- Despesas pendentes
            SELECT 
                TO_CHAR(ap.due_date, 'MM/YYYY') as month_key,
                COALESCE(cc.name, 'Sem Centro de Custo') as cost_center_name,
                'pending' as expense_type,
                SUM(ap.amount) as total_amount,
                COUNT(*) as record_count
            FROM accounts_payable ap 
            LEFT JOIN cost_centers cc ON cc.id = ap.cost_center_id
            WHERE ap.company_id = :company_id
                AND ap.status IN ('pending', 'unpaid', 'overdue')
                AND ap.due_date >= :start_date 
                AND ap.due_date <= :end_date
            GROUP BY 
                TO_CHAR(ap.due_date, 'MM/YYYY'),
                cc.name
            ORDER BY 
                month_key DESC,
                cost_center_name,
                expense_type
        """)
        
        # Executar consulta consolidada
        expenses_results = db.execute(expenses_query, {
            'company_id': company_id,
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()
        
        print(f"DEBUG DRE - Total registros de despesas encontrados: {len(expenses_results)}")
        
        # Processar dados em memória
        receivables_by_month = {}
        payables_by_month = {}
        ml_by_month = {}
        cost_centers_by_month = {}
        
        # Processar receitas - usar due_date para faturamento correto
        for receivable in all_receivables:
            if receivable.due_date:  # Mudança: usar due_date em vez de paid_date
                month_key = receivable.due_date.strftime('%m/%Y')
                if month_key not in receivables_by_month:
                    receivables_by_month[month_key] = 0.0
                receivables_by_month[month_key] += float(receivable.amount or 0)
        
        # Processar despesas (resultados da consulta consolidada)
        for row in expenses_results:
            month_key = row.month_key
            cost_center_name = row.cost_center_name
            expense_type = row.expense_type
            total_amount = float(row.total_amount or 0)
            
            # Total por mês
            if month_key not in payables_by_month:
                payables_by_month[month_key] = 0.0
            payables_by_month[month_key] += total_amount
            
            # Por centro de custo
            if month_key not in cost_centers_by_month:
                cost_centers_by_month[month_key] = {}
            if cost_center_name not in cost_centers_by_month[month_key]:
                cost_centers_by_month[month_key][cost_center_name] = 0.0
            cost_centers_by_month[month_key][cost_center_name] += total_amount
        
        # Processar pedidos ML - usar date_created para faturamento correto
        ml_fees_by_month = {}  # Nova variável para taxas do ML
        for order in all_ml_orders:
            if order.date_created:  # Mudança: usar date_created e remover regra dos 7 dias
                month_key = order.date_created.strftime('%m/%Y')
                if month_key not in ml_by_month:
                    ml_by_month[month_key] = 0.0
                if month_key not in ml_fees_by_month:
                    ml_fees_by_month[month_key] = 0.0
                
                # Faturamento BRUTO (valor total pago pelo cliente)
                ml_by_month[month_key] += float(order.total_amount or 0)
                
                # Taxas do ML como despesa separada
                ml_fees_by_month[month_key] += float(order.total_fees or 0)
        
        print(f"DEBUG DRE - Receitas por mês: {receivables_by_month}")
        print(f"DEBUG DRE - Despesas por mês: {payables_by_month}")
        print(f"DEBUG DRE - ML por mês: {ml_by_month}")
        print(f"DEBUG DRE - Taxas ML por mês: {ml_fees_by_month}")
        print(f"DEBUG DRE - Centros de custo por mês: {cost_centers_by_month}")
        
        # OTIMIZAÇÃO: Usar dados já consolidados da consulta SQL
        print("DEBUG DRE - Processando dados consolidados...")
        
        # Iterar sobre cada mês para preencher o relatório
        for month_info in months_data:
            month_name = month_info['name']
            month_key = month_info['start_date'].strftime('%m/%Y')
            is_future = month_info.get('is_future', False)

            print(f"DEBUG DRE - Processando mês: {month_name} ({month_key}), Futuro: {is_future}")

            # RECEITAS - Usar dados já processados
            receivables_revenue = receivables_by_month.get(month_key, 0.0)
            ml_revenue = ml_by_month.get(month_key, 0.0)
            total_revenue_month = receivables_revenue + ml_revenue
            
            print(f"DEBUG DRE - {month_name} - Receitas Contas a Receber: {receivables_revenue}")
            print(f"DEBUG DRE - {month_name} - Receitas Mercado Livre: {ml_revenue}")
            print(f"DEBUG DRE - {month_name} - Total Receitas: {total_revenue_month}")

            # DESPESAS - Usar dados já processados da consulta SQL consolidada
            payables_expenses = payables_by_month.get(month_key, 0.0)
            ml_fees_expenses = ml_fees_by_month.get(month_key, 0.0)
            total_expenses_month = payables_expenses + ml_fees_expenses
            
            print(f"DEBUG DRE - {month_name} - Despesas Contas a Pagar: {payables_expenses}")
            print(f"DEBUG DRE - {month_name} - Taxas Mercado Livre: {ml_fees_expenses}")
            print(f"DEBUG DRE - {month_name} - Total Despesas: {total_expenses_month}")

            # Calcular Resultado
            result_month = total_revenue_month - total_expenses_month
            print(f"DEBUG DRE - {month_name} - Resultado: {result_month}")

            # Preencher o relatório DRE
            dre_report['data']['RECEITAS']['Contas a Receber'][month_name] = receivables_revenue
            dre_report['data']['RECEITAS']['Mercado Livre'][month_name] = ml_revenue
            dre_report['data']['RECEITAS']['total'][month_name] = total_revenue_month
            dre_report['data']['DESPESAS']['Taxas Mercado Livre'][month_name] = ml_fees_expenses
            dre_report['data']['DESPESAS']['total'][month_name] = total_expenses_month
            dre_report['data']['RESULTADO']['total'][month_name] = result_month

            # Preencher dados por centro de custo (já processados na consulta SQL)
            if month_key in cost_centers_by_month:
                for cc_name, total in cost_centers_by_month[month_key].items():
                    if cc_name not in dre_report['cost_centers']:
                        dre_report['cost_centers'][cc_name] = {m['name']: 0.0 for m in months_data}
                    dre_report['cost_centers'][cc_name][month_name] = float(total or 0)

            # NOTA: Dados por centro de custo já foram processados na consulta SQL consolidada
            # e preenchidos acima na seção "Preencher dados por centro de custo"

        # Calcular projeções para meses futuros baseadas no histórico
        print("DEBUG DRE - Calculando projeções para meses futuros...")
        
        # Calcular médias históricas
        historical_receivables = []
        historical_ml = []
        
        for month_info in months_data:
            if not month_info.get('is_future', False):
                month_name = month_info['name']
                receivables_val = dre_report['data']['RECEITAS']['Contas a Receber'][month_name]
                ml_val = dre_report['data']['RECEITAS']['Mercado Livre'][month_name]
                
                if receivables_val > 0:
                    historical_receivables.append(receivables_val)
                if ml_val > 0:
                    historical_ml.append(ml_val)
        
        # Calcular médias
        avg_receivables = sum(historical_receivables) / len(historical_receivables) if historical_receivables else 0
        avg_ml = sum(historical_ml) / len(historical_ml) if historical_ml else 0
        
        print(f"DEBUG DRE - Média histórica Contas a Receber: {avg_receivables}")
        print(f"DEBUG DRE - Média histórica Mercado Livre: {avg_ml}")
        
        # Aplicar projeções nos meses futuros
        for month_info in months_data:
            if month_info.get('is_future', False):
                month_name = month_info['name']
                print(f"DEBUG DRE - Aplicando projeção para {month_name}")
                
                # Aplicar projeções
                dre_report['data']['RECEITAS']['Contas a Receber'][month_name] = avg_receivables
                dre_report['data']['RECEITAS']['Mercado Livre'][month_name] = avg_ml
                dre_report['data']['RECEITAS']['total'][month_name] = avg_receivables + avg_ml
                
                # Recalcular resultado para meses futuros
                dre_report['data']['RESULTADO']['total'][month_name] = dre_report['data']['RECEITAS']['total'][month_name] - dre_report['data']['DESPESAS']['total'][month_name]

        return dre_report
        
    except Exception as e:
        import traceback
        error_msg = f"Erro ao gerar DRE: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=str(e))

@financial_router.get("/api/financial/expenses-by-category")
async def get_expenses_by_category(
    cost_center: Optional[str] = None,
    month: Optional[str] = None,
    type: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna despesas agrupadas por categoria com filtros opcionais"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        result = auth_controller.get_user_by_session(session_token, db)
        print(f"DEBUG - Resultado da autenticação: {result}")
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result["error"])
        
        user_data = result.get('user', {})
        company_id = user_data.get('company_id')
        print(f"DEBUG - Company ID encontrado: {company_id}")
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        print(f"DEBUG - Buscando despesas por categoria - Company: {company_id}")
        print(f"DEBUG - Filtros - Centro de custo: {cost_center}, Mês: {month}, Tipo: {type}")
        
        # Construir consulta base
        query = db.query(
            FinancialCategory.name.label('category_name'),
            func.sum(AccountPayable.amount).label('total_amount')
        ).join(
            AccountPayable, FinancialCategory.id == AccountPayable.category_id
        ).filter(
            AccountPayable.company_id == company_id
        )
        
        # Aplicar filtros
        if cost_center:
            query = query.join(CostCenter, CostCenter.id == AccountPayable.cost_center_id).filter(
                CostCenter.name == cost_center
            )
        
        if type == 'paid':
            query = query.filter(
                AccountPayable.status.in_(['paid', 'received', 'completed']),
                AccountPayable.paid_date.isnot(None)
            )
            if month:
                # Para despesas pagas, filtrar por data de pagamento
                month_date = datetime.strptime(month, '%m/%Y')
                month_start = month_date.replace(day=1)
                if month_date.month == 12:
                    month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
                query = query.filter(
                    AccountPayable.paid_date >= month_start,
                    AccountPayable.paid_date <= month_end
                )
        elif type == 'pending':
            query = query.filter(
                AccountPayable.status.in_(['pending', 'unpaid', 'overdue'])
            )
            if month:
                # Para despesas pendentes, filtrar por data de vencimento
                month_date = datetime.strptime(month, '%m/%Y')
                month_start = month_date.replace(day=1)
                if month_date.month == 12:
                    month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
                query = query.filter(
                    AccountPayable.due_date >= month_start,
                    AccountPayable.due_date <= month_end
                )
        else:
            # Sem filtro de tipo - incluir todas as despesas
            if month:
                month_date = datetime.strptime(month, '%m/%Y')
                month_start = month_date.replace(day=1)
                if month_date.month == 12:
                    month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
                query = query.filter(
                    or_(
                        and_(
                            AccountPayable.status.in_(['paid', 'received', 'completed']),
                            AccountPayable.paid_date >= month_start,
                            AccountPayable.paid_date <= month_end
                        ),
                        and_(
                            AccountPayable.status.in_(['pending', 'unpaid', 'overdue']),
                            AccountPayable.due_date >= month_start,
                            AccountPayable.due_date <= month_end
                        )
                    )
                )
        
        # Executar consulta
        results = query.group_by(FinancialCategory.id, FinancialCategory.name).all()
        
        print(f"DEBUG - Resultados encontrados: {len(results)}")
        
        # Processar resultados
        categories = {}
        for category_name, total_amount in results:
            categories[category_name] = float(total_amount or 0)
        
        print(f"DEBUG - Categorias processadas: {categories}")
        
        return {
            'categories': categories,
            'total': sum(categories.values()),
            'filters': {
                'cost_center': cost_center,
                'month': month,
                'type': type
            }
        }
        
    except Exception as e:
        import traceback
        error_msg = f"Erro ao buscar despesas por categoria: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=str(e))

@financial_router.get("/api/financial/expenses-filters")
async def get_expenses_filters(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna filtros disponíveis para despesas (centros de custo e meses)"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result["error"])
        
        user_data = result.get('user', {})
        company_id = user_data.get('company_id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        print(f"DEBUG - Buscando filtros para Company: {company_id}")
        
        # Buscar centros de custo
        cost_centers = db.query(CostCenter.name).filter(
            CostCenter.company_id == company_id
        ).order_by(CostCenter.name).all()
        
        cost_center_list = [cc.name for cc in cost_centers]
        print(f"DEBUG - Centros de custo encontrados: {cost_center_list}")
        
        # Gerar lista de meses: últimos 6 meses + próximos 6 meses
        today = datetime.now()
        month_list = []
        
        # Últimos 6 meses
        for i in range(6, 0, -1):
            month_date = today - timedelta(days=30*i)
            month_key = month_date.strftime('%m/%Y')
            month_list.append(month_key)
        
        # Mês atual
        current_month = today.strftime('%m/%Y')
        month_list.append(current_month)
        
        # Próximos 6 meses
        for i in range(1, 7):
            # Usar primeiro dia do mês para evitar erro de "day is out of range"
            if today.month + i > 12:
                # Próximo ano
                next_year = today.year + 1
                next_month = today.month + i - 12
            else:
                next_year = today.year
                next_month = today.month + i
            # Usar dia 1 para evitar problemas com meses que têm menos dias
            month_date = datetime(next_year, next_month, 1)
            month_key = month_date.strftime('%m/%Y')
            month_list.append(month_key)
        
        print(f"DEBUG - Meses gerados: {month_list}")
        print(f"DEBUG - Mês atual: {current_month}")
        
        return {
            'cost_centers': cost_center_list,
            'months': month_list,
            'current_month': current_month
        }
        
    except Exception as e:
        import traceback
        error_msg = f"Erro ao buscar filtros: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=str(e))

@financial_router.get("/api/financial/revenues-by-category")
async def get_revenues_by_category(
    month: Optional[str] = None,
    type: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna receitas agrupadas por categoria com filtros opcionais"""
    try:
        print("DEBUG RECEITAS - Iniciando endpoint")
        
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        result = auth_controller.get_user_by_session(session_token, db)
        user_data = result.get('user', {})
        company_id = user_data.get('company_id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        print(f"DEBUG RECEITAS - Company ID: {company_id}")
        
        # Construir filtros de data se mês foi especificado
        date_filter = ""
        if month and month != "":
            month_parts = month.split('/')
            if len(month_parts) == 2:
                month_num = int(month_parts[0])
                year_num = int(month_parts[1])
                start_date = datetime(year_num, month_num, 1)
                if month_num == 12:
                    end_date = datetime(year_num + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year_num, month_num + 1, 1) - timedelta(days=1)
                
                date_filter = f"AND DATE(ar.due_date) >= '{start_date.date()}' AND DATE(ar.due_date) <= '{end_date.date()}'"
                ml_date_filter = f"AND DATE(ml.date_created) >= '{start_date.date()}' AND DATE(ml.date_created) <= '{end_date.date()}'"
            else:
                date_filter = ""
                ml_date_filter = ""
        else:
            date_filter = ""
            ml_date_filter = ""
        
        # Construir filtros de tipo
        type_filter = ""
        ml_type_filter = ""
        if type == 'paid':
            type_filter = "AND ar.status IN ('paid', 'received', 'completed') AND ar.paid_date IS NOT NULL"
            ml_type_filter = "AND ml.status IN ('PAID', 'SHIPPED', 'DELIVERED')"
        elif type == 'pending':
            type_filter = "AND ar.status IN ('pending', 'unpaid', 'overdue')"
            ml_type_filter = "AND ml.status IN ('PENDING', 'CONFIRMED')"
        
        # Consulta SQL única com UNION ALL
        revenues_query = text(f"""
            SELECT 
                fc.name AS category_name,
                SUM(ar.amount) AS total_amount
            FROM financial_categories fc
            LEFT JOIN accounts_receivable ar ON fc.id = ar.category_id
            WHERE ar.company_id = :company_id
            {date_filter}
            {type_filter}
            GROUP BY fc.id, fc.name
            
            UNION ALL
            
            SELECT 
                'Vendas Mercado Livre' AS category_name,
                SUM(ml.total_amount) AS total_amount
            FROM ml_orders ml
            WHERE ml.company_id = :company_id
            {ml_date_filter}
            {ml_type_filter}
            GROUP BY 1
        """)
        
        print(f"DEBUG RECEITAS - SQL Query: {revenues_query}")
        
        # Executar consulta SQL
        results = db.execute(revenues_query, {'company_id': company_id}).fetchall()
        
        print(f"DEBUG RECEITAS - Results: {results}")
        
        # Processar resultados
        categories = {}
        for category_name, total_amount in results:
            if category_name and total_amount:
                if category_name in categories:
                    categories[category_name] += float(total_amount or 0)
                else:
                    categories[category_name] = float(total_amount or 0)
        
        print(f"DEBUG RECEITAS - Categories: {categories}")
        
        return {
            'categories': categories,
            'total': sum(categories.values()),
            'filters': {
                'month': month,
                'type': type
            }
        }
        
    except Exception as e:
        import traceback
        print(f"Erro ao carregar receitas por categoria: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@financial_router.get("/api/financial/revenues-filters")
async def get_revenues_filters(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna filtros disponíveis para receitas (centros de custo e meses)"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        result = auth_controller.get_user_by_session(session_token, db)
        user_data = result.get('user', {})
        company_id = user_data.get('company_id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        # Buscar centros de custo
        cost_centers = db.query(CostCenter.name).filter(
            CostCenter.company_id == company_id
        ).order_by(CostCenter.name).all()
        cost_center_list = [cc.name for cc in cost_centers]
        
        # Gerar lista de meses (últimos 6 meses + mês atual + próximos 6 meses)
        today = datetime.now()
        month_list = []
        
        # Últimos 6 meses
        for i in range(6, 0, -1):
            month_date = today - timedelta(days=30*i)
            month_list.append(month_date.strftime('%m/%Y'))
        
        # Mês atual
        current_month = today.strftime('%m/%Y')
        month_list.append(current_month)
        
        # Próximos 6 meses
        for i in range(1, 7):
            # Usar primeiro dia do mês para evitar erro de "day is out of range"
            if today.month + i > 12:
                # Próximo ano
                next_year = today.year + 1
                next_month = today.month + i - 12
            else:
                next_year = today.year
                next_month = today.month + i
            # Usar dia 1 para evitar problemas com meses que têm menos dias
            month_date = datetime(next_year, next_month, 1)
            month_list.append(month_date.strftime('%m/%Y'))
        
        return {
            'cost_centers': cost_center_list,
            'months': month_list,
            'current_month': current_month
        }
        
    except Exception as e:
        print(f"Erro ao carregar filtros de receitas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# =====================================================
# ROTAS DE API - PLANEJAMENTO FINANCEIRO
# =====================================================

@financial_router.post("/api/financial/planning/create")
async def create_annual_planning(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Cria planejamento financeiro anual"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do body da requisição
    try:
        body = await request.json()
        year = body.get("year")
        months_data = body.get("months", [])
        
        # Se não informar ano, usar ano atual
        if not year:
            from datetime import datetime
            year = datetime.now().year
    except Exception as e:
        # Se não conseguir fazer parse do JSON, usar ano atual
        from datetime import datetime
        year = datetime.now().year
        months_data = []
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.create_annual_planning(company_id, year, months_data)

@financial_router.post("/api/financial/planning/create-current")
async def create_current_year_planning(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Cria planejamento financeiro para o ano atual"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Usar ano atual
    from datetime import datetime
    year = datetime.now().year
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.create_annual_planning(company_id, year)

@financial_router.get("/api/financial/planning/{year}")
async def get_annual_planning(
    year: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Busca planejamento financeiro anual"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.get_annual_planning(company_id, year)

@financial_router.put("/api/financial/planning/monthly/{monthly_planning_id}")
async def update_monthly_planning(
    monthly_planning_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Atualiza planejamento mensal"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    # Obter dados do body da requisição
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=422, detail="Dados inválidos")
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.update_monthly_planning(monthly_planning_id, data)

@financial_router.put("/api/financial/planning/cost-center/{monthly_planning_id}/{cost_center_id}")
async def update_cost_center_planning(
    monthly_planning_id: int,
    cost_center_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Atualiza planejamento por centro de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    # Obter dados do body da requisição
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=422, detail="Dados inválidos")
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.update_cost_center_planning(monthly_planning_id, cost_center_id, data)

@financial_router.put("/api/financial/planning/category/{cost_center_planning_id}/{category_id}")
async def update_category_planning(
    cost_center_planning_id: int,
    category_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Atualiza planejamento por categoria"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    # Obter dados do body da requisição
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=422, detail="Dados inválidos")
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.update_category_planning(cost_center_planning_id, category_id, data)

@financial_router.delete("/api/financial/planning/clear/{year}")
async def clear_annual_planning(
    year: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Remove todos os planejamentos de um ano"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.clear_annual_planning(company_id, year)

@financial_router.put("/api/financial/planning/update/{year}")
async def update_annual_planning(
    year: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Atualiza planejamento financeiro anual"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do body da requisição
    try:
        data = await request.json()
        months_data = data.get("months", [])
    except Exception as e:
        raise HTTPException(status_code=422, detail="Dados inválidos")
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.update_annual_planning(company_id, year, months_data)

@financial_router.get("/api/financial/planning-analysis")
async def get_planning_analysis(
    year: int = Query(..., description="Ano do planejamento"),
    month: Optional[str] = Query(None, description="Mês específico (01-12)"),
    metric: str = Query("revenue", description="Métrica: revenue, expenses, profit"),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Análise de evolução: Planejamento vs Real"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    from app.controllers.financial_planning_controller import FinancialPlanningController
    controller = FinancialPlanningController(db)
    
    return controller.get_planning_analysis(company_id, year, month, metric)
