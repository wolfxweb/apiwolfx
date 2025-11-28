"""
Serviço para gerenciamento de saldo e débito de tokens de IA
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models.saas_models import Company

logger = logging.getLogger(__name__)


class TokenBalanceService:
    """Serviço para gerenciar saldo e débito de tokens de IA"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_balance(self, company_id: int) -> Dict:
        """
        Obtém saldo de tokens da empresa
        
        Returns:
            Dict com monthly, purchased e total
        """
        try:
            logger.info(f"🔍 Buscando saldo de tokens para company_id: {company_id}")
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                logger.warning(f"⚠️ Empresa não encontrada com ID: {company_id}")
                return {
                    "success": False,
                    "error": "Empresa não encontrada"
                }
            
            # Log dos valores brutos do banco
            monthly_raw = company.ai_tokens_monthly
            purchased_raw = company.ai_tokens_purchased
            logger.info(f"📊 Valores brutos do banco - monthly: {monthly_raw} (type: {type(monthly_raw)}), purchased: {purchased_raw} (type: {type(purchased_raw)})")
            
            # Converter None para 0, mas manter valores numéricos
            monthly = monthly_raw if monthly_raw is not None else 0
            purchased = purchased_raw if purchased_raw is not None else 0
            total = monthly + purchased
            
            logger.info(f"✅ Saldo calculado - monthly: {monthly}, purchased: {purchased}, total: {total}")
            
            return {
                "success": True,
                "monthly": monthly,
                "purchased": purchased,
                "total": total
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter saldo de tokens: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_balance(self, company_id: int, required_tokens: int) -> Dict:
        """
        Verifica se há saldo suficiente para a quantidade de tokens solicitada
        
        Args:
            company_id: ID da empresa
            required_tokens: Quantidade de tokens necessária
            
        Returns:
            Dict com success=True se há saldo suficiente, False caso contrário
        """
        try:
            balance = self.get_balance(company_id)
            if not balance.get("success"):
                return balance
            
            total_available = balance.get("total", 0)
            
            if total_available < required_tokens:
                return {
                    "success": False,
                    "error": "Saldo insuficiente de tokens",
                    "required": required_tokens,
                    "available": total_available,
                    "monthly": balance.get("monthly", 0),
                    "purchased": balance.get("purchased", 0)
                }
            
            return {
                "success": True,
                "available": total_available,
                "monthly": balance.get("monthly", 0),
                "purchased": balance.get("purchased", 0)
            }
        except Exception as e:
            logger.error(f"❌ Erro ao verificar saldo: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def debit_tokens(self, company_id: int, total_tokens: int) -> Dict:
        """
        Debita tokens da empresa (primeiro de ai_tokens_monthly, depois de ai_tokens_purchased)
        
        Args:
            company_id: ID da empresa
            total_tokens: Quantidade total de tokens a debitar
            
        Returns:
            Dict com success=True se débito foi bem-sucedido, False caso contrário
            Inclui saldos atualizados após o débito
        """
        try:
            # Usar select_for_update para evitar race conditions
            company = self.db.query(Company).filter(Company.id == company_id).with_for_update().first()
            
            if not company:
                return {
                    "success": False,
                    "error": "Empresa não encontrada"
                }
            
            # Obter saldos atuais
            monthly = company.ai_tokens_monthly or 0
            purchased = company.ai_tokens_purchased or 0
            total_available = monthly + purchased
            
            # Verificar se há saldo suficiente
            if total_available < total_tokens:
                return {
                    "success": False,
                    "error": "Saldo insuficiente de tokens",
                    "required": total_tokens,
                    "available": total_available,
                    "monthly": monthly,
                    "purchased": purchased
                }
            
            # Debitar primeiro de ai_tokens_monthly
            remaining_to_debit = total_tokens
            
            if monthly > 0:
                if monthly >= remaining_to_debit:
                    # Todo o débito pode ser feito de monthly
                    company.ai_tokens_monthly = monthly - remaining_to_debit
                    remaining_to_debit = 0
                else:
                    # Usar todo monthly e continuar com purchased
                    remaining_to_debit -= monthly
                    company.ai_tokens_monthly = 0
            
            # Se ainda faltar, debitar de ai_tokens_purchased
            if remaining_to_debit > 0:
                if purchased >= remaining_to_debit:
                    company.ai_tokens_purchased = purchased - remaining_to_debit
                    remaining_to_debit = 0
                else:
                    # Não deveria chegar aqui (já verificamos saldo total)
                    return {
                        "success": False,
                        "error": "Erro interno: saldo insuficiente durante débito"
                    }
            
            # Salvar alterações
            self.db.flush()
            
            # Obter saldos atualizados
            updated_monthly = company.ai_tokens_monthly or 0
            updated_purchased = company.ai_tokens_purchased or 0
            updated_total = updated_monthly + updated_purchased
            
            logger.info(f"✅ Tokens debitados: {total_tokens} tokens da empresa {company_id}")
            logger.info(f"   - Saldo anterior: monthly={monthly}, purchased={purchased}, total={total_available}")
            logger.info(f"   - Saldo atualizado: monthly={updated_monthly}, purchased={updated_purchased}, total={updated_total}")
            
            return {
                "success": True,
                "debited": total_tokens,
                "monthly": updated_monthly,
                "purchased": updated_purchased,
                "total": updated_total
            }
        except Exception as e:
            logger.error(f"❌ Erro ao debitar tokens: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

