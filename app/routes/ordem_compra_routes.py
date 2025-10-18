"""
Rotas para Ordens de Compra
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.ordem_compra_controller import OrdemCompraController
from app.controllers.auth_controller import AuthController
from app.views.template_renderer import render_template
from app.models.saas_models import OrdemCompra, OrdemCompraItem, Fornecedor

logger = logging.getLogger(__name__)

ordem_compra_router = APIRouter()
ordem_compra_controller = OrdemCompraController()
auth_controller = AuthController()

def get_company_id_from_user(user_data: dict) -> int:
    """Extrair company_id dos dados do usuário"""
    return user_data.get("company_id")

# Rotas HTML
@ordem_compra_router.get("/ordem-compra", response_class=HTMLResponse)
async def ordem_compra_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de ordens de compra"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    return render_template("ordem_compra.html", user=user_data)

@ordem_compra_router.get("/ordem-compra/nova", response_class=HTMLResponse)
async def nova_ordem_compra_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de nova ordem de compra"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    return render_template("nova_ordem_compra.html", user=user_data)

@ordem_compra_router.get("/ordem-compra/editar/{ordem_id}", response_class=HTMLResponse)
async def editar_ordem_compra_page(
    ordem_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de edição de ordem de compra"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Buscar dados da ordem
    ordem = db.query(OrdemCompra).filter(
        OrdemCompra.id == ordem_id,
        OrdemCompra.company_id == company_id
    ).first()
    
    if not ordem:
        return RedirectResponse(url="/ordem-compra", status_code=302)
    
    # Buscar itens da ordem
    itens = db.query(OrdemCompraItem).filter(
        OrdemCompraItem.ordem_compra_id == ordem_id
    ).all()
    
    # Preparar dados da ordem
    ordem_data = {
        "id": ordem.id,
        "numero_ordem": ordem.numero_ordem,
        "data_ordem": ordem.data_ordem.isoformat() if ordem.data_ordem else None,
        "data_entrega_prevista": ordem.data_entrega_prevista.isoformat() if ordem.data_entrega_prevista else None,
        "status": ordem.status,
        "valor_total": float(ordem.valor_total or 0),
        "desconto": float(ordem.desconto or 0),
        "valor_final": float(ordem.valor_final or 0),
        "moeda": ordem.moeda,
        "cotacao_moeda": float(ordem.cotacao_moeda or 1.0),
        "tipo_ordem": ordem.tipo_ordem,
        "comissao_agente": float(ordem.comissao_agente or 0),
        "percentual_comissao": float(ordem.percentual_comissao or 0),
        "valor_transporte": float(ordem.valor_transporte or 0),
        "percentual_importacao": float(ordem.percentual_importacao or 0),
        "taxas_adicionais": float(ordem.taxas_adicionais or 0),
        "valor_impostos": float(ordem.valor_impostos or 0),
        "fornecedor_id": ordem.fornecedor_id,
        "fornecedor_nome": ordem.fornecedor.nome if ordem.fornecedor else None,
        "condicoes_pagamento": ordem.condicoes_pagamento,
        "prazo_entrega": ordem.prazo_entrega,
        "observacoes": ordem.observacoes,
        "itens": [
            {
                "id": item.id,
                "produto_nome": item.produto_nome,
                "produto_descricao": item.produto_descricao,
                "produto_codigo": item.produto_codigo,
                "produto_imagem": item.produto_imagem,
                "descricao_fornecedor": item.descricao_fornecedor,
                "quantidade": float(item.quantidade),
                "valor_unitario": float(item.valor_unitario),
                "valor_total": float(item.valor_total),
                "url": item.url,
                "observacoes": item.observacoes
            }
            for item in itens
        ]
    }
    
    # Log para debug
    logger.info(f"Dados da ordem carregados: {ordem_data}")
    logger.info(f"Número de itens: {len(ordem_data['itens'])}")
    
    return render_template("nova_ordem_compra.html", user=user_data, ordem_data=ordem_data, is_editing=True)

# Rotas API
@ordem_compra_router.get("/api/ordem-compra")
async def get_ordens_compra(
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar ordens de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    ordens = ordem_compra_controller.get_ordens_compra(company_id, db, status, search, date_from, date_to)
    
    return {
        "success": True,
        "ordens": ordens,
        "total": len(ordens)
    }

@ordem_compra_router.get("/api/ordem-compra/{ordem_id}")
async def get_ordem_compra(
    ordem_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar ordem de compra por ID"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    ordem = ordem_compra_controller.get_ordem_compra_by_id(ordem_id, company_id, db)
    
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de compra não encontrada")
    
    return {
        "success": True,
        "ordem": ordem
    }

@ordem_compra_router.post("/api/ordem-compra")
async def create_ordem_compra(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    
    # Validações básicas
    if not body.get('numero_ordem') and not body.get('itens'):
        raise HTTPException(status_code=400, detail="Número da ordem ou itens são obrigatórios")
    
    result = ordem_compra_controller.create_ordem_compra(body, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao criar ordem de compra"))
    
    return result

@ordem_compra_router.put("/api/ordem-compra/{ordem_id}")
async def update_ordem_compra(
    ordem_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    
    result = ordem_compra_controller.update_ordem_compra(ordem_id, body, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao atualizar ordem de compra"))
    
    return result

@ordem_compra_router.delete("/api/ordem-compra/{ordem_id}")
async def delete_ordem_compra(
    ordem_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para deletar ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    result = ordem_compra_controller.delete_ordem_compra(ordem_id, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao deletar ordem de compra"))
    
    return result

@ordem_compra_router.patch("/api/ordem-compra/{ordem_id}/status")
async def update_status_ordem(
    ordem_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para alterar status da ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    status = body.get("status")
    
    if not status:
        raise HTTPException(status_code=400, detail="Status é obrigatório")
    
    result = ordem_compra_controller.update_status_ordem(ordem_id, status, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao alterar status da ordem"))
    
    return result

# Rotas para gerenciar links externos
@ordem_compra_router.get("/api/ordem-compra/{ordem_id}/links")
async def get_ordem_compra_links(
    ordem_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar links externos de uma ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    links = ordem_compra_controller.get_ordem_compra_links(ordem_id, company_id, db)
    
    return {"success": True, "links": links}

@ordem_compra_router.post("/api/ordem-compra/{ordem_id}/links")
async def add_ordem_compra_link(
    ordem_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para adicionar link externo a uma ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    
    result = ordem_compra_controller.add_ordem_compra_link(ordem_id, company_id, body, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao adicionar link"))
    
    return result

@ordem_compra_router.put("/api/ordem-compra/links/{link_id}")
async def update_ordem_compra_link(
    link_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar link externo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    
    result = ordem_compra_controller.update_ordem_compra_link(link_id, company_id, body, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao atualizar link"))
    
    return result

@ordem_compra_router.delete("/api/ordem-compra/links/{link_id}")
async def delete_ordem_compra_link(
    link_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para deletar link externo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    result = ordem_compra_controller.delete_ordem_compra_link(link_id, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao deletar link"))
    
    return result
