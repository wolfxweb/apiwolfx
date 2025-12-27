from fastapi import APIRouter, Depends, Request, Cookie, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, validator
import logging
import csv
import io
import json
from datetime import datetime

from app.config.database import get_db
from app.controllers.ml_orders_controller import MLOrdersController
from app.controllers.auth_controller import AuthController

ml_orders_router = APIRouter()

class InternalStatusPayload(BaseModel):
    status: Optional[str] = None

    @validator("status")
    def validate_status(cls, value):
        allowed = {"aguardando_processamento", "separacao", "expedicao", "pronto_envio", "enviado"}
        if value is not None and value not in allowed:
            raise ValueError("Status interno inválido.")
        return value

@ml_orders_router.get("/orders", response_class=HTMLResponse)
async def orders_list(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Lista de pedidos do Mercado Libre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("ml_orders.html", user=user_data)

@ml_orders_router.get("/orders/{ml_order_id}", response_class=HTMLResponse)
async def order_details_page(
    ml_order_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de detalhes de um pedido específico"""
    try:
        if not session_token:
            return RedirectResponse(url="/auth/login", status_code=302)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return RedirectResponse(url="/auth/login", status_code=302)
        
        # Verificar se plano está inativo e redirecionar para profile
        if result.get("should_redirect_to_profile"):
            return RedirectResponse(url="/auth/profile", status_code=302)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar o pedido pelo ml_order_id primeiro
        from app.models.saas_models import MLOrder
        order = db.query(MLOrder).filter(
            MLOrder.ml_order_id == ml_order_id,
            MLOrder.company_id == company_id
        ).first()
        
        if not order:
            from app.views.template_renderer import render_template
            return render_template("error.html", error_message="Pedido não encontrado", back_url="/ml/orders")
        
        # Buscar detalhes do pedido usando o ID interno
        controller = MLOrdersController(db)
        order_details = controller.get_order_details(company_id, order.id)
        
        if not order_details.get("success"):
            from app.views.template_renderer import render_template
            return render_template("error.html", error_message=order_details.get("error", "Pedido não encontrado"), back_url="/ml/orders")
        
        from app.views.template_renderer import render_template
        return render_template("ml_order_details.html", request=request, user=user_data, order=order_details.get("order"))
        
    except Exception as e:
        logging.error(f"Erro na página de detalhes do pedido: {e}")
        from app.views.template_renderer import render_template
        return render_template("error.html", error_message="Erro ao carregar detalhes do pedido", back_url="/ml/orders")

@ml_orders_router.get("/api/orders")
async def get_orders_api(
    ml_account_id: Optional[int] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    shipping_status_filter: Optional[str] = Query(None),
    logistic_filter: Optional[str] = Query(None),
    internal_status_filter: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    buffering_date: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar orders"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        data = controller.get_orders_list(
            company_id=company_id,
            ml_account_id=ml_account_id,
            limit=limit,
            offset=offset,
            shipping_status_filter=shipping_status_filter,
            logistic_filter=logistic_filter,
            internal_status_filter=internal_status_filter,
            date_from=date_from,
            date_to=date_to,
            buffering_date=buffering_date,
            search_query=search_query
        )
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/{order_id}/internal-status")
async def set_internal_status_api(
    order_id: str,
    payload: InternalStatusPayload,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Define o status interno de processamento de um pedido"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)

        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)

        user_data = result["user"]
        company_id = user_data["company"]["id"]
        user_id = user_data.get("id")

        controller = MLOrdersController(db)
        update_result = controller.set_internal_status(
            company_id=company_id,
            order_identifier=order_id,
            status=payload.status,
            user_id=user_id
        )

        status_code = 200 if update_result.get("success") else 400
        return JSONResponse(content=update_result, status_code=status_code)

    except ValueError as ve:
        return JSONResponse(content={"success": False, "error": str(ve)}, status_code=400)
    except Exception as e:
        logging.error(f"Erro ao atualizar status interno do pedido {order_id}: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/sync")
async def sync_orders_api(
    background_tasks: BackgroundTasks,
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    API para sincronizar orders da API do Mercado Libre (em background)
    
    Retorna imediatamente e processa em background para evitar timeout do ngrok
    """
    try:
        print(f"🔍 SYNC ENDPOINT: Recebeu requisição")
        print(f"   session_token: {session_token[:20] if session_token else 'None'}...")
        
        if not session_token:
            print("❌ Sem session_token")
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            print(f"❌ Sessão inválida: {result.get('error')}")
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        print(f"✅ Usuário autenticado: company_id={company_id}")
        print(f"🚀 Iniciando sincronização em background...")
        
        # Adicionar tarefa em background
        from app.config.database import SessionLocal
        
        def sync_in_background():
            """Executa sincronização em background"""
            db_bg = SessionLocal()
            try:
                controller = MLOrdersController(db_bg)
                result = controller.sync_orders(company_id=company_id, ml_account_id=ml_account_id, is_full_import=False)
                print(f"✅ BACKGROUND SYNC CONCLUÍDA: {result.get('total_saved', 0)} novos, {result.get('total_updated', 0)} atualizados")
            except Exception as e:
                print(f"❌ BACKGROUND SYNC ERRO: {e}")
            finally:
                db_bg.close()
        
        background_tasks.add_task(sync_in_background)
        
        # Retornar imediatamente
        response_data = {
            "success": True,
            "message": "Sincronização iniciada em background. Aguarde alguns minutos e atualize a página.",
            "status": "processing"
        }
        
        print(f"✅ Retornando resposta imediata")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint sync orders: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/import")
async def import_orders_api(
    days: Optional[int] = Query(30, ge=1, le=30),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para importar orders da API do Mercado Libre com limite de dias (máximo 30)"""
    try:
        logging.info(f"Iniciando importação - days: {days}, date_from: {date_from}, date_to: {date_to}, ml_account_id: {ml_account_id}")
        
        if not session_token:
            logging.warning("Sessão não encontrada")
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            logging.warning(f"Erro de autenticação: {result.get('error')}")
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        user_id = user_data["id"]
        logging.info(f"Usuário autenticado - company_id: {company_id}, user_id: {user_id}")
        
        # Se não foram fornecidas datas, calcular baseado nos dias
        if not date_from or not date_to:
            from datetime import datetime, timedelta
            date_to_obj = datetime.now()
            date_from_obj = date_to_obj - timedelta(days=days)
            date_from = date_from_obj.strftime('%Y-%m-%d')
            date_to = date_to_obj.strftime('%Y-%m-%d')
        
        controller = MLOrdersController(db)
        logging.info(f"Iniciando sync_orders com período: {date_from} a {date_to}")
        result = controller.sync_orders(
            company_id=company_id, 
            ml_account_id=ml_account_id, 
            is_full_import=True,
            date_from=date_from,
            date_to=date_to,
            user_id=user_id  # Passar user_id para obter token via TokenManager
        )
        logging.info(f"Resultado do sync_orders: {result}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint import orders: {e}", exc_info=True)
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/summary")
async def get_orders_summary_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar resumo de orders"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.get_orders_summary(company_id=company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint orders summary: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/delete")
async def delete_orders_api(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para remover pedidos selecionados"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Obter dados do corpo da requisição
        body = await request.json()
        order_ids = body.get("order_ids", [])
        
        if not order_ids:
            return JSONResponse(content={
                "success": False,
                "error": "Nenhum pedido selecionado"
            }, status_code=400)
        
        controller = MLOrdersController(db)
        result = controller.delete_orders(company_id=company_id, order_ids=order_ids)
        
        if result.get("success"):
            return JSONResponse(content=result)
        else:
            return JSONResponse(content=result, status_code=400)
        
    except Exception as e:
        logging.error(f"Erro no endpoint delete orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/delete-all")
async def delete_all_orders_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para remover todos os pedidos da empresa"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.delete_all_orders(company_id=company_id)
        
        if result.get("success"):
            return JSONResponse(content=result)
        else:
            return JSONResponse(content=result, status_code=400)
        
    except Exception as e:
        logging.error(f"Erro no endpoint delete all orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/count")
async def count_orders_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para verificar total de pedidos disponíveis no ML"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.count_available_orders(company_id=company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint count orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/import-batch")
async def import_batch_orders_api(
    offset: int = Query(0),
    limit: int = Query(50),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para importar um lote específico de pedidos"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.import_orders_batch(
            company_id=company_id,
            offset=offset,
            limit=limit
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint import batch: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/import-background")
async def start_background_import_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Inicia importação de todos os pedidos em background"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar conta ML ativa
        from app.models.saas_models import MLAccount, MLAccountStatus
        account = db.query(MLAccount).filter(
            MLAccount.company_id == company_id,
            MLAccount.status == MLAccountStatus.ACTIVE
        ).first()
        
        if not account:
            return JSONResponse(content={
                "success": False,
                "error": "Nenhuma conta ML ativa encontrada"
            }, status_code=400)
        
        # Contar pedidos a importar
        controller = MLOrdersController(db)
        count_result = controller.count_available_orders(company_id)
        
        if not count_result.get("success"):
            return JSONResponse(content=count_result, status_code=400)
        
        total_orders = count_result.get("remaining", 0)
        
        if total_orders == 0:
            return JSONResponse(content={
                "success": False,
                "error": "Nenhum pedido novo para importar"
            }, status_code=400)
        
        # Iniciar job em background
        from app.services.background_import_service import background_import_service
        from app.config.database import DATABASE_URL
        db_url = DATABASE_URL
        
        job_id = background_import_service.start_import_job(
            company_id=company_id,
            ml_account_id=account.id,
            total_orders=total_orders,
            db_url=db_url
        )
        
        return JSONResponse(content={
            "success": True,
            "job_id": job_id,
            "message": f"Importação iniciada em background. Total: {total_orders} pedidos"
        })
        
    except Exception as e:
        logging.error(f"Erro ao iniciar importação em background: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/import-status/{job_id}")
async def get_import_status_api(
    job_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Verifica status de um job de importação"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        # Buscar status do job
        from app.services.background_import_service import background_import_service
        job_status = background_import_service.get_job_status(job_id)
        
        if not job_status:
            return JSONResponse(content={
                "success": False,
                "error": "Job não encontrado"
            }, status_code=404)
        
        return JSONResponse(content={
            "success": True,
            "job": job_status
        })
        
    except Exception as e:
        logging.error(f"Erro ao verificar status do job: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/import-cancel/{job_id}")
async def cancel_import_api(
    job_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Cancela um job de importação em execução"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        # Cancelar job
        from app.services.background_import_service import background_import_service
        cancelled = background_import_service.cancel_job(job_id)
        
        if cancelled:
            return JSONResponse(content={
                "success": True,
                "message": "Job cancelado com sucesso"
            })
        else:
            return JSONResponse(content={
                "success": False,
                "error": "Job não encontrado"
            }, status_code=404)
        
    except Exception as e:
        logging.error(f"Erro ao cancelar job: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

# IMPORTANTE: Esta rota deve ficar por ÚLTIMO pois usa parâmetro dinâmico {order_id}
@ml_orders_router.get("/api/orders/{order_id}")
async def get_order_details_api(
    order_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar detalhes de uma order específica"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.get_order_details(company_id=company_id, order_id=order_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint order details: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)
