from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import logging
import requests
from datetime import datetime, timedelta

from app.models.saas_models import MLOrder, OrderStatus, MLAccount, MLAccountStatus

logger = logging.getLogger(__name__)

class MLOrdersService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
    
    def get_orders_by_account(self, ml_account_id: int, company_id: int, 
                             limit: int = 50, offset: int = 0,
                             status_filter: Optional[str] = None,
                             date_from: Optional[str] = None,
                             date_to: Optional[str] = None) -> Dict:
        """Busca orders de uma conta ML específica"""
        try:
            logger.info(f"Buscando orders para ml_account_id: {ml_account_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa",
                    "orders": [],
                    "total": 0
                }
            
            # Buscar orders do banco de dados
            query = self.db.query(MLOrder).filter(
                MLOrder.ml_account_id == ml_account_id,
                MLOrder.company_id == company_id
            )
            
            # Aplicar filtros
            if status_filter:
                try:
                    status_enum = OrderStatus(status_filter)
                    query = query.filter(MLOrder.status == status_enum)
                except ValueError:
                    logger.warning(f"Status inválido: {status_filter}")
            
            if date_from:
                try:
                    date_from_obj = datetime.fromisoformat(date_from)
                    query = query.filter(MLOrder.date_created >= date_from_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_from}")
            
            if date_to:
                try:
                    date_to_obj = datetime.fromisoformat(date_to)
                    query = query.filter(MLOrder.date_created <= date_to_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_to}")
            
            # Ordenar por data de criação (mais recentes primeiro)
            query = query.order_by(MLOrder.date_created.desc())
            
            # Paginação
            total = query.count()
            orders = query.offset(offset).limit(limit).all()
            
            # Converter para formato de resposta
            orders_data = []
            for order in orders:
                orders_data.append({
                    "id": order.id,
                    "ml_order_id": order.ml_order_id,
                    "order_id": order.order_id,
                    
                    # Dados do comprador
                    "buyer_nickname": order.buyer_nickname,
                    "buyer_email": order.buyer_email,
                    "buyer_first_name": order.buyer_first_name,
                    "buyer_last_name": order.buyer_last_name,
                    
                    # Dados do vendedor
                    "seller_nickname": order.seller_nickname,
                    
                    # Status e valores
                    "status": order.status.value if order.status else None,
                    "status_detail": order.status_detail,
                    "total_amount": order.total_amount,
                    "paid_amount": order.paid_amount,
                    "currency_id": order.currency_id,
                    
                    # Pagamento
                    "payment_status": order.payment_status,
                    "payment_method_id": order.payment_method_id,
                    "payment_type_id": order.payment_type_id,
                    
                    # Envio
                    "shipping_cost": order.shipping_cost,
                    "shipping_method": order.shipping_method,
                    "shipping_status": order.shipping_status,
                    
                    # Taxas
                    "total_fees": order.total_fees,
                    "sale_fees": order.sale_fees,
                    "shipping_fees": order.shipping_fees,
                    
                    # Publicidade
                    "is_advertising_sale": order.is_advertising_sale,
                    "advertising_cost": order.advertising_cost,
                    
                    # Descontos
                    "coupon_amount": order.coupon_amount,
                    "discounts_applied": order.discounts_applied,
                    
                    # Datas
                    "date_created": order.date_created.isoformat() if order.date_created else None,
                    "date_closed": order.date_closed.isoformat() if order.date_closed else None,
                    "last_updated": order.last_updated.isoformat() if order.last_updated else None,
                    
                    # Dados completos
                    "order_items": order.order_items,
                    "shipping_address": order.shipping_address,
                    "payments": order.payments,
                    "tags": order.tags,
                    "feedback": order.feedback,
                    "context": order.context
                })
            
            return {
                "success": True,
                "orders": orders_data,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar orders: {e}")
            return {
                "success": False,
                "error": str(e),
                "orders": [],
                "total": 0
            }
    
    def sync_orders_from_api(self, ml_account_id: int, company_id: int, 
                           limit: int = 50, is_full_import: bool = False) -> Dict:
        """Sincroniza orders da API do Mercado Libre para o banco"""
        try:
            logger.info(f"Sincronizando orders para ml_account_id: {ml_account_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa"
                }
            
            # Obter token ativo
            access_token = self._get_active_token(ml_account_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token não encontrado ou expirado"
                }
            
            # Buscar orders da API
            if is_full_import:
                # Importação completa - limitar para evitar sobrecarga
                logger.info("Importação completa - limitando a 50 pedidos para evitar sobrecarga")
                orders_data = self._fetch_orders_from_api(access_token, account.ml_user_id, limit=50)
            else:
                # Sincronização rápida - apenas os mais recentes
                orders_data = self._fetch_orders_from_api(access_token, account.ml_user_id, limit)
            
            if not orders_data:
                return {
                    "success": False,
                    "error": "Nenhuma order encontrada na API"
                }
            
            # Salvar orders no banco
            saved_count = 0
            updated_count = 0
            
            # Adicionar delay entre processamentos para evitar sobrecarga
            import time
            
            for i, order_data in enumerate(orders_data):
                # Adicionar delay a cada 5 pedidos para evitar sobrecarga
                if i > 0 and i % 5 == 0:
                    logger.info(f"Processando pedido {i+1}/{len(orders_data)} - pausa para evitar sobrecarga")
                    time.sleep(5)  # Pausa de 5 segundos
                try:
                    result = self._save_order_to_database(order_data, ml_account_id, company_id)
                    if result["action"] == "created":
                        saved_count += 1
                    elif result["action"] == "updated":
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Erro ao salvar order {order_data.get('id')}: {e}")
                    continue
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Sincronização concluída: {saved_count} orders criadas, {updated_count} orders atualizadas",
                "saved_count": saved_count,
                "updated_count": updated_count,
                "total_processed": len(orders_data)
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar orders: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fetch_all_orders_from_api(self, access_token: str, seller_id: str) -> List[Dict]:
        """Busca TODOS os orders da API do Mercado Libre em lotes"""
        try:
            all_orders = []
            offset = 0
            limit = 50  # Máximo permitido pela API
            max_requests = 20  # Limite de segurança para evitar loops infinitos
            
            for request_count in range(max_requests):
                logger.info(f"Buscando orders - offset: {offset}, limit: {limit}")
                
                orders_batch = self._fetch_orders_from_api(access_token, seller_id, limit, offset)
                
                if not orders_batch:
                    logger.info(f"Nenhuma order encontrada no lote {request_count + 1}")
                    break
                
                all_orders.extend(orders_batch)
                logger.info(f"Lote {request_count + 1}: {len(orders_batch)} orders encontradas")
                
                # Se retornou menos que o limite, chegamos ao fim
                if len(orders_batch) < limit:
                    logger.info(f"Fim dos orders atingido - total: {len(all_orders)}")
                    break
                
                offset += limit
                
                # Pequena pausa entre requisições para não sobrecarregar a API
                import time
                time.sleep(0.5)
            
            logger.info(f"Importação completa finalizada: {len(all_orders)} orders totais")
            return all_orders
                
        except Exception as e:
            logger.error(f"Erro ao buscar todos os orders da API: {e}")
            return []

    def _fetch_orders_from_api(self, access_token: str, seller_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Busca orders da API do Mercado Libre"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Buscar orders recentes do vendedor
            orders_url = f"{self.base_url}/orders/search"
            params = {
                "seller": seller_id,
                "limit": limit,
                "offset": offset,
                "sort": "date_desc"
            }
            
            response = requests.get(orders_url, headers=headers, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.warning(f"Erro ao buscar orders da API: {response.status_code} - {response.text[:200]}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar orders da API: {e}")
            return []
    
    def _fetch_complete_order_data(self, order_data: Dict, access_token: str) -> Dict:
        """Busca informações completas de uma order incluindo detalhes de envio, descontos e publicidade"""
        try:
            ml_order_id = order_data.get("id")
            complete_data = order_data.copy()
            
            # 1. Buscar detalhes completos da order
            order_details = self._fetch_order_details(ml_order_id, access_token)
            if order_details:
                complete_data.update(order_details)
            
            # 2. Buscar detalhes de envio se existir shipping_id
            shipping_id = order_data.get("shipping", {}).get("id")
            if shipping_id:
                shipping_details = self._fetch_shipping_details(shipping_id, access_token)
                if shipping_details:
                    complete_data["shipping_details"] = shipping_details
            
            # 3. Buscar descontos aplicados (com tratamento de erro para evitar sobrecarga)
            try:
                discounts = self._fetch_order_discounts(ml_order_id, access_token)
                if discounts:
                    complete_data["discounts_applied"] = discounts
            except Exception as e:
                logger.warning(f"Erro ao buscar descontos da order {ml_order_id}: {e}")
                # Continuar sem descontos se houver erro
            
            # 4. Verificar se foi venda por anúncio (Product Ads)
            advertising_info = self._check_advertising_sale(order_data, access_token)
            if advertising_info:
                complete_data.update(advertising_info)
            
            # 5. Calcular taxas e comissões
            fees_info = self._calculate_order_fees(order_data)
            if fees_info:
                complete_data.update(fees_info)
            
            return complete_data
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados completos da order {ml_order_id}: {e}")
            return order_data
    
    def _fetch_order_details(self, ml_order_id: int, access_token: str) -> Optional[Dict]:
        """Busca detalhes completos de uma order específica"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/orders/{ml_order_id}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erro ao buscar detalhes da order {ml_order_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da order: {e}")
            return None
    
    def _fetch_shipping_details(self, shipping_id: str, access_token: str) -> Optional[Dict]:
        """Busca detalhes de envio"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/shipments/{shipping_id}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erro ao buscar detalhes do envio {shipping_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do envio: {e}")
            return None
    
    def _fetch_order_discounts(self, ml_order_id: int, access_token: str) -> Optional[Dict]:
        """Busca descontos aplicados em uma order"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/orders/{ml_order_id}/discounts"
            
            # Timeout menor para evitar sobrecarga
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # 404 é normal - nem todos os pedidos têm descontos
                return None
            else:
                logger.warning(f"Erro ao buscar descontos da order {ml_order_id}: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout ao buscar descontos da order {ml_order_id}")
            return None
        except Exception as e:
            logger.warning(f"Erro ao buscar descontos da order {ml_order_id}: {e}")
            return None
    
    def _check_advertising_sale(self, order_data: Dict, access_token: str) -> Optional[Dict]:
        """Verifica se a venda foi através de anúncio (Product Ads)"""
        try:
            # Por enquanto, retornamos None pois a verificação de Product Ads
            # requer análise mais complexa das métricas de publicidade
            # TODO: Implementar verificação real de Product Ads
            
            # Verificar se há tags que indicam venda por anúncio
            tags = order_data.get("tags", [])
            context = order_data.get("context", {})
            
            advertising_info = {
                "is_advertising_sale": False,
                "advertising_campaign_id": None,
                "advertising_cost": 0,
                "advertising_metrics": {}
            }
            
            # Verificar contexto da venda
            flows = context.get("flows", [])
            if "cbt" in flows:  # Cross Border Trade pode indicar publicidade
                advertising_info["is_advertising_sale"] = True
            
            return advertising_info
            
        except Exception as e:
            logger.error(f"Erro ao verificar venda por anúncio: {e}")
            return None
    
    def _calculate_order_fees(self, order_data: Dict) -> Optional[Dict]:
        """Calcula taxas e comissões da order"""
        try:
            order_items = order_data.get("order_items", [])
            
            total_fees = 0
            listing_fees = 0
            sale_fees = 0
            shipping_fees = 0
            
            # Calcular taxas dos itens
            for item in order_items:
                sale_fee = item.get("sale_fee", 0)
                if sale_fee:
                    sale_fees += sale_fee
                    total_fees += sale_fee
            
            # Calcular taxas de envio
            shipping = order_data.get("shipping", {})
            shipping_cost = shipping.get("cost", 0)
            if shipping_cost:
                shipping_fees = shipping_cost
                total_fees += shipping_cost
            
            return {
                "total_fees": total_fees,
                "listing_fees": listing_fees,
                "sale_fees": sale_fees,
                "shipping_fees": shipping_fees
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular taxas da order: {e}")
            return None
    
    def _save_order_to_database(self, order_data: Dict, ml_account_id: int, company_id: int) -> Dict:
        """Salva ou atualiza uma order no banco de dados com informações completas"""
        try:
            ml_order_id = order_data.get("id")
            
            # Verificar se a order já existe
            existing_order = self.db.query(MLOrder).filter(
                MLOrder.ml_order_id == ml_order_id
            ).first()
            
            # Obter token para buscar informações adicionais
            access_token = self._get_active_token(ml_account_id)
            
            # Buscar informações completas da order
            complete_order_data = self._fetch_complete_order_data(order_data, access_token)
            
            # Converter dados da API para o modelo
            order_dict = self._convert_api_order_to_model(complete_order_data, ml_account_id, company_id)
            
            if existing_order:
                # Atualizar order existente
                for key, value in order_dict.items():
                    if key not in ["id", "ml_order_id", "created_at"]:
                        setattr(existing_order, key, value)
                
                existing_order.updated_at = datetime.utcnow()
                return {"action": "updated", "order": existing_order}
            else:
                # Criar nova order
                new_order = MLOrder(**order_dict)
                self.db.add(new_order)
                return {"action": "created", "order": new_order}
                
        except Exception as e:
            logger.error(f"Erro ao salvar order no banco: {e}")
            raise e
    
    def _convert_api_order_to_model(self, order_data: Dict, ml_account_id: int, company_id: int) -> Dict:
        """Converte dados da API para formato do modelo - Versão Completa"""
        try:
            # Converter status
            status_mapping = {
                "confirmed": OrderStatus.CONFIRMED,
                "payment_required": OrderStatus.PENDING,
                "payment_in_process": OrderStatus.PENDING,
                "paid": OrderStatus.PAID,
                "ready_to_ship": OrderStatus.PAID,
                "shipped": OrderStatus.SHIPPED,
                "delivered": OrderStatus.DELIVERED,
                "cancelled": OrderStatus.CANCELLED,
                "refunded": OrderStatus.REFUNDED
            }
            
            status = order_data.get("status", "pending")
            order_status = status_mapping.get(status, OrderStatus.PENDING)
            
            # Converter datas
            date_created = None
            if order_data.get("date_created"):
                try:
                    date_created = datetime.fromisoformat(order_data["date_created"].replace('Z', '+00:00'))
                except:
                    pass
            
            date_closed = None
            if order_data.get("date_closed"):
                try:
                    date_closed = datetime.fromisoformat(order_data["date_closed"].replace('Z', '+00:00'))
                except:
                    pass
            
            last_updated = None
            if order_data.get("last_updated"):
                try:
                    last_updated = datetime.fromisoformat(order_data["last_updated"].replace('Z', '+00:00'))
                except:
                    pass
            
            # Extrair dados do comprador
            buyer = order_data.get("buyer", {})
            
            # Extrair dados do vendedor
            seller = order_data.get("seller", {})
            
            # Extrair dados de pagamento
            payments = order_data.get("payments", [])
            payment_status = None
            payment_method_id = None
            payment_type_id = None
            
            if payments:
                payment = payments[0]
                payment_status = payment.get("status")
                payment_method_id = payment.get("payment_method_id")
                payment_type_id = payment.get("payment_type_id")
            
            # Extrair dados de envio
            shipping = order_data.get("shipping", {})
            shipping_details = order_data.get("shipping_details", {})
            
            # Extrair cupom
            coupon = order_data.get("coupon", {})
            
            return {
                # === DADOS BÁSICOS ===
                "company_id": company_id,
                "ml_account_id": ml_account_id,
                "ml_order_id": order_data.get("id"),
                "order_id": str(order_data.get("id")),
                
                # Status e datas
                "status": order_status,
                "status_detail": order_data.get("status_detail"),
                "date_created": date_created,
                "date_closed": date_closed,
                "last_updated": last_updated,
                
                # Valores monetários
                "total_amount": order_data.get("total_amount"),
                "paid_amount": order_data.get("paid_amount"),
                "currency_id": order_data.get("currency_id"),
                
                # === DADOS DO COMPRADOR ===
                "buyer_id": buyer.get("id"),
                "buyer_nickname": buyer.get("nickname"),
                "buyer_email": buyer.get("email"),
                "buyer_first_name": buyer.get("first_name"),
                "buyer_last_name": buyer.get("last_name"),
                "buyer_phone": buyer.get("phone"),
                
                # === DADOS DO VENDEDOR ===
                "seller_id": seller.get("id"),
                "seller_nickname": seller.get("nickname"),
                "seller_phone": seller.get("phone"),
                
                # === PAGAMENTOS ===
                "payments": payments,
                "payment_method_id": payment_method_id,
                "payment_type_id": payment_type_id,
                "payment_status": payment_status,
                
                # === ENVIO E LOGÍSTICA ===
                "shipping_id": shipping.get("id"),
                "shipping_cost": shipping.get("cost") or shipping_details.get("cost"),
                "shipping_method": shipping.get("method") or shipping_details.get("shipping_method"),
                "shipping_status": shipping.get("status") or shipping_details.get("status"),
                "shipping_address": shipping.get("receiver_address") or shipping_details.get("receiver_address"),
                "shipping_details": shipping_details,
                
                # === ITENS DO PEDIDO ===
                "order_items": order_data.get("order_items"),
                
                # === TAXAS E COMISSÕES ===
                "total_fees": order_data.get("total_fees", 0),
                "listing_fees": order_data.get("listing_fees", 0),
                "sale_fees": order_data.get("sale_fees", 0),
                "shipping_fees": order_data.get("shipping_fees", 0),
                
                # === DESCONTOS E PROMOÇÕES ===
                "discounts_applied": order_data.get("discounts_applied"),
                "coupon_amount": coupon.get("amount", 0),
                "coupon_id": coupon.get("id"),
                
                # === PUBLICIDADE E ANÚNCIOS ===
                "is_advertising_sale": order_data.get("is_advertising_sale", False),
                "advertising_campaign_id": order_data.get("advertising_campaign_id"),
                "advertising_cost": order_data.get("advertising_cost", 0),
                "advertising_metrics": order_data.get("advertising_metrics", {}),
                
                # === CONTEXTO DA VENDA ===
                "context": order_data.get("context"),
                "pack_id": order_data.get("pack_id"),
                "pickup_id": order_data.get("pickup_id"),
                
                # === MEDIAÇÕES E DISPUTAS ===
                "mediations": order_data.get("mediations"),
                "order_request": order_data.get("order_request"),
                
                # === FEEDBACK ===
                "feedback": order_data.get("feedback"),
                
                # === TAGS E METADADOS ===
                "tags": order_data.get("tags"),
                "fulfilled": order_data.get("fulfilled"),
                "comment": order_data.get("comment"),
                
                # === IMPOSTOS ===
                "taxes": order_data.get("taxes"),
                
                # === DETALHES DE CANCELAMENTO ===
                "cancel_detail": order_data.get("cancel_detail")
            }
            
        except Exception as e:
            logger.error(f"Erro ao converter dados da order: {e}")
            raise e
    
    def _get_active_token(self, ml_account_id: int) -> Optional[str]:
        """Obtém token ativo para uma conta ML específica, tentando renovar se expirado"""
        try:
            from sqlalchemy import text
            
            # Primeiro, tentar buscar token válido
            query = text("""
                SELECT access_token, refresh_token, expires_at
                FROM tokens 
                WHERE ml_account_id = :ml_account_id 
                AND is_active = true 
                AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {"ml_account_id": ml_account_id}).fetchone()
            
            if result:
                return result[0]
            
            # Se não encontrou token válido, tentar renovar com refresh token
            logger.info(f"Token expirado para ml_account_id: {ml_account_id}, tentando renovar...")
            
            # Buscar refresh token
            refresh_query = text("""
                SELECT refresh_token, access_token
                FROM tokens 
                WHERE ml_account_id = :ml_account_id 
                AND is_active = true 
                AND refresh_token IS NOT NULL
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            refresh_result = self.db.execute(refresh_query, {"ml_account_id": ml_account_id}).fetchone()
            
            if refresh_result and refresh_result[0]:
                # Tentar renovar o token
                new_token = self._refresh_token(refresh_result[0], ml_account_id)
                if new_token:
                    return new_token
            
            logger.warning(f"Nenhum token ativo encontrado para ml_account_id: {ml_account_id}")
            return None
                
        except Exception as e:
            logger.error(f"Erro ao obter token ativo: {e}")
            return None
    
    def _refresh_token(self, refresh_token: str, ml_account_id: int) -> Optional[str]:
        """Tenta renovar token usando refresh token"""
        try:
            import requests
            
            # Dados para renovar token
            data = {
                "grant_type": "refresh_token",
                "client_id": "6987936494418444",
                "client_secret": "puvG9Z7XBgICZg5yK3t0PAXAmnco18Tl",
                "refresh_token": refresh_token
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post("https://api.mercadolibre.com/oauth/token", data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Salvar novo token no banco
                from app.models.saas_models import Token
                from datetime import datetime, timedelta
                
                # Desativar tokens antigos
                self.db.query(Token).filter(
                    Token.ml_account_id == ml_account_id,
                    Token.is_active == True
                ).update({"is_active": False})
                
                # Buscar user_id da empresa da conta ML
                from app.models.saas_models import MLAccount, User
                account = self.db.query(MLAccount).filter(MLAccount.id == ml_account_id).first()
                user_id = None
                if account:
                    # Buscar qualquer usuário da empresa
                    user = self.db.query(User).filter(User.company_id == account.company_id).first()
                    user_id = user.id if user else None
                
                # Criar novo token
                new_token = Token(
                    user_id=user_id,
                    ml_account_id=ml_account_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in", 21600),
                    scope=token_data.get("scope", ""),
                    expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                    is_active=True
                )
                
                self.db.add(new_token)
                self.db.commit()
                
                logger.info(f"Token renovado com sucesso para ml_account_id: {ml_account_id}")
                return token_data["access_token"]
            else:
                logger.error(f"Erro ao renovar token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return None
    
    def delete_orders(self, order_ids: List[int], company_id: int) -> Dict:
        """Remove pedidos selecionados do banco de dados"""
        try:
            logger.info(f"Removendo pedidos: {order_ids} para company_id: {company_id}")
            
            # Buscar pedidos que pertencem à empresa
            orders_to_delete = self.db.query(MLOrder).filter(
                MLOrder.id.in_(order_ids),
                MLOrder.company_id == company_id
            ).all()
            
            if not orders_to_delete:
                return {
                    "success": False,
                    "error": "Nenhum pedido encontrado para remoção"
                }
            
            # Verificar se todos os pedidos pertencem à empresa
            found_ids = [order.id for order in orders_to_delete]
            missing_ids = set(order_ids) - set(found_ids)
            
            if missing_ids:
                return {
                    "success": False,
                    "error": f"Alguns pedidos não foram encontrados ou não pertencem à sua empresa: {missing_ids}"
                }
            
            # Remover pedidos
            deleted_count = 0
            for order in orders_to_delete:
                self.db.delete(order)
                deleted_count += 1
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"{deleted_count} pedido(s) removido(s) com sucesso",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger.error(f"Erro ao remover pedidos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro ao remover pedidos: {str(e)}"
            }
    
    def delete_all_orders(self, company_id: int) -> Dict:
        """Remove todos os pedidos da empresa do banco de dados"""
        try:
            logger.info(f"Removendo todos os pedidos para company_id: {company_id}")
            
            # Buscar todos os pedidos da empresa
            orders_to_delete = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            ).all()
            
            if not orders_to_delete:
                return {
                    "success": False,
                    "error": "Nenhum pedido encontrado para remoção"
                }
            
            # Contar pedidos antes de remover
            total_count = len(orders_to_delete)
            
            # Remover todos os pedidos
            for order in orders_to_delete:
                self.db.delete(order)
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Todos os pedidos ({total_count}) foram removidos com sucesso",
                "deleted_count": total_count
            }
            
        except Exception as e:
            logger.error(f"Erro ao remover todos os pedidos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro ao remover todos os pedidos: {str(e)}"
            }
