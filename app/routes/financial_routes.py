"""
Rotas para o módulo financeiro SaaS
Seguindo o padrão do sistema
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, date

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.models.financial_models import (
    FinancialAccount, FinancialCategory, CostCenter, FinancialCustomer,
    AccountReceivable, FinancialSupplier, AccountPayable, FinancialTransaction
)
from app.models.saas_models import Fornecedor, OrdemCompra

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
    """Página de planejamento financeiro (em desenvolvimento)"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("financial_reports.html", user=user_data)

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
    
    # Criar novo centro de custo no banco
    new_cost_center = CostCenter(
        company_id=company_id,
        code=cost_center_data.get("code", ""),
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
            "description": acc.description,
            "created_at": acc.created_at,
            "company_id": acc.company_id
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
        
        # Verificar saldo suficiente
        current_balance = float(from_account.current_balance or 0)
        if amount > current_balance:
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
        
        # Atualizar saldos
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
        description=account_data.get("description")
    )
    
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
    if account_data.get("initial_balance") is not None:
        account.initial_balance = float(account_data.get("initial_balance"))
    if account_data.get("current_balance") is not None:
        account.current_balance = float(account_data.get("current_balance"))
    if account_data.get("is_active") is not None:
        account.is_active = account_data.get("is_active")
    if account_data.get("description") is not None:
        account.description = account_data.get("description")
    
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
        
        logger.info(f"✅ {len(created_entries)} despesas recorrentes criadas: {base_description}")
        return {"message": f"{len(created_entries)} despesas recorrentes criadas com sucesso", "count": len(created_entries)}
    
    # Se for parcelamento, criar múltiplas entradas
    elif total_installments > 1:
        # Criar conta principal (parent)
        parent_payable = AccountPayable(
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
            installment_number=0,  # Conta principal
            total_installments=total_installments,
            is_fixed=payable_data.get("is_fixed", False),
            notes=payable_data.get("notes")
        )
        
        db.add(parent_payable)
        db.commit()
        db.refresh(parent_payable)
        
        # Criar parcelas
        installment_amount = float(payable_data.get("amount")) / total_installments
        
        # Usar data de vencimento da primeira parcela se fornecida, senão usar due_date
        if installment_due_date:
            base_due_date = datetime.strptime(installment_due_date, "%Y-%m-%d").date()
        else:
            base_due_date = datetime.strptime(payable_data.get("due_date"), "%Y-%m-%d").date()
        
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
                parent_payable_id=parent_payable.id,
                is_fixed=payable_data.get("is_fixed", False),
                notes=payable_data.get("notes")
            )
            
            db.add(installment)
        
        db.commit()
        
        logger.info(f"✅ Parcelamento criado: {parent_payable.description} - {total_installments} parcelas (ID: {parent_payable.id})")
        return {"message": f"Parcelamento criado com sucesso - {total_installments} parcelas", "id": parent_payable.id}
    
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
            parent_id = payable.parent_payable_id if payable.parent_payable_id else payable_id
            
            # Remover todas as parcelas (incluindo a principal)
            all_installments = db.query(AccountPayable).filter(
                or_(
                    AccountPayable.id == parent_id,
                    AccountPayable.parent_payable_id == parent_id
                ),
                AccountPayable.company_id == company_id
            ).all()
            
            deleted_count = len(all_installments)
            for installment in all_installments:
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
    if not remove_future_entries or (not payable.is_recurring and payable.total_installments <= 1):
        db.delete(payable)
    
    db.commit()
    
    if remove_future_entries and deleted_count > 1:
        logger.info(f"✅ Conta a pagar e {deleted_count - 1} lançamentos futuros excluídos: {payable.description} (ID: {payable_id})")
        return {"message": f"Conta e {deleted_count - 1} lançamentos futuros excluídos com sucesso"}
    else:
        logger.info(f"✅ Conta a pagar excluída: {payable.description} (ID: {payable_id})")
        return {"message": "Conta a pagar excluída com sucesso"}

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
    
    # Se marcando como pago, definir data de pagamento
    if new_status == "paid":
        payable.paid_date = datetime.now().date()
        if not payable.paid_amount:
            payable.paid_amount = float(payable.amount)
    else:
        # Se mudando para outro status, limpar dados de pagamento
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
    """API para obter dados do dashboard financeiro"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    from datetime import datetime, timedelta
    from sqlalchemy import extract
    
    # Data atual e início do mês
    today = datetime.now()
    
    # Calcular período baseado no filtro
    if period == "today":
        month_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_week":
        # Início da semana (segunda-feira)
        days_since_monday = today.weekday()
        month_start = (today - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_month":
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period == "last_month":
        month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        month_end = today.replace(day=1) - timedelta(days=1)
    elif period == "next_month":
        next_month = today.replace(day=1) + timedelta(days=32)
        month_start = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period == "next_30_days":
        month_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = (today + timedelta(days=30)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "next_60_days":
        month_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = (today + timedelta(days=60)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "next_90_days":
        month_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = (today + timedelta(days=90)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_year":
        month_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    elif period == "custom" and date_from and date_to:
        month_start = datetime.fromisoformat(date_from)
        month_end = datetime.fromisoformat(date_to)
    else:
        # Padrão: este mês
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # 1. Estatísticas do período filtrado
    # Receitas do período (contas a receber pagas + pedidos ML recebidos)
    monthly_receivables = db.query(AccountReceivable).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status.in_(['paid', 'received']),
        AccountReceivable.paid_date >= month_start,
        AccountReceivable.paid_date <= month_end
    ).all()
    
    received_revenue = sum(float(rec.paid_amount or rec.amount) for rec in monthly_receivables)
    
    # Inicializar pending_revenue antes de usar
    pending_revenue = 0
    
    # Adicionar pedidos ML como receitas (todos os pedidos pagos, não apenas entregues)
    from app.models.saas_models import Company, MLOrder, OrderStatus
    company = db.query(Company).filter(Company.id == company_id).first()
    
    if company and company.ml_orders_as_receivables:
        # Buscar pedidos ML pagos do período
        ml_orders_paid = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED]),
            MLOrder.date_closed >= month_start,
            MLOrder.date_closed <= month_end
        ).all()
        
        for order in ml_orders_paid:
            # Calcular valor líquido (total - taxas)
            net_amount = float(order.total_amount or 0) - float(order.total_fees or 0)
            
            # Aplicar mesma lógica da tela de Contas a Receber: só é "recebido" se entregue há mais de 7 dias
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
                        # Só adicionar como recebido se foi entregue há mais de 7 dias
                        received_revenue += net_amount
                    else:
                        # Se foi entregue há menos de 7 dias, vai para pendente
                        pending_revenue += net_amount
                else:
                    # Se não tem data de entrega, considerar como pendente
                    pending_revenue += net_amount
            else:
                # Se não foi entregue, considerar como pendente
                pending_revenue += net_amount
    
    # Receitas pendentes (contas a receber pendentes com vencimento no período)
    monthly_receivables_pending = db.query(AccountReceivable).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status == 'pending',
        AccountReceivable.due_date >= month_start,
        AccountReceivable.due_date <= month_end
    ).all()
    
    pending_revenue += sum(float(rec.amount) for rec in monthly_receivables_pending)
    
    # Nota: A lógica dos pedidos ML já foi aplicada acima, não precisa duplicar
    
    # Total de receitas
    monthly_revenue = received_revenue + pending_revenue
    
    # Despesas do período (contas a pagar - pagas e pendentes)
    # Contas pagas no período
    monthly_payables_paid = db.query(AccountPayable).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status == 'paid',
        AccountPayable.paid_date >= month_start,
        AccountPayable.paid_date <= month_end
    ).all()
    
    # Contas pendentes com vencimento no período
    monthly_payables_pending = db.query(AccountPayable).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status == 'pending',
        AccountPayable.due_date >= month_start,
        AccountPayable.due_date <= month_end
    ).all()
    
    # Separar despesas pagas e pendentes
    paid_expenses = sum(float(pay.paid_amount or pay.amount) for pay in monthly_payables_paid)
    pending_expenses = sum(float(pay.amount) for pay in monthly_payables_pending)
    monthly_expenses = paid_expenses + pending_expenses
    
    # Lucro do mês
    monthly_profit = monthly_revenue - monthly_expenses
    
    # Saldo atual das contas bancárias
    bank_accounts = db.query(FinancialAccount).filter(
        FinancialAccount.company_id == company_id,
        FinancialAccount.is_active == True
    ).all()
    
    current_balance = sum(float(acc.current_balance) for acc in bank_accounts)
    
    # Calcular projeção de caixa: Saldo atual + receitas pendentes - despesas pendentes
    cash_projection = current_balance + pending_revenue - pending_expenses
    
    # 2. Dados históricos - sempre mostrar últimos 6 meses
    monthly_data = []
    
    # Sempre mostrar dados dos últimos 6 meses para o gráfico
    for i in range(6):
        month_date = (today - timedelta(days=30*i)).replace(day=1)
        next_month = (month_date + timedelta(days=32)).replace(day=1)
        
        # Receitas do mês (contas a receber + pedidos ML)
        month_receivables = db.query(AccountReceivable).filter(
            AccountReceivable.company_id == company_id,
            AccountReceivable.status.in_(['paid', 'received']),
            AccountReceivable.paid_date >= month_date,
            AccountReceivable.paid_date < next_month
        ).all()
        
        month_revenue = sum(float(rec.paid_amount or rec.amount) for rec in month_receivables)
        
        # Adicionar pedidos ML do mês
        if company and company.ml_orders_as_receivables:
            month_ml_orders = db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED]),
                MLOrder.date_closed >= month_date,
                MLOrder.date_closed < next_month
            ).all()
            
            for order in month_ml_orders:
                net_amount = float(order.total_amount or 0) - float(order.total_fees or 0)
                month_revenue += net_amount
        
        # Despesas do mês
        month_payables = db.query(AccountPayable).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status == 'paid',
            AccountPayable.paid_date >= month_date,
            AccountPayable.paid_date < next_month
        ).all()
        
        month_expenses = sum(float(pay.paid_amount or pay.amount) for pay in month_payables)
        
        monthly_data.append({
            "month": month_date.strftime("%m/%Y"),
            "revenue": month_revenue,
            "expenses": month_expenses
        })
    
    monthly_data.reverse()  # Ordenar do mais antigo para o mais recente
    
    # 3. Top categorias do mês (incluindo Mercado Livre)
    top_categories = []
    categories = db.query(FinancialCategory).filter(
        FinancialCategory.company_id == company_id
    ).all()
    
    for category in categories:
        # Calcular total de receitas desta categoria no mês
        category_receivables = db.query(AccountReceivable).filter(
            AccountReceivable.company_id == company_id,
            AccountReceivable.category_id == category.id,
            AccountReceivable.status.in_(['paid', 'received']),
            AccountReceivable.paid_date >= month_start
        ).all()
        
        category_amount = sum(float(rec.paid_amount or rec.amount) for rec in category_receivables)
        
        if category_amount > 0:
            top_categories.append({
                "name": category.name,
                "amount": category_amount
            })
    
    # Adicionar categoria "Mercado Livre" se houver pedidos ML
    if company and company.ml_orders_as_receivables:
        ml_orders_month = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED]),
            MLOrder.date_closed >= month_start
        ).all()
        
        if ml_orders_month:
            ml_total = sum(float(order.total_amount or 0) - float(order.total_fees or 0) for order in ml_orders_month)
            top_categories.append({
                "name": "Mercado Livre",
                "amount": ml_total
            })
    
    # Ordenar por valor e pegar top 5
    top_categories.sort(key=lambda x: x['amount'], reverse=True)
    top_categories = top_categories[:5]
    
    # 4. Contas a receber recentes (próximas 5) - incluindo pedidos ML
    recent_receivables = db.query(AccountReceivable).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status == 'pending'
    ).order_by(AccountReceivable.due_date).limit(5).all()
    
    recent_receivables_data = [
        {
            "customer_name": rec.customer_name,
            "amount": float(rec.amount),
            "due_date": rec.due_date.isoformat() if rec.due_date else None,
            "status": rec.status
        }
        for rec in recent_receivables
    ]
    
    # Adicionar pedidos ML pendentes se estiver ativado
    if company and company.ml_orders_as_receivables:
        ml_orders_pending = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED]),
            MLOrder.date_closed.isnot(None)
        ).order_by(MLOrder.date_closed.desc()).limit(5).all()
        
        for order in ml_orders_pending:
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
                due_date = actual_payment_date.isoformat()
            else:
                due_date = payment_date.isoformat() if payment_date else None
            
            # Só adicionar se ainda estiver pendente
            if ml_status == "pending":
                recent_receivables_data.append({
                    "customer_name": order.buyer_nickname or order.buyer_first_name or "Cliente ML",
                    "amount": net_amount,
                    "due_date": due_date,
                    "status": ml_status
                })
        
        # Ordenar por data de vencimento e pegar apenas os 5 mais próximos
        recent_receivables_data.sort(key=lambda x: x['due_date'] or '9999-12-31')
        recent_receivables_data = recent_receivables_data[:5]
    
    # 5. Contas a pagar recentes (próximas 5)
    recent_payables = db.query(AccountPayable).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status == 'pending'
    ).order_by(AccountPayable.due_date).limit(5).all()
    
    recent_payables_data = [
        {
            "supplier_name": pay.supplier_name,
            "amount": float(pay.amount),
            "due_date": pay.due_date.isoformat() if pay.due_date else None,
            "status": pay.status
        }
        for pay in recent_payables
    ]
    
    # Calcular fluxo de caixa (receitas recebidas - despesas pagas)
    cash_flow = received_revenue - paid_expenses
    
    return {
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
        "monthly_profit": monthly_profit,
        "current_balance": cash_projection,
        "received_revenue": received_revenue,
        "pending_revenue": pending_revenue,
        "paid_expenses": paid_expenses,
        "pending_expenses": pending_expenses,
        "cash_flow": cash_flow,
        "monthly_data": monthly_data,
        "top_categories": top_categories,
        "recent_receivables": recent_receivables_data,
        "recent_payables": recent_payables_data
    }