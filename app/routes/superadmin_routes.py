"""
Rotas para SuperAdmin - Painel de administração do sistema
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import string

from app.config.database import get_db
from app.controllers.superadmin_controller import SuperAdminController
from app.views.template_renderer import render_template
from app.models.saas_models import User, UserSession, Company, UserRole
from app.config.settings import settings

# Router para superadmin
superadmin_router = APIRouter()

def get_superadmin_session(request: Request, session_token: Optional[str] = Cookie(None)) -> Optional[dict]:
    """Verifica se o usuário está autenticado como superadmin"""
    if not session_token:
        return None
    
    # TODO: Implementar verificação de sessão de superadmin
    # Por enquanto, vamos usar uma verificação simples
    return {"id": 1, "username": "admin", "role": "super_admin"}

@superadmin_router.get("/superadmin", response_class=HTMLResponse)
async def superadmin_login_page(request: Request):
    """Página de login do superadmin"""
    return render_template("superadmin/login.html")

@superadmin_router.post("/superadmin/login")
async def superadmin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login do superadmin"""
    controller = SuperAdminController(db)
    superadmin = controller.authenticate(username, password)
    
    if not superadmin:
        return render_template("superadmin/login.html", error="Credenciais inválidas")
    
    # Criar token de sessão para superadmin
    def _generate_session_token() -> str:
        """Gera token de sessão seguro"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
    
    superadmin_session_token = _generate_session_token()
    superadmin_id_str = str(superadmin["id"])
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Login superadmin bem-sucedido: {superadmin.get('username')} (ID: {superadmin_id_str})")
    
    # Redirecionar para o dashboard
    response = RedirectResponse(url="/superadmin/dashboard", status_code=302)
    
    # Definir cookie de sessão do superadmin (separado do session_token normal)
    # IMPORTANTE: path="/" para que o cookie seja enviado em todas as rotas
    response.set_cookie(
        key="superadmin_session",
        value=superadmin_session_token,
        httponly=False,  # Permitir acesso via JavaScript
        secure=settings.is_production,  # True em produção (HTTPS), False em dev (HTTP)
        samesite="lax",
        path="/",  # IMPORTANTE: definir path para "/" para que funcione em todas as rotas
        max_age=604800  # 7 dias
    )
    
    # Também armazenar o ID do superadmin em um cookie (criptografado seria melhor, mas por enquanto simples)
    response.set_cookie(
        key="superadmin_id",
        value=superadmin_id_str,
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        path="/",  # IMPORTANTE: definir path para "/" para que funcione em todas as rotas
        max_age=604800
    )
    
    logger.info(f"✅ Cookies de superadmin definidos: superadmin_session={bool(superadmin_session_token)}, superadmin_id={superadmin_id_str}")
    
    return response

@superadmin_router.get("/superadmin/dashboard", response_class=HTMLResponse)
async def superadmin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Dashboard principal do superadmin"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    overview = controller.get_system_overview()
    
    return render_template("superadmin/dashboard.html", overview=overview, request=request)

@superadmin_router.get("/superadmin/companies", response_class=HTMLResponse)
async def superadmin_companies(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lista de empresas"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    companies_data = controller.get_companies_list(page=page, status=status)
    
    return render_template("superadmin/companies.html", 
                         companies_data=companies_data,
                         current_status=status)

@superadmin_router.get("/superadmin/companies/{company_id}", response_class=HTMLResponse)
async def superadmin_company_details(
    request: Request,
    company_id: int,
    db: Session = Depends(get_db)
):
    """Detalhes de uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    company_details = controller.get_company_details(company_id)
    
    if not company_details:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    return render_template("superadmin/company_details.html", 
                         company_details=company_details)

