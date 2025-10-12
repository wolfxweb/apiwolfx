"""
Rotas para monitoramento de catálogo do Mercado Livre
"""
from fastapi import APIRouter, Depends, Cookie, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers.catalog_monitoring_controller import CatalogMonitoringController
from app.services.saas_service import SAASService

router = APIRouter(prefix="/api/catalog-monitoring", tags=["Catalog Monitoring"])


def get_company_id(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> int:
    """Obtém company_id do usuário autenticado"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    saas_service = SAASService(db)
    session = saas_service.get_session_by_token(session_token)
    
    if not session or not session.user:
        raise HTTPException(status_code=401, detail="Sessão inválida")
    
    return session.user.company_id


@router.post("/activate")
async def activate_monitoring(
    catalog_product_id: str = Query(..., description="ID do produto no catálogo ML"),
    ml_product_id: Optional[int] = Query(None, description="ID do produto ML da empresa"),
    company_id: int = Depends(get_company_id),
    db: Session = Depends(get_db)
):
    """
    Ativa o monitoramento de um catálogo
    Executa a primeira coleta imediatamente
    """
    controller = CatalogMonitoringController(db)
    return controller.activate_monitoring(
        company_id=company_id,
        catalog_product_id=catalog_product_id,
        ml_product_id=ml_product_id
    )


@router.post("/deactivate")
async def deactivate_monitoring(
    catalog_product_id: str = Query(..., description="ID do produto no catálogo ML"),
    company_id: int = Depends(get_company_id),
    db: Session = Depends(get_db)
):
    """Desativa o monitoramento de um catálogo"""
    controller = CatalogMonitoringController(db)
    return controller.deactivate_monitoring(
        company_id=company_id,
        catalog_product_id=catalog_product_id
    )


@router.get("/status")
async def get_monitoring_status(
    catalog_product_id: str = Query(..., description="ID do produto no catálogo ML"),
    company_id: int = Depends(get_company_id),
    db: Session = Depends(get_db)
):
    """Busca o status do monitoramento de um catálogo"""
    controller = CatalogMonitoringController(db)
    return controller.get_monitoring_status(
        company_id=company_id,
        catalog_product_id=catalog_product_id
    )


@router.get("/latest")
async def get_latest_data(
    catalog_product_id: str = Query(..., description="ID do produto no catálogo ML"),
    company_id: int = Depends(get_company_id),
    db: Session = Depends(get_db)
):
    """Busca os dados mais recentes do catálogo (dados atuais)"""
    controller = CatalogMonitoringController(db)
    data = controller.get_latest_data(
        company_id=company_id,
        catalog_product_id=catalog_product_id
    )
    
    if not data:
        raise HTTPException(status_code=404, detail="Nenhum dado encontrado")
    
    return data


@router.get("/history")
async def get_history(
    catalog_product_id: str = Query(..., description="ID do produto no catálogo ML"),
    limit: int = Query(100, description="Número máximo de registros", ge=1, le=1000),
    company_id: int = Depends(get_company_id),
    db: Session = Depends(get_db)
):
    """Busca o histórico completo de monitoramento de um catálogo"""
    controller = CatalogMonitoringController(db)
    return controller.get_history(
        company_id=company_id,
        catalog_product_id=catalog_product_id,
        limit=limit
    )

