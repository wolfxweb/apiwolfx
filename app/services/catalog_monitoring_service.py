"""
Serviço de monitoramento de catálogo do Mercado Livre
Coleta dados dos participantes do catálogo e armazena histórico
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import statistics

from app.models.saas_models import (
    MLCatalogMonitoring,
    MLCatalogHistory,
    CatalogParticipant,
    MLProduct,
    Company
)

logger = logging.getLogger(__name__)


class CatalogMonitoringService:
    """Serviço para monitoramento automático de catálogos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def collect_catalog_data_for_all_active(self):
        """
        Coleta dados de todos os catálogos ativos
        Chamado pelo BackgroundScheduler a cada 12 horas
        """
        logger.info("🔄 Iniciando coleta de dados de catálogos ativos...")
        
        # Buscar todos os monitoramentos ativos
        active_monitorings = self.db.query(MLCatalogMonitoring).filter(
            MLCatalogMonitoring.is_active == True
        ).all()
        
        if not active_monitorings:
            logger.info("ℹ️  Nenhum catálogo ativo para monitorar")
            return
        
        logger.info(f"📊 Encontrados {len(active_monitorings)} catálogos ativos para monitorar")
        
        success_count = 0
        error_count = 0
        
        for monitoring in active_monitorings:
            try:
                self.collect_catalog_data(monitoring)
                success_count += 1
                logger.info(f"✅ Catálogo {monitoring.catalog_product_id} (Company {monitoring.company_id}) coletado")
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Erro ao coletar catálogo {monitoring.catalog_product_id}: {str(e)}")
        
        logger.info(f"✅ Coleta finalizada: {success_count} sucessos, {error_count} erros")
    
    def collect_catalog_data(self, monitoring: MLCatalogMonitoring):
        """
        Coleta dados de um catálogo específico e salva no histórico
        """
        catalog_product_id = monitoring.catalog_product_id
        company_id = monitoring.company_id
        
        logger.info(f"🔍 Coletando dados do catálogo {catalog_product_id} para company {company_id}")
        
        # Buscar todos os participantes do catálogo
        participants = self.db.query(CatalogParticipant).filter(
            and_(
                CatalogParticipant.catalog_product_id == catalog_product_id,
                CatalogParticipant.company_id == company_id
            )
        ).all()
        
        if not participants:
            logger.warning(f"⚠️  Nenhum participante encontrado para catálogo {catalog_product_id}")
            return
        
        # Calcular estatísticas
        prices = [p.price for p in participants if p.price]
        available_quantities = [p.available_quantity for p in participants if p.available_quantity]
        sold_quantities = [p.sold_quantity for p in participants if p.sold_quantity]
        
        # Encontrar vencedor da buy box
        buy_box_winner = next((p for p in participants if p.buy_box_winner), None)
        
        # Encontrar produto da empresa (se existir)
        company_product = None
        company_position = None
        company_price = None
        company_has_buy_box = False
        
        if monitoring.ml_product_id:
            ml_product = self.db.query(MLProduct).filter(
                MLProduct.id == monitoring.ml_product_id
            ).first()
            
            if ml_product:
                # Procurar o produto da empresa nos participantes
                for idx, participant in enumerate(participants, 1):
                    if participant.ml_item_id == ml_product.ml_item_id:
                        company_product = participant
                        company_position = idx
                        company_price = participant.price
                        company_has_buy_box = participant.buy_box_winner
                        break
        
        # Preparar snapshot dos participantes
        participants_snapshot = []
        for idx, p in enumerate(participants, 1):
            participants_snapshot.append({
                "position": idx,
                "ml_item_id": p.ml_item_id,
                "seller_id": p.seller_id,
                "seller_nickname": p.seller_nickname,
                "price": p.price,
                "available_quantity": p.available_quantity,
                "sold_quantity": p.sold_quantity,
                "buy_box_winner": p.buy_box_winner,
                "status": p.status,
                "condition": p.condition,
                "shipping_free": p.shipping_free,
                "seller_reputation_level": p.seller_reputation_level,
                "seller_power_seller": p.seller_power_seller
            })
        
        # Criar registro de histórico
        history = MLCatalogHistory(
            company_id=company_id,
            catalog_product_id=catalog_product_id,
            ml_product_id=monitoring.ml_product_id,
            monitoring_id=monitoring.id,
            
            # Dados do catálogo
            total_participants=len(participants),
            buy_box_winner_id=buy_box_winner.seller_id if buy_box_winner else None,
            buy_box_winner_price=buy_box_winner.price if buy_box_winner else None,
            
            # Posição da empresa
            company_position=company_position,
            company_price=company_price,
            company_has_buy_box=company_has_buy_box,
            
            # Estatísticas de preços
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
            avg_price=int(statistics.mean(prices)) if prices else None,
            median_price=int(statistics.median(prices)) if prices else None,
            
            # Estatísticas de quantidade
            total_available_quantity=sum(available_quantities) if available_quantities else 0,
            total_sold_quantity=sum(sold_quantities) if sold_quantities else 0,
            
            # Snapshot completo
            participants_snapshot=participants_snapshot,
            
            collected_at=datetime.now()
        )
        
        self.db.add(history)
        
        # Atualizar last_check_at no monitoramento
        monitoring.last_check_at = datetime.now()
        
        self.db.commit()
        
        logger.info(f"💾 Histórico salvo: {len(participants)} participantes, "
                   f"Posição empresa: {company_position or 'N/A'}, "
                   f"Buy Box: {'SIM' if company_has_buy_box else 'NÃO'}")
    
    def activate_monitoring(self, company_id: int, catalog_product_id: str, 
                          ml_product_id: Optional[int] = None) -> MLCatalogMonitoring:
        """
        Ativa o monitoramento para um catálogo específico
        Executa a primeira coleta imediatamente
        """
        # Verificar se já existe um monitoramento
        existing = self.db.query(MLCatalogMonitoring).filter(
            and_(
                MLCatalogMonitoring.company_id == company_id,
                MLCatalogMonitoring.catalog_product_id == catalog_product_id
            )
        ).first()
        
        if existing:
            if existing.is_active:
                logger.info(f"ℹ️  Monitoramento já está ativo para catálogo {catalog_product_id}")
                return existing
            else:
                # Reativar
                existing.is_active = True
                existing.activated_at = datetime.now()
                existing.deactivated_at = None
                self.db.commit()
                monitoring = existing
                logger.info(f"♻️  Monitoramento reativado para catálogo {catalog_product_id}")
        else:
            # Criar novo
            monitoring = MLCatalogMonitoring(
                company_id=company_id,
                catalog_product_id=catalog_product_id,
                ml_product_id=ml_product_id,
                is_active=True,
                activated_at=datetime.now()
            )
            self.db.add(monitoring)
            self.db.commit()
            logger.info(f"✅ Novo monitoramento criado para catálogo {catalog_product_id}")
        
        # Executar primeira coleta imediatamente
        try:
            self.collect_catalog_data(monitoring)
            logger.info(f"🎯 Primeira coleta executada com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro na primeira coleta: {str(e)}")
        
        return monitoring
    
    def deactivate_monitoring(self, company_id: int, catalog_product_id: str):
        """Desativa o monitoramento para um catálogo"""
        monitoring = self.db.query(MLCatalogMonitoring).filter(
            and_(
                MLCatalogMonitoring.company_id == company_id,
                MLCatalogMonitoring.catalog_product_id == catalog_product_id,
                MLCatalogMonitoring.is_active == True
            )
        ).first()
        
        if monitoring:
            monitoring.is_active = False
            monitoring.deactivated_at = datetime.now()
            self.db.commit()
            logger.info(f"🔴 Monitoramento desativado para catálogo {catalog_product_id}")
            return True
        
        return False
    
    def get_catalog_history(self, company_id: int, catalog_product_id: str, 
                          limit: int = 100) -> List[MLCatalogHistory]:
        """Busca o histórico de um catálogo"""
        return self.db.query(MLCatalogHistory).filter(
            and_(
                MLCatalogHistory.company_id == company_id,
                MLCatalogHistory.catalog_product_id == catalog_product_id
            )
        ).order_by(MLCatalogHistory.collected_at.desc()).limit(limit).all()
    
    def get_latest_catalog_data(self, company_id: int, catalog_product_id: str) -> Optional[MLCatalogHistory]:
        """Busca os dados mais recentes de um catálogo"""
        return self.db.query(MLCatalogHistory).filter(
            and_(
                MLCatalogHistory.company_id == company_id,
                MLCatalogHistory.catalog_product_id == catalog_product_id
            )
        ).order_by(MLCatalogHistory.collected_at.desc()).first()