@superadmin_router.get("/superadmin/assistants", response_class=HTMLResponse)
async def superadmin_assistants(
    request: Request,
    db: Session = Depends(get_db)
):
    """Gerenciar agentes OpenAI"""
    # TODO: Verificar autenticação de superadmin
    # Garantir colunas de boas-vindas antes de renderizar a tela (fallback de migração)
    try:
        from sqlalchemy import text as sql_text
        # Testar existência das colunas consultando uma linha
        db.execute(sql_text("SELECT welcome_message, welcome_enabled, welcome_use_model FROM openai_assistants LIMIT 1"))
    except Exception:
        try:
            import importlib.util, os
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            welcome_path = os.path.join(base_dir, 'database', 'fixes', '2025_11_16_add_welcome_fields_openai_assistants.py')
            if os.path.exists(welcome_path):
                specw = importlib.util.spec_from_file_location("add_welcome_fields_openai_assistants", welcome_path)
                welcome_module = importlib.util.module_from_spec(specw)
                specw.loader.exec_module(welcome_module)
                try:
                    db.rollback()
                except Exception:
                    pass
                welcome_module.run(db)
                try:
                    db.rollback()
                except Exception:
                    pass
        except Exception:
            pass
    return render_template("superadmin/assistants.html", request=request)

@superadmin_router.get("/superadmin/assistants/new", response_class=HTMLResponse)
async def superadmin_assistants_new(
    request: Request,
    db: Session = Depends(get_db)
):
    """Criar novo agente OpenAI"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/assistants_form.html", request=request, assistant_id=None)

@superadmin_router.get("/superadmin/assistants/{assistant_id}/edit", response_class=HTMLResponse)
async def superadmin_assistants_edit(
    request: Request,
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """Editar agente OpenAI"""
    # TODO: Verificar autenticação de superadmin
    # Garantir colunas de boas-vindas antes de renderizar a tela (fallback de migração)
    try:
        from sqlalchemy import text as sql_text
        db.execute(sql_text("SELECT welcome_message, welcome_enabled, welcome_use_model FROM openai_assistants LIMIT 1"))
    except Exception:
        try:
            import importlib.util, os
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            welcome_path = os.path.join(base_dir, 'database', 'fixes', '2025_11_16_add_welcome_fields_openai_assistants.py')
            if os.path.exists(welcome_path):
                specw = importlib.util.spec_from_file_location("add_welcome_fields_openai_assistants", welcome_path)
                welcome_module = importlib.util.module_from_spec(specw)
                specw.loader.exec_module(welcome_module)
                try:
                    db.rollback()
                except Exception:
                    pass
                welcome_module.run(db)
                try:
                    db.rollback()
                except Exception:
                    pass
        except Exception:
            pass
    return render_template("superadmin/assistants_form.html", request=request, assistant_id=assistant_id)

@superadmin_router.get("/superadmin/assistants/usage", response_class=HTMLResponse)
async def superadmin_assistants_usage(
    request: Request,
    db: Session = Depends(get_db)
):
    """Monitorar uso de tokens dos agentes"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/assistants_usage.html", request=request)


@superadmin_router.get("/superadmin/tools", response_class=HTMLResponse)
async def superadmin_tools(
    request: Request,
    db: Session = Depends(get_db)
):
    """Gerenciar ferramentas OpenAI (SuperAdmin)"""
    return render_template("superadmin/tools.html", request=request)


@superadmin_router.get("/superadmin/tools/new", response_class=HTMLResponse)
async def superadmin_tools_new(
    request: Request,
    db: Session = Depends(get_db)
):
    """Criar nova ferramenta"""
    return render_template("superadmin/tool_form.html", request=request, tool_id=None)


@superadmin_router.get("/superadmin/tools/{tool_id}/edit", response_class=HTMLResponse)
async def superadmin_tools_edit(
    request: Request,
    tool_id: int,
    db: Session = Depends(get_db)
):
    """Editar ferramenta"""
    return render_template("superadmin/tool_form.html", request=request, tool_id=tool_id)

