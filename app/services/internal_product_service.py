"""
Serviço para gerenciar produtos internos/customizados
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.saas_models import InternalProduct, Product, Company

logger = logging.getLogger(__name__)


class InternalProductService:
    """Serviço para gerenciar produtos internos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_internal_product(
        self, 
        company_id: int,
        name: str,
        internal_sku: str,
        base_product_id: Optional[int] = None,
        description: Optional[str] = None,
        cost_price: Optional[float] = None,
        selling_price: Optional[float] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        supplier: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Cria um novo produto interno"""
        try:
            # Verificar se o SKU interno já existe na empresa usando SKU Management
            from app.services.sku_management_service import SKUManagementService
            sku_service = SKUManagementService(self.db)
            
            # Não bloquear se SKU existe, apenas registrar nova associação
            
            # Se base_product_id foi fornecido, verificar se existe
            base_product = None
            if base_product_id:
                base_product = self.db.query(Product).filter(
                    and_(
                        Product.id == base_product_id,
                        Product.company_id == company_id
                    )
                ).first()
                
                if not base_product:
                    return {"error": "Produto base não encontrado"}
            
            # Criar o produto interno
            internal_product = InternalProduct(
                company_id=company_id,
                base_product_id=base_product_id,
                name=name,
                description=description,
                internal_sku=internal_sku,
                cost_price=cost_price,
                selling_price=selling_price,
                category=category,
                brand=brand,
                supplier=supplier,
                **kwargs
            )
            
            self.db.add(internal_product)
            self.db.commit()
            self.db.refresh(internal_product)
            
            # Registrar SKU no sistema de gerenciamento
            try:
                platform_item_id = base_product.ml_item_id if base_product else f"INTERNAL-{internal_product.id}"
                sku_service.register_sku(
                    sku=internal_sku,
                    platform="mercadolivre" if base_product else "internal",
                    platform_item_id=platform_item_id,
                    company_id=company_id,
                    product_id=base_product_id,
                    internal_product_id=internal_product.id
                )
            except Exception as e:
                logger.warning(f"Erro ao registrar SKU no sistema: {e}")
                # Não falha a criação do produto se o registro do SKU falhar
            
            return {
                "success": True,
                "product": {
                    "id": internal_product.id,
                    "name": internal_product.name,
                    "internal_sku": internal_product.internal_sku,
                    "base_product_id": internal_product.base_product_id,
                    "created_at": internal_product.created_at
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar produto interno: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def get_internal_products(
        self, 
        company_id: int,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lista produtos internos da empresa"""
        try:
            query = self.db.query(InternalProduct).filter(
                InternalProduct.company_id == company_id
            )
            
            # Filtros opcionais
            if status:
                query = query.filter(InternalProduct.status == status)
            
            if category:
                query = query.filter(InternalProduct.category == category)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        InternalProduct.name.ilike(search_term),
                        InternalProduct.internal_sku.ilike(search_term),
                        InternalProduct.description.ilike(search_term)
                    )
                )
            
            # Contar total
            total = query.count()
            
            # Aplicar paginação
            products = query.offset(offset).limit(limit).all()
            
            # Buscar contagem de anúncios associados para cada produto
            from app.models.saas_models import SKUManagement
            product_announcements = {}
            for product in products:
                announcements_count = self.db.query(SKUManagement).filter(
                    and_(
                        SKUManagement.internal_product_id == product.id,
                        SKUManagement.status == "active"
                    )
                ).count()
                product_announcements[product.id] = announcements_count
            
            return {
                "success": True,
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "internal_sku": p.internal_sku,
                        "description": p.description,
                        "cost_price": float(p.cost_price) if p.cost_price else None,
                        "selling_price": float(p.selling_price) if p.selling_price else None,
                        "category": p.category,
                        "brand": p.brand,
                        "status": p.status,
                        "current_stock": p.current_stock,
                        "base_product_id": p.base_product_id,
                        "main_image": p.main_image,
                        "tax_rate": float(p.tax_rate) if p.tax_rate else 0.0,
                        "marketing_cost": float(p.marketing_cost) if p.marketing_cost else 0.0,
                        "other_costs": float(p.other_costs) if p.other_costs else 0.0,
                        "expected_profit_margin": float(p.expected_profit_margin) if p.expected_profit_margin else 0.0,
                        "announcements_count": product_announcements.get(p.id, 0),
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                        "updated_at": p.updated_at.isoformat() if p.updated_at else None
                    }
                    for p in products
                ],
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Erro ao listar produtos internos: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def get_internal_product(self, product_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um produto interno específico"""
        try:
            product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.id == product_id,
                    InternalProduct.company_id == company_id
                )
            ).first()
            
            if not product:
                return {"error": "Produto interno não encontrado"}
            
            # Buscar produto base se existir
            base_product = None
            if product.base_product_id:
                base_product = self.db.query(Product).filter(
                    Product.id == product.base_product_id
                ).first()
            
            return {
                "success": True,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "internal_sku": product.internal_sku,
                    "barcode": product.barcode,
                    "cost_price": float(product.cost_price) if product.cost_price else None,
                    "selling_price": float(product.selling_price) if product.selling_price else None,
                    "tax_rate": float(product.tax_rate) if product.tax_rate else None,
                    "marketing_cost": float(product.marketing_cost) if product.marketing_cost else None,
                    "other_costs": float(product.other_costs) if product.other_costs else None,
                    "category": product.category,
                    "brand": product.brand,
                    "model": product.model,
                    "supplier": product.supplier,
                    "status": product.status,
                    "is_featured": product.is_featured,
                    "min_stock": product.min_stock,
                    "current_stock": product.current_stock,
                    "main_image": product.main_image,
                    "additional_images": product.additional_images,
                    "notes": product.notes,
                    "internal_notes": product.internal_notes,
                    "base_product": {
                        "id": base_product.id,
                        "title": base_product.title,
                        "ml_item_id": base_product.ml_item_id,
                        "thumbnail": base_product.thumbnail
                    } if base_product else None,
                    "created_at": product.created_at,
                    "updated_at": product.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter produto interno: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def update_internal_product(
        self, 
        product_id: int, 
        company_id: int, 
        **update_data
    ) -> Dict[str, Any]:
        """Atualiza um produto interno"""
        try:
            product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.id == product_id,
                    InternalProduct.company_id == company_id
                )
            ).first()
            
            if not product:
                return {"error": "Produto interno não encontrado"}
            
            # Verificar se o novo SKU já existe (se foi alterado)
            if "internal_sku" in update_data and update_data["internal_sku"] != product.internal_sku:
                existing = self.db.query(InternalProduct).filter(
                    and_(
                        InternalProduct.company_id == company_id,
                        InternalProduct.internal_sku == update_data["internal_sku"],
                        InternalProduct.id != product_id
                    )
                ).first()
                
                if existing:
                    return {"error": "SKU interno já existe para esta empresa"}
            
            # Atualizar campos
            for field, value in update_data.items():
                if hasattr(product, field):
                    setattr(product, field, value)
            
            self.db.commit()
            self.db.refresh(product)
            
            return {
                "success": True,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "internal_sku": product.internal_sku,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar produto interno: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def delete_internal_product(self, product_id: int, company_id: int) -> Dict[str, Any]:
        """Remove um produto interno"""
        try:
            product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.id == product_id,
                    InternalProduct.company_id == company_id
                )
            ).first()
            
            if not product:
                return {"error": "Produto interno não encontrado"}
            
            self.db.delete(product)
            self.db.commit()
            
            return {"success": True, "message": "Produto interno removido com sucesso"}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover produto interno: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def get_base_products(self, company_id: int, search: Optional[str] = None) -> Dict[str, Any]:
        """Lista produtos do ML que podem ser usados como base"""
        try:
            query = self.db.query(Product).filter(Product.company_id == company_id)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Product.title.ilike(search_term),
                        Product.sku.ilike(search_term)
                    )
                )
            
            products = query.limit(100).all()
            
            return {
                "success": True,
                "base_products": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "ml_item_id": p.ml_item_id,
                        "sku": p.sku,
                        "thumbnail": p.thumbnail,
                        "price": p.cost_price
                    }
                    for p in products
                ]
            }
            
        except Exception as e:
            logger.error(f"Erro ao listar produtos base: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def bulk_delete_internal_products(self, product_ids: list, company_id: int) -> Dict[str, Any]:
        """Exclui múltiplos produtos internos"""
        try:
            if not product_ids:
                return {"error": "Nenhum produto selecionado para exclusão"}
            
            # Verificar se todos os produtos pertencem à empresa
            products = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.id.in_(product_ids),
                    InternalProduct.company_id == company_id
                )
            ).all()
            
            if not products:
                return {"error": "Nenhum produto encontrado para exclusão"}
            
            # Verificar se todos os IDs solicitados foram encontrados
            found_ids = [p.id for p in products]
            missing_ids = [pid for pid in product_ids if pid not in found_ids]
            
            if missing_ids:
                return {"error": f"Produtos não encontrados: {missing_ids}"}
            
            # Excluir produtos
            deleted_count = 0
            for product in products:
                self.db.delete(product)
                deleted_count += 1
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"{deleted_count} produto(s) excluído(s) com sucesso",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao excluir produtos em massa: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def bulk_update_internal_products(
        self,
        company_id: int,
        cost_price: Optional[float] = None,
        tax_rate: Optional[float] = None,
        marketing_cost: Optional[float] = None,
        other_costs: Optional[float] = None
    ) -> Dict[str, Any]:
        """Atualiza valores em massa em todos os produtos internos da empresa"""
        try:
            # Buscar todos os produtos da empresa
            products = self.db.query(InternalProduct).filter(
                InternalProduct.company_id == company_id
            ).all()
            
            if not products:
                return {"error": "Nenhum produto encontrado para atualizar"}
            
            # Atualizar produtos
            updated_count = 0
            update_fields = []
            
            for product in products:
                updated = False
                
                if cost_price is not None:
                    product.cost_price = str(cost_price)
                    updated = True
                    if 'Preço de Custo' not in update_fields:
                        update_fields.append('Preço de Custo')
                
                if tax_rate is not None:
                    product.tax_rate = str(tax_rate)
                    updated = True
                    if 'Impostos' not in update_fields:
                        update_fields.append('Impostos')
                
                if marketing_cost is not None:
                    product.marketing_cost = str(marketing_cost)
                    updated = True
                    if 'Marketing' not in update_fields:
                        update_fields.append('Marketing')
                
                if other_costs is not None:
                    product.other_costs = str(other_costs)
                    updated = True
                    if 'Outros Custos' not in update_fields:
                        update_fields.append('Outros Custos')
                
                if updated:
                    updated_count += 1
            
            self.db.commit()
            
            fields_str = ', '.join(update_fields)
            
            return {
                "success": True,
                "message": f"{updated_count} produto(s) atualizado(s) com sucesso",
                "updated_count": updated_count,
                "fields_updated": update_fields
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar produtos em massa: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def get_pricing_data_by_sku(self, internal_sku: str, company_id: int) -> Dict[str, Any]:
        """Busca dados de preços e taxas por SKU interno para análise"""
        try:
            product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.internal_sku == internal_sku,
                    InternalProduct.company_id == company_id,
                    InternalProduct.status == "active"
                )
            ).first()
            
            if not product:
                return {"error": f"Produto interno com SKU '{internal_sku}' não encontrado"}
            
            # Calcular dados para análise de preços
            cost_price = float(product.cost_price) if product.cost_price else 0.0
            tax_rate = float(product.tax_rate) if product.tax_rate else 0.0
            marketing_cost = float(product.marketing_cost) if product.marketing_cost else 0.0
            other_costs = float(product.other_costs) if product.other_costs else 0.0
            selling_price = float(product.selling_price) if product.selling_price else 0.0
            
            # Calcular totais
            total_costs = cost_price + marketing_cost + other_costs
            tax_amount = (selling_price * tax_rate / 100) if selling_price and tax_rate else 0.0
            total_costs_with_tax = total_costs + tax_amount
            
            # Calcular margem
            profit_margin = 0.0
            if selling_price > 0:
                profit_margin = ((selling_price - total_costs_with_tax) / selling_price) * 100
            
            return {
                "success": True,
                "pricing_data": {
                    "product_id": product.id,
                    "name": product.name,
                    "internal_sku": product.internal_sku,
                    "cost_price": cost_price,
                    "selling_price": selling_price,
                    "tax_rate": tax_rate,
                    "tax_amount": tax_amount,
                    "marketing_cost": marketing_cost,
                    "other_costs": other_costs,
                    "total_costs": total_costs,
                    "total_costs_with_tax": total_costs_with_tax,
                    "profit_margin": profit_margin,
                    "expected_profit_margin": float(product.expected_profit_margin) if product.expected_profit_margin else 0.0,
                    "category": product.category,
                    "brand": product.brand,
                    "supplier": product.supplier,
                    "status": product.status,
                    "current_stock": product.current_stock,
                    "base_product_id": product.base_product_id,
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de preços por SKU: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def get_pricing_data_by_skus(self, internal_skus: list, company_id: int) -> Dict[str, Any]:
        """Busca dados de preços e taxas para múltiplos SKUs"""
        try:
            if not internal_skus:
                return {"error": "Lista de SKUs vazia"}
            
            products = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.internal_sku.in_(internal_skus),
                    InternalProduct.company_id == company_id,
                    InternalProduct.status == "active"
                )
            ).all()
            
            if not products:
                return {"error": "Nenhum produto encontrado com os SKUs fornecidos"}
            
            pricing_data = []
            found_skus = []
            
            for product in products:
                cost_price = float(product.cost_price) if product.cost_price else 0.0
                tax_rate = float(product.tax_rate) if product.tax_rate else 0.0
                marketing_cost = float(product.marketing_cost) if product.marketing_cost else 0.0
                other_costs = float(product.other_costs) if product.other_costs else 0.0
                selling_price = float(product.selling_price) if product.selling_price else 0.0
                
                # Calcular totais
                total_costs = cost_price + marketing_cost + other_costs
                tax_amount = (selling_price * tax_rate / 100) if selling_price and tax_rate else 0.0
                total_costs_with_tax = total_costs + tax_amount
                
                # Calcular margem
                profit_margin = 0.0
                if selling_price > 0:
                    profit_margin = ((selling_price - total_costs_with_tax) / selling_price) * 100
                
                pricing_data.append({
                    "product_id": product.id,
                    "name": product.name,
                    "internal_sku": product.internal_sku,
                    "cost_price": cost_price,
                    "selling_price": selling_price,
                    "tax_rate": tax_rate,
                    "tax_amount": tax_amount,
                    "marketing_cost": marketing_cost,
                    "other_costs": other_costs,
                    "total_costs": total_costs,
                    "total_costs_with_tax": total_costs_with_tax,
                    "profit_margin": profit_margin,
                    "expected_profit_margin": float(product.expected_profit_margin) if product.expected_profit_margin else 0.0,
                    "category": product.category,
                    "brand": product.brand,
                    "supplier": product.supplier,
                    "status": product.status,
                    "current_stock": product.current_stock,
                    "base_product_id": product.base_product_id
                })
                
                found_skus.append(product.internal_sku)
            
            # Verificar SKUs não encontrados
            missing_skus = [sku for sku in internal_skus if sku not in found_skus]
            
            return {
                "success": True,
                "pricing_data": pricing_data,
                "total_found": len(pricing_data),
                "missing_skus": missing_skus,
                "found_skus": found_skus
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de preços por SKUs: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def update_internal_product_from_ml(
        self,
        company_id: int,
        ml_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atualiza produto interno com dados do Mercado Livre (inclui resincronização)"""
        try:
            # Primeiro, buscar produto ML para obter o SKU
            from app.models.saas_models import MLProduct
            ml_product = None
            
            if ml_product_id:
                ml_product = self.db.query(MLProduct).filter(
                    and_(
                        MLProduct.id == ml_product_id,
                        MLProduct.company_id == company_id
                    )
                ).first()
            elif ml_item_id:
                ml_product = self.db.query(MLProduct).filter(
                    and_(
                        MLProduct.ml_item_id == ml_item_id,
                        MLProduct.company_id == company_id
                    )
                ).first()
            else:
                return {"error": "ID do produto ML ou item_id é obrigatório"}
            
            if not ml_product:
                return {"error": "Produto do Mercado Livre não encontrado"}
            
            logger.info(f"🔍 Produto ML encontrado: {ml_product.title} (SKU: {ml_product.seller_sku}, Item ID: {ml_product.ml_item_id})")
            
            # Buscar produto interno pelo SKU e company_id
            internal_product = self.db.query(InternalProduct).filter(
                and_(
                    InternalProduct.internal_sku == ml_product.seller_sku,
                    InternalProduct.company_id == company_id
                )
            ).first()
            
            if not internal_product:
                # Log detalhado para debug
                logger.warning(f"⚠️ Nenhum produto interno encontrado com SKU '{ml_product.seller_sku}' para company_id {company_id}")
                
                # Listar todos os produtos internos desta empresa para debug
                all_internal_products = self.db.query(InternalProduct).filter(
                    InternalProduct.company_id == company_id
                ).all()
                
                logger.info(f"📋 Produtos internos disponíveis na empresa {company_id}:")
                for p in all_internal_products:
                    logger.info(f"   - {p.name} (SKU: {p.internal_sku})")
                
                return {
                    "success": False,
                    "message": f"Nenhum produto interno encontrado com SKU '{ml_product.seller_sku}' para esta empresa"
                }
            
            logger.info(f"✅ Produto interno encontrado: {internal_product.name} (SKU: {internal_product.internal_sku})")
            
            # 🔄 RESINCRONIZAR COM MERCADO LIVRE VIA API
            logger.info(f"🔄 Resincronizando produto {ml_product.ml_item_id} com API do Mercado Livre...")
            
            try:
                # Buscar conta ML da empresa
                from app.models.saas_models import MLAccount, MLAccountStatus
                ml_account = self.db.query(MLAccount).filter(
                    and_(
                        MLAccount.company_id == company_id,
                        MLAccount.status == MLAccountStatus.ACTIVE
                    )
                ).first()
                
                if not ml_account:
                    logger.warning("⚠️ Nenhuma conta ML ativa encontrada, pulando resincronização")
                else:
                    # Resincronizar produto específico via API do ML
                    from app.services.ml_product_service import MLProductService
                    ml_service = MLProductService(self.db)
                    
                    # Obter token válido (com renovação automática se necessário)
                    token = ml_service.get_active_token(ml_account.id)
                    if not token:
                        logger.error(f"❌ Token não encontrado para a conta ML {ml_account.id}")
                    else:
                        logger.info(f"✅ Token válido obtido para conta ML {ml_account.id}")
                        # Buscar dados atualizados diretamente da API do Mercado Livre
                        updated_data = ml_service.fetch_product_details(ml_product.ml_item_id, token)
                        
                        if updated_data:
                            # Atualizar produto ML no banco com dados da API
                            ml_product.title = updated_data.get("title", ml_product.title)
                            ml_product.price = updated_data.get("price", ml_product.price)
                            ml_product.available_quantity = updated_data.get("available_quantity", ml_product.available_quantity)
                            ml_product.sold_quantity = updated_data.get("sold_quantity", ml_product.sold_quantity)
                            
                            # Mapear status usando o método do MLProductService
                            status_str = updated_data.get("status")
                            if status_str:
                                ml_product.status = ml_service._map_status(status_str)
                            
                            ml_product.description = updated_data.get("description", ml_product.description)
                            ml_product.category_id = updated_data.get("category_id", ml_product.category_id)
                            ml_product.seller_sku = updated_data.get("seller_sku", ml_product.seller_sku)
                            ml_product.permalink = updated_data.get("permalink", ml_product.permalink)
                            ml_product.thumbnail = updated_data.get("thumbnail", ml_product.thumbnail)
                            
                            # Atualizar preço promocional se existir
                            promotional_price = updated_data.get("promotional_price")
                            if promotional_price:
                                # Se tem preço promocional, usar ele como preço de venda
                                ml_product.price = promotional_price
                                logger.info(f"💰 Preço promocional encontrado na API: R$ {promotional_price}")
                            else:
                                # Usar preço normal da API
                                logger.info(f"💰 Preço normal da API: R$ {ml_product.price}")
                            
                            self.db.commit()
                            self.db.refresh(ml_product)
                            
                            logger.info(f"✅ Produto ML {ml_product.ml_item_id} resincronizado com sucesso via API")
                        else:
                            logger.warning(f"⚠️ Falha na resincronização do produto {ml_product.ml_item_id} via API")
                        
            except Exception as sync_error:
                logger.error(f"❌ Erro na resincronização via API: {sync_error}")
                # Continua com a atualização mesmo se a resincronização falhar
            
            # Atualizar dados do produto interno com informações do ML
            update_data = {}
            updated_fields = []
            
            # Atualizar título se mudou
            if ml_product.title != internal_product.name:
                update_data["name"] = ml_product.title
                updated_fields.append("nome")
                logger.info(f"📝 Atualizando nome: '{internal_product.name}' → '{ml_product.title}'")
            
            # Atualizar preço de venda se mudou (usar preço promocional se disponível)
            current_price = ml_product.price
            if current_price and float(current_price) != float(internal_product.selling_price or 0):
                update_data["selling_price"] = current_price
                updated_fields.append("preço de venda")
                logger.info(f"💰 Atualizando preço de venda: R$ {internal_product.selling_price} → R$ {current_price}")
            
            # Atualizar descrição se mudou
            if ml_product.description and ml_product.description != internal_product.description:
                update_data["description"] = ml_product.description
                updated_fields.append("descrição")
                logger.info(f"📄 Atualizando descrição")
            
            # Atualizar categoria se mudou
            if ml_product.category_id and ml_product.category_id != internal_product.category:
                update_data["category"] = ml_product.category_id
                updated_fields.append("categoria")
                logger.info(f"🏷️ Atualizando categoria: '{internal_product.category}' → '{ml_product.category_id}'")
            
            # Aplicar atualizações se houver
            if update_data:
                for key, value in update_data.items():
                    setattr(internal_product, key, value)
                
                self.db.commit()
                self.db.refresh(internal_product)
                
                logger.info(f"✅ Produto interno {internal_product.id} atualizado com dados do ML")
                
                return {
                    "success": True,
                    "message": "Produto interno atualizado com dados resincronizados do Mercado Livre",
                    "product_name": internal_product.name,
                    "updated_fields": updated_fields,
                    "ml_item_id": ml_product.ml_item_id
                }
            else:
                return {
                    "success": True,
                    "message": "Produto interno já está atualizado (dados resincronizados do Mercado Livre)",
                    "product_name": internal_product.name,
                    "updated_fields": [],
                    "ml_item_id": ml_product.ml_item_id
                }
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar produto interno do ML: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}