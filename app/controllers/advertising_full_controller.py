"""Controller completo para gestão de publicidade"""
from sqlalchemy.orm import Session
from typing import Optional
from app.services.ml_campaign_service import MLCampaignService
from app.services.ml_product_ads_service import MLProductAdsService
from app.services.token_manager import TokenManager
from app.services.campaign_sync_service import CampaignSyncService
from app.models.saas_models import MLAccount, UserMLAccount, Token, User
import logging

logger = logging.getLogger(__name__)

class AdvertisingFullController:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_service = MLCampaignService(db)
        self.ads_service = MLProductAdsService(db)
        self.token_manager = TokenManager(db)
        self.sync_service = CampaignSyncService(db)
    
    def _get_advertiser_id(self, access_token: str) -> Optional[int]:
        """Busca advertiser_id da API do Mercado Livre"""
        logger.info(f"🚀 INICIANDO _get_advertiser_id() - Token: {access_token[:20]}...")
        try:
            import requests
            url = "https://api.mercadolibre.com/advertising/advertisers"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Api-Version": "1"
            }
            params = {"product_id": "PADS"}
            
            logger.info(f"🔎 Chamando API: {url} com product_id=PADS")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            logger.info(f"📡 Status da resposta: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"📦 Resposta da API: {data}")
                advertisers = data.get("advertisers", [])
                
                if advertisers:
                    advertiser_id = advertisers[0].get("advertiser_id")
                    logger.info(f"✅ Advertiser ID encontrado: {advertiser_id}")
                    return advertiser_id
                else:
                    logger.warning(f"⚠️ Nenhum advertiser retornado pela API")
            else:
                logger.error(f"❌ Erro ao buscar advertiser: {response.status_code} - {response.text[:200]}")
            
            return None
                        
        except Exception as e:
            logger.error(f"❌ Erro ao buscar advertiser_id: {e}", exc_info=True)
            return None
    
    def get_campaigns(self, company_id: int):
        """Lista campanhas da empresa - BUSCA LOCAL"""
        try:
            logger.info(f"📂 Buscando campanhas locais - company_id: {company_id}")
            return self.sync_service.get_local_campaigns(company_id)
        except Exception as e:
            logger.error(f"❌ ERRO: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def sync_campaigns(self, company_id: int):
        """Sincroniza campanhas do ML para o banco local"""
        try:
            logger.info(f"🔄 Sincronizando campanhas - company_id: {company_id}")
            return self.sync_service.sync_campaigns_for_company(company_id)
        except Exception as e:
            logger.error(f"❌ ERRO: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def create_campaign(self, company_id: int, campaign_data: dict):
        """Cria nova campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            # Obter token válido com renovação automática
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            campaign = self.campaign_service.create_campaign(
                account.site_id, advertiser_id, access_token, campaign_data
            )
            
            return {"success": True, "campaign": campaign}
        except Exception as e:
            logger.error(f"Erro ao criar campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_campaign(self, company_id: int, campaign_id: int, updates: dict):
        """Atualiza campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            # Obter token válido com renovação automática
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            result = self.campaign_service.update_campaign(
                account.site_id, advertiser_id, campaign_id, access_token, updates
            )
            
            return {"success": True, "campaign": result}
        except Exception as e:
            logger.error(f"Erro ao atualizar campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_campaign(self, company_id: int, campaign_id: int):
        """Deleta campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            # Obter token válido com renovação automática
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            result = self.campaign_service.delete_campaign(
                account.site_id, advertiser_id, campaign_id, access_token
            )
            
            return {"success": result}
        except Exception as e:
            logger.error(f"Erro ao deletar campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_metrics_summary(self, company_id: int, date_from: str = None, date_to: str = None, status: str = None):
        """Busca métricas consolidadas de todas as campanhas sincronizadas (com filtro de período e status)"""
        try:
            from app.models.advertising_models import MLCampaign, MLCampaignMetrics
            from sqlalchemy import func
            from datetime import datetime, timedelta
            
            # Se não forneceu datas, usar últimos 30 dias por padrão
            if not date_to:
                date_to = datetime.now().date()
            else:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            
            if not date_from:
                date_from = date_to - timedelta(days=30)
            else:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            
            logger.info(f"📊 Buscando métricas consolidadas - company_id: {company_id}, período: {date_from} a {date_to}, status: {status}")
            
            # Buscar campanhas da empresa com filtro de status
            query = self.db.query(MLCampaign.id).filter(
                MLCampaign.company_id == company_id
            )
            
            # Aplicar filtro de status se fornecido
            if status and status != 'all':
                if status == 'active':
                    query = query.filter(MLCampaign.status == 'active')
                elif status == 'paused':
                    query = query.filter(MLCampaign.status.in_(['paused', 'inactive']))
            
            campaign_ids = query.all()
            campaign_ids = [c[0] for c in campaign_ids]
            
            # Contar campanhas conforme o filtro
            campaigns_count = len(campaign_ids)
            
            # Definir label do contador baseado no filtro
            if status == 'active':
                campaigns_label = 'Campanhas Ativas'
            elif status == 'paused':
                campaigns_label = 'Campanhas Pausadas'
            else:
                campaigns_label = 'Total de Campanhas'
            
            if not campaign_ids:
                return {
                    "success": True,
                    "metrics": {
                        "campaigns_count": 0,
                        "campaigns_label": campaigns_label,
                        "active_campaigns": 0,  # Mantido para compatibilidade
                        "total_spent": 0,
                        "total_investment": 0,
                        "total_revenue": 0,
                        "avg_roas": 0,
                        "total_clicks": 0,
                        "total_impressions": 0,
                        "total_conversions": 0,
                        "ctr": 0
                    }
                }
            
            # Buscar totais agregados das métricas diárias no período especificado
            totals = self.db.query(
                func.sum(MLCampaignMetrics.spent).label('total_spent'),
                func.sum(MLCampaignMetrics.total_amount).label('total_revenue'),
                func.sum(MLCampaignMetrics.clicks).label('total_clicks'),
                func.sum(MLCampaignMetrics.impressions).label('total_impressions'),
                func.sum(MLCampaignMetrics.advertising_items_quantity).label('total_conversions')
            ).filter(
                MLCampaignMetrics.campaign_id.in_(campaign_ids),
                MLCampaignMetrics.metric_date >= date_from,
                MLCampaignMetrics.metric_date <= date_to
            ).first()
            
            # Extrair valores
            total_spent = float(totals.total_spent or 0)
            total_revenue = float(totals.total_revenue or 0)
            total_clicks = int(totals.total_clicks or 0)
            total_impressions = int(totals.total_impressions or 0)
            total_conversions = int(totals.total_conversions or 0)
            total_campaigns = len(campaign_ids)
            
            # Se não houver métricas no período OU se for muito baixo, buscar totais acumulados das campanhas
            # Isso garante que sempre mostre dados, mesmo que não haja métricas detalhadas do período
            if total_spent == 0 or total_revenue == 0:
                logger.info(f"⚠️ Métricas insuficientes no período {date_from} a {date_to}, buscando totais acumulados das campanhas")
                campaigns_totals = self.db.query(
                    func.sum(MLCampaign.total_spent).label('total_spent'),
                    func.sum(MLCampaign.total_revenue).label('total_revenue'),
                    func.sum(MLCampaign.total_clicks).label('total_clicks'),
                    func.sum(MLCampaign.total_impressions).label('total_impressions'),
                    func.sum(MLCampaign.total_conversions).label('total_conversions')
                ).filter(
                    MLCampaign.id.in_(campaign_ids)
                ).first()
                
                if campaigns_totals and (campaigns_totals.total_spent or 0) > 0:
                    total_spent = float(campaigns_totals.total_spent or 0)
                    total_revenue = float(campaigns_totals.total_revenue or 0)
                    total_clicks = int(campaigns_totals.total_clicks or 0)
                    total_impressions = int(campaigns_totals.total_impressions or 0)
                    total_conversions = int(campaigns_totals.total_conversions or 0)
                    logger.info(f"✅ Usando totais acumulados das campanhas: R$ {total_spent} gasto, R$ {total_revenue} receita")
            
            # Calcular ROAS médio
            avg_roas = (total_revenue / total_spent) if total_spent > 0 else 0
            
            # Calcular CTR
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            
            logger.info(f"✅ Métricas calculadas: {campaigns_count} campanhas ({campaigns_label}), R$ {total_spent} gasto, R$ {total_revenue} receita, ROAS {avg_roas:.2f}x")
            
            return {
                "success": True,
                "metrics": {
                    "campaigns_count": campaigns_count,
                    "campaigns_label": campaigns_label,
                    "active_campaigns": campaigns_count,  # Mantido para compatibilidade
                    "total_spent": total_spent,
                    "total_investment": total_spent,  # Alias para compatibilidade
                    "total_revenue": total_revenue,
                    "avg_roas": avg_roas,
                    "average_roas": avg_roas,  # Alias para compatibilidade
                    "total_clicks": total_clicks,
                    "total_impressions": total_impressions,
                    "total_conversions": total_conversions,
                    "total_campaigns": total_campaigns,
                    "ctr": ctr
                }
            }
        except Exception as e:
            logger.error(f"❌ Erro ao buscar métricas: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_campaign_details(self, company_id: int, campaign_id: str, date_from: str = None, date_to: str = None):
        """Busca detalhes completos de uma campanha com métricas (incluindo diárias e resumo)"""
        try:
            from datetime import datetime, timedelta
            import requests
            
            # Se não forneceu datas, usar últimos 30 dias por padrão
            if not date_to:
                date_to = datetime.now().date()
            else:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            
            if not date_from:
                date_from = date_to - timedelta(days=30)
            else:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            
            logger.info(f"📊 Buscando detalhes da campanha {campaign_id} - período: {date_from} a {date_to}")
            
            # Buscar conta e token
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            # Buscar detalhes da campanha com métricas agregadas
            metrics_list = "clicks,prints,ctr,cost,cpc,acos,organic_units_quantity,organic_units_amount,organic_items_quantity,direct_items_quantity,indirect_items_quantity,advertising_items_quantity,cvr,roas,sov,direct_units_quantity,indirect_units_quantity,units_quantity,direct_amount,indirect_amount,total_amount,impression_share,top_impression_share,lost_impression_share_by_budget,lost_impression_share_by_ad_rank,acos_benchmark"
            
            url = f"https://api.mercadolibre.com/advertising/{account.site_id}/product_ads/campaigns/{campaign_id}"
            params = {
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "metrics": metrics_list
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Api-Version": "2"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"❌ Erro ao buscar detalhes da campanha: {response.status_code} - {response.text[:200]}")
                return {"success": False, "error": f"API error: {response.status_code}"}
            
            campaign_data = response.json()
            
            # Buscar métricas diárias
            params["aggregation_type"] = "DAILY"
            response_daily = requests.get(url, params=params, headers=headers, timeout=30)
            daily_metrics = []
            
            if response_daily.status_code == 200:
                daily_data = response_daily.json()
                if isinstance(daily_data, list):
                    daily_metrics = daily_data
                elif isinstance(daily_data, dict) and "results" in daily_data:
                    daily_metrics = daily_data["results"]
            
            logger.info(f"✅ Detalhes da campanha obtidos com sucesso - {len(daily_metrics)} métricas diárias")
            
            return {
                "success": True,
                "campaign": campaign_data,
                "daily_metrics": daily_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes da campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_campaign_ads(self, company_id: int, campaign_id: str, date_from: str = None, date_to: str = None, limit: int = 100):
        """Busca anúncios/produtos de uma campanha com suas métricas"""
        try:
            from datetime import datetime, timedelta
            import requests
            
            # Se não forneceu datas, usar últimos 30 dias por padrão
            if not date_to:
                date_to = datetime.now().date()
            else:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            
            if not date_from:
                date_from = date_to - timedelta(days=30)
            else:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            
            logger.info(f"📦 Buscando anúncios da campanha {campaign_id} - período: {date_from} a {date_to}")
            
            # Buscar conta e token
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            # Buscar anúncios da campanha
            metrics_list = "clicks,prints,ctr,cost,cpc,acos,organic_units_quantity,organic_units_amount,organic_items_quantity,direct_items_quantity,indirect_items_quantity,advertising_items_quantity,cvr,roas,sov,direct_units_quantity,indirect_units_quantity,units_quantity,direct_amount,indirect_amount,total_amount"
            
            url = f"https://api.mercadolibre.com/advertising/{account.site_id}/advertisers/{advertiser_id}/product_ads/ads/search"
            params = {
                "filters[campaign_id]": campaign_id,
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "metrics": metrics_list,
                "limit": limit,
                "offset": 0
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Api-Version": "2"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"❌ Erro ao buscar anúncios: {response.status_code} - {response.text[:200]}")
                return {"success": False, "error": f"API error: {response.status_code}"}
            
            data = response.json()
            ads = data.get("results", [])
            paging = data.get("paging", {})
            
            logger.info(f"✅ {len(ads)} anúncios obtidos com sucesso")
            
            return {
                "success": True,
                "ads": ads,
                "paging": paging
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar anúncios da campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_campaign_price_evolution(self, company_id: int, campaign_id: str, date_from: str = None, date_to: str = None):
        """
        Calcula a evolução do preço médio dos produtos da campanha baseado nos pedidos reais
        
        Args:
            company_id: ID da empresa
            campaign_id: ID da campanha
            date_from: Data inicial (YYYY-MM-DD)
            date_to: Data final (YYYY-MM-DD)
        
        Returns:
            Dict com success e daily_prices (lista de datas e preços médios)
        """
        try:
            from app.models.saas_models import MLOrder
            from app.models.advertising_models import MLCampaignProduct
            from sqlalchemy import func, cast, Date
            from datetime import datetime, timedelta, date
            
            # Processar datas
            if not date_to:
                date_to = date.today()
            else:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            
            if not date_from:
                date_from = date_to - timedelta(days=30)
            else:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            
            logger.info(f"📊 Calculando evolução de preços - Campanha: {campaign_id}, Período: {date_from} a {date_to}")
            
            # Buscar conta e token para consultar a API do ML (mesma fonte da tabela "Anúncios da Campanha")
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            # Buscar anúncios ATIVOS da campanha direto da API do ML (mesma fonte da tabela)
            import requests
            url = f"https://api.mercadolibre.com/advertising/{account.site_id}/advertisers/{advertiser_id}/product_ads/ads/search"
            params = {
                "filters[campaign_id]": campaign_id,
                "limit": 200,
                "offset": 0
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Api-Version": "2"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"❌ Erro ao buscar anúncios da campanha: {response.status_code}")
                return {"success": False, "error": f"API error: {response.status_code}"}
            
            ads_data = response.json()
            ads = ads_data.get("results", [])
            
            # Criar set com APENAS os item_id dos anúncios ATIVOS na campanha
            product_ids = set()
            for ad in ads:
                # Filtrar apenas anúncios com status "active" (mesmo filtro da tabela)
                if ad.get("status") == "active":
                    item_id = ad.get("item_id")
                    if item_id:
                        product_ids.add(item_id)
                        logger.info(f"   ✅ Produto ATIVO: {item_id} - {ad.get('title', 'N/A')[:50]}")
                else:
                    logger.info(f"   ⏸️  Produto {ad.get('status', 'unknown').upper()}: {ad.get('item_id')} - {ad.get('title', 'N/A')[:50]}")
            
            logger.info(f"📦 {len(product_ids)} produtos ATIVOS na campanha (API DO MERCADO LIVRE): {product_ids}")
            
            # Buscar pedidos no período usando SQL direto com jsonb_array_elements
            # Isso replica a query SQL que o usuário forneceu
            from sqlalchemy import text
            
            # Converter product_ids para string SQL-safe
            product_ids_str = ','.join([f"'{pid}'" for pid in product_ids])
            
            if not product_ids:
                logger.warning("⚠️ Nenhum produto ATIVO encontrado na campanha")
                return {
                    "success": True,
                    "daily_sales": [],
                    "sales_details": []
                }
            
            logger.info(f"📋 Buscando vendas para produtos: {product_ids}")
            logger.info(f"🔍 product_ids_str: {product_ids_str}")
            
            # Query SQL EXATA que funciona no DBeaver
            sql_query_str = f"""
                SELECT 
                    DATE(date_created) as data_venda,
                    order_id,
                    item_data->'item'->>'id' as item_id,
                    item_data->'item'->>'title' as titulo,
                    CAST(item_data->>'quantity' AS INTEGER) as quantidade,
                    CAST(item_data->>'unit_price' AS NUMERIC) as preco_unitario
                FROM ml_orders,
                     jsonb_array_elements(order_items::jsonb) as item_data,
                     jsonb_array_elements(catalog_products::jsonb) as catalog_products
                WHERE company_id = :company_id
                AND (
                    catalog_products->>'item_id' IN ({product_ids_str})
                    OR 
                    item_data->'item'->>'id' IN ({product_ids_str})
                )
                AND status IN ('PAID', 'CONFIRMED', 'DELIVERED', 'SHIPPED')
                AND date_created >= :date_from
                AND date_created <= :date_to
                ORDER BY date_created DESC
            """
            
            logger.info(f"📝 SQL Query: {sql_query_str[:500]}...")
            sql_query = text(sql_query_str)
            
            result = self.db.execute(sql_query, {
                'company_id': company_id,
                'date_from': date_from,
                'date_to': date_to
            })
            
            # Processar resultados
            daily_data = {}
            sales_details = []
            
            for row in result:
                order_date = row.data_venda
                item_id = row.item_id
                titulo = row.titulo or 'N/A'
                quantidade = row.quantidade
                preco_unitario = float(row.preco_unitario)
                total = quantidade * preco_unitario
                
                logger.debug(f"✅ Venda encontrada: {item_id} - {quantidade}x R$ {preco_unitario}")
                
                # Adicionar detalhes da venda para debug
                sales_details.append({
                    'date': order_date.strftime('%Y-%m-%d'),
                    'item_id': item_id,
                    'title': titulo[:50],
                    'quantity': quantidade,
                    'unit_price': preco_unitario,
                    'total': round(total, 2)
                })
                
                if order_date not in daily_data:
                    daily_data[order_date] = {
                        'sales_count': 0,
                        'prices': [],
                        'total_revenue': 0
                    }
                
                # Adicionar cada unidade vendida individualmente
                for _ in range(quantidade):
                    daily_data[order_date]['prices'].append(preco_unitario)
                
                daily_data[order_date]['sales_count'] += quantidade
                daily_data[order_date]['total_revenue'] += total
            
            # Log resumo de vendas encontradas
            total_sales_found = sum(data['sales_count'] for data in daily_data.values())
            logger.info(f"💰 Total de vendas encontradas: {total_sales_found} em {len(daily_data)} dias diferentes")
            
            # Formatar resultado com vendas e preços por dia
            daily_sales = []
            current_date = date_from
            
            while current_date <= date_to:
                if current_date in daily_data:
                    data = daily_data[current_date]
                    # Calcular preço médio apenas para referência
                    avg_price = data['total_revenue'] / data['sales_count'] if data['sales_count'] > 0 else 0
                    min_price = min(data['prices']) if data['prices'] else 0
                    max_price = max(data['prices']) if data['prices'] else 0
                    # Só incluir preços se houver vendas
                    prices_list = [round(p, 2) for p in data['prices'][:50]] if data['sales_count'] > 0 else []
                else:
                    avg_price = 0
                    min_price = 0
                    max_price = 0
                    prices_list = []
                    data = {'sales_count': 0, 'total_revenue': 0}
                
                daily_sales.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'sales_count': data['sales_count'],
                    'average_price': round(avg_price, 2),
                    'min_price': round(min_price, 2),
                    'max_price': round(max_price, 2),
                    'total_revenue': round(data['total_revenue'], 2),
                    'prices': prices_list  # Lista vazia se não houver vendas
                })
                
                current_date += timedelta(days=1)
            
            logger.info(f"✅ Evolução de vendas calculada: {len(daily_sales)} dias")
            
            # Ordenar sales_details por data (mais recente primeiro)
            sales_details.sort(key=lambda x: x['date'], reverse=True)
            
            return {
                "success": True,
                "daily_sales": daily_sales,
                "sales_details": sales_details  # Detalhes individuais para debug
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular evolução de preços: {e}", exc_info=True)
            return {"success": False, "error": str(e)}