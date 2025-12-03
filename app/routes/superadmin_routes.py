"""
Rotas para SuperAdmin - Painel de administração do sistema
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Cookie, Query, Body, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import string

from app.config.database import get_db
from app.controllers.superadmin_controller import SuperAdminController
from app.controllers.support_controller import SupportController
from app.controllers.auth_controller import AuthController
from app.views.template_renderer import render_template
from app.models.saas_models import User, UserSession, Company, UserRole
from app.config.settings import settings

# Router para superadmin
superadmin_router = APIRouter()

def get_superadmin_user(request: Request, db: Session = Depends(get_db)) -> dict:
    """Obtém usuário superadmin da sessão"""
    from app.models.saas_models import SuperAdmin
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Primeiro, verificar se há cookie de sessão de superadmin
    superadmin_session = request.cookies.get("superadmin_session")
    superadmin_id = request.cookies.get("superadmin_id")
    
    logger.info(f"🔍 Verificando superadmin - session: {bool(superadmin_session)}, id: {superadmin_id}")
    
    if superadmin_session and superadmin_id:
        # Buscar superadmin diretamente na tabela SuperAdmin
        try:
            superadmin = db.query(SuperAdmin).filter(
                SuperAdmin.id == int(superadmin_id),
                SuperAdmin.is_active == True
            ).first()
            
            if superadmin:
                logger.info(f"✅ Superadmin autenticado via cookie: {superadmin.email}")
                # Retornar um dict compatível com o formato esperado
                return {
                    "id": superadmin.id,
                    "email": superadmin.email,
                    "first_name": superadmin.first_name,
                    "last_name": superadmin.last_name,
                    "role": "super_admin",  # Definir role como super_admin
                    "company_id": None,  # Superadmin não tem company_id
                    "company": None
                }
        except (ValueError, TypeError):
            pass
    
    # Fallback: tentar verificar via sessão normal de usuário
    try:
        result = AuthController().get_user_by_session(request.cookies.get("session_token"), db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Não autenticado")
        
        user = result.get("user", {})
        logger.info(f"✅ Usuário autenticado: {user.get('email')} (role: {user.get('role')})")
        
        # Verificar se é superadmin de duas formas:
        # 1. Se o role do usuário é super_admin
        # 2. Se existe um registro na tabela SuperAdmin com o mesmo email
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
        
        if is_superadmin:
            logger.info(f"✅ Acesso permitido para superadmin: {user.get('email')}")
            return user
    except HTTPException:
        # Se não conseguir autenticar via usuário normal, continuar para verificar erro
        pass
    
    # Se chegou aqui, não é superadmin
    logger.warning(f"❌ Acesso negado - não é superadmin. Path: {request.url.path}")
    raise HTTPException(status_code=403, detail="Acesso negado. Apenas superadmins podem acessar.")

def get_superadmin_session(request: Request, session_token: Optional[str] = Cookie(None)) -> Optional[dict]:
    """Verifica se o usuário está autenticado como superadmin (deprecated - usar get_superadmin_user)"""
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
        # Buscar assinatura ativa da empresa (ou trial)
        subscription = db.query(Subscription).filter(
            Subscription.company_id == company_id
        ).filter(
            (Subscription.status == "active") | (Subscription.is_trial == True)
        ).order_by(Subscription.created_at.desc()).first()
        
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
                "status": subscription.status,
                "is_trial": subscription.is_trial if subscription.is_trial is not None else False,
                "ends_at": subscription.ends_at.isoformat() if subscription.ends_at else None,
                "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None
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

@superadmin_router.get("/superadmin/documentation", response_class=HTMLResponse)
async def superadmin_documentation(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de documentação - Manuais do sistema e ferramentas do agente IA"""
    from pathlib import Path
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Caminhos dos diretórios de manuais
    # Tentar múltiplos caminhos possíveis
    import os
    
    possible_base_dirs = [
        Path("/app"),  # Docker/Produção (prioridade - código clonado do Git)
        Path(__file__).parent.parent.parent.resolve(),  # app/routes -> app -> raiz (desenvolvimento local)
        Path(os.getcwd()),  # Diretório de trabalho atual
        Path("."),  # Relativo
    ]
    
    # Também tentar dentro de public (se os manuais foram copiados)
    possible_manuais_dirs = []
    for base in possible_base_dirs:
        possible_manuais_dirs.append(base / "manuais")
        possible_manuais_dirs.append(base / "public" / "manuais")
    
    base_dir = None
    manuais_dir_found = None
    
    for manuais_test in possible_manuais_dirs:
        if manuais_test.exists() and manuais_test.is_dir():
            # Encontrar o base_dir correspondente
            if "public" in str(manuais_test):
                base_dir = manuais_test.parent.parent  # public/manuais -> public -> raiz
            else:
                base_dir = manuais_test.parent  # manuais -> raiz
            manuais_dir_found = manuais_test
            logger.info(f"✅ Manuais dir encontrado: {manuais_dir_found.resolve()}")
            logger.info(f"✅ Base dir: {base_dir.resolve()}")
            break
    
    if not base_dir or not manuais_dir_found:
        logger.error(f"❌ Não foi possível encontrar o diretório manuais. Tentados: {possible_manuais_dirs}")
        # Retornar página vazia mas funcional
        return render_template("superadmin/documentation.html", 
                             request=request,
                             manuais_gerais=[],
                             manuais_agente_ia=[],
                             error="Diretório de manuais não encontrado")
    
    manuais_dir = manuais_dir_found
    agente_ia_dir = manuais_dir / "agente_ia"
    
    # Debug: verificar caminhos
    logger.info(f"🔍 Manuais dir: {manuais_dir.resolve()}, exists: {manuais_dir.exists()}")
    logger.info(f"🔍 Agente IA dir: {agente_ia_dir.resolve()}, exists: {agente_ia_dir.exists()}")
    
    # Listar manuais gerais
    manuais_gerais = []
    if manuais_dir.exists() and manuais_dir.is_dir():
        try:
            files_found = list(manuais_dir.glob("*.md"))
            logger.info(f"📄 Arquivos .md encontrados em manuais/: {len(files_found)}")
            for file in sorted(files_found):
                # Excluir arquivos que não são manuais
                if file.name not in ["00_INDICE_GERAL.md"] and not file.name.startswith("img"):
                    manuais_gerais.append({
                        "nome": file.stem.replace("_", " ").title(),
                        "arquivo": file.name,
                        "caminho": str(file.relative_to(base_dir))
                    })
            logger.info(f"✅ Manuais gerais adicionados: {len(manuais_gerais)}")
        except Exception as e:
            logger.error(f"❌ Erro ao listar manuais gerais: {e}", exc_info=True)
    else:
        logger.warning(f"⚠️ Diretório manuais não existe ou não é um diretório: {manuais_dir.resolve()}")
    
    # Listar manuais de agente IA
    manuais_agente_ia = []
    if agente_ia_dir.exists() and agente_ia_dir.is_dir():
        try:
            files_found = list(agente_ia_dir.glob("*.md"))
            logger.info(f"📄 Arquivos .md encontrados em manuais/agente_ia/: {len(files_found)}")
            for file in sorted(files_found):
                # Excluir índices
                if file.name not in ["00_INDICE_FERRAMENTAS.md", "AJUSTES_FERRAMENTAS.md"]:
                    # Marcar PROMPT_INSTRUCOES_AGENTE.md como exemplo de configuração
                    is_example = file.name == "PROMPT_INSTRUCOES_AGENTE.md"
                    manuais_agente_ia.append({
                        "nome": file.stem.replace("_", " ").title(),
                        "arquivo": file.name,
                        "caminho": str(file.relative_to(base_dir)),
                        "is_example": is_example  # Flag para destacar como exemplo
                    })
            logger.info(f"✅ Manuais agente IA adicionados: {len(manuais_agente_ia)}")
        except Exception as e:
            logger.error(f"❌ Erro ao listar manuais agente IA: {e}", exc_info=True)
    else:
        logger.warning(f"⚠️ Diretório agente_ia não existe ou não é um diretório: {agente_ia_dir.resolve()}")
    
    # Debug: log final
    logger.info(f"📊 Resumo: {len(manuais_gerais)} manuais gerais, {len(manuais_agente_ia)} manuais agente IA")
    
    return render_template("superadmin/documentation.html", 
                         request=request,
                         manuais_gerais=manuais_gerais,
                         manuais_agente_ia=manuais_agente_ia)

