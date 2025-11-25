"""
Serviço para gerenciar movimentações de estoque
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from decimal import Decimal
from datetime import datetime, timedelta
from app.models.saas_models import (
    StockMovement, StockMovementType, ProductStock, Warehouse, WarehouseType
)
from app.utils.notification_logger import global_logger

logger = logging.getLogger(__name__)


class StockMovementService:
    """Serviço para gerenciar movimentações de estoque"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_movement(
        self,
        company_id: int,
        warehouse_id: int,
        product_stock_id: int,
        movement_type: str,
        quantity: float,
        previous_quantity: float,
        new_quantity: float,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        ml_order_id: Optional[int] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
        commit: bool = True
    ) -> Dict[str, Any]:
        """Registra uma movimentação de estoque
        
        Args:
            commit: Se True, faz commit imediato. Se False, apenas adiciona à sessão (para commit posterior).
        """
        try:
            # Verificar se product_stock pertence à empresa
            product_stock = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.id == product_stock_id,
                    ProductStock.company_id == company_id
                )
            ).first()
            
            if not product_stock:
                return {
                    "success": False,
                    "error": "Estoque não encontrado"
                }
            
            movement = StockMovement(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_stock_id=product_stock_id,
                movement_type=StockMovementType(movement_type),
                quantity=quantity,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                ml_order_id=ml_order_id,
                notes=notes,
                created_by=created_by
            )
            
            self.db.add(movement)
            
            if commit:
                self.db.commit()
                self.db.refresh(movement)
                logger.info(f"✅ Movimentação registrada e commitada: {movement_type} - {quantity} unidades (Stock ID: {product_stock_id}, Movement ID: {movement.id})")
            else:
                self.db.flush()  # Apenas flush para obter o ID sem commit
                logger.info(f"✅ Movimentação adicionada à sessão (sem commit): {movement_type} - {quantity} unidades (Stock ID: {product_stock_id}, Movement ID: {movement.id})")
            
            return {
                "success": True,
                "movement": {
                    "id": movement.id,
                    "type": movement.movement_type.value,
                    "quantity": float(movement.quantity),
                    "created_at": movement.created_at.isoformat() if movement.created_at else None
                }
            }
            
        except Exception as e:
            if commit:
                self.db.rollback()
            logger.error(f"❌ Erro ao registrar movimentação: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao registrar movimentação: {str(e)}"
            }
    
    def get_movement_history(
        self,
        company_id: int,
        product_stock_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        movement_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Obtém histórico de movimentações"""
        try:
            query = self.db.query(StockMovement).filter(
                StockMovement.company_id == company_id
            )
            
            if product_stock_id:
                query = query.filter(StockMovement.product_stock_id == product_stock_id)
            
            if warehouse_id:
                query = query.filter(StockMovement.warehouse_id == warehouse_id)
            
            if movement_type:
                # IMPORTANTE: Usar cast para evitar problemas com EnumValueType no SQLAlchemy
                from sqlalchemy import cast, String
                movement_type_str = str(movement_type) if not isinstance(movement_type, str) else movement_type
                # Se for um enum, extrair o value
                if hasattr(movement_type, 'value'):
                    movement_type_str = str(movement_type.value)
                query = query.filter(cast(StockMovement.movement_type, String) == movement_type_str)
            
            if date_from:
                query = query.filter(StockMovement.created_at >= date_from)
            
            if date_to:
                query = query.filter(StockMovement.created_at <= date_to)
            
            # Se buscar por produto, precisa filtrar via product_stock
            if internal_product_id or ml_item_id:
                product_stock_query = self.db.query(ProductStock.id).filter(
                    ProductStock.company_id == company_id
                )
                
                if internal_product_id:
                    product_stock_query = product_stock_query.filter(
                        ProductStock.internal_product_id == internal_product_id
                    )
                
                if ml_item_id:
                    product_stock_query = product_stock_query.filter(
                        ProductStock.ml_item_id == ml_item_id
                    )
                
                product_stock_ids = [ps[0] for ps in product_stock_query.all()]
                query = query.filter(StockMovement.product_stock_id.in_(product_stock_ids))
            
            total = query.count()
            
            movements = query.order_by(desc(StockMovement.created_at)).limit(limit).offset(offset).all()
            
            return {
                "success": True,
                "movements": [
                    {
                        "id": m.id,
                        "warehouse_id": m.warehouse_id,
                        "warehouse_name": m.warehouse.name if m.warehouse else None,
                        "movement_type": m.movement_type.value,
                        "quantity": float(m.quantity),
                        "previous_quantity": float(m.previous_quantity),
                        "new_quantity": float(m.new_quantity),
                        "reference_type": m.reference_type,
                        "reference_id": m.reference_id,
                        "ml_order_id": m.ml_order_id,
                        "notes": m.notes,
                        "created_by": m.created_by,
                        "created_at": m.created_at.isoformat() if m.created_at else None
                    }
                    for m in movements
                ],
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico de movimentações: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar histórico: {str(e)}"
            }
    
    def sync_sale_to_stock(
        self,
        company_id: int,
        ml_order_id: int,
        ml_item_id: str,
        quantity: int,
        warehouse_id: Optional[int] = None,
        order_number: Optional[str] = None,
        order_date: Optional[str] = None,
        sales_channel: Optional[str] = None,
        sync_ml_skus: bool = False
    ) -> Dict[str, Any]:
        """Sincroniza venda com estoque - PRIMEIRO dá baixa, DEPOIS sincroniza com ML se necessário
        
        Args:
            sync_ml_skus: Se True, sincroniza SKUs não-full com ML após registrar movimentação
        """
        try:
            from app.models.saas_models import MLOrder, SKUManagement, MLProduct, MLAccount, MLAccountStatus
            from app.services.stock_service import StockService
            import json
            
            # Verificar se pedido existe e pertence à empresa
            order = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.id == ml_order_id,
                    MLOrder.company_id == company_id
                )
            ).first()
            
            if not order:
                return {
                    "success": False,
                    "error": "Pedido não encontrado"
                }
            
            # Buscar internal_product_id via SKUManagement
            sku_mgmt = self.db.query(SKUManagement).filter(
                SKUManagement.platform_item_id == ml_item_id,
                SKUManagement.company_id == company_id,
                SKUManagement.status == "active"
            ).first()
            
            internal_product_id = sku_mgmt.internal_product_id if sku_mgmt else None
            
            # Log global: início da sincronização
            global_logger.log_event(
                event_type="stock_sync/order_processing",
                data={
                    "action": "start",
                    "ml_order_id": str(order.ml_order_id),
                    "ml_item_id": ml_item_id,
                    "item_quantity": quantity,
                    "company_id": company_id,
                    "internal_product_id": internal_product_id,
                    "warehouse_id": warehouse_id
                },
                company_id=company_id,
                success=True
            )
            
            if not internal_product_id:
                logger.warning(f"⚠️ internal_product_id não encontrado para ml_item_id {ml_item_id} - apenas registrando baixa sem sincronização ML")
                global_logger.log_event(
                    event_type="stock_sync/warning",
                    data={
                        "message": "internal_product_id não encontrado",
                        "ml_item_id": ml_item_id,
                        "ml_order_id": str(order.ml_order_id)
                    },
                    company_id=company_id,
                    success=False,
                    error_message="internal_product_id não encontrado"
                )
            
            # Identificar se produto é Full (fulfillment)
            is_fulfillment = False
            ml_product = self.db.query(MLProduct).filter(
                MLProduct.ml_item_id == ml_item_id,
                MLProduct.company_id == company_id
            ).first()
            
            if ml_product and ml_product.shipping:
                shipping_data = ml_product.shipping
                if isinstance(shipping_data, str):
                    try:
                        shipping_data = json.loads(shipping_data)
                    except:
                        shipping_data = {}
                
                if shipping_data.get("logistic_type") == "fulfillment":
                    is_fulfillment = True
            
            # Verificar também nas tags
            if not is_fulfillment and ml_product and ml_product.tags:
                tags_list = ml_product.tags if isinstance(ml_product.tags, list) else []
                if any(tag in ["fulfillment", "meli_fulfillment", "FULL"] for tag in tags_list):
                    is_fulfillment = True
            
            # Se não especificou warehouse, tentar encontrar por ml_item_id ou internal_product_id
            logger.info(f"🔍 [ESTOQUE] Buscando warehouse para ml_item_id={ml_item_id}, internal_product_id={internal_product_id}")
            
            if not warehouse_id:
                # Buscar estoque específico do anúncio (para Full)
                product_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.ml_item_id == ml_item_id
                    )
                ).first()
                
                if product_stock:
                    warehouse_id = product_stock.warehouse_id
                    logger.info(f"✅ [ESTOQUE] Warehouse encontrado via ml_item_id: {warehouse_id}")
                elif internal_product_id:
                    # Buscar estoque compartilhado do produto interno
                    shared_stock = self.db.query(ProductStock).filter(
                        and_(
                            ProductStock.company_id == company_id,
                            ProductStock.internal_product_id == internal_product_id,
                            ProductStock.ml_item_id.is_(None)  # Estoque compartilhado
                        )
                    ).first()
                    
                    if shared_stock:
                        warehouse_id = shared_stock.warehouse_id
                        logger.info(f"✅ [ESTOQUE] Warehouse encontrado via internal_product_id: {warehouse_id}")
                    else:
                        logger.warning(f"⚠️ [ESTOQUE] Estoque compartilhado não encontrado para internal_product_id={internal_product_id}")
                        # Buscar fulfillment (compartilhado)
                        fulfillment_warehouse = self.db.query(Warehouse).filter(
                            and_(
                                Warehouse.type == WarehouseType.FULFILLMENT,
                                Warehouse.is_shared == True
                            )
                        ).first()
                        
                        if fulfillment_warehouse:
                            warehouse_id = fulfillment_warehouse.id
                            logger.info(f"✅ [ESTOQUE] Warehouse fulfillment encontrado: {warehouse_id}")
                        else:
                            logger.warning(f"⚠️ [ESTOQUE] Warehouse fulfillment não encontrado")
                else:
                    logger.warning(f"⚠️ [ESTOQUE] Não há internal_product_id para buscar warehouse compartilhado")
            
            if not warehouse_id:
                error_msg = f"Depósito não encontrado para este anúncio (ml_item_id={ml_item_id}, internal_product_id={internal_product_id})"
                logger.error(f"❌ [ESTOQUE] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
            
            logger.info(f"✅ [ESTOQUE] Warehouse definido: {warehouse_id}")
            
            # PRIMEIRO: Dar baixa no estoque interno com quantidade DO ITEM
            logger.info(f"📦 [ESTOQUE] Iniciando baixa no estoque: quantity={-quantity}, internal_product_id={internal_product_id}, ml_item_id={ml_item_id}, is_fulfillment={is_fulfillment}")
            
            global_logger.log_event(
                event_type="stock_sync/stock_decrease",
                data={
                    "action": "decreasing_stock",
                    "ml_order_id": str(order.ml_order_id),
                    "ml_item_id": ml_item_id,
                    "quantity": -quantity,
                    "is_fulfillment": is_fulfillment,
                    "internal_product_id": internal_product_id,
                    "warehouse_id": warehouse_id
                },
                company_id=company_id,
                success=True
            )
            
            # Para produtos fulfillment, não tentar dar baixa (estoque é gerenciado pelo ML)
            # Apenas registrar a movimentação para histórico
            stock_decrease_success = False
            stock_service = None  # Inicializar para uso posterior na sincronização ML
            
            if is_fulfillment:
                # Para fulfillment, também atualizar a quantidade no ProductStock para histórico
                logger.info(f"ℹ️ [ESTOQUE] Produto fulfillment - atualizando quantidade no ProductStock para histórico")
                # Buscar ou criar ProductStock primeiro
                product_stock_fulfillment = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.warehouse_id == warehouse_id,
                        ProductStock.ml_item_id == ml_item_id
                    )
                ).first()
                
                if not product_stock_fulfillment:
                    # Criar ProductStock se não existir
                    product_stock_fulfillment = ProductStock(
                        company_id=company_id,
                        warehouse_id=warehouse_id,
                        ml_item_id=ml_item_id,
                        internal_product_id=internal_product_id,
                        quantity=Decimal("0"),
                        reserved_quantity=Decimal("0")
                    )
                    self.db.add(product_stock_fulfillment)
                    self.db.flush()
                    logger.info(f"✅ ProductStock criado para fulfillment")
                
                # Atualizar quantidade (diminuir a quantidade vendida)
                previous_qty = float(product_stock_fulfillment.quantity) if product_stock_fulfillment.quantity else 0.0
                new_qty = max(0.0, previous_qty - quantity)
                product_stock_fulfillment.quantity = Decimal(str(new_qty))
                product_stock_fulfillment.last_movement_date = datetime.utcnow()
                self.db.flush()
                
                logger.info(f"📦 [ESTOQUE] Fulfillment: quantidade atualizada {previous_qty} → {new_qty} (venda de {quantity} unidade(s))")
                stock_decrease_success = True  # Considerar sucesso para continuar com registro
            elif not internal_product_id:
                # Produto normal sem internal_product_id - não pode dar baixa no estoque compartilhado
                logger.warning(f"⚠️ [ESTOQUE] Produto normal sem internal_product_id - pulando baixa no estoque, apenas registrando movimentação")
                logger.warning(f"⚠️ [ESTOQUE] ml_item_id={ml_item_id} não está associado a um produto interno via SKUManagement")
                stock_decrease_success = True  # Considerar sucesso para continuar com registro (apenas histórico)
            else:
                # Produto normal COM internal_product_id - dar baixa no estoque compartilhado
                stock_service = StockService(self.db)
                result = stock_service.update_stock(
                    company_id=company_id,
                    warehouse_id=warehouse_id,
                    quantity=-quantity,  # Negativo para saída - quantidade DO ITEM vendido
                    internal_product_id=internal_product_id,
                    ml_item_id=None,  # Produtos normais não têm ml_item_id no estoque compartilhado
                    movement_type="sale"
                )
                
                logger.info(f"📦 [ESTOQUE] Resultado do update_stock: success={result.get('success')}, error={result.get('error')}")
                stock_decrease_success = result.get("success", False)
                
                if not stock_decrease_success:
                    error_msg = result.get("error", "Erro desconhecido")
                    logger.warning(f"⚠️ [ESTOQUE] Falha ao dar baixa no estoque: {error_msg} - mas continuando para registrar movimentação")
            
            logger.info(f"✅ [ESTOQUE] Processando registro de movimentação...")
            
            # Obter ou criar ProductStock para registro
            if is_fulfillment:
                # Para Full, buscar estoque específico do anúncio (já foi atualizado acima)
                product_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.warehouse_id == warehouse_id,
                        ProductStock.ml_item_id == ml_item_id
                    )
                ).first()
                
                # Se não encontrou, usar o que foi criado acima (product_stock_fulfillment)
                if not product_stock:
                    # Se chegou aqui, significa que não foi criado acima, criar agora
                    logger.warning(f"⚠️ ProductStock não encontrado para fulfillment ml_item_id {ml_item_id}, criando registro básico")
                    product_stock = ProductStock(
                        company_id=company_id,
                        warehouse_id=warehouse_id,
                        ml_item_id=ml_item_id,
                        internal_product_id=internal_product_id,  # Pode ser None para fulfillment sem associação
                        quantity=Decimal("0"),  # Iniciar com 0
                        reserved_quantity=Decimal("0")
                    )
                    self.db.add(product_stock)
                    self.db.flush()
                    logger.info(f"✅ ProductStock criado para registro de movimentação fulfillment")
                else:
                    # ProductStock já existe e foi atualizado acima, apenas refresh para garantir dados atualizados
                    self.db.refresh(product_stock)
                    logger.info(f"✅ ProductStock fulfillment encontrado e atualizado (quantidade atual: {product_stock.quantity})")
            elif not internal_product_id:
                # Produto normal SEM internal_product_id - criar ProductStock apenas com ml_item_id para histórico
                logger.warning(f"⚠️ [ESTOQUE] Produto normal sem internal_product_id - criando ProductStock apenas para histórico")
                product_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.warehouse_id == warehouse_id,
                        ProductStock.ml_item_id == ml_item_id,
                        ProductStock.internal_product_id.is_(None)
                    )
                ).first()
                
                if not product_stock:
                    product_stock = ProductStock(
                        company_id=company_id,
                        warehouse_id=warehouse_id,
                        ml_item_id=ml_item_id,
                        internal_product_id=None,  # Sem associação com produto interno
                        quantity=0,  # Não gerencia quantidade (apenas histórico)
                        reserved_quantity=0
                    )
                    self.db.add(product_stock)
                    self.db.flush()
                    logger.info(f"✅ ProductStock criado para registro histórico (sem internal_product_id)")
            else:
                # Para normal COM internal_product_id, buscar estoque compartilhado
                product_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.warehouse_id == warehouse_id,
                        ProductStock.internal_product_id == internal_product_id,
                        ProductStock.ml_item_id.is_(None)  # Estoque compartilhado
                    )
                ).first()
                
                # Se não encontrou após a baixa, tentar criar (deve ter sido criado pelo update_stock, mas garantir)
                if not product_stock:
                    logger.warning(f"⚠️ ProductStock não encontrado após baixa - criando estoque compartilhado")
                    product_stock = ProductStock(
                        company_id=company_id,
                        warehouse_id=warehouse_id,
                        internal_product_id=internal_product_id,
                        ml_item_id=None,  # Estoque compartilhado
                        quantity=0,
                        reserved_quantity=0
                    )
                    self.db.add(product_stock)
                    self.db.flush()
                    logger.info(f"✅ ProductStock criado para estoque compartilhado")
            
            if not product_stock:
                logger.error(f"❌ ProductStock não encontrado/criado para ml_item_id {ml_item_id}, internal_product_id={internal_product_id}")
                return {
                    "success": False,
                    "error": "Estoque não encontrado após baixa"
                }
            
            # Calcular quantidade disponível após baixa
            # Para fulfillment, a quantidade pode ser 0 (gerenciada pelo ML)
            available_quantity = float(product_stock.quantity - product_stock.reserved_quantity) if product_stock.quantity else 0.0
            
            # Formatar observação com número do pedido
            order_num = order_number or str(order.ml_order_id)
            order_dt = order_date or (order.date_created.strftime("%d/%m/%Y %H:%M") if order.date_created else "")
            channel = sales_channel or "Mercado Livre"
            # Referência principal: "Pedido {número}"
            notes = f"Pedido {order_num} - {order_dt} - {channel} - {quantity} unidade(s)"
            if is_fulfillment:
                notes += " (Fulfillment - estoque gerenciado pelo ML)"
            
            # Calcular previous_quantity e new_quantity para refletir a baixa
            # Mesmo para fulfillment, registramos a baixa na movimentação (mesmo que não altere o estoque físico)
            if is_fulfillment:
                # Para fulfillment: registrar a baixa na movimentação mesmo que não altere o estoque físico
                # Pegar quantidade atual do ProductStock (pode ser 0 ou valor anterior)
                current_qty = float(product_stock.quantity) if product_stock.quantity else 0.0
                previous_quantity = current_qty
                # Diminuir a quantidade vendida (mesmo que não altere o estoque físico, registramos na movimentação)
                new_quantity = max(0.0, current_qty - quantity)
                logger.info(f"📦 [ESTOQUE] Fulfillment: registrando baixa de {quantity} unidade(s) - {previous_quantity} → {new_quantity}")
            elif stock_decrease_success:
                # Para produtos normais com baixa bem-sucedida, calcular baseado na quantidade atual
                previous_quantity = float(product_stock.quantity) + quantity
                new_quantity = float(product_stock.quantity)
            else:
                # Para produtos normais com baixa falhada, usar quantidade atual (não alterada)
                previous_quantity = float(product_stock.quantity) if product_stock.quantity else 0.0
                new_quantity = previous_quantity
            
            # Registrar movimentação (sempre, mesmo se baixa falhou)
            # IMPORTANTE: commit=False para que o commit seja feito em _sync_order_to_stock
            movement_result = self.record_movement(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_stock_id=product_stock.id,
                movement_type="sale",
                quantity=-quantity,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                reference_type="order",
                reference_id=ml_order_id,
                ml_order_id=ml_order_id,
                notes=notes,
                commit=False  # Commit será feito em _sync_order_to_stock
            )
            
            if not movement_result.get("success"):
                logger.error(f"❌ Falha ao registrar movimentação: {movement_result.get('error')}")
                return movement_result
            
            logger.info(f"✅ Baixa no estoque: {quantity} unidade(s) do item {ml_item_id} (Pedido: {order_num})")
            if is_fulfillment:
                logger.info(f"ℹ️ [ESTOQUE] Movimentação registrada para fulfillment (estoque gerenciado pelo ML)")
            elif not stock_decrease_success:
                logger.warning(f"⚠️ [ESTOQUE] Movimentação registrada mas baixa de estoque falhou")
            
            # Log global: baixa realizada
            global_logger.log_event(
                event_type="stock_sync/stock_decrease",
                data={
                    "action": "stock_decreased",
                    "ml_order_id": str(order.ml_order_id),
                    "ml_item_id": ml_item_id,
                    "quantity_decreased": quantity,
                    "available_quantity_after": available_quantity,
                    "is_fulfillment": is_fulfillment,
                    "warehouse_id": warehouse_id,
                    "stock_decrease_success": stock_decrease_success,
                    "movement_registered": True
                },
                company_id=company_id,
                success=True
            )
            
            # DEPOIS: Se produto normal (não Full) e tem internal_product_id, sincronizar com ML
            # Apenas se sync_ml_skus=True (sincronização pode ser feita depois em lote)
            if sync_ml_skus and not is_fulfillment and internal_product_id:
                logger.info(f"🔄 Sincronizando estoque com ML para produto {internal_product_id} - quantidade após baixa: {available_quantity}")
                
                # Log global: início da sincronização ML
                global_logger.log_event(
                    event_type="stock_sync/ml_sync",
                    data={
                        "action": "starting_ml_sync",
                        "ml_order_id": str(order.ml_order_id),
                        "internal_product_id": internal_product_id,
                        "available_quantity": available_quantity,
                        "warehouse_id": warehouse_id
                    },
                    company_id=company_id,
                    success=True
                )
                
                # Garantir que stock_service está definido
                if not stock_service:
                    stock_service = StockService(self.db)
                
                sync_result = stock_service.sync_stock_to_ml_announcements(
                    company_id=company_id,
                    internal_product_id=internal_product_id,
                    new_quantity=Decimal(str(available_quantity)),  # Quantidade TOTAL disponível após baixa
                    warehouse_id=warehouse_id
                )
                
                if sync_result.get("success"):
                    synced_count = sync_result.get("synced_count", 0)
                    error_count = sync_result.get("error_count", 0)
                    logger.info(f"✅ Sincronização ML concluída: {synced_count} anúncio(s) atualizado(s) para produto {internal_product_id}")
                    
                    # Log global: sincronização ML concluída
                    global_logger.log_event(
                        event_type="stock_sync/ml_sync",
                        data={
                            "action": "ml_sync_completed",
                            "ml_order_id": str(order.ml_order_id),
                            "internal_product_id": internal_product_id,
                            "synced_count": synced_count,
                            "error_count": error_count,
                            "available_quantity": available_quantity,
                            "details": sync_result.get("details", [])
                        },
                        company_id=company_id,
                        success=error_count == 0,
                        error_message=f"{error_count} erro(s)" if error_count > 0 else None
                    )
                else:
                    logger.warning(f"⚠️ Erro na sincronização ML: {sync_result.get('error')}")
                    
                    # Log global: erro na sincronização ML
                    global_logger.log_event(
                        event_type="stock_sync/ml_sync",
                        data={
                            "action": "ml_sync_failed",
                            "ml_order_id": str(order.ml_order_id),
                            "internal_product_id": internal_product_id,
                            "error": sync_result.get("error", "Erro desconhecido")
                        },
                        company_id=company_id,
                        success=False,
                        error_message=sync_result.get("error", "Erro na sincronização ML")
                    )
            else:
                # Log global: produto Full ou sem internal_product_id - não sincroniza ML
                global_logger.log_event(
                    event_type="stock_sync/ml_sync",
                    data={
                        "action": "ml_sync_skipped",
                        "ml_order_id": str(order.ml_order_id),
                        "ml_item_id": ml_item_id,
                        "is_fulfillment": is_fulfillment,
                        "has_internal_product_id": internal_product_id is not None,
                        "reason": "fulfillment" if is_fulfillment else "no_internal_product_id"
                    },
                    company_id=company_id,
                    success=True
                )
            
            # Log global: sincronização completa
            global_logger.log_event(
                event_type="stock_sync/order_processing",
                data={
                    "action": "completed",
                    "ml_order_id": str(order.ml_order_id),
                    "ml_item_id": ml_item_id,
                    "quantity": quantity,
                    "available_quantity": available_quantity,
                    "is_fulfillment": is_fulfillment,
                    "synced_ml": not is_fulfillment and internal_product_id is not None
                },
                    company_id=company_id,
                    success=True
                )
            
            # Retornar sucesso mesmo se baixa falhou, desde que movimentação foi registrada
            return {
                "success": True,
                "message": f"Venda sincronizada com estoque: {quantity} unidade(s)",
                "available_quantity": available_quantity,
                "is_fulfillment": is_fulfillment,
                "stock_decreased": stock_decrease_success,
                "movement_registered": True,
                "synced_ml": not is_fulfillment and internal_product_id is not None
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao sincronizar venda com estoque: {str(e)}")
            
            # Log global: erro na sincronização
            global_logger.log_event(
                event_type="stock_sync/error",
                data={
                    "action": "sync_failed",
                    "ml_order_id": ml_order_id,
                    "ml_item_id": ml_item_id,
                    "error": str(e)
                },
                company_id=company_id,
                success=False,
                error_message=str(e)
            )
            
            return {
                "success": False,
                "error": f"Erro ao sincronizar venda: {str(e)}"
            }
    
    def get_sales_by_period(
        self,
        company_id: int,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Obtém vendas (movimentações tipo 'sale') por período"""
        try:
            date_from = datetime.utcnow() - timedelta(days=days)
            
            return self.get_movement_history(
                company_id=company_id,
                warehouse_id=warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id,
                movement_type="sale",
                date_from=date_from,
                limit=1000
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar vendas por período: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar vendas: {str(e)}"
            }

