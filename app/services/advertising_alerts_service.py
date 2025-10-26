"""
Serviço para alertas de publicidade (budget, performance, etc)
"""
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdvertisingAlertsService:
    """Serviço para monitorar campanhas e gerar alertas"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def check_budget_alerts(self, company_id: int) -> List[Dict]:
        """
        Verifica se alguma campanha está próxima do limite de budget
        
        Args:
            company_id: ID da empresa
        
        Returns:
            Lista de alertas de budget
        """
        try:
            from app.controllers.advertising_full_controller import AdvertisingFullController
            
            controller = AdvertisingFullController(self.db)
            campaigns_result = controller.get_campaigns(company_id)
            
            if not campaigns_result.get("success"):
                return []
            
            campaigns = campaigns_result.get("campaigns", [])
            alerts = []
            
            for campaign in campaigns:
                budget = campaign.get("budget", {}).get("amount", 0)
                spent = campaign.get("spent", 0)
                
                if budget > 0:
                    usage_percent = (spent / budget) * 100
                    
                    # Alert se gastar mais de 80% do budget
                    if usage_percent >= 80:
                        alerts.append({
                            "type": "budget_warning",
                            "severity": "high" if usage_percent >= 95 else "medium",
                            "campaign_id": campaign.get("id"),
                            "campaign_name": campaign.get("name"),
                            "message": f"Campanha '{campaign.get('name')}' gastou {usage_percent:.1f}% do orçamento",
                            "budget": budget,
                            "spent": spent,
                            "usage_percent": usage_percent
                        })
            
            logger.info(f"✅ {len(alerts)} alertas de budget encontrados")
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar alertas de budget: {e}")
            return []
    
    def check_performance_alerts(self, company_id: int) -> List[Dict]:
        """
        Verifica campanhas com baixa performance (ROAS, CTR, etc)
        
        Args:
            company_id: ID da empresa
        
        Returns:
            Lista de alertas de performance
        """
        try:
            from app.controllers.advertising_full_controller import AdvertisingFullController
            
            controller = AdvertisingFullController(self.db)
            campaigns_result = controller.get_campaigns(company_id)
            
            if not campaigns_result.get("success"):
                return []
            
            campaigns = campaigns_result.get("campaigns", [])
            alerts = []
            
            for campaign in campaigns:
                if campaign.get("status") != "active":
                    continue
                
                roas = campaign.get("roas", 0)
                ctr = campaign.get("ctr", 0)
                
                # Alert se ROAS < 1 (perdendo dinheiro)
                if roas > 0 and roas < 1:
                    alerts.append({
                        "type": "low_roas",
                        "severity": "high",
                        "campaign_id": campaign.get("id"),
                        "campaign_name": campaign.get("name"),
                        "message": f"Campanha '{campaign.get('name')}' com ROAS baixo: {roas:.2f}x",
                        "roas": roas,
                        "recommendation": "Considere pausar ou otimizar esta campanha"
                    })
                
                # Alert se CTR < 1% (baixo engajamento)
                if ctr > 0 and ctr < 1:
                    alerts.append({
                        "type": "low_ctr",
                        "severity": "medium",
                        "campaign_id": campaign.get("id"),
                        "campaign_name": campaign.get("name"),
                        "message": f"Campanha '{campaign.get('name')}' com CTR baixo: {ctr:.2f}%",
                        "ctr": ctr,
                        "recommendation": "Revise os anúncios e palavras-chave"
                    })
            
            logger.info(f"✅ {len(alerts)} alertas de performance encontrados")
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar alertas de performance: {e}")
            return []
    
    def get_all_alerts(self, company_id: int) -> Dict:
        """
        Busca todos os alertas disponíveis
        
        Args:
            company_id: ID da empresa
        
        Returns:
            Dicionário com todos os alertas
        """
        budget_alerts = self.check_budget_alerts(company_id)
        performance_alerts = self.check_performance_alerts(company_id)
        
        all_alerts = budget_alerts + performance_alerts
        
        # Ordenar por severidade
        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_alerts.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))
        
        return {
            "total_alerts": len(all_alerts),
            "high_severity": len([a for a in all_alerts if a.get("severity") == "high"]),
            "medium_severity": len([a for a in all_alerts if a.get("severity") == "medium"]),
            "alerts": all_alerts
        }