@superadmin_router.get("/superadmin/plans", response_class=HTMLResponse)
async def superadmin_plans(
    request: Request,
    db: Session = Depends(get_db)
):
    """Lista de planos"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/plans.html")

@superadmin_router.post("/superadmin/companies/{company_id}/status")
async def update_company_status(
    request: Request,
    company_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Atualiza status de uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    success = controller.update_company_status(company_id, status)
    
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao atualizar status")
    
    return RedirectResponse(url=f"/superadmin/companies/{company_id}", status_code=302)

@superadmin_router.get("/superadmin/plans", response_class=HTMLResponse)
async def superadmin_plans(
    request: Request,
    db: Session = Depends(get_db)
):
    """Lista de planos"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    plans = controller.get_plans_list()
    
    return render_template("superadmin/plans.html", plans=plans)

@superadmin_router.post("/superadmin/plans/create")
async def create_plan(
    request: Request,
    plan_name: str = Form(...),
    price: str = Form(...),
    currency: str = Form(default="BRL"),
    features: str = Form(default="{}"),
    db: Session = Depends(get_db)
):
    """Cria um novo plano"""
    # TODO: Verificar autenticação de superadmin
    import json
    
    try:
        plan_features = json.loads(features)
    except:
        plan_features = {}
    
    controller = SuperAdminController(db)
    success = controller.create_plan({
        "plan_name": plan_name,
        "price": price,
        "currency": currency,
        "plan_features": plan_features
    })
    
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao criar plano")
    
    return RedirectResponse(url="/superadmin/plans", status_code=302)

@superadmin_router.post("/superadmin/companies/{company_id}/assign-plan")
async def assign_plan_to_company(
    request: Request,
    company_id: int,
    plan_name: str = Form(...),
    duration_months: int = Form(default=1),
    db: Session = Depends(get_db)
):
    """Atribui um plano a uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    success = controller.assign_plan_to_company(company_id, plan_name, duration_months)
    
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao atribuir plano")
    
    return RedirectResponse(url=f"/superadmin/companies/{company_id}", status_code=302)

# ==================== API REST PARA EMPRESAS ====================

@superadmin_router.get("/api/superadmin/companies")
async def api_get_companies(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """API: Lista empresas com paginação"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    companies_data = controller.get_companies_list(page=page, per_page=per_page, status=status)
    return companies_data

