"""
Serviço para gerenciar estoque e depósitos
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from decimal import Decimal
from datetime import datetime
from app.models.saas_models import (
    Warehouse, ProductStock, InternalProduct, MLProduct, 
    WarehouseType, Company
)

logger = logging.getLogger(__name__)


class StockService:
    """Serviço para gerenciar estoque e depósitos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_warehouse(
        self,
        company_id: int,
        name: str,
        type: str,
        address: Optional[str] = None,
        contact_info: Optional[Dict] = None,
        is_shared: bool = False
    ) -> Dict[str, Any]:
        """Cria um novo depósito"""
        try:
            # Validar entrada
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "Nome do depósito é obrigatório"
                }
            
            if not type:
                return {
                    "success": False,
                    "error": "Tipo do depósito é obrigatório"
                }
            
            # Validar tipo
            try:
                warehouse_type = WarehouseType(type.lower())
            except (ValueError, AttributeError) as e:
                return {
                    "success": False,
                    "error": f"Tipo inválido: {type}. Use 'fulfillment' ou 'custom'. Erro: {str(e)}"
                }
            
            # Verificar se é fulfillment (deve ser compartilhado e não ter company_id)
            if warehouse_type == WarehouseType.FULFILLMENT:
                is_shared = True
                company_id = None  # Fulfillment é compartilhado
            
            # Verificar se já existe depósito com mesmo nome na empresa (ou compartilhado)
            if company_id:
                existing = self.db.query(Warehouse).filter(
                    and_(
                        Warehouse.company_id == company_id,
                        Warehouse.name == name,
                        Warehouse.status == "active"
                    )
                ).first()
            else:
                # Para depósitos compartilhados, verificar por nome e is_shared
                existing = self.db.query(Warehouse).filter(
                    and_(
                        Warehouse.name == name,
                        Warehouse.is_shared == True,
                        Warehouse.status == "active"
                    )
                ).first()
            
            if existing:
                return {
                    "success": False,
                    "error": "Já existe um depósito com este nome"
                }
            
            # Criar warehouse
            # O SQLAlchemy deve converter o enum para o valor automaticamente
            warehouse = Warehouse(
                company_id=company_id,
                name=name.strip(),
                type=warehouse_type,  # Passar o enum, SQLAlchemy usa o valor (.value)
                is_shared=is_shared,
                address=address.strip() if address else None,
                contact_info=contact_info if contact_info else None,
                status="active"
            )
            
            # Log para debug
            logger.info(f"🔍 Criando warehouse: name={name}, type={warehouse_type}, type.value={warehouse_type.value}")
            
            self.db.add(warehouse)
            self.db.commit()
            self.db.refresh(warehouse)
            
            logger.info(f"✅ Depósito criado: {name} (ID: {warehouse.id}, Company: {company_id})")
            
            return {
                "success": True,
                "warehouse": {
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "type": warehouse.type.value,
                    "is_shared": warehouse.is_shared,
                    "status": warehouse.status
                }
            }
            
        except Exception as e:
            self.db.rollback()
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"❌ Erro ao criar depósito: {str(e)}\n{error_trace}")
            return {
                "success": False,
                "error": f"Erro ao criar depósito: {str(e)}"
            }
    
    def get_warehouses(self, company_id: int, include_shared: bool = True) -> Dict[str, Any]:
        """Lista depósitos da empresa (incluindo compartilhados se solicitado)"""
        try:
            query = self.db.query(Warehouse).filter(
                or_(
                    Warehouse.company_id == company_id,
                    and_(Warehouse.is_shared == True, include_shared)
                )
            ).filter(Warehouse.status == "active")
            
            warehouses = query.all()
            
            return {
                "success": True,
                "warehouses": [
                    {
                        "id": w.id,
                        "name": w.name,
                        "type": w.type.value,
                        "is_shared": w.is_shared,
                        "address": w.address,
                        "contact_info": w.contact_info,
                        "status": w.status,
                        "created_at": w.created_at.isoformat() if w.created_at else None
                    }
                    for w in warehouses
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar depósitos: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao listar depósitos: {str(e)}"
            }
    
    def get_warehouse(self, warehouse_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um depósito específico"""
        try:
            warehouse = self.db.query(Warehouse).filter(
                and_(
                    Warehouse.id == warehouse_id,
                    or_(
                        Warehouse.company_id == company_id,
                        Warehouse.is_shared == True
                    )
                )
            ).first()
            
            if not warehouse:
                return {
                    "success": False,
                    "error": "Depósito não encontrado"
                }
            
            return {
                "success": True,
                "warehouse": {
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "type": warehouse.type.value,
                    "is_shared": warehouse.is_shared,
                    "address": warehouse.address,
                    "contact_info": warehouse.contact_info,
                    "status": warehouse.status,
                    "created_at": warehouse.created_at.isoformat() if warehouse.created_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar depósito: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar depósito: {str(e)}"
            }
    
    def update_warehouse(
        self,
        warehouse_id: int,
        company_id: int,
        name: Optional[str] = None,
        address: Optional[str] = None,
        contact_info: Optional[Dict] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atualiza um depósito"""
        try:
            # Buscar depósito - pode ser próprio da empresa ou compartilhado (fulfillment)
            warehouse = self.db.query(Warehouse).filter(
                and_(
                    Warehouse.id == warehouse_id,
                    or_(
                        Warehouse.company_id == company_id,  # Depósitos próprios
                        Warehouse.is_shared == True  # Depósitos compartilhados (fulfillment)
                    )
                )
            ).first()
            
            if not warehouse:
                return {
                    "success": False,
                    "error": "Depósito não encontrado ou sem permissão"
                }
            
            # Se for depósito compartilhado (fulfillment), permitir atualizar nome e endereço
            # mas não permitir alterar status ou outros campos críticos
            if warehouse.is_shared and warehouse.company_id != company_id:
                logger.info(f"🔍 Depósito compartilhado detectado: is_shared={warehouse.is_shared}, company_id={warehouse.company_id}, user_company_id={company_id}")
                if status and status != warehouse.status:
                    logger.warning(f"⚠️ Tentativa de alterar status de depósito compartilhado: '{warehouse.status}' → '{status}'")
                    return {
                        "success": False,
                        "error": "Não é possível alterar o status de depósitos compartilhados"
                    }
                # Não permitir alterar status de depósitos compartilhados
                if status is not None:
                    status = None
            
            # Verificar se há alterações antes de atualizar
            has_changes = False
            
            # Atualizar campos apenas se foram fornecidos e são diferentes
            if name is not None:
                name = name.strip() if isinstance(name, str) else name
                if name and name != warehouse.name:
                    warehouse.name = name
                    has_changes = True
            if address is not None:
                new_address = address.strip() if isinstance(address, str) and address else address
                if new_address != warehouse.address:
                    warehouse.address = new_address
                    has_changes = True
            if contact_info is not None:
                if contact_info != warehouse.contact_info:
                    warehouse.contact_info = contact_info
                    has_changes = True
            if status is not None and status != warehouse.status:
                warehouse.status = status
                has_changes = True
            
            # Se não houver alterações, retornar sucesso sem fazer commit
            if not has_changes:
                logger.info(f"ℹ️ Nenhuma alteração detectada para depósito {warehouse_id}")
                warehouse_type_value = warehouse.type.value if hasattr(warehouse.type, 'value') else str(warehouse.type)
                return {
                    "success": True,
                    "warehouse": {
                        "id": warehouse.id,
                        "name": warehouse.name,
                        "type": warehouse_type_value,
                        "status": warehouse.status
                    },
                    "message": "Nenhuma alteração necessária"
                }
            
            warehouse.updated_at = datetime.utcnow()
            
            try:
                self.db.commit()
                self.db.refresh(warehouse)
            except Exception as commit_error:
                logger.error(f"❌ Erro no commit/refresh: {str(commit_error)}")
                import traceback
                logger.error(traceback.format_exc())
                raise
            
            logger.info(f"✅ Depósito atualizado: {warehouse.name} (ID: {warehouse.id})")
            
            # Garantir que o tipo seja convertido corretamente
            warehouse_type_value = warehouse.type.value if hasattr(warehouse.type, 'value') else str(warehouse.type)
            
            return {
                "success": True,
                "warehouse": {
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "type": warehouse_type_value,
                    "status": warehouse.status
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao atualizar depósito: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao atualizar depósito: {str(e)}"
            }
    
    def delete_warehouse(
        self,
        warehouse_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """Remove um depósito (soft delete - marca como inactive)"""
        try:
            # Buscar depósito - só pode remover próprios depósitos (não compartilhados)
            warehouse = self.db.query(Warehouse).filter(
                and_(
                    Warehouse.id == warehouse_id,
                    Warehouse.company_id == company_id,  # Só pode remover próprios depósitos
                    Warehouse.is_shared == False  # Não pode remover depósitos compartilhados
                )
            ).first()
            
            if not warehouse:
                return {
                    "success": False,
                    "error": "Depósito não encontrado, sem permissão ou é compartilhado"
                }
            
            # Verificar se há estoque com quantidade > 0 associado
            from app.models.saas_models import ProductStock
            from sqlalchemy import func
            
            # Verificar se há estoque com quantidade > 0
            stock_with_quantity = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.warehouse_id == warehouse_id,
                    ProductStock.quantity > 0
                )
            ).count()
            
            if stock_with_quantity > 0:
                return {
                    "success": False,
                    "error": f"Não é possível remover o depósito. Existem {stock_with_quantity} produto(s) com estoque neste depósito."
                }
            
            # Verificar se há movimentações associadas (opcional - para histórico)
            from app.models.saas_models import StockMovement
            movements_count = self.db.query(StockMovement).filter(
                StockMovement.warehouse_id == warehouse_id
            ).count()
            
            # Se houver movimentações, avisar mas permitir remover (soft delete mantém histórico)
            if movements_count > 0:
                logger.info(f"⚠️ Depósito {warehouse_id} tem {movements_count} movimentação(ões) no histórico")
            
            # Soft delete - marcar como inactive
            warehouse.status = "inactive"
            warehouse.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(warehouse)
            
            logger.info(f"✅ Depósito removido (inactive): {warehouse.name} (ID: {warehouse.id})")
            
            return {
                "success": True,
                "message": "Depósito removido com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao remover depósito: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao remover depósito: {str(e)}"
            }
    
    def get_or_create_product_stock(
        self,
        company_id: int,
        warehouse_id: int,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        is_fulfillment: bool = False
    ) -> ProductStock:
        """
        Obtém ou cria estoque de produto.
        
        IMPORTANTE:
        - Anúncios Full (fulfillment): estoque INDIVIDUAL por ml_item_id (cada anúncio tem seu próprio estoque)
        - Anúncios normais: estoque COMPARTILHADO por produto interno (todos os anúncios compartilham)
        """
        # Verificar se warehouse existe e é acessível
        warehouse = self.db.query(Warehouse).filter(
            and_(
                Warehouse.id == warehouse_id,
                or_(
                    Warehouse.company_id == company_id,
                    Warehouse.is_shared == True
                )
            )
        ).first()
        
        if not warehouse:
            raise ValueError("Depósito não encontrado ou sem permissão")
        
        if not internal_product_id:
            raise ValueError("internal_product_id é obrigatório para criar estoque")
        
        # Para anúncios Full: estoque individual por ml_item_id
        if is_fulfillment and ml_item_id:
            product_stock = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.company_id == company_id,
                    ProductStock.warehouse_id == warehouse_id,
                    ProductStock.internal_product_id == internal_product_id,
                    ProductStock.ml_item_id == ml_item_id  # Estoque individual para Full
                )
            ).first()
            
            if not product_stock:
                product_stock = ProductStock(
                    company_id=company_id,
                    warehouse_id=warehouse_id,
                    internal_product_id=internal_product_id,
                    ml_item_id=ml_item_id,  # Estoque individual para Full
                    quantity=Decimal("0"),
                    reserved_quantity=Decimal("0")
                )
                self.db.add(product_stock)
                self.db.flush()
            
            return product_stock
        
        # Para anúncios normais: estoque compartilhado (sem ml_item_id)
        product_stock = self.db.query(ProductStock).filter(
            and_(
                ProductStock.company_id == company_id,
                ProductStock.warehouse_id == warehouse_id,
                ProductStock.internal_product_id == internal_product_id,
                ProductStock.ml_item_id.is_(None)  # Estoque compartilhado
            )
        ).first()
        
        if not product_stock:
            product_stock = ProductStock(
                company_id=company_id,
                warehouse_id=warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=None,  # Estoque compartilhado para anúncios normais
                quantity=Decimal("0"),
                reserved_quantity=Decimal("0")
            )
            self.db.add(product_stock)
            self.db.flush()
        
        return product_stock
    
    def get_product_stock(
        self,
        company_id: int,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obtém estoque de produto"""
        try:
            query = self.db.query(ProductStock).filter(
                ProductStock.company_id == company_id
            )
            
            if internal_product_id:
                query = query.filter(ProductStock.internal_product_id == internal_product_id)
            if ml_item_id:
                query = query.filter(ProductStock.ml_item_id == ml_item_id)
            if warehouse_id:
                query = query.filter(ProductStock.warehouse_id == warehouse_id)
            
            # Contar total antes de aplicar limit/offset
            total = query.count()
            
            # Aplicar paginação se fornecida
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            stocks = query.all()
            
            result_stocks = []
            for s in stocks:
                stock_data = {
                    "id": s.id,
                    "product_stock_id": s.id,  # Adicionar para compatibilidade
                    "warehouse_id": s.warehouse_id,
                    "warehouse_name": s.warehouse.name if s.warehouse else None,
                    "warehouse_type": s.warehouse.type.value if s.warehouse and s.warehouse.type else None,
                    "internal_product_id": s.internal_product_id,
                    "ml_item_id": s.ml_item_id,
                    "quantity": float(s.quantity),
                    "reserved_quantity": float(s.reserved_quantity),
                    "available_quantity": float(s.quantity - s.reserved_quantity),
                    "min_stock": float(s.min_stock) if s.min_stock else None,
                    "max_stock": float(s.max_stock) if s.max_stock else None,
                    "reorder_point": float(s.reorder_point) if s.reorder_point else None
                }
                
                # Adicionar informações do produto interno
                if s.internal_product:
                    stock_data["product_name"] = s.internal_product.name
                    stock_data["product_sku"] = s.internal_product.internal_sku
                elif s.internal_product_id:
                    product = self.db.query(InternalProduct).filter(
                        InternalProduct.id == s.internal_product_id
                    ).first()
                    if product:
                        stock_data["product_name"] = product.name
                        stock_data["product_sku"] = product.internal_sku
                
                # Adicionar informações do anúncio ML
                if s.ml_item_id:
                    try:
                        ml_product = self.db.query(MLProduct).filter(
                            MLProduct.ml_item_id == s.ml_item_id,
                            MLProduct.company_id == company_id
                        ).first()
                        if ml_product:
                            stock_data["announcement_title"] = ml_product.title if ml_product.title else None
                            stock_data["announcement_sku"] = getattr(ml_product, 'seller_sku', None) or ml_product.ml_item_id
                    except Exception as e:
                        logger.warning(f"Erro ao buscar informações do anúncio ML {s.ml_item_id}: {str(e)}")
                        stock_data["announcement_title"] = None
                        stock_data["announcement_sku"] = s.ml_item_id
                
                result_stocks.append(stock_data)
            
            return {
                "success": True,
                "stocks": result_stocks,
                "total": total,
                "limit": limit,
                "offset": offset or 0,
                "total_quantity": sum(float(s.quantity) for s in stocks),
                "total_reserved": sum(float(s.reserved_quantity) for s in stocks),
                "total_available": sum(float(s.quantity - s.reserved_quantity) for s in stocks)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar estoque: {str(e)}"
            }
    
    def get_all_stocks_for_product(
        self,
        company_id: int,
        internal_product_id: int
    ) -> Dict[str, Any]:
        """Obtém todo o estoque de um produto (todos os depósitos)"""
        return self.get_product_stock(
            company_id=company_id,
            internal_product_id=internal_product_id
        )
    
    def get_stock_by_announcement(
        self,
        company_id: int,
        ml_item_id: str,
        warehouse_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obtém estoque por anúncio (ml_item_id)"""
        return self.get_product_stock(
            company_id=company_id,
            ml_item_id=ml_item_id,
            warehouse_id=warehouse_id
        )
    
    def update_stock(
        self,
        company_id: int,
        warehouse_id: int,
        quantity: float,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        movement_type: str = "adjustment"
    ) -> Dict[str, Any]:
        """Atualiza estoque (entrada/saída)"""
        try:
            product_stock = self.get_or_create_product_stock(
                company_id=company_id,
                warehouse_id=warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id
            )
            
            previous_quantity = product_stock.quantity
            new_quantity = previous_quantity + Decimal(str(quantity))
            
            if new_quantity < 0:
                return {
                    "success": False,
                    "error": "Estoque insuficiente"
                }
            
            product_stock.quantity = new_quantity
            product_stock.last_movement_date = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(product_stock)
            
            # Registrar movimentação (será feito pelo stock_movement_service)
            from app.services.stock_movement_service import StockMovementService
            movement_service = StockMovementService(self.db)
            movement_service.record_movement(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_stock_id=product_stock.id,
                movement_type=movement_type,
                quantity=quantity,
                previous_quantity=float(previous_quantity),
                new_quantity=float(new_quantity)
            )
            
            logger.info(f"✅ Estoque atualizado: {quantity} unidades (Warehouse: {warehouse_id})")
            
            return {
                "success": True,
                "product_stock": {
                    "id": product_stock.id,
                    "quantity": float(product_stock.quantity),
                    "reserved_quantity": float(product_stock.reserved_quantity),
                    "available_quantity": float(product_stock.quantity - product_stock.reserved_quantity)
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao atualizar estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao atualizar estoque: {str(e)}"
            }
    
    def set_stock_quantity(
        self,
        company_id: int,
        product_stock_id: int,
        new_quantity: float,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Define a quantidade absoluta do estoque"""
        try:
            product_stock = self.db.query(ProductStock).filter(
                ProductStock.id == product_stock_id,
                ProductStock.company_id == company_id
            ).first()
            
            if not product_stock:
                return {
                    "success": False,
                    "error": "Estoque não encontrado"
                }
            
            previous_quantity = float(product_stock.quantity)
            quantity_difference = Decimal(str(new_quantity)) - product_stock.quantity
            
            if new_quantity < 0:
                return {
                    "success": False,
                    "error": "Quantidade não pode ser negativa"
                }
            
            product_stock.quantity = Decimal(str(new_quantity))
            product_stock.last_movement_date = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(product_stock)
            
            # Registrar movimentação
            from app.services.stock_movement_service import StockMovementService
            movement_service = StockMovementService(self.db)
            movement_service.record_movement(
                company_id=company_id,
                warehouse_id=product_stock.warehouse_id,
                product_stock_id=product_stock.id,
                movement_type="adjustment",
                quantity=float(quantity_difference),
                previous_quantity=previous_quantity,
                new_quantity=float(new_quantity),
                notes=notes or f"Atualização manual: {previous_quantity} → {new_quantity}"
            )
            
            logger.info(f"✅ Quantidade de estoque definida: {previous_quantity} → {new_quantity} (Stock ID: {product_stock_id})")
            
            return {
                "success": True,
                "stock": {
                    "id": product_stock.id,
                    "quantity": float(product_stock.quantity),
                    "previous_quantity": float(previous_quantity),
                    "new_quantity": float(new_quantity)
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao atualizar estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao atualizar estoque: {str(e)}"
            }
    
    def reserve_stock(
        self,
        company_id: int,
        warehouse_id: int,
        quantity: float,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reserva estoque para pedido"""
        try:
            product_stock = self.get_or_create_product_stock(
                company_id=company_id,
                warehouse_id=warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id
            )
            
            available = product_stock.quantity - product_stock.reserved_quantity
            
            if available < Decimal(str(quantity)):
                return {
                    "success": False,
                    "error": "Estoque disponível insuficiente para reserva"
                }
            
            product_stock.reserved_quantity += Decimal(str(quantity))
            
            self.db.commit()
            self.db.refresh(product_stock)
            
            logger.info(f"✅ Estoque reservado: {quantity} unidades (Warehouse: {warehouse_id})")
            
            return {
                "success": True,
                "reserved_quantity": float(product_stock.reserved_quantity),
                "available_quantity": float(product_stock.quantity - product_stock.reserved_quantity)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao reservar estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao reservar estoque: {str(e)}"
            }
    
    def release_stock(
        self,
        company_id: int,
        warehouse_id: int,
        quantity: float,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Libera reserva de estoque"""
        try:
            product_stock = self.get_or_create_product_stock(
                company_id=company_id,
                warehouse_id=warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id
            )
            
            if product_stock.reserved_quantity < Decimal(str(quantity)):
                return {
                    "success": False,
                    "error": "Quantidade reservada insuficiente para liberação"
                }
            
            product_stock.reserved_quantity -= Decimal(str(quantity))
            
            self.db.commit()
            self.db.refresh(product_stock)
            
            logger.info(f"✅ Estoque liberado: {quantity} unidades (Warehouse: {warehouse_id})")
            
            return {
                "success": True,
                "reserved_quantity": float(product_stock.reserved_quantity),
                "available_quantity": float(product_stock.quantity - product_stock.reserved_quantity)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao liberar estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao liberar estoque: {str(e)}"
            }
    
    def transfer_stock(
        self,
        company_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        quantity: float,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transfere estoque entre depósitos"""
        try:
            # Verificar se ambos os depósitos são acessíveis
            from_warehouse = self.db.query(Warehouse).filter(
                and_(
                    Warehouse.id == from_warehouse_id,
                    or_(
                        Warehouse.company_id == company_id,
                        Warehouse.is_shared == True
                    )
                )
            ).first()
            
            to_warehouse = self.db.query(Warehouse).filter(
                and_(
                    Warehouse.id == to_warehouse_id,
                    or_(
                        Warehouse.company_id == company_id,
                        Warehouse.is_shared == True
                    )
                )
            ).first()
            
            if not from_warehouse or not to_warehouse:
                return {
                    "success": False,
                    "error": "Depósito não encontrado ou sem permissão"
                }
            
            # Obter estoque de origem
            from_stock = self.get_or_create_product_stock(
                company_id=company_id,
                warehouse_id=from_warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id
            )
            
            available = from_stock.quantity - from_stock.reserved_quantity
            
            if available < Decimal(str(quantity)):
                return {
                    "success": False,
                    "error": "Estoque disponível insuficiente para transferência"
                }
            
            # Remover do depósito de origem
            from_stock.quantity -= Decimal(str(quantity))
            
            # Adicionar ao depósito de destino
            to_stock = self.get_or_create_product_stock(
                company_id=company_id,
                warehouse_id=to_warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id
            )
            
            to_stock.quantity += Decimal(str(quantity))
            
            self.db.commit()
            
            # Registrar movimentações
            from app.services.stock_movement_service import StockMovementService
            movement_service = StockMovementService(self.db)
            
            movement_service.record_movement(
                company_id=company_id,
                warehouse_id=from_warehouse_id,
                product_stock_id=from_stock.id,
                movement_type="transfer",
                quantity=-quantity,
                previous_quantity=float(from_stock.quantity + Decimal(str(quantity))),
                new_quantity=float(from_stock.quantity),
                reference_type="transfer",
                reference_id=to_warehouse_id
            )
            
            movement_service.record_movement(
                company_id=company_id,
                warehouse_id=to_warehouse_id,
                product_stock_id=to_stock.id,
                movement_type="transfer",
                quantity=quantity,
                previous_quantity=float(to_stock.quantity - Decimal(str(quantity))),
                new_quantity=float(to_stock.quantity),
                reference_type="transfer",
                reference_id=from_warehouse_id
            )
            
            logger.info(f"✅ Estoque transferido: {quantity} unidades de {from_warehouse_id} para {to_warehouse_id}")
            
            return {
                "success": True,
                "from_warehouse": {
                    "id": from_warehouse_id,
                    "quantity": float(from_stock.quantity)
                },
                "to_warehouse": {
                    "id": to_warehouse_id,
                    "quantity": float(to_stock.quantity)
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao transferir estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao transferir estoque: {str(e)}"
            }
    
    def configure_announcement_warehouse(
        self,
        company_id: int,
        internal_product_id: int,
        ml_item_id: str,
        warehouse_id: int
    ) -> Dict[str, Any]:
        """Configura qual depósito um anúncio específico deve usar"""
        try:
            # Validar que o produto interno pertence à empresa
            internal_product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.id == internal_product_id,
                    InternalProduct.company_id == company_id
                )
            ).first()
            
            if not internal_product:
                return {
                    "success": False,
                    "error": "Produto interno não encontrado"
                }
            
            # Validar que o depósito é acessível
            warehouse = self.db.query(Warehouse).filter(
                and_(
                    Warehouse.id == warehouse_id,
                    or_(
                        Warehouse.company_id == company_id,
                        Warehouse.is_shared == True
                    ),
                    Warehouse.status == "active"
                )
            ).first()
            
            if not warehouse:
                return {
                    "success": False,
                    "error": "Depósito não encontrado ou sem permissão"
                }
            
            # Verificar se o anúncio está associado ao produto interno (via SKUManagement)
            from app.models.saas_models import SKUManagement
            sku_management = self.db.query(SKUManagement).filter(
                and_(
                    SKUManagement.internal_product_id == internal_product_id,
                    SKUManagement.company_id == company_id,
                    SKUManagement.platform_item_id == ml_item_id,
                    SKUManagement.status == "active"
                )
            ).first()
            
            if not sku_management:
                return {
                    "success": False,
                    "error": "Anúncio não está associado a este produto interno"
                }
            
            # Buscar quantidade disponível do anúncio no ML
            ml_product = self.db.query(MLProduct).filter(
                and_(
                    MLProduct.ml_item_id == ml_item_id,
                    MLProduct.company_id == company_id
                )
            ).first()
            
            ml_available_quantity = Decimal("0")
            if ml_product and ml_product.available_quantity:
                ml_available_quantity = Decimal(str(ml_product.available_quantity))
            
            # Determinar se é anúncio Full (fulfillment)
            is_fulfillment = False
            if ml_product:
                # Verificar no campo shipping (JSON)
                if ml_product.shipping:
                    import json
                    if isinstance(ml_product.shipping, str):
                        try:
                            shipping_data = json.loads(ml_product.shipping)
                        except:
                            shipping_data = {}
                    else:
                        shipping_data = ml_product.shipping
                    
                    logistic_type = shipping_data.get("logistic_type")
                    if logistic_type == "fulfillment":
                        is_fulfillment = True
                
                # Verificar também nas tags
                if not is_fulfillment and ml_product.tags:
                    tags_list = ml_product.tags if isinstance(ml_product.tags, list) else []
                    if any(tag in ["fulfillment", "meli_fulfillment", "FULL"] for tag in tags_list):
                        is_fulfillment = True
                
                logger.info(f"🔍 Anúncio {ml_item_id}: is_fulfillment={is_fulfillment}, warehouse_id={warehouse_id}")
            
            # Para anúncios Full: estoque individual por ml_item_id
            # Para anúncios normais: estoque compartilhado (sem ml_item_id)
            if is_fulfillment:
                # Buscar estoque individual existente para este anúncio Full
                existing_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.internal_product_id == internal_product_id,
                        ProductStock.ml_item_id == ml_item_id  # Estoque individual para Full
                    )
                ).first()
                
                # Se já existe estoque em outro depósito, transferir quantidade
                if existing_stock and existing_stock.warehouse_id != warehouse_id:
                    if existing_stock.quantity > 0:
                        # Transferir estoque para o novo depósito
                        product_stock = self.get_or_create_product_stock(
                            company_id=company_id,
                            warehouse_id=warehouse_id,
                            internal_product_id=internal_product_id,
                            ml_item_id=ml_item_id,  # Estoque individual para Full
                            is_fulfillment=True
                        )
                        product_stock.quantity = existing_stock.quantity
                        product_stock.reserved_quantity = existing_stock.reserved_quantity
                        # Marcar estoque antigo como zero
                        existing_stock.quantity = Decimal("0")
                        existing_stock.reserved_quantity = Decimal("0")
                    else:
                        product_stock = self.get_or_create_product_stock(
                            company_id=company_id,
                            warehouse_id=warehouse_id,
                            internal_product_id=internal_product_id,
                            ml_item_id=ml_item_id,  # Estoque individual para Full
                            is_fulfillment=True
                        )
                else:
                    # Buscar ou criar ProductStock individual para Full
                    product_stock = self.get_or_create_product_stock(
                        company_id=company_id,
                        warehouse_id=warehouse_id,
                        internal_product_id=internal_product_id,
                        ml_item_id=ml_item_id,  # Estoque individual para Full
                        is_fulfillment=True
                    )
            else:
                # Anúncios normais: estoque compartilhado
                existing_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.internal_product_id == internal_product_id,
                        ProductStock.ml_item_id.is_(None)  # Estoque compartilhado
                    )
                ).first()
                
                # Se já existe estoque em outro depósito, transferir quantidade
                if existing_stock and existing_stock.warehouse_id != warehouse_id:
                    if existing_stock.quantity > 0:
                        # Transferir estoque para o novo depósito
                        product_stock = self.get_or_create_product_stock(
                            company_id=company_id,
                            warehouse_id=warehouse_id,
                            internal_product_id=internal_product_id,
                            ml_item_id=None,  # Estoque compartilhado
                            is_fulfillment=False
                        )
                        product_stock.quantity = existing_stock.quantity
                        product_stock.reserved_quantity = existing_stock.reserved_quantity
                        # Marcar estoque antigo como zero
                        existing_stock.quantity = Decimal("0")
                        existing_stock.reserved_quantity = Decimal("0")
                    else:
                        product_stock = self.get_or_create_product_stock(
                            company_id=company_id,
                            warehouse_id=warehouse_id,
                            internal_product_id=internal_product_id,
                            ml_item_id=None,  # Estoque compartilhado
                            is_fulfillment=False
                        )
                else:
                    # Buscar ou criar ProductStock compartilhado
                    product_stock = self.get_or_create_product_stock(
                        company_id=company_id,
                        warehouse_id=warehouse_id,
                        internal_product_id=internal_product_id,
                        ml_item_id=None,  # Estoque compartilhado
                        is_fulfillment=False
                    )
            
            # Se o estoque está vazio (0) e há quantidade disponível no ML, importar
            if product_stock.quantity == 0 and ml_available_quantity > 0:
                previous_quantity = product_stock.quantity
                product_stock.quantity = ml_available_quantity
                product_stock.last_movement_date = datetime.utcnow()
                
                # Registrar movimentação de entrada (importação)
                from app.services.stock_movement_service import StockMovementService
                movement_service = StockMovementService(self.db)
                movement_service.record_movement(
                    company_id=company_id,
                    warehouse_id=warehouse_id,
                    product_stock_id=product_stock.id,
                    movement_type="in",
                    quantity=float(ml_available_quantity),
                    previous_quantity=float(previous_quantity),
                    new_quantity=float(product_stock.quantity),
                    notes=f"Importação automática da quantidade do anúncio ML ({ml_item_id})"
                )
                
                logger.info(f"📦 Quantidade importada do ML: {ml_available_quantity} unidades para anúncio {ml_item_id}")
            
            product_stock.warehouse_id = warehouse_id
            product_stock.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(product_stock)
            
            logger.info(f"✅ Depósito configurado para anúncio {ml_item_id}: Warehouse {warehouse_id}, Quantidade: {product_stock.quantity}")
            
            return {
                "success": True,
                "message": "Depósito configurado com sucesso",
                "product_stock": {
                    "id": product_stock.id,
                    "warehouse_id": product_stock.warehouse_id,
                    "warehouse_name": warehouse.name,
                    "quantity": float(product_stock.quantity),
                    "reserved_quantity": float(product_stock.reserved_quantity)
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao configurar depósito do anúncio: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Erro ao configurar depósito: {str(e)}"
            }
    
    def bulk_configure_announcement_warehouse(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id_fulfillment: Optional[int] = None,
        warehouse_id_normal: Optional[int] = None
    ) -> Dict[str, Any]:
        """Configura depósitos em massa para anúncios de um produto interno"""
        try:
            # Validar que o produto interno pertence à empresa
            internal_product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.id == internal_product_id,
                    InternalProduct.company_id == company_id
                )
            ).first()
            
            if not internal_product:
                return {
                    "success": False,
                    "error": "Produto interno não encontrado"
                }
            
            # Buscar todos os anúncios do produto interno
            from app.services.internal_product_service import InternalProductService
            internal_service = InternalProductService(self.db)
            announcements_result = internal_service.get_ml_announcements_by_internal_product(
                internal_product_id=internal_product_id,
                company_id=company_id
            )
            
            if not announcements_result.get("success"):
                return {
                    "success": False,
                    "error": announcements_result.get("error", "Erro ao buscar anúncios")
                }
            
            announcements = announcements_result.get("announcements", [])
            
            if not announcements:
                return {
                    "success": False,
                    "error": "Nenhum anúncio encontrado para este produto"
                }
            
            # Separar anúncios Full e normais
            full_announcements = [ann for ann in announcements if ann.get("is_fulfillment", False)]
            normal_announcements = [ann for ann in announcements if not ann.get("is_fulfillment", False)]
            
            success_count = 0
            error_count = 0
            errors = []
            
            # Configurar anúncios Full
            if warehouse_id_fulfillment:
                for announcement in full_announcements:
                    ml_item_id = announcement.get("ml_item_id")
                    if not ml_item_id:
                        error_count += 1
                        errors.append(f"Anúncio sem ID: {announcement.get('title', 'Desconhecido')}")
                        continue
                    
                    result = self.configure_announcement_warehouse(
                        company_id=company_id,
                        internal_product_id=internal_product_id,
                        ml_item_id=ml_item_id,
                        warehouse_id=warehouse_id_fulfillment
                    )
                    
                    if result.get("success"):
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Anúncio {ml_item_id}: {result.get('error', 'Erro desconhecido')}")
            
            # Configurar anúncios normais
            if warehouse_id_normal:
                for announcement in normal_announcements:
                    ml_item_id = announcement.get("ml_item_id")
                    if not ml_item_id:
                        error_count += 1
                        errors.append(f"Anúncio sem ID: {announcement.get('title', 'Desconhecido')}")
                        continue
                    
                    result = self.configure_announcement_warehouse(
                        company_id=company_id,
                        internal_product_id=internal_product_id,
                        ml_item_id=ml_item_id,
                        warehouse_id=warehouse_id_normal
                    )
                    
                    if result.get("success"):
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Anúncio {ml_item_id}: {result.get('error', 'Erro desconhecido')}")
            
            logger.info(f"✅ Configuração em massa concluída: {success_count} sucesso(s), {error_count} erro(s)")
            
            return {
                "success": True,
                "message": f"Configuração em massa concluída: {success_count} anúncio(s) configurado(s) com sucesso",
                "success_count": success_count,
                "error_count": error_count,
                "total_processed": success_count + error_count,
                "full_count": len(full_announcements),
                "normal_count": len(normal_announcements),
                "errors": errors if errors else None
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao configurar depósitos em massa: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Erro ao configurar depósitos em massa: {str(e)}"
            }
    
    def bulk_configure_all_announcements_warehouse(
        self,
        company_id: int,
        warehouse_id_fulfillment: Optional[int] = None,
        warehouse_id_normal: Optional[int] = None
    ) -> Dict[str, Any]:
        """Configura depósitos em massa para TODOS os anúncios da empresa"""
        try:
            from app.models.saas_models import SKUManagement, MLProduct
            
            # Buscar todos os SKUManagement ativos da empresa
            sku_managements = self.db.query(SKUManagement).filter(
                and_(
                    SKUManagement.company_id == company_id,
                    SKUManagement.status == "active",
                    SKUManagement.platform_item_id.isnot(None)
                )
            ).all()
            
            if not sku_managements:
                return {
                    "success": True,
                    "message": "Nenhum anúncio encontrado para configurar",
                    "success_count": 0,
                    "error_count": 0,
                    "total_processed": 0
                }
            
            # Coletar todos os ml_item_ids únicos
            ml_item_ids = list(set([sm.platform_item_id for sm in sku_managements if sm.platform_item_id]))
            
            # Buscar todos os MLProducts da empresa
            ml_products = self.db.query(MLProduct).filter(
                and_(
                    MLProduct.company_id == company_id,
                    MLProduct.ml_item_id.in_(ml_item_ids)
                )
            ).all()
            
            # Criar um mapa de ml_item_id -> (internal_product_id, is_fulfillment)
            announcements_map = {}
            for ml_product in ml_products:
                # Buscar o internal_product_id via SKUManagement
                sku_mgmt = next((sm for sm in sku_managements if sm.platform_item_id == ml_product.ml_item_id), None)
                if sku_mgmt and sku_mgmt.internal_product_id:
                    # Determinar se é fulfillment
                    is_fulfillment = False
                    
                    # Verificar no campo shipping (JSON)
                    if ml_product.shipping:
                        import json
                        if isinstance(ml_product.shipping, str):
                            try:
                                shipping_data = json.loads(ml_product.shipping)
                            except:
                                shipping_data = {}
                        else:
                            shipping_data = ml_product.shipping
                        
                        logistic_type = shipping_data.get("logistic_type")
                        if logistic_type == "fulfillment":
                            is_fulfillment = True
                    
                    # Verificar também nas tags
                    if not is_fulfillment and ml_product.tags:
                        tags_list = ml_product.tags if isinstance(ml_product.tags, list) else []
                        if any(tag in ["fulfillment", "meli_fulfillment", "FULL"] for tag in tags_list):
                            is_fulfillment = True
                    
                    announcements_map[ml_product.ml_item_id] = {
                        "internal_product_id": sku_mgmt.internal_product_id,
                        "is_fulfillment": is_fulfillment
                    }
            
            logger.info(f"📊 Total de anúncios mapeados: {len(announcements_map)}")
            full_count = sum(1 for data in announcements_map.values() if data.get("is_fulfillment", False))
            normal_count = len(announcements_map) - full_count
            logger.info(f"📊 Anúncios Full: {full_count}, Anúncios normais: {normal_count}")
            
            success_count = 0
            error_count = 0
            errors = []
            
            # Processar anúncios Full
            if warehouse_id_fulfillment:
                full_announcements = [ml_id for ml_id, data in announcements_map.items() if data.get("is_fulfillment", False)]
                logger.info(f"🔧 Configurando {len(full_announcements)} anúncios Full para warehouse {warehouse_id_fulfillment}")
                
                for ml_item_id in full_announcements:
                    data = announcements_map[ml_item_id]
                    result = self.configure_announcement_warehouse(
                        company_id=company_id,
                        internal_product_id=data["internal_product_id"],
                        ml_item_id=ml_item_id,
                        warehouse_id=warehouse_id_fulfillment
                    )
                    
                    if result.get("success"):
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Anúncio {ml_item_id}: {result.get('error', 'Erro desconhecido')}")
            
            # Processar anúncios não-Full
            if warehouse_id_normal:
                normal_announcements = [ml_id for ml_id, data in announcements_map.items() if not data.get("is_fulfillment", False)]
                
                for ml_item_id in normal_announcements:
                    data = announcements_map[ml_item_id]
                    result = self.configure_announcement_warehouse(
                        company_id=company_id,
                        internal_product_id=data["internal_product_id"],
                        ml_item_id=ml_item_id,
                        warehouse_id=warehouse_id_normal
                    )
                    
                    if result.get("success"):
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Anúncio {ml_item_id}: {result.get('error', 'Erro desconhecido')}")
            
            logger.info(f"✅ Configuração em massa (todos os anúncios) concluída: {success_count} sucesso(s), {error_count} erro(s)")
            
            return {
                "success": True,
                "message": f"Configuração em massa concluída: {success_count} anúncio(s) configurado(s) com sucesso",
                "success_count": success_count,
                "error_count": error_count,
                "total_processed": success_count + error_count,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao configurar depósitos em massa (todos os anúncios): {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Erro ao configurar depósitos em massa: {str(e)}"
            }
    
    def get_announcement_warehouse_config(
        self,
        company_id: int,
        internal_product_id: int
    ) -> Dict[str, Any]:
        """Lista configurações de estoque por anúncio de um produto interno"""
        try:
            # Validar que o produto interno pertence à empresa
            internal_product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.id == internal_product_id,
                    InternalProduct.company_id == company_id
                )
            ).first()
            
            if not internal_product:
                return {
                    "success": False,
                    "error": "Produto interno não encontrado"
                }
            
            # Buscar anúncios associados via SKUManagement
            from app.models.saas_models import SKUManagement, MLProduct
            from app.services.internal_product_service import InternalProductService
            
            internal_service = InternalProductService(self.db)
            announcements_result = internal_service.get_ml_announcements_by_internal_product(
                internal_product_id=internal_product_id,
                company_id=company_id
            )
            
            if not announcements_result.get("success"):
                return announcements_result
            
            announcements_data = announcements_result.get("announcements", [])
            configs = []
            
            # Para cada anúncio, buscar configuração de estoque
            # IMPORTANTE: Anúncios Full têm estoque individual, anúncios normais compartilham estoque
            for announcement in announcements_data:
                ml_item_id = announcement.get("ml_item_id")
                is_fulfillment = announcement.get("is_fulfillment", False)
                
                warehouse_info = None
                stock_info = {
                    "quantity": 0.0,
                    "reserved_quantity": 0.0,
                    "available_quantity": 0.0
                }
                
                # Para anúncios Full: buscar estoque individual por ml_item_id
                # Para anúncios normais: buscar estoque compartilhado (sem ml_item_id)
                if is_fulfillment:
                    product_stock = self.db.query(ProductStock).filter(
                        and_(
                            ProductStock.company_id == company_id,
                            ProductStock.internal_product_id == internal_product_id,
                            ProductStock.ml_item_id == ml_item_id  # Estoque individual para Full
                        )
                    ).first()
                else:
                    product_stock = self.db.query(ProductStock).filter(
                        and_(
                            ProductStock.company_id == company_id,
                            ProductStock.internal_product_id == internal_product_id,
                            ProductStock.ml_item_id.is_(None)  # Estoque compartilhado
                        )
                    ).first()
                
                if product_stock:
                    # Buscar informações do depósito
                    warehouse = self.db.query(Warehouse).filter(
                        Warehouse.id == product_stock.warehouse_id
                    ).first()
                    
                    if warehouse:
                        warehouse_info = {
                            "id": warehouse.id,
                            "name": warehouse.name,
                            "type": warehouse.type.value if hasattr(warehouse.type, 'value') else str(warehouse.type),
                            "is_shared": warehouse.is_shared
                        }
                    
                    stock_info = {
                        "quantity": float(product_stock.quantity),
                        "reserved_quantity": float(product_stock.reserved_quantity),
                        "available_quantity": float(product_stock.quantity - product_stock.reserved_quantity),
                        "product_stock_id": product_stock.id
                    }
                
                configs.append({
                    "ml_item_id": ml_item_id,
                    "title": announcement.get("title", ""),
                    "status": announcement.get("status", ""),
                    "available_quantity_ml": announcement.get("available_quantity", 0),
                    "warehouse": warehouse_info,
                    "stock": stock_info
                })
            
            return {
                "success": True,
                "internal_product": {
                    "id": internal_product.id,
                    "name": internal_product.name,
                    "internal_sku": internal_product.internal_sku
                },
                "announcements": configs,
                "count": len(configs)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar configurações de estoque: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Erro ao buscar configurações: {str(e)}"
            }
    
    def clear_all_stocks(
        self,
        company_id: int
    ) -> Dict[str, Any]:
        """Remove todos os estoques da empresa"""
        try:
            # Buscar todos os estoques da empresa
            stocks = self.db.query(ProductStock).filter(
                ProductStock.company_id == company_id
            ).all()
            
            deleted_count = len(stocks)
            
            if deleted_count == 0:
                return {
                    "success": True,
                    "message": "Nenhum estoque encontrado para remover",
                    "deleted_count": 0
                }
            
            # Remover todos os estoques
            for stock in stocks:
                self.db.delete(stock)
            
            self.db.commit()
            
            logger.info(f"✅ Todos os estoques removidos: {deleted_count} registro(s) da empresa {company_id}")
            
            return {
                "success": True,
                "message": f"Todos os estoques foram removidos com sucesso",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao limpar todos os estoques: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Erro ao limpar estoques: {str(e)}"
            }

