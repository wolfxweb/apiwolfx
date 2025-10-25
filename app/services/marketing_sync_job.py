"""
Job automático para sincronização de custos de marketing.

Este job:
1. Executa automaticamente a sincronização de custos
2. Pode ser executado via cron ou scheduler
3. Registra logs detalhados da execução
4. Envia notificações em caso de erro
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services.marketing_costs_service import MarketingCostsService
from app.models.saas_models import Company, MLAccount, MLAccountStatus

logger = logging.getLogger(__name__)

class MarketingSyncJob:
    """Job para sincronização automática de custos de marketing"""
    
    def __init__(self):
        self.db = next(get_db())
        self.marketing_service = MarketingCostsService(self.db)
    
    async def run_sync_for_all_companies(self, months: int = 1) -> Dict:
        """
        Executa sincronização para todas as empresas ativas
        
        Args:
            months: Número de meses para sincronizar (padrão: 1)
            
        Returns:
            Resultado da execução do job
        """
        try:
            logger.info(f"🚀 Iniciando job de sincronização de custos de marketing (últimos {months} mês(es))")
            
            # Buscar todas as empresas ativas
            companies = self.db.query(Company).filter(
                Company.is_active == True
            ).all()
            
            if not companies:
                logger.warning("⚠️ Nenhuma empresa ativa encontrada")
                return {
                    "success": True,
                    "message": "Nenhuma empresa ativa encontrada",
                    "companies_processed": 0,
                    "total_cost": 0,
                    "total_orders": 0
                }
            
            logger.info(f"📊 Encontradas {len(companies)} empresa(s) ativa(s)")
            
            total_cost = 0
            total_orders = 0
            companies_processed = 0
            companies_with_errors = []
            
            for company in companies:
                try:
                    logger.info(f"🔄 Processando empresa: {company.name} (ID: {company.id})")
                    
                    # Verificar se a empresa tem contas ML ativas
                    ml_accounts = self.db.query(MLAccount).filter(
                        MLAccount.company_id == company.id,
                        MLAccount.status == MLAccountStatus.ACTIVE
                    ).all()
                    
                    if not ml_accounts:
                        logger.info(f"  ⚠️ Empresa {company.name} não possui contas ML ativas")
                        continue
                    
                    # Sincronizar custos da empresa
                    result = self.marketing_service.sync_marketing_costs_for_company(
                        company.id, months
                    )
                    
                    if result["success"]:
                        total_cost += result["total_cost"]
                        total_orders += result["orders_updated"]
                        companies_processed += 1
                        
                        logger.info(f"  ✅ Empresa {company.name}: R$ {result['total_cost']:.2f} em {result['orders_updated']} pedidos")
                    else:
                        companies_with_errors.append({
                            "company_id": company.id,
                            "company_name": company.name,
                            "error": result.get("error", "Erro desconhecido")
                        })
                        
                        logger.error(f"  ❌ Erro na empresa {company.name}: {result.get('error', 'Erro desconhecido')}")
                
                except Exception as e:
                    companies_with_errors.append({
                        "company_id": company.id,
                        "company_name": company.name,
                        "error": str(e)
                    })
                    
                    logger.error(f"  ❌ Erro ao processar empresa {company.name}: {e}")
                    continue
            
            # Resultado final
            result = {
                "success": True,
                "message": f"Job executado com sucesso: {companies_processed} empresa(s) processada(s)",
                "companies_processed": companies_processed,
                "companies_with_errors": len(companies_with_errors),
                "total_cost": total_cost,
                "total_orders": total_orders,
                "execution_time": datetime.now().isoformat(),
                "errors": companies_with_errors
            }
            
            if companies_with_errors:
                logger.warning(f"⚠️ {len(companies_with_errors)} empresa(s) com erro(es)")
            else:
                logger.info(f"✅ Job concluído com sucesso: R$ {total_cost:.2f} em {total_orders} pedidos")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro crítico no job de sincronização: {e}")
            return {
                "success": False,
                "error": str(e),
                "companies_processed": 0,
                "total_cost": 0,
                "total_orders": 0
            }
    
    async def run_sync_for_company(self, company_id: int, months: int = 1) -> Dict:
        """
        Executa sincronização para uma empresa específica
        
        Args:
            company_id: ID da empresa
            months: Número de meses para sincronizar
            
        Returns:
            Resultado da sincronização da empresa
        """
        try:
            logger.info(f"🔄 Executando sincronização para empresa {company_id} (últimos {months} mês(es))")
            
            result = self.marketing_service.sync_marketing_costs_for_company(company_id, months)
            
            if result["success"]:
                logger.info(f"✅ Sincronização concluída para empresa {company_id}: R$ {result['total_cost']:.2f} em {result['orders_updated']} pedidos")
            else:
                logger.error(f"❌ Erro na sincronização da empresa {company_id}: {result.get('error', 'Erro desconhecido')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização da empresa {company_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_cost": 0,
                "orders_updated": 0
            }
    
    async def run_daily_sync(self) -> Dict:
        """
        Executa sincronização diária (último mês)
        
        Returns:
            Resultado da sincronização diária
        """
        return await self.run_sync_for_all_companies(months=1)
    
    async def run_weekly_sync(self) -> Dict:
        """
        Executa sincronização semanal (últimos 3 meses)
        
        Returns:
            Resultado da sincronização semanal
        """
        return await self.run_sync_for_all_companies(months=3)
    
    async def run_monthly_sync(self) -> Dict:
        """
        Executa sincronização mensal (últimos 6 meses)
        
        Returns:
            Resultado da sincronização mensal
        """
        return await self.run_sync_for_all_companies(months=6)

# Funções de conveniência para execução externa
async def run_daily_marketing_sync():
    """Executa sincronização diária de custos de marketing"""
    job = MarketingSyncJob()
    return await job.run_daily_sync()

async def run_weekly_marketing_sync():
    """Executa sincronização semanal de custos de marketing"""
    job = MarketingSyncJob()
    return await job.run_weekly_sync()

async def run_monthly_marketing_sync():
    """Executa sincronização mensal de custos de marketing"""
    job = MarketingSyncJob()
    return await job.run_monthly_sync()

# Função para execução via cron
def cron_daily_sync():
    """Função para execução via cron (diária)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_daily_marketing_sync())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Erro na execução cron diária: {e}")
        return {"success": False, "error": str(e)}

def cron_weekly_sync():
    """Função para execução via cron (semanal)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_weekly_marketing_sync())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Erro na execução cron semanal: {e}")
        return {"success": False, "error": str(e)}

def cron_monthly_sync():
    """Função para execução via cron (mensal)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_monthly_marketing_sync())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Erro na execução cron mensal: {e}")
        return {"success": False, "error": str(e)}
