"""
Service para gerenciar mensagens pós-venda do Mercado Livre
"""
import logging
import requests
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.saas_models import MLMessageThread, MLMessage, MLMessageThreadStatus, MLMessageType, MLAccount, MLAccountStatus
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MLMessagesService:
    """Service para gerenciar mensagens pós-venda do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _get_access_token(self, user_id: int) -> Optional[str]:
        """Obtém token válido usando TokenManager"""
        try:
            token_manager = TokenManager(self.db)
            return token_manager.get_valid_token(user_id)
        except Exception as e:
            logger.error(f"Erro ao obter token para user_id {user_id}: {e}")
            return None
    
    def get_reasons_to_communicate(self, access_token: str) -> List[Dict]:
        """Busca os motivos disponíveis para iniciar uma comunicação pós-venda"""
        try:
            url = f"{self.base_url}/messages/options/reasons"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao buscar motivos: {response.status_code} - {response.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Erro ao buscar motivos para comunicar: {e}", exc_info=True)
            return []
    
    def create_message_thread(self, package_id: str, reason: str, message_text: str, access_token: str,
                             seller_id: str = None, buyer_id: str = None) -> Dict:
        """
        Cria uma nova conversa/mensagem pós-venda
        
        Conforme documentação: POST /messages/packs/$PACK_ID/sellers/$USER_ID?tag=post_sale
        """
        if not seller_id:
            # Tentar obter seller_id do token
            try:
                user_info_url = f"{self.base_url}/users/me"
                response = requests.get(user_info_url, headers={
                    **self.headers,
                    "Authorization": f"Bearer {access_token}"
                }, timeout=10)
                if response.status_code == 200:
                    user_data = response.json()
                    seller_id = str(user_data.get("id", ""))
            except Exception as e:
                logger.error(f"Erro ao obter seller_id: {e}")
                return {"error": "seller_id não encontrado"}
        
        if not seller_id:
            return {"error": "seller_id obrigatório"}
        
        if not buyer_id:
            return {"error": "buyer_id obrigatório para criar mensagem"}
        
        try:
            # Endpoint correto conforme documentação oficial
            url = f"{self.base_url}/messages/packs/{package_id}/sellers/{seller_id}"
            params = {"tag": "post_sale"}
            
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            # Estrutura conforme documentação
            payload = {
                "from": {
                    "user_id": seller_id
                },
                "to": {
                    "user_id": buyer_id
                },
                "text": message_text
            }
            
            response = requests.post(url, headers=headers, params=params, json=payload, timeout=15)
            
            if response.status_code == 201 or response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao criar mensagem: {response.status_code} - {response.text[:200]}")
                return {"error": f"Erro {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            logger.error(f"Erro ao criar mensagem pós-venda: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_thread_messages(self, package_id: str, access_token: str, seller_id: str = None) -> Optional[Dict]:
        """
        Busca todas as mensagens de uma conversa/pacote
        
        Conforme documentação: GET /messages/packs/$PACK_ID/sellers/$USER_ID?tag=post_sale
        """
        if not seller_id:
            logger.warning("⚠️ seller_id não fornecido, tentando obter do token...")
            # Tentar obter seller_id do token (informação do usuário logado)
            try:
                user_info_url = f"{self.base_url}/users/me"
                response = requests.get(user_info_url, headers={
                    **self.headers,
                    "Authorization": f"Bearer {access_token}"
                }, timeout=10)
                if response.status_code == 200:
                    user_data = response.json()
                    seller_id = str(user_data.get("id", ""))
                    logger.info(f"✅ Seller ID obtido: {seller_id}")
            except Exception as e:
                logger.error(f"❌ Erro ao obter seller_id do token: {e}")
                return None
        
        if not seller_id:
            logger.error("❌ seller_id obrigatório para buscar mensagens")
            return None
        
        logger.info(f"🌐 ========== BUSCANDO DETALHES DO THREAD NA API ==========")
        logger.info(f"🌐 Package ID: {package_id}")
        logger.info(f"🌐 Seller ID: {seller_id}")
        
        try:
            # Endpoint correto conforme documentação oficial
            url = f"{self.base_url}/messages/packs/{package_id}/sellers/{seller_id}"
            params = {"tag": "post_sale", "mark_as_read": False}  # mark_as_read=false para não marcar como lidas
            
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            logger.info(f"📤 Enviando requisição GET para {url}")
            logger.info(f"📤 Parâmetros: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            logger.info(f"📥 Resposta recebida: Status Code = {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Dados recebidos com sucesso!")
                logger.info(f"📊 Tipo do retorno: {type(data)}")
                if isinstance(data, dict):
                    logger.info(f"📊 Chaves principais: {list(data.keys())}")
                    # Normalizar estrutura para compatibilidade
                    messages = data.get("messages", [])
                    logger.info(f"📊 Total de mensagens: {len(messages)}")
                logger.info(f"🌐 ========== THREAD RECEBIDO COM SUCESSO ==========")
                return data
            else:
                logger.error(f"❌ Erro ao buscar mensagens do pacote {package_id}")
                logger.error(f"❌ Status Code: {response.status_code}")
                logger.error(f"❌ Resposta (primeiros 500 caracteres): {response.text[:500]}")
                logger.error(f"🌐 ========== ERRO AO BUSCAR THREAD ==========")
                return None
        except Exception as e:
            logger.error(f"❌ ========== EXCEÇÃO AO BUSCAR THREAD ==========")
            logger.error(f"❌ Package ID: {package_id}")
            logger.error(f"❌ Seller ID: {seller_id}")
            logger.error(f"❌ Erro: {str(e)}")
            logger.error(f"❌ Tipo: {type(e).__name__}")
            logger.error(f"❌ Traceback:", exc_info=True)
            logger.error(f"❌ ========== FIM DA EXCEÇÃO ==========")
            return None
    
    def send_message(self, package_id: str, message_text: str, access_token: str, 
                    seller_id: str = None, buyer_id: str = None) -> Dict:
        """
        Envia uma mensagem em uma conversa existente
        
        Conforme documentação: POST /messages/packs/$PACK_ID/sellers/$USER_ID?tag=post_sale
        """
        if not seller_id:
            # Tentar obter seller_id do token
            try:
                user_info_url = f"{self.base_url}/users/me"
                response = requests.get(user_info_url, headers={
                    **self.headers,
                    "Authorization": f"Bearer {access_token}"
                }, timeout=10)
                if response.status_code == 200:
                    user_data = response.json()
                    seller_id = str(user_data.get("id", ""))
            except Exception as e:
                logger.error(f"Erro ao obter seller_id: {e}")
                return {"error": "seller_id não encontrado"}
        
        if not seller_id:
            return {"error": "seller_id obrigatório"}
        
        if not buyer_id:
            return {"error": "buyer_id obrigatório para enviar mensagem"}
        
        try:
            # Endpoint correto conforme documentação oficial
            url = f"{self.base_url}/messages/packs/{package_id}/sellers/{seller_id}"
            params = {"tag": "post_sale"}
            
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            # Estrutura conforme documentação
            payload = {
                "from": {
                    "user_id": seller_id
                },
                "to": {
                    "user_id": buyer_id
                },
                "text": message_text
            }
            
            response = requests.post(url, headers=headers, params=params, json=payload, timeout=15)
            
            if response.status_code == 201 or response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text[:200]}")
                return {"error": f"Erro {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_packages(self, ml_user_id: str, access_token: str, limit: int = 50, offset: int = 0, 
                     date_from: Optional[str] = None, date_to: Optional[str] = None, 
                     fetch_all: bool = False) -> List[Dict]:
        """
        Busca pacotes/conversas do vendedor através dos pedidos
        
        Nota: Conforme documentação oficial, o pack_id deve ser obtido na resposta de /orders/$ORDER_ID.
        Se pack_id for null, o order_id deve ser usado como padrão.
        Esta função busca pedidos recentes e extrai os pack_ids.
        
        Args:
            ml_user_id: ID do vendedor no ML
            access_token: Token de acesso OAuth
            limit: Número de resultados por página (máximo geralmente 50)
            offset: Offset para paginação
            date_from: Data inicial no formato ISO (YYYY-MM-DD ou YYYY-MM-DDTHH:mm:ss)
            date_to: Data final no formato ISO
            fetch_all: Se True, busca todas as páginas disponíveis
        
        Returns:
            Lista de pacotes/conversas (extraídos dos pedidos)
        """
        try:
            logger.info(f"📦 ========== INICIANDO BUSCA DE PACOTES VIA PEDIDOS ==========")
            logger.info(f"📦 ML User ID: {ml_user_id}")
            logger.info(f"📦 Limit por página: {limit}")
            logger.info(f"📦 Offset inicial: {offset}")
            logger.info(f"📦 Buscar todas as páginas: {fetch_all}")
            if date_from:
                logger.info(f"📦 Data inicial: {date_from}")
            if date_to:
                logger.info(f"📦 Data final: {date_to}")
            
            # Buscar pedidos para obter pack_ids
            # Conforme documentação: "Para conhecer o pack_id, você deverá obter-lo na resposta de /orders/$ORDER_ID"
            all_packages = []
            current_offset = offset
            max_iterations = 100
            iteration = 0
            
            while iteration < max_iterations:
                # Buscar pedidos do vendedor
                orders_url = f"{self.base_url}/orders/search"
                headers = {
                    **self.headers,
                    "Authorization": f"Bearer {access_token}"
                }
                
                params = {
                    "seller": ml_user_id,
                    "limit": limit,
                    "offset": current_offset,
                    "order.status": "all"  # Buscar todos os status para ter mais chance de encontrar mensagens
                }
                
                # Adicionar filtros de data se fornecidos
                if date_from:
                    params["order.date_created.from"] = date_from
                if date_to:
                    params["order.date_created.to"] = date_to
                
                logger.info(f"📦 Buscando pedidos página {iteration + 1} (offset={current_offset})...")
                
                response = requests.get(orders_url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    orders = data.get("results", [])
                    
                    logger.info(f"📦 Página {iteration + 1}: {len(orders)} pedidos encontrados")
                    
                    if not orders:
                        logger.info(f"📦 Nenhum pedido na página {iteration + 1}, finalizando busca")
                        break
                    
                    # Extrair pack_ids dos pedidos
                    for order in orders:
                        order_id = order.get("id")
                        pack_id = order.get("pack_id") or order_id  # Se pack_id for null, usar order_id
                        
                        if pack_id:
                            package_data = {
                                "id": pack_id,
                                "order_id": order_id,
                                "pack_id": pack_id,
                                "buyer": order.get("buyer", {}),
                                "order_date": order.get("date_created"),
                                "status": order.get("status"),
                                "order_data": order  # Guardar dados completos do pedido
                            }
                            all_packages.append(package_data)
                    
                    logger.info(f"📦 {len(all_packages)} pacotes extraídos até agora")
                    
                    # Verificar se há mais páginas
                    total = data.get("paging", {}).get("total", 0)
                    if total > 0:
                        logger.info(f"📦 Total de pedidos disponíveis: {total}")
                    
                    # Se não estiver buscando todas as páginas ou não houver mais resultados
                    if not fetch_all or len(orders) < limit:
                        break
                    
                    # Avançar para próxima página
                    current_offset += limit
                    iteration += 1
                    
                    # Pequeno delay para não sobrecarregar a API
                    import time
                    time.sleep(0.5)
                    
                elif response.status_code == 404:
                    logger.warning(f"⚠️ Endpoint /orders/search retornou 404")
                    logger.warning(f"⚠️ Tentando método alternativo...")
                    break
                else:
                    logger.error(f"❌ Erro ao buscar pedidos: Status {response.status_code}")
                    logger.error(f"❌ Resposta: {response.text[:500]}")
                    break
            
            logger.info(f"✅ ========== BUSCA DE PACOTES CONCLUÍDA ==========")
            logger.info(f"✅ Total de pacotes encontrados: {len(all_packages)}")
            logger.info(f"✅ Páginas processadas: {iteration + 1}")
            
            if len(all_packages) == 0:
                logger.warning(f"⚠️ Nenhum pacote encontrado. Possíveis razões:")
                logger.warning(f"   1. Não há pedidos recentes com mensagens pós-venda")
                logger.warning(f"   2. As mensagens são recebidas principalmente através de webhooks/notificações")
                logger.warning(f"   3. Os pedidos não possuem pack_id associado")
            
            return all_packages
            
        except Exception as e:
            logger.error(f"❌ ========== ERRO AO BUSCAR PACOTES ==========")
            logger.error(f"❌ ML User ID: {ml_user_id}")
            logger.error(f"❌ Erro: {str(e)}", exc_info=True)
            logger.error(f"❌ ========== FIM DO ERRO ==========")
            return []
    
    def save_thread_to_db(self, thread_data: Dict, company_id: int, ml_account_id: int, ml_user_id: str) -> Optional[MLMessageThread]:
        """Salva ou atualiza uma thread/conversa no banco"""
        logger.info(f"💾 ========== SALVANDO THREAD NO BANCO ==========")
        logger.info(f"💾 Company ID: {company_id}")
        logger.info(f"💾 ML Account ID: {ml_account_id}")
        logger.info(f"💾 ML User ID: {ml_user_id}")
        
        try:
            package_id = thread_data.get("package_id") or thread_data.get("id")
            logger.info(f"💾 Package ID extraído: {package_id}")
            
            if not package_id:
                logger.warning("❌ Thread sem package_id, ignorando...")
                logger.warning(f"❌ Dados recebidos: {list(thread_data.keys())}")
                return None
            
            # Buscar thread existente
            logger.info(f"🔍 Verificando se thread já existe no banco: package_id={package_id}, company_id={company_id}")
            thread = self.db.query(MLMessageThread).filter(
                MLMessageThread.ml_thread_id == str(package_id),
                MLMessageThread.company_id == company_id
            ).first()
            
            if thread:
                logger.info(f"📝 Thread existente encontrada! ID: {thread.id}, atualizando...")
            else:
                logger.info(f"✨ Nova thread, criando...")
            
            buyer_data = thread_data.get("buyer", {})
            buyer_id = str(buyer_data.get("id", "")) if buyer_data else "UNKNOWN"
            buyer_nickname = buyer_data.get("nickname") if buyer_data else None
            
            messages_data = thread_data.get("messages", [])
            last_message = messages_data[-1] if messages_data else {}
            
            order_ids = []
            if thread_data.get("order_ids"):
                order_ids = thread_data["order_ids"]
            elif thread_data.get("orders"):
                order_ids = [o.get("id") for o in thread_data["orders"] if o.get("id")]
            
            if thread:
                # Atualizar thread existente
                thread.ml_package_id = str(package_id)
                thread.ml_buyer_id = buyer_id
                thread.buyer_nickname = buyer_nickname
                thread.status = MLMessageThreadStatus.OPEN if thread_data.get("status") != "closed" else MLMessageThreadStatus.CLOSED
                thread.last_message_date = datetime.fromisoformat(last_message.get("date").replace("Z", "+00:00")) if last_message.get("date") else None
                thread.last_message_text = last_message.get("text") if last_message else None
                thread.order_ids = order_ids
                thread.thread_data = thread_data
                thread.last_sync = datetime.now()
                thread.updated_at = datetime.now()
            else:
                # Criar nova thread
                thread = MLMessageThread(
                    company_id=company_id,
                    ml_account_id=ml_account_id,
                    ml_thread_id=str(package_id),
                    ml_package_id=str(package_id),
                    ml_buyer_id=buyer_id,
                    buyer_nickname=buyer_nickname,
                    reason=thread_data.get("reason"),
                    subject=thread_data.get("subject"),
                    status=MLMessageThreadStatus.OPEN if thread_data.get("status") != "closed" else MLMessageThreadStatus.CLOSED,
                    last_message_date=datetime.fromisoformat(last_message.get("date").replace("Z", "+00:00")) if last_message.get("date") else None,
                    last_message_text=last_message.get("text") if last_message else None,
                    order_ids=order_ids,
                    thread_data=thread_data,
                    last_sync=datetime.now()
                )
                self.db.add(thread)
            
            logger.info(f"💾 Fazendo commit do thread no banco...")
            self.db.commit()
            self.db.refresh(thread)
            
            logger.info(f"✅ Thread commitado! ID no banco: {thread.id}")
            
            # Salvar mensagens individuais
            logger.info(f"📨 Processando {len(messages_data)} mensagens...")
            if messages_data:
                saved_messages = 0
                for idx, msg_data in enumerate(messages_data):
                    logger.info(f"📨 Salvando mensagem {idx + 1}/{len(messages_data)}: message_id={msg_data.get('id')}")
                    saved_msg = self.save_message_to_db(msg_data, thread.id, company_id, ml_user_id)
                    if saved_msg:
                        saved_messages += 1
                
                logger.info(f"✅ {saved_messages}/{len(messages_data)} mensagens salvas com sucesso")
            else:
                logger.info(f"ℹ️ Nenhuma mensagem para salvar")
            
            logger.info(f"💾 ========== THREAD SALVO COM SUCESSO ==========")
            logger.info(f"✅ Thread {package_id} salva/atualizada no banco com ID: {thread.id}")
            return thread
            
        except Exception as e:
            logger.error(f"❌ ========== ERRO AO SALVAR THREAD ==========")
            logger.error(f"❌ Package ID: {package_id}")
            logger.error(f"❌ Company ID: {company_id}")
            logger.error(f"❌ Erro: {str(e)}")
            logger.error(f"❌ Tipo: {type(e).__name__}")
            logger.error(f"❌ Traceback:", exc_info=True)
            self.db.rollback()
            logger.error(f"❌ Rollback executado")
            logger.error(f"❌ ========== FIM DO ERRO ==========")
            return None
    
    def save_message_to_db(self, message_data: Dict, thread_id: int, company_id: int, ml_user_id: str) -> Optional[MLMessage]:
        """Salva ou atualiza uma mensagem individual no banco"""
        try:
            ml_message_id = str(message_data.get("id", ""))
            if not ml_message_id:
                logger.warning("Mensagem sem ID, ignorando...")
                return None
            
            # Buscar mensagem existente
            message = self.db.query(MLMessage).filter(
                MLMessage.ml_message_id == ml_message_id,
                MLMessage.thread_id == thread_id
            ).first()
            
            from_data = message_data.get("from", {})
            to_data = message_data.get("to", {})
            
            from_user_id = str(from_data.get("user_id", from_data.get("id", ""))) if from_data else "UNKNOWN"
            from_nickname = from_data.get("nickname") if from_data else None
            
            to_user_id = str(to_data.get("user_id", to_data.get("id", ""))) if to_data else "UNKNOWN"
            to_nickname = to_data.get("nickname") if to_data else None
            
            is_seller = from_user_id == str(ml_user_id)
            
            message_date = None
            if message_data.get("date"):
                try:
                    message_date = datetime.fromisoformat(message_data.get("date").replace("Z", "+00:00"))
                except:
                    message_date = datetime.now()
            else:
                message_date = datetime.now()
            
            if message:
                # Atualizar mensagem existente
                message.message_text = message_data.get("text", "")
                message.from_nickname = from_nickname
                message.to_nickname = to_nickname
                message.read = message_data.get("read", False)
                message.message_data = message_data
                message.updated_at = datetime.now()
            else:
                # Criar nova mensagem
                message = MLMessage(
                    thread_id=thread_id,
                    company_id=company_id,
                    ml_message_id=ml_message_id,
                    from_user_id=from_user_id,
                    from_nickname=from_nickname,
                    to_user_id=to_user_id,
                    to_nickname=to_nickname,
                    message_text=message_data.get("text", ""),
                    message_type=MLMessageType.TEXT,  # Por enquanto apenas texto
                    is_seller=is_seller,
                    message_date=message_date,
                    read=message_data.get("read", False),
                    message_data=message_data
                )
                self.db.add(message)
            
            self.db.commit()
            self.db.refresh(message)
            
            return message
            
        except Exception as e:
            logger.error(f"Erro ao salvar mensagem no banco: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def sync_messages(self, company_id: int, user_id: int, ml_account_id: int = None, 
                     date_from: Optional[str] = None, date_to: Optional[str] = None,
                     fetch_all: bool = True) -> Dict:
        """
        Sincroniza mensagens pós-venda de todas as contas ML ativas da empresa
        
        Args:
            company_id: ID da empresa
            user_id: ID do usuário (para obter token)
            ml_account_id: ID específico da conta ML (opcional)
            date_from: Data inicial para filtrar mensagens (formato ISO: YYYY-MM-DD)
            date_to: Data final para filtrar mensagens (formato ISO: YYYY-MM-DD)
            fetch_all: Se True, busca todas as páginas disponíveis (padrão: True para buscar histórico completo)
        
        Returns:
            Dicionário com resultado da sincronização
        """
        try:
            logger.info(f"🔄 ========== INICIANDO SINCRONIZAÇÃO DE MENSAGENS ==========")
            logger.info(f"🔄 Company ID: {company_id}")
            logger.info(f"🔄 User ID: {user_id}")
            if ml_account_id:
                logger.info(f"🔄 ML Account ID específico: {ml_account_id}")
            if date_from:
                logger.info(f"🔄 Período: de {date_from} até {date_to or 'hoje'}")
            
            access_token = self._get_access_token(user_id)
            if not access_token:
                logger.error(f"❌ Token de acesso não encontrado ou expirado")
                return {
                    "success": False,
                    "error": "Token de acesso não encontrado ou expirado",
                    "synced": 0
                }
            
            # Buscar contas ML ativas
            accounts_query = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            )
            
            if ml_account_id:
                accounts_query = accounts_query.filter(MLAccount.id == ml_account_id)
            
            accounts = accounts_query.all()
            
            if not accounts:
                logger.warning(f"⚠️ Nenhuma conta ML ativa encontrada para company_id: {company_id}")
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada",
                    "synced": 0
                }
            
            logger.info(f"🔄 Contas ML encontradas: {len(accounts)}")
            
            total_synced = 0
            total_processed = 0
            errors = []
            
            for account in accounts:
                try:
                    ml_user_id = str(account.ml_user_id)
                    logger.info(f"🔄 Processando conta ML: {account.nickname} (ID: {account.id}, ML User: {ml_user_id})")
                    
                    # Buscar pacotes/conversas com paginação completa
                    packages = self.get_packages(
                        ml_user_id, 
                        access_token, 
                        limit=50,
                        fetch_all=fetch_all,
                        date_from=date_from,
                        date_to=date_to
                    )
                    
                    logger.info(f"🔄 {len(packages)} pacotes encontrados para a conta {account.nickname}")
                    
                    if len(packages) == 0:
                        logger.warning(f"⚠️ Nenhum pacote encontrado para a conta {account.nickname}")
                        logger.warning(f"⚠️ O Mercado Livre pode não fornecer um endpoint público para buscar histórico de mensagens.")
                        logger.warning(f"⚠️ As mensagens são recebidas apenas através de notificações webhook quando há novas mensagens.")
                        continue
                    
                    for package_data in packages:
                        try:
                            total_processed += 1
                            package_id = package_data.get("id")
                            
                            logger.info(f"🔄 Processando pacote {total_processed}/{len(packages)}: {package_id}")
                            
                            # Buscar detalhes completos do pacote (mensagens)
                            seller_id = ml_user_id
                            thread_details = self.get_thread_messages(package_id, access_token, seller_id=seller_id)
                            if thread_details:
                                package_data.update(thread_details)
                            
                            # Salvar no banco
                            saved = self.save_thread_to_db(package_data, company_id, account.id, ml_user_id)
                            if saved:
                                total_synced += 1
                                logger.info(f"✅ Pacote {package_id} salvo com sucesso")
                            else:
                                logger.warning(f"⚠️ Falha ao salvar pacote {package_id}")
                                
                        except Exception as e:
                            error_msg = f"Erro ao processar pacote {package_data.get('id')}: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            errors.append(error_msg)
                
                except Exception as e:
                    error_msg = f"Erro ao sincronizar conta {account.nickname}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            logger.info(f"✅ ========== SINCRONIZAÇÃO CONCLUÍDA ==========")
            logger.info(f"✅ Total de pacotes processados: {total_processed}")
            logger.info(f"✅ Total de pacotes salvos: {total_synced}")
            if errors:
                logger.warning(f"⚠️ Total de erros: {len(errors)}")
            
            return {
                "success": True,
                "synced": total_synced,
                "processed": total_processed,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"❌ ========== ERRO NA SINCRONIZAÇÃO ==========")
            logger.error(f"❌ Erro: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "synced": 0
            }