@superadmin_router.get("/api/superadmin/documentation/debug")
async def debug_documentation():
    """Endpoint de debug para verificar caminhos dos manuais"""
    from pathlib import Path
    import os
    
    debug_info = {
        "current_working_dir": str(Path(os.getcwd())),
        "file_location": str(Path(__file__)),
        "base_calculated": str(Path(__file__).parent.parent.parent.resolve()),
        "manuais_paths": {}
    }
    
    possible_bases = [
        ("from_file", Path(__file__).parent.parent.parent.resolve()),
        ("from_cwd", Path(os.getcwd())),
        ("docker", Path("/app")),
    ]
    
    for name, base in possible_bases:
        manuais = base / "manuais"
        debug_info["manuais_paths"][name] = {
            "base": str(base),
            "manuais_path": str(manuais),
            "exists": manuais.exists(),
            "is_dir": manuais.is_dir() if manuais.exists() else False,
            "file_count": len(list(manuais.glob("*.md"))) if manuais.exists() else 0
        }
    
    return debug_info

@superadmin_router.get("/api/manual/{filename:path}")
async def view_manual(filename: str):
    """Visualiza um manual em formato Markdown renderizado como HTML"""
    from pathlib import Path
    from fastapi.responses import HTMLResponse
    import os
    
    try:
        import markdown
    except ImportError:
        raise HTTPException(status_code=500, detail="Biblioteca markdown não instalada. Execute: pip install markdown")
    
    # Tentar múltiplos caminhos
    possible_paths = [
        Path("/app") / "manuais" / filename,  # Docker
        Path("/app") / "public" / "manuais" / filename,  # Docker public
        Path(__file__).parent.parent.parent / "manuais" / filename,  # Local
        Path(__file__).parent.parent.parent / "public" / "manuais" / filename,  # Local public
        Path(os.getcwd()) / "manuais" / filename,  # CWD
        Path(os.getcwd()) / "public" / "manuais" / filename,  # CWD public
    ]
    
    manual_path = None
    for path in possible_paths:
        if path.exists() and path.is_file():
            manual_path = path
            break
    
    if not manual_path:
        raise HTTPException(status_code=404, detail=f"Manual não encontrado: {filename}")
    
    # Verificar segurança (deve estar em manuais ou public/manuais)
    path_str = str(manual_path.resolve())
    if "manuais" not in path_str or ".." in filename:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    content = manual_path.read_text(encoding="utf-8")
    
    # Converter Markdown para HTML
    try:
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    except Exception as e:
        # Se falhar, usar apenas o texto puro
        html_content = f"<pre>{content}</pre>"
    
    # Criar página HTML completa
    html_page = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{filename} - Documentação</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; background-color: #f8f9fa; }}
            .manual-container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .manual-header {{ border-bottom: 2px solid #007bff; padding-bottom: 15px; margin-bottom: 30px; }}
            pre {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
            pre code {{ background-color: transparent; padding: 0; }}
            table {{ width: 100%; margin: 20px 0; }}
            table th, table td {{ padding: 10px; border: 1px solid #dee2e6; }}
            table th {{ background-color: #007bff; color: white; }}
        </style>
    </head>
    <body>
        <div class="manual-container">
            <div class="manual-header">
                <h1><i class="bi bi-file-text"></i> {filename}</h1>
                <a href="/superadmin/documentation" class="btn btn-outline-primary btn-sm">
                    <i class="bi bi-arrow-left"></i> Voltar
                </a>
            </div>
            <div class="manual-content">
                {html_content}
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_page)

@superadmin_router.get("/api/manual/agente_ia/{filename:path}")
async def view_agente_ia_manual(filename: str):
    """Visualiza um manual de agente IA em formato Markdown renderizado como HTML"""
    from pathlib import Path
    from fastapi.responses import HTMLResponse
    import os
    
    try:
        import markdown
    except ImportError:
        raise HTTPException(status_code=500, detail="Biblioteca markdown não instalada. Execute: pip install markdown")
    
    # Tentar múltiplos caminhos
    possible_paths = [
        Path("/app") / "manuais" / "agente_ia" / filename,  # Docker
        Path("/app") / "public" / "manuais" / "agente_ia" / filename,  # Docker public
        Path(__file__).parent.parent.parent / "manuais" / "agente_ia" / filename,  # Local
        Path(__file__).parent.parent.parent / "public" / "manuais" / "agente_ia" / filename,  # Local public
        Path(os.getcwd()) / "manuais" / "agente_ia" / filename,  # CWD
        Path(os.getcwd()) / "public" / "manuais" / "agente_ia" / filename,  # CWD public
    ]
    
    manual_path = None
    for path in possible_paths:
        if path.exists() and path.is_file():
            manual_path = path
            break
    
    if not manual_path:
        raise HTTPException(status_code=404, detail=f"Manual não encontrado: {filename}")
    
    # Verificar segurança (deve estar em manuais/agente_ia ou public/manuais/agente_ia)
    path_str = str(manual_path.resolve())
    if "agente_ia" not in path_str or ".." in filename:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    content = manual_path.read_text(encoding="utf-8")
    
    # Converter Markdown para HTML
    try:
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    except Exception as e:
        # Se falhar, usar apenas o texto puro
        html_content = f"<pre>{content}</pre>"
    
    # Criar página HTML completa
    html_page = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{filename} - Documentação Agente IA</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; background-color: #f8f9fa; }}
            .manual-container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .manual-header {{ border-bottom: 2px solid #28a745; padding-bottom: 15px; margin-bottom: 30px; }}
            pre {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
            pre code {{ background-color: transparent; padding: 0; }}
            table {{ width: 100%; margin: 20px 0; }}
            table th, table td {{ padding: 10px; border: 1px solid #dee2e6; }}
            table th {{ background-color: #28a745; color: white; }}
        </style>
    </head>
    <body>
        <div class="manual-container">
            <div class="manual-header">
                <h1><i class="bi bi-robot"></i> {filename}</h1>
                <a href="/superadmin/documentation" class="btn btn-outline-success btn-sm">
                    <i class="bi bi-arrow-left"></i> Voltar
                </a>
            </div>
            <div class="manual-content">
                {html_content}
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_page)


# ==================== ROTAS DE TICKETS DE SUPORTE ====================

@superadmin_router.get("/superadmin/support/tickets", response_class=HTMLResponse)
async def superadmin_support_tickets(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de listagem de tickets de suporte (superadmin)"""
    # Verificar se é superadmin
    user_data = get_superadmin_user(request, db)
    
    return render_template("superadmin/support_tickets.html", user=user_data, request=request)


@superadmin_router.get("/superadmin/support/tickets/{ticket_id}", response_class=HTMLResponse)
async def superadmin_support_ticket_view(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de visualização de um ticket específico (superadmin)"""
    # Verificar se é superadmin
    user_data = get_superadmin_user(request, db)
    
    controller = SupportController(db)
    ticket_result = controller.get_ticket(ticket_id, company_id=None)  # None para superadmin
    
    if not ticket_result.get("success"):
        return RedirectResponse(url="/superadmin/support/tickets", status_code=302)
    
    return render_template(
        "superadmin/support_ticket_view.html",
        request=request,
        user=user_data,
        ticket=ticket_result.get("ticket")
    )


@superadmin_router.get("/api/superadmin/support/tickets", response_class=JSONResponse)
async def superadmin_list_tickets_api(
    request: Request,
    status: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """API para listar tickets de suporte de todas as empresas (superadmin)"""
    # Verificar se é superadmin
    try:
        user_data = get_superadmin_user(request, db)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    
    controller = SupportController(db)
    response = controller.list_all_tickets(
        company_id=company_id,
        status=status
    )
    
    return JSONResponse(content=response)


@superadmin_router.get("/api/superadmin/support/tickets/{ticket_id}", response_class=JSONResponse)
async def superadmin_get_ticket_api(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para obter detalhes de um ticket (superadmin)"""
    # Verificar se é superadmin
    try:
        user_data = get_superadmin_user(request, db)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    
    controller = SupportController(db)
    response = controller.get_ticket(ticket_id, company_id=None)  # None para superadmin
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=404,
            content=response
        )


@superadmin_router.post("/api/superadmin/support/tickets/{ticket_id}/messages", response_class=JSONResponse)
async def superadmin_add_message_api(
    ticket_id: int,
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db)
):
    """API para adicionar mensagem do suporte a um ticket (superadmin)"""
    # Verificar se é superadmin
    try:
        user_data = get_superadmin_user(request, db)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    
    # Superadmin não está na tabela users, então user_id deve ser None
    # O campo is_from_support=True já indica que é do suporte
    controller = SupportController(db)
    response = controller.add_message_to_ticket(
        ticket_id=ticket_id,
        company_id=None,  # None para superadmin
        user_id=None,  # None porque superadmin não está na tabela users
        message_content=message,
        is_from_support=True  # Sempre do suporte quando vem do superadmin
    )
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=400,
            content=response
        )


@superadmin_router.post("/api/superadmin/support/tickets/{ticket_id}/attachments", response_class=JSONResponse)
async def superadmin_upload_attachment_api(
    ticket_id: int,
    request: Request,
    file: UploadFile = File(...),
    message_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """API para fazer upload de anexo em um ticket (superadmin)"""
    # Verificar se é superadmin
    try:
        user_data = get_superadmin_user(request, db)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    
    # Superadmin não está na tabela users, então uploaded_by deve ser None
    # Ler conteúdo do arquivo
    file_content = await file.read()
    
    controller = SupportController(db)
    response = controller.upload_attachment(
        ticket_id=ticket_id,
        company_id=None,  # None para superadmin
        user_id=None,  # None porque superadmin não está na tabela users
        filename=file.filename,
        file_content=file_content,
        content_type=file.content_type or "application/octet-stream",
        message_id=message_id
    )
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=400,
            content=response
        )


@superadmin_router.patch("/api/superadmin/support/tickets/{ticket_id}/status", response_class=JSONResponse)
async def superadmin_update_ticket_status_api(
    ticket_id: int,
    request: Request,
    status_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para atualizar status de um ticket (superadmin)"""
    # Verificar se é superadmin
    try:
        user_data = get_superadmin_user(request, db)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    
    status = status_data.get("status")
    if not status:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Status não fornecido"}
        )
    
    controller = SupportController(db)
    response = controller.update_ticket_status(
        ticket_id=ticket_id,
        company_id=None,  # None para superadmin
        status=status
    )
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=400,
            content=response
        )


# ========== ROTAS DE PACOTES DE TOKENS ==========

@superadmin_router.get("/superadmin/token-packages", response_class=HTMLResponse)
async def superadmin_token_packages(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de gerenciamento de pacotes de tokens"""
    return render_template("superadmin/token_packages.html", request=request)

@superadmin_router.get("/api/superadmin/token-packages")
async def api_get_token_packages(
    active_only: bool = Query(False, description="Listar apenas pacotes ativos"),
    db: Session = Depends(get_db)
):
    """API: Lista pacotes de tokens"""
    controller = SuperAdminController(db)
    packages = controller.list_token_packages(active_only=active_only)
    return {"success": True, "packages": packages}

@superadmin_router.post("/api/superadmin/token-packages")
async def api_create_token_package(
    request: Request,
    db: Session = Depends(get_db)
):
    """API: Cria um novo pacote de tokens"""
    controller = SuperAdminController(db)
    
    try:
        package_data = await request.json()
        result = controller.create_token_package(package_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.put("/api/superadmin/token-packages/{package_id}")
async def api_update_token_package(
    package_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API: Atualiza um pacote de tokens"""
    controller = SuperAdminController(db)
    
    try:
        package_data = await request.json()
        result = controller.update_token_package(package_id, package_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.delete("/api/superadmin/token-packages/{package_id}")
async def api_delete_token_package(
    package_id: int,
    db: Session = Depends(get_db)
):
    """API: Deleta um pacote de tokens"""
    controller = SuperAdminController(db)
    
    try:
        result = controller.delete_token_package(package_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.get("/api/superadmin/support/tickets/{ticket_id}/attachments", response_class=JSONResponse)
async def superadmin_get_ticket_attachments_api(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para listar anexos de um ticket (superadmin)"""
    # Verificar se é superadmin
    try:
        user_data = get_superadmin_user(request, db)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    
    controller = SupportController(db)
    response = controller.get_ticket_attachments(
        ticket_id=ticket_id,
        company_id=None  # None para superadmin
    )
    
    if response.get("success"):
        return JSONResponse(content=response)
    else:
        return JSONResponse(
            status_code=404,
            content=response
        )

