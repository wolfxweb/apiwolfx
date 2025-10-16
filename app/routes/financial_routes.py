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
    AccountReceivable, FinancialSupplier, AccountPayable
)

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
    
    # Buscar categorias no banco de dados
    categories = db.query(FinancialCategory).filter(
        FinancialCategory.company_id == company_id
    ).order_by(FinancialCategory.name).all()
    
    return [
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
    
    # Criar nova categoria no banco
    from app.models.financial_models import CategoryType
    
    new_category = FinancialCategory(
        company_id=company_id,
        code=category_data.get("code", ""),
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
    company_id = user_data.get("company_id")
    
    # Buscar categoria existente
    category_index = None
    for i, cat in enumerate(mock_categories):
        if cat["id"] == category_id:
            category_index = i
            break
    
    if category_index is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Atualizar categoria
    mock_categories[category_index].update({
        "code": category_data.get("code", mock_categories[category_index]["code"]),
        "name": category_data.get("name", mock_categories[category_index]["name"]),
        "type": category_data.get("type", mock_categories[category_index]["type"]),
        "monthly_limit": float(category_data.get("monthly_limit", 0)) if category_data.get("monthly_limit") else None,
        "description": category_data.get("description", mock_categories[category_index]["description"]),
        "is_active": category_data.get("is_active", mock_categories[category_index]["is_active"]),
        "updated_at": datetime.now()
    })
    
    logger.info(f"✅ Categoria atualizada: {mock_categories[category_index]['name']} (ID: {category_id})")
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
    company_id = user_data.get("company_id")
    
    # Buscar categoria existente
    category_index = None
    category_name = None
    for i, cat in enumerate(mock_categories):
        if cat["id"] == category_id:
            category_index = i
            category_name = cat["name"]
            break
    
    if category_index is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Remover categoria
    mock_categories.pop(category_index)
    
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
    company_id = user_data.get("company_id")
    
    # Buscar centros de custo no banco de dados
    cost_centers = db.query(CostCenter).filter(
        CostCenter.company_id == company_id
    ).order_by(CostCenter.name).all()
    
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
    company_id = user_data.get("company_id")
    
    # Buscar contas bancárias no banco de dados
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.company_id == company_id
    ).order_by(FinancialAccount.bank_name, FinancialAccount.account_name).all()
    
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
    """API para obter contas a receber"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar contas a receber no banco de dados
    receivables = db.query(AccountReceivable).filter(
        AccountReceivable.company_id == company_id
    ).order_by(desc(AccountReceivable.due_date)).all()
    
    return [
        {
            "id": rec.id,
            "customer_name": rec.customer_name,  # Campo de texto livre
            "category_id": rec.category_id,
            "cost_center_id": rec.cost_center_id,
            "account_id": rec.account_id,
            "invoice_number": rec.invoice_number,
            "description": rec.description,
            "amount": float(rec.amount),
            "due_date": rec.due_date.isoformat() if rec.due_date else None,
            "paid_date": rec.paid_date.isoformat() if rec.paid_date else None,
            "paid_amount": float(rec.paid_amount) if rec.paid_amount else None,
            "status": rec.status,
            "installment_number": rec.installment_number,
            "total_installments": rec.total_installments,
            "parent_receivable_id": rec.parent_receivable_id,
            "is_recurring": rec.is_recurring,
            "recurring_frequency": rec.recurring_frequency,
            "recurring_end_date": rec.recurring_end_date.isoformat() if rec.recurring_end_date else None,
            "notes": rec.notes,
            "created_at": rec.created_at,
            "updated_at": rec.updated_at
        }
        for rec in receivables
    ]

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
    
    return [
                {
                    "id": pay.id,
                    "supplier_name": pay.supplier_name,  # Campo texto livre
                    "category_id": pay.category_id,
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
    
    # Verificar se é parcelamento
    total_installments = payable_data.get("total_installments", 1)
    is_recurring = payable_data.get("is_recurring", False)
    recurring_frequency = payable_data.get("recurring_frequency")
    installment_due_date = payable_data.get("installment_due_date")
    
    # Se for despesa recorrente, criar apenas uma entrada com frequência
    if is_recurring and recurring_frequency:
        new_payable = AccountPayable(
            company_id=company_id,
            supplier_name=payable_data.get("supplier_name"),  # Campo texto livre
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
            is_recurring=True,
            recurring_frequency=recurring_frequency,
            recurring_end_date=datetime.strptime(payable_data.get("recurring_end_date"), "%Y-%m-%d").date() if payable_data.get("recurring_end_date") else None,
            is_fixed=payable_data.get("is_fixed", False),
            notes=payable_data.get("notes")
        )
        
        db.add(new_payable)
        db.commit()
        db.refresh(new_payable)
        
        logger.info(f"✅ Despesa recorrente criada: {new_payable.description} (ID: {new_payable.id})")
        return {"message": "Despesa recorrente criada com sucesso", "id": new_payable.id}
    
    # Se for parcelamento, criar múltiplas entradas
    elif total_installments > 1:
        # Criar conta principal (parent)
        parent_payable = AccountPayable(
            company_id=company_id,
            supplier_name=payable_data.get("supplier_name"),  # Campo texto livre
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
    
    # Atualizar campos
    if payable_data.get("supplier_name") is not None:
        payable.supplier_name = payable_data.get("supplier_name")
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
    
    # Remover conta a pagar
    db.delete(payable)
    db.commit()
    
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

@financial_router.post("/api/financial/receivables/{receivable_id}/mark-paid")
async def mark_receivable_as_paid(
    receivable_id: int,
    payment_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para marcar conta a receber como paga"""
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
    
    # Atualizar status de pagamento
    receivable.status = "paid"
    receivable.paid_date = datetime.strptime(payment_data.get("paid_date"), "%Y-%m-%d").date()
    receivable.paid_amount = payment_data.get("paid_amount", receivable.amount)
    
    db.commit()
    
    logger.info(f"✅ Conta a receber marcada como paga: {receivable.description} (ID: {receivable_id})")
    return {"message": "Conta a receber marcada como paga com sucesso"}

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