@superadmin_router.get("/api/superadmin/companies/{company_id}")
async def api_get_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """API: Obtém detalhes de uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    company_details = controller.get_company_details(company_id)
    
    if not company_details:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    return company_details

@superadmin_router.post("/api/superadmin/companies")
async def api_create_company(
    company_data: dict,
    db: Session = Depends(get_db)
):
    """API: Cria uma nova empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.create_company(company_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.put("/api/superadmin/companies/{company_id}")
async def api_update_company(
    company_id: int,
    company_data: dict,
    db: Session = Depends(get_db)
):
    """API: Atualiza uma empresa existente"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.update_company(company_id, company_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.delete("/api/superadmin/companies/{company_id}")
async def api_delete_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """API: Exclui uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.delete_company(company_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = str(e)
        # Se for erro do banco, extrair informação relevante
        if hasattr(e, 'orig') and e.orig:
            error_detail = str(e.orig)
        elif hasattr(e, 'args') and e.args:
            error_detail = str(e.args[0]) if isinstance(e.args[0], str) else str(e)
        
        # Log detalhado
        print(f"❌ Erro ao excluir empresa {company_id} via API: {error_detail}")
        print(traceback.format_exc())
        
        raise HTTPException(status_code=500, detail=f"Erro interno: {error_detail}")

@superadmin_router.get("/api/superadmin/companies/{company_id}/payments")
async def get_company_payments(
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    API: Lista todos os pagamentos de uma empresa no Asaas
    """
    try:
        from app.models.saas_models import Company
        from app.services.asaas_service import asaas_service
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Buscar empresa
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Verificar se tem CPF/CNPJ
        if not company.cnpj:
            return {
                "success": True,
                "payments": [],
                "message": "CPF/CNPJ não cadastrado para esta empresa"
            }
        
        cpf_cnpj = company.cnpj
        logger.info(f"🔍 Buscando pagamentos para empresa {company_id} (CPF/CNPJ: {cpf_cnpj})")
        
        # Buscar cliente no Asaas pelo CPF/CNPJ
        customer = asaas_service.find_customer_by_cpf_cnpj(cpf_cnpj)
        
        if not customer or not customer.get("id"):
            logger.warning(f"⚠️ Cliente não encontrado no Asaas para CPF/CNPJ: {cpf_cnpj}")
            return {
                "success": True,
                "payments": [],
                "message": "Cliente não encontrado no Asaas"
            }
        
        customer_id = customer["id"]
        logger.info(f"✅ Cliente encontrado no Asaas: {customer_id}")
        
        # Buscar TODOS os pagamentos do cliente no Asaas
        payments = asaas_service.get_customer_payments(customer_id, limit=500)
        
        logger.info(f"📊 Total de {len(payments)} pagamentos encontrados")
        
        # Formatar pagamentos para o frontend
        formatted_payments = []
        for payment in payments:
            status = payment.get("status", "PENDING")
            formatted_payments.append({
                "id": payment.get("id"),
                "value": payment.get("value", 0),
                "status": status.lower(),
                "billingType": payment.get("billingType", ""),
                "dueDate": payment.get("dueDate"),
                "paymentDate": payment.get("paymentDate"),
                "description": payment.get("description", ""),
                "invoiceUrl": payment.get("invoiceUrl"),
                "created_at": payment.get("dateCreated") or payment.get("dueDate"),
                "originalStatus": status
            })
        
        # Ordenar por data mais recente primeiro
        formatted_payments.sort(key=lambda x: (
            x.get("paymentDate") or x.get("dueDate") or x.get("created_at") or ""
        ), reverse=True)
        
        return {
            "success": True,
            "payments": formatted_payments,
            "total": len(formatted_payments),
            "company_id": company_id,
            "company_name": company.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar pagamentos da empresa {company_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@superadmin_router.get("/api/superadmin/companies/{company_id}/subscription")
async def api_get_company_subscription(
    company_id: int,
    db: Session = Depends(get_db)
):
    """API: Busca assinatura ativa da empresa"""
    # TODO: Verificar autenticação de superadmin
    from app.models.saas_models import Subscription
    
    try:
        # Buscar assinatura ativa da empresa
        subscription = db.query(Subscription).filter(
            Subscription.company_id == company_id,
            Subscription.status == "active"
        ).first()
        
        if not subscription:
            return {"subscription": None, "plan_template_id": None}
        
        # Buscar o template do plano com o mesmo nome
        plan_template = db.query(Subscription).filter(
            Subscription.plan_name == subscription.plan_name,
            Subscription.status == "template"
        ).first()
        
        return {
            "subscription": {
                "id": subscription.id,
                "plan_name": subscription.plan_name,
                "price": subscription.price,
                "status": subscription.status
            },
            "plan_template_id": plan_template.id if plan_template else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ==================== API REST PARA PLANOS ====================

@superadmin_router.get("/api/superadmin/plans")
async def api_get_plans(db: Session = Depends(get_db)):
    """API: Lista todos os planos"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    return controller.get_plans_overview()

@superadmin_router.post("/api/superadmin/plans")
async def api_create_plan(
    request: Request,
    db: Session = Depends(get_db)
):
    """API: Cria um novo plano"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        plan_data = await request.json()
        result = controller.create_plan_template(plan_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.put("/api/superadmin/plans/{plan_id}")
async def api_update_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API: Atualiza um plano existente"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        plan_data = await request.json()
        result = controller.update_plan_template(plan_id, plan_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.delete("/api/superadmin/plans/{plan_id}")
async def api_delete_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """API: Exclui um plano"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.delete_plan_template(plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@superadmin_router.get("/superadmin/financial/revenue", response_class=HTMLResponse)
async def superadmin_financial_revenue(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de receitas - Lista todos os pagamentos do Asaas"""
    from app.views.template_renderer import render_template
    return render_template("superadmin/financial_revenue.html", request=request)


@superadmin_router.get("/api/superadmin/financial/revenue", response_model=Dict[str, Any])
async def api_get_all_payments(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    status: Optional[str] = None,
    billing_type: Optional[str] = None,
    company_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    API: Lista todos os pagamentos do Asaas de todas as empresas
    """
    try:
        from app.models.saas_models import Company, Subscription
        from app.services.asaas_service import asaas_service
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Buscar todas as empresas com assinatura Asaas
        companies_with_asaas = db.query(Company).join(Subscription).filter(
            Subscription.asaas_customer_id.isnot(None)
        ).all()
        
        all_payments = []
        companies_map = {}
        
        for company in companies_with_asaas:
            if not company.cnpj:
                continue
            
            # Buscar cliente no Asaas
            customer = asaas_service.find_customer_by_cpf_cnpj(company.cnpj)
            if not customer or not customer.get("id"):
                continue
            
            customer_id = customer["id"]
            companies_map[customer_id] = company
            
            # Buscar pagamentos do cliente
            try:
                payments = asaas_service.get_customer_payments(customer_id, limit=1000)
                for payment in payments:
                    payment["_company_id"] = company.id
                    payment["_company_name"] = company.name
                    payment["_customer_id"] = customer_id
                    all_payments.append(payment)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar pagamentos para empresa {company.id}: {e}")
        
        # Aplicar filtros
        filtered_payments = all_payments
        
        if status:
            filtered_payments = [p for p in filtered_payments if p.get("status", "").upper() == status.upper()]
        
        if billing_type:
            filtered_payments = [p for p in filtered_payments if p.get("billingType") == billing_type]
        
        if company_id:
            filtered_payments = [p for p in filtered_payments if p.get("_company_id") == company_id]
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                filtered_payments = [
                    p for p in filtered_payments 
                    if (p.get("paymentDate") or p.get("dueDate"))
                    and datetime.strptime((p.get("paymentDate") or p.get("dueDate"))[:10], "%Y-%m-%d") >= date_from_obj
                ]
            except Exception as e:
                logger.warning(f"⚠️ Erro ao filtrar por data inicial: {e}")
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                filtered_payments = [
                    p for p in filtered_payments 
                    if (p.get("paymentDate") or p.get("dueDate"))
                    and datetime.strptime((p.get("paymentDate") or p.get("dueDate"))[:10], "%Y-%m-%d") <= date_to_obj
                ]
            except Exception as e:
                logger.warning(f"⚠️ Erro ao filtrar por data final: {e}")
        
        # Ordenar por data mais recente
        filtered_payments.sort(key=lambda x: (
            x.get("paymentDate") or x.get("dueDate") or x.get("dateCreated") or ""
        ), reverse=True)
        
        # Paginação
        total = len(filtered_payments)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_payments = filtered_payments[start:end]
        
        # Formatar pagamentos
        formatted_payments = []
        for payment in paginated_payments:
            formatted_payments.append({
                "id": payment.get("id"),
                "company_id": payment.get("_company_id"),
                "company_name": payment.get("_company_name"),
                "value": payment.get("value", 0),
                "status": payment.get("status", "").lower(),
                "billingType": payment.get("billingType", ""),
                "dueDate": payment.get("dueDate"),
                "paymentDate": payment.get("paymentDate"),
                "description": payment.get("description", ""),
                "invoiceUrl": payment.get("invoiceUrl"),
                "created_at": payment.get("dateCreated") or payment.get("dueDate"),
            })
        
        return {
            "success": True,
            "payments": formatted_payments,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar pagamentos: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@superadmin_router.get("/api/superadmin/financial/companies", response_model=Dict[str, Any])
async def api_get_companies_for_filter(
    request: Request,
    db: Session = Depends(get_db)
):
    """API: Lista empresas para filtro"""
    try:
        from app.models.saas_models import Company, Subscription
        
        companies = db.query(Company).join(Subscription).filter(
            Subscription.asaas_customer_id.isnot(None)
        ).all()
        
        return {
            "success": True,
            "companies": [
                {"id": c.id, "name": c.name}
                for c in companies
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
