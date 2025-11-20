"""
Serviço para processamento em lote de lançamentos ML Cash para todas as empresas
"""
import logging
from typing import Dict, List
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.models.saas_models import Company, CompanyStatus
from app.models.financial_models import FinancialAccount
from app.services.ml_cash_service import MLCashService

logger = logging.getLogger(__name__)


class MLCashBatchService:
    """Serviço para processar lançamentos ML Cash para todas as empresas"""
    
    def process_all_companies(self) -> Dict:
        """
        Processa lançamentos pendentes para todas as empresas ativas que possuem conta principal
        
        Returns:
            Dict com estatísticas do processamento
        """
        db = SessionLocal()
        try:
            logger.info("🔄 [ML CASH BATCH] Iniciando processamento de lançamentos para todas as empresas...")
            
            # Buscar todas as empresas ativas
            companies = db.query(Company).filter(
                Company.status == CompanyStatus.ACTIVE
            ).all()
            
            logger.info(f"📊 [ML CASH BATCH] Encontradas {len(companies)} empresas ativas")
            
            total_processed = 0
            total_amount = 0.0
            companies_processed = 0
            companies_skipped = 0
            companies_with_errors = 0
            errors = []
            
            for company in companies:
                try:
                    # Verificar se a empresa tem conta principal configurada
                    default_account = db.query(FinancialAccount).filter(
                        FinancialAccount.company_id == company.id,
                        FinancialAccount.is_active == True
                    ).first()
                    
                    if not default_account:
                        logger.info(f"⏭️ [ML CASH BATCH] Empresa {company.id} ({company.name}) sem conta principal - pulando")
                        companies_skipped += 1
                        continue
                    
                    logger.info(f"💰 [ML CASH BATCH] Processando empresa {company.id} ({company.name})...")
                    
                    cash_service = MLCashService(db)
                    result = cash_service.process_cash_entries_for_received_orders(company.id)
                    
                    if result.get("success"):
                        processed_count = result.get("processed_count", 0)
                        amount = result.get("total_amount", 0.0)
                        
                        total_processed += processed_count
                        total_amount += amount
                        companies_processed += 1
                        
                        if processed_count > 0:
                            logger.info(f"✅ [ML CASH BATCH] Empresa {company.id}: {processed_count} lançamentos, R$ {amount:.2f}")
                        else:
                            logger.info(f"ℹ️ [ML CASH BATCH] Empresa {company.id}: nenhum lançamento pendente")
                    else:
                        error_msg = result.get("error", "Erro desconhecido")
                        logger.warning(f"⚠️ [ML CASH BATCH] Empresa {company.id} falhou: {error_msg}")
                        companies_with_errors += 1
                        errors.append({
                            "company_id": company.id,
                            "company_name": company.name,
                            "error": error_msg
                        })
                        
                except Exception as e:
                    logger.error(f"❌ [ML CASH BATCH] Erro ao processar empresa {company.id}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    companies_with_errors += 1
                    errors.append({
                        "company_id": company.id,
                        "company_name": company.name,
                        "error": str(e)
                    })
                    continue
            
            logger.info(f"✅ [ML CASH BATCH] Processamento concluído:")
            logger.info(f"   - Empresas processadas: {companies_processed}")
            logger.info(f"   - Empresas puladas (sem conta): {companies_skipped}")
            logger.info(f"   - Empresas com erro: {companies_with_errors}")
            logger.info(f"   - Total de lançamentos: {total_processed}")
            logger.info(f"   - Valor total: R$ {total_amount:.2f}")
            
            return {
                "success": True,
                "total_companies": len(companies),
                "companies_processed": companies_processed,
                "companies_skipped": companies_skipped,
                "companies_with_errors": companies_with_errors,
                "total_processed": total_processed,
                "total_amount": total_amount,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"❌ [ML CASH BATCH] Erro no processamento em lote: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            db.close()

