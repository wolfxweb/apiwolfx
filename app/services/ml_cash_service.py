"""
Serviço para gerenciar lançamentos automáticos no caixa para pedidos ML
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.saas_models import MLOrder, OrderStatus, Company
from app.models.financial_models import FinancialAccount, FinancialTransaction

logger = logging.getLogger(__name__)

class MLCashService:
    """Serviço para lançamentos automáticos no caixa de pedidos ML"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_cash_entries_for_received_orders(self, company_id: int) -> Dict:
        """
        Processa lançamentos no caixa para pedidos ML recebidos a partir deste mês
        que ainda não foram lançados
        """
        try:
            logger.info(f"💰 Processando lançamentos no caixa para empresa {company_id}")
            
            # Buscar pedidos que ainda não foram lançados
            received_orders = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.company_id == company_id,
                    MLOrder.cash_entry_created == False,  # Ainda não foi lançado
                    MLOrder.status == OrderStatus.PAID  # Processar pedidos pagos
                )
            ).all()
            
            logger.info(f"📦 Encontrados {len(received_orders)} pedidos para processar")
            
            # Log detalhado dos critérios de busca
            total_orders = self.db.query(MLOrder).filter(MLOrder.company_id == company_id).count()
            paid_orders = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.company_id == company_id,
                    MLOrder.status == OrderStatus.PAID
                )
            ).count()
            not_processed = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.company_id == company_id,
                    MLOrder.cash_entry_created == False
                )
            ).count()
            logger.info(f"📊 Estatísticas da empresa {company_id}:")
            logger.info(f"   📦 Total de pedidos: {total_orders}")
            logger.info(f"   💰 Pedidos pagos: {paid_orders}")
            logger.info(f"   ⏳ Não processados: {not_processed}")
            
            if not received_orders:
                logger.info("ℹ️ Nenhum pedido elegível encontrado")
                return {
                    "success": True,
                    "message": "Nenhum pedido recebido encontrado para lançamento",
                    "processed_count": 0,
                    "total_amount": 0.0
                }
            
            # Buscar conta bancária padrão da empresa
            default_account = self.db.query(FinancialAccount).filter(
                and_(
                    FinancialAccount.company_id == company_id,
                    FinancialAccount.is_active == True
                )
            ).first()
            
            if not default_account:
                return {
                    "success": False,
                    "error": "Nenhuma conta bancária ativa encontrada para a empresa"
                }
            
            processed_count = 0
            total_amount = 0.0
            
            for order in received_orders:
                try:
                    # Verificar se o pedido foi realmente entregue há mais de 7 dias
                    if self._is_order_really_received(order):
                        # Calcular valor líquido (total - taxas)
                        net_amount = float(order.total_amount or 0) - float(order.total_fees or 0)
                        
                        if net_amount > 0:
                            # Lançar no caixa
                            self._create_cash_entry(order, default_account, net_amount)
                            
                            # Marcar como lançado
                            order.cash_entry_created = True
                            order.cash_entry_date = datetime.now()
                            order.cash_entry_amount = net_amount
                            order.cash_entry_account_id = default_account.id
                            
                            processed_count += 1
                            total_amount += net_amount
                            
                            logger.info(f"✅ Pedido {order.ml_order_id} lançado no caixa: R$ {net_amount:.2f}")
                        else:
                            logger.warning(f"⚠️ Pedido {order.ml_order_id} com valor líquido zero ou negativo")
                    else:
                        logger.info(f"ℹ️ Pedido {order.ml_order_id} ainda não foi entregue há 7 dias")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar pedido {order.ml_order_id}: {e}")
                    continue
            
            # Commit das alterações
            self.db.commit()
            
            logger.info(f"✅ Processamento concluído: {processed_count} pedidos, R$ {total_amount:.2f}")
            
            return {
                "success": True,
                "message": f"{processed_count} pedidos lançados no caixa",
                "processed_count": processed_count,
                "total_amount": total_amount
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de lançamentos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _is_order_really_received(self, order: MLOrder) -> bool:
        """
        Verifica se o pedido foi realmente entregue há mais de 7 dias
        """
        try:
            # Para pedidos PAID, considerar como recebido (dinheiro já está na conta)
            is_received = order.status == OrderStatus.PAID
            
            if not is_received:
                return False
            
            # Verificar data de entrega
            delivery_date = None
            if order.shipping_details and isinstance(order.shipping_details, dict):
                status_history = order.shipping_details.get('status_history', {})
                if status_history and 'date_delivered' in status_history:
                    try:
                        delivery_date_str = status_history['date_delivered']
                        delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                    except:
                        pass
            
            if delivery_date:
                # Verificar se passou 7 dias desde a entrega
                days_since_delivery = (datetime.now() - delivery_date.replace(tzinfo=None)).days
                return days_since_delivery >= 7
            else:
                # Se não conseguiu extrair a data, usar data de fechamento do pedido
                if order.date_closed:
                    days_since_closed = (datetime.now() - order.date_closed).days
                    return days_since_closed >= 7
                
                return False
                
        except Exception as e:
            logger.error(f"Erro ao verificar se pedido foi recebido: {e}")
            return False
    
    def _create_cash_entry(self, order: MLOrder, account: FinancialAccount, amount: float):
        """
        Cria lançamento no caixa (atualiza saldo da conta e registra transação)
        """
        try:
            # 1. Criar transação financeira (histórico)
            transaction = FinancialTransaction(
                company_id=order.company_id,
                account_id=account.id,
                transaction_type="credit",
                amount=amount,
                description=f"Recebimento ML - Pedido #{order.ml_order_id}",
                transaction_date=datetime.now().date(),
                reference_type="ml_order",
                reference_id=order.ml_order_id
            )
            
            self.db.add(transaction)
            
            # 2. Atualizar saldo da conta
            account.current_balance = float(account.current_balance or 0) + amount
            
            logger.info(f"💰 Transação criada: +R$ {amount:.2f} na conta {account.account_name}")
            logger.info(f"💰 Saldo da conta {account.account_name} atualizado: R$ {account.current_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Erro ao criar lançamento no caixa: {e}")
            raise e
    
    def get_pending_cash_entries(self, company_id: int) -> List[Dict]:
        """
        Retorna lista de pedidos que podem ser lançados no caixa
        """
        try:
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            pending_orders = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.company_id == company_id,
                    MLOrder.cash_entry_created == False,
                    MLOrder.date_closed >= current_month_start,
                    MLOrder.status == OrderStatus.PAID  # Processar pedidos pagos
                )
            ).all()
            
            result = []
            for order in pending_orders:
                if self._is_order_really_received(order):
                    net_amount = float(order.total_amount or 0) - float(order.total_fees or 0)
                    result.append({
                        "order_id": order.ml_order_id,
                        "amount": net_amount,
                        "date_closed": order.date_closed,
                        "status": str(order.status),
                        "shipping_status": order.shipping_status
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar pedidos pendentes: {e}")
            return []
