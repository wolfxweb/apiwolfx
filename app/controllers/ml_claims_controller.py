"""
Controller para gerenciar Claims (Reclamações e Devoluções) do Mercado Livre
"""
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.services.ml_claims_service import MLClaimsService
from app.models.saas_models import (
    MLClaim, MLClaimMessage, MLClaimEvidence, MLClaimStatus, MLClaimType,
    MLAccount, MLAccountStatus, User, Company
)
from app.services.token_manager import TokenManager
from app.utils.notification_logger import global_logger

logger = logging.getLogger(__name__)

class MLClaimsController:
    """Controller para gerenciar claims e devoluções"""
    
    def __init__(self, db: Session):
        self.db = db
        self.service = MLClaimsService()
    
    def get_claims(
        self,
        company_id: int,
        ml_account_id: Optional[int] = None,
        claim_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Lista claims da empresa (garantindo que ml_account_id pertence ao company_id)
        
        Args:
            company_id: ID da empresa
            ml_account_id: ID da conta ML (opcional, filtra por conta específica)
            claim_type: 'mediations' ou 'returns' (opcional)
            status: 'opened', 'closed', 'cancelled', 'expired' (opcional)
            limit: Número de resultados
            offset: Paginação
            
        Returns:
            Dict com lista de claims e total
        """
        try:
            query = self.db.query(MLClaim).filter(MLClaim.company_id == company_id)
            
            if ml_account_id:
                # Garantir que a conta ML pertence à empresa
                ml_account = self.db.query(MLAccount).filter(
                    MLAccount.id == ml_account_id,
                    MLAccount.company_id == company_id
                ).first()
                
                if not ml_account:
                    return {
                        "success": False,
                        "error": f"Conta ML {ml_account_id} não encontrada ou não pertence à sua empresa",
                        "claims": [],
                        "total": 0
                    }
                
                query = query.filter(MLClaim.ml_account_id == ml_account_id)
            
            if claim_type:
                try:
                    claim_type_enum = MLClaimType[claim_type.upper()] if isinstance(claim_type, str) else claim_type
                    query = query.filter(MLClaim.claim_type == claim_type_enum)
                except (KeyError, ValueError):
                    logger.warning(f"Tipo de claim inválido: {claim_type}")
            
            if status:
                try:
                    status_enum = MLClaimStatus[status.upper()] if isinstance(status, str) else status
                    query = query.filter(MLClaim.status == status_enum)
                except (KeyError, ValueError):
                    logger.warning(f"Status de claim inválido: {status}")
            
            # Contar total antes de aplicar limit/offset
            total = query.count()
            
            # Aplicar ordenação, limit e offset
            claims = query.order_by(MLClaim.date_created.desc()).offset(offset).limit(limit).all()
            
            claims_data = []
            for claim in claims:
                claims_data.append({
                    "id": claim.id,
                    "ml_claim_id": claim.ml_claim_id,
                    "ml_order_id": claim.ml_order_id,
                    "claim_type": claim.claim_type.value if claim.claim_type else None,
                    "status": claim.status.value if claim.status else None,
                    "buyer_nickname": claim.buyer_nickname,
                    "date_created": claim.date_created.isoformat() if claim.date_created else None,
                    "date_updated": claim.date_updated.isoformat() if claim.date_updated else None,
                    "resolution_reason": claim.resolution_reason,
                    "resolution_status": claim.resolution_status,
                    "ml_account_id": claim.ml_account_id
                })
            
            return {
                "success": True,
                "claims": claims_data,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Erro ao listar claims: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "claims": [],
                "total": 0
            }
    
    def get_claim_details(self, claim_id: int, company_id: int) -> Dict:
        """
        Busca detalhes completos de um claim específico
        
        Args:
            claim_id: ID do claim no banco local
            company_id: ID da empresa (para validação de segurança)
            
        Returns:
            Dict com detalhes do claim
        """
        try:
            claim = self.db.query(MLClaim).filter(
                MLClaim.id == claim_id,
                MLClaim.company_id == company_id
            ).first()
            
            if not claim:
                return {
                    "success": False,
                    "error": "Claim não encontrado ou não pertence à sua empresa"
                }
            
            # Buscar mensagens
            messages = self.db.query(MLClaimMessage).filter(
                MLClaimMessage.claim_id == claim.id
            ).order_by(MLClaimMessage.date_created.asc()).all()
            
            messages_data = []
            for msg in messages:
                messages_data.append({
                    "id": msg.id,
                    "ml_message_id": msg.ml_message_id,
                    "from_type": msg.from_type,
                    "message_text": msg.message_text,
                    "date_created": msg.date_created.isoformat() if msg.date_created else None
                })
            
            # Buscar evidências
            evidences = self.db.query(MLClaimEvidence).filter(
                MLClaimEvidence.claim_id == claim.id
            ).all()
            
            evidences_data = []
            for evid in evidences:
                evidences_data.append({
                    "id": evid.id,
                    "ml_evidence_id": evid.ml_evidence_id,
                    "evidence_type": evid.evidence_type,
                    "evidence_url": evid.evidence_url
                })
            
            return {
                "success": True,
                "claim": {
                    "id": claim.id,
                    "ml_claim_id": claim.ml_claim_id,
                    "ml_order_id": claim.ml_order_id,
                    "ml_buyer_id": claim.ml_buyer_id,
                    "ml_seller_id": claim.ml_seller_id,
                    "claim_type": claim.claim_type.value if claim.claim_type else None,
                    "status": claim.status.value if claim.status else None,
                    "buyer_nickname": claim.buyer_nickname,
                    "date_created": claim.date_created.isoformat() if claim.date_created else None,
                    "date_updated": claim.date_updated.isoformat() if claim.date_updated else None,
                    "date_closed": claim.date_closed.isoformat() if claim.date_closed else None,
                    "resolution_reason": claim.resolution_reason,
                    "resolution_status": claim.resolution_status,
                    "resolution_date": claim.resolution_date.isoformat() if claim.resolution_date else None,
                    "claim_data": claim.claim_data,
                    "ml_account_id": claim.ml_account_id,
                    "messages": messages_data,
                    "evidences": evidences_data
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do claim: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_claims(self, company_id: int, user_id: int, ml_account_id: Optional[int] = None) -> Dict:
        """
        Sincroniza claims do Mercado Livre com o banco de dados
        
        Args:
            company_id: ID da empresa
            user_id: ID do usuário
            ml_account_id: ID da conta ML (opcional, sincroniza todas se não informado)
            
        Returns:
            Dict com resultado da sincronização
        """
        try:
            # Buscar token - usar token da empresa
            token_manager = TokenManager(self.db)
            token_record = token_manager.get_token_record_for_company(company_id)
            if not token_record or not token_record.access_token:
                return {"success": False, "error": "Token não encontrado"}
            access_token = token_record.access_token
            
            # Buscar contas ML da empresa
            if ml_account_id:
                ml_accounts = self.db.query(MLAccount).filter(
                    MLAccount.id == ml_account_id,
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).all()
            else:
                ml_accounts = self.db.query(MLAccount).filter(
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).all()
            
            if not ml_accounts:
                return {"success": False, "error": "Nenhuma conta ML ativa encontrada"}
            
            logger.info(f"📋 Encontradas {len(ml_accounts)} contas ML ativas para company_id {company_id}")
            for acc in ml_accounts:
                logger.info(f"  - Conta ML ID: {acc.id}, Nickname: {acc.nickname}, ml_user_id: {acc.ml_user_id}")
            
            # Criar mapa de ml_user_id -> ml_account para busca rápida
            ml_accounts_map = {str(acc.ml_user_id): acc for acc in ml_accounts}
            
            total_synced = 0
            total_updated = 0
            total_created = 0
            
            # Sincronizar claims de cada tipo
            for claim_type in ["mediations", "returns"]:
                logger.info(f"🔄 Sincronizando claims tipo: {claim_type}")
                
                # Buscar claims do ML usando o token disponível
                claims_data = self.service.get_claims(
                    access_token=access_token,
                    claim_type=claim_type,
                    limit=100,
                    offset=0
                )
                
                claims_list = claims_data.get("data", [])
                logger.info(f"📦 Encontrados {len(claims_list)} claims do tipo {claim_type} na API")
                
                for claim_data in claims_list:
                    try:
                        ml_claim_id = str(claim_data.get("id"))
                        
                        # Tentar obter seller_id de diferentes formas
                        seller_obj = claim_data.get("seller", {})
                        ml_seller_id = None
                        
                        if seller_obj:
                            if isinstance(seller_obj, dict):
                                ml_seller_id = seller_obj.get("id")
                            elif isinstance(seller_obj, (int, str)):
                                ml_seller_id = str(seller_obj)
                        
                        # Se ainda não encontrou, tentar buscar do resource_id (order_id)
                        if not ml_seller_id:
                            resource_id = claim_data.get("resource_id")
                            if resource_id:
                                # Buscar order para obter seller_id
                                try:
                                    order_url = f"{self.service.base_url}/orders/{resource_id}"
                                    headers = {"Authorization": f"Bearer {access_token}"}
                                    order_response = requests.get(order_url, headers=headers, timeout=10)
                                    if order_response.status_code == 200:
                                        order_data = order_response.json()
                                        seller_info = order_data.get("seller", {})
                                        if isinstance(seller_info, dict):
                                            ml_seller_id = seller_info.get("id")
                                        elif seller_info:
                                            ml_seller_id = str(seller_info)
                                        logger.debug(f"✅ Seller ID obtido do order {resource_id}: {ml_seller_id}")
                                except Exception as e:
                                    logger.debug(f"Erro ao buscar order {resource_id}: {e}")
                        
                        if not ml_seller_id:
                            logger.warning(f"⚠️ Seller ID não encontrado no claim {ml_claim_id}, dados: {claim_data.get('seller')}, resource_id: {claim_data.get('resource_id')}")
                            continue
                        
                        ml_seller_id = str(ml_seller_id)
                        
                        # Encontrar conta ML correspondente usando o mapa
                        ml_account = ml_accounts_map.get(ml_seller_id)
                        
                        if not ml_account:
                            logger.warning(f"⚠️ Conta ML não encontrada para seller_id: {ml_seller_id} (claim: {ml_claim_id}). Contas disponíveis: {list(ml_accounts_map.keys())}")
                            continue
                        
                        logger.debug(f"✅ Claim {ml_claim_id} associado à conta ML {ml_account.id} ({ml_account.nickname})")
                        
                        # Verificar se claim já existe
                        existing_claim = self.db.query(MLClaim).filter(
                            MLClaim.ml_claim_id == ml_claim_id,
                            MLClaim.company_id == company_id
                        ).first()
                        
                        # Parsear datas
                        date_created = None
                        date_updated = None
                        date_closed = None
                        resolution_date = None
                        
                        if claim_data.get("date_created"):
                            try:
                                date_created = datetime.fromisoformat(claim_data["date_created"].replace("Z", "+00:00"))
                            except:
                                pass
                        
                        if claim_data.get("date_updated"):
                            try:
                                date_updated = datetime.fromisoformat(claim_data["date_updated"].replace("Z", "+00:00"))
                            except:
                                pass
                        
                        if claim_data.get("date_closed"):
                            try:
                                date_closed = datetime.fromisoformat(claim_data["date_closed"].replace("Z", "+00:00"))
                            except:
                                pass
                        
                        resolution = claim_data.get("resolution", {})
                        if resolution.get("date"):
                            try:
                                resolution_date = datetime.fromisoformat(resolution["date"].replace("Z", "+00:00"))
                            except:
                                pass
                        
                        # Parsear enums
                        claim_type_enum = MLClaimType.MEDIATIONS if claim_type == "mediations" else MLClaimType.RETURNS
                        status_str = claim_data.get("status", "opened").lower()
                        status_enum = MLClaimStatus.OPENED
                        try:
                            status_enum = MLClaimStatus[status_str.upper()]
                        except:
                            pass
                        
                        if existing_claim:
                            # Atualizar claim existente
                            existing_claim.status = status_enum
                            existing_claim.date_updated = date_updated
                            existing_claim.date_closed = date_closed
                            existing_claim.resolution_reason = resolution.get("reason")
                            existing_claim.resolution_status = resolution.get("status")
                            existing_claim.resolution_date = resolution_date
                            existing_claim.claim_data = claim_data
                            existing_claim.last_sync = datetime.now()
                            total_updated += 1
                        else:
                            # Criar novo claim
                            new_claim = MLClaim(
                                company_id=company_id,
                                ml_account_id=ml_account.id,
                                ml_claim_id=ml_claim_id,
                                ml_order_id=str(claim_data.get("resource_id", "")),
                                ml_buyer_id=str(claim_data.get("buyer", {}).get("id", "")),
                                ml_seller_id=ml_seller_id,
                                claim_type=claim_type_enum,
                                status=status_enum,
                                resolution_reason=resolution.get("reason"),
                                resolution_status=resolution.get("status"),
                                resolution_date=resolution_date,
                                date_created=date_created or datetime.now(),
                                date_updated=date_updated,
                                date_closed=date_closed,
                                buyer_nickname=claim_data.get("buyer", {}).get("nickname"),
                                claim_data=claim_data,
                                last_sync=datetime.now()
                            )
                            self.db.add(new_claim)
                            total_created += 1
                        
                        total_synced += 1
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar claim {claim_data.get('id')}: {e}", exc_info=True)
                        continue
                
                self.db.commit()
            
            logger.info(f"✅ Sincronização concluída: {total_created} criados, {total_updated} atualizados, {total_synced} total")
            
            return {
                "success": True,
                "message": f"Sincronização concluída: {total_created} criados, {total_updated} atualizados",
                "created": total_created,
                "updated": total_updated,
                "total": total_synced
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao sincronizar claims: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_notification(self, resource: str, ml_user_id: int, company_id: int) -> bool:
        """
        Processa notificação de claim (chamado pelo notification controller)
        
        Args:
            resource: Resource da notificação (ex: "/post-purchase/v1/claims/123456789")
            ml_user_id: ID do usuário ML
            company_id: ID da empresa
            
        Returns:
            True se processado com sucesso, False caso contrário
        """
        try:
            # Extrair claim_id do resource: "/post-purchase/v1/claims/123456789"
            claim_id = resource.split("/")[-1]
            
            logger.info(f"⚠️ Processando notificação de claim - Claim ID: {claim_id}, ML User ID: {ml_user_id}, Company ID: {company_id}")
            
            # Buscar conta ML
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.ml_user_id == str(ml_user_id),
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not ml_account:
                error_msg = f"Conta ML não encontrada para ml_user_id: {ml_user_id}, company_id: {company_id}"
                logger.warning(error_msg)
                global_logger.log_event(
                    event_type="claim_processed",
                    data={
                        "claim_id": claim_id,
                        "ml_account_id": None,
                        "action": "error",
                        "description": error_msg
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return False
            
            ml_account_id = ml_account.id
            logger.info(f"✅ Conta ML encontrada: ID {ml_account_id}, Nickname: {ml_account.nickname}")
            
            # Obter token - usar token da empresa
            token_manager = TokenManager(self.db)
            token_record = token_manager.get_token_record_for_company(company_id)
            if not token_record or not token_record.access_token:
                error_msg = f"Token não encontrado para company_id: {company_id}"
                logger.warning(error_msg)
                return False
            access_token = token_record.access_token
            
            # Buscar detalhes do claim na API
            logger.info(f"📡 Buscando detalhes do claim {claim_id} na API do Mercado Livre...")
            claim_data = self.service.get_claim_details(claim_id, access_token)
            
            if not claim_data:
                logger.error(f"❌ Não foi possível buscar detalhes do claim {claim_id}")
                return False
            
            # Processar e salvar claim
            self._save_claim_from_api(claim_data, company_id, ml_account_id)
            
            logger.info(f"✅ Claim {claim_id} processado com sucesso")
            global_logger.log_event(
                event_type="claim_processed",
                data={
                    "claim_id": claim_id,
                    "ml_account_id": ml_account_id,
                    "action": "synced",
                    "description": f"Claim {claim_id} sincronizado com sucesso"
                },
                company_id=company_id,
                success=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar notificação de claim: {e}", exc_info=True)
            return False
    
    def _save_claim_from_api(self, claim_data: Dict, company_id: int, ml_account_id: int):
        """
        Salva ou atualiza claim a partir dos dados da API
        
        Args:
            claim_data: Dados do claim retornados pela API
            company_id: ID da empresa
            ml_account_id: ID da conta ML
        """
        try:
            ml_claim_id = str(claim_data.get("id"))
            
            # Verificar se já existe
            existing_claim = self.db.query(MLClaim).filter(
                MLClaim.ml_claim_id == ml_claim_id,
                MLClaim.company_id == company_id
            ).first()
            
            # Parsear datas
            date_created = None
            date_updated = None
            date_closed = None
            resolution_date = None
            
            if claim_data.get("date_created"):
                try:
                    date_created = datetime.fromisoformat(claim_data["date_created"].replace("Z", "+00:00"))
                except:
                    pass
            
            if claim_data.get("date_updated"):
                try:
                    date_updated = datetime.fromisoformat(claim_data["date_updated"].replace("Z", "+00:00"))
                except:
                    pass
            
            if claim_data.get("date_closed"):
                try:
                    date_closed = datetime.fromisoformat(claim_data["date_closed"].replace("Z", "+00:00"))
                except:
                    pass
            
            resolution = claim_data.get("resolution", {})
            if resolution.get("date"):
                try:
                    resolution_date = datetime.fromisoformat(resolution["date"].replace("Z", "+00:00"))
                except:
                    pass
            
            # Parsear enums
            claim_type_str = claim_data.get("type", "returns")
            claim_type_enum = MLClaimType.MEDIATIONS if claim_type_str == "mediations" else MLClaimType.RETURNS
            
            status_str = claim_data.get("status", "opened").lower()
            status_enum = MLClaimStatus.OPENED
            try:
                status_enum = MLClaimStatus[status_str.upper()]
            except:
                pass
            
            if existing_claim:
                # Atualizar
                existing_claim.status = status_enum
                existing_claim.date_updated = date_updated
                existing_claim.date_closed = date_closed
                existing_claim.resolution_reason = resolution.get("reason")
                existing_claim.resolution_status = resolution.get("status")
                existing_claim.resolution_date = resolution_date
                existing_claim.claim_data = claim_data
                existing_claim.last_sync = datetime.now()
            else:
                # Criar novo
                new_claim = MLClaim(
                    company_id=company_id,
                    ml_account_id=ml_account_id,
                    ml_claim_id=ml_claim_id,
                    ml_order_id=str(claim_data.get("resource_id", "")),
                    ml_buyer_id=str(claim_data.get("buyer", {}).get("id", "")),
                    ml_seller_id=str(claim_data.get("seller", {}).get("id", "")),
                    claim_type=claim_type_enum,
                    status=status_enum,
                    resolution_reason=resolution.get("reason"),
                    resolution_status=resolution.get("status"),
                    resolution_date=resolution_date,
                    date_created=date_created or datetime.now(),
                    date_updated=date_updated,
                    date_closed=date_closed,
                    buyer_nickname=claim_data.get("buyer", {}).get("nickname"),
                    claim_data=claim_data,
                    last_sync=datetime.now()
                )
                self.db.add(new_claim)
            
            # Processar mensagens
            messages = claim_data.get("messages", [])
            for msg_data in messages:
                ml_message_id = str(msg_data.get("id", ""))
                if not ml_message_id:
                    continue
                
                existing_msg = self.db.query(MLClaimMessage).filter(
                    MLClaimMessage.ml_message_id == ml_message_id
                ).first()
                
                if not existing_msg and existing_claim:
                    msg_date = None
                    if msg_data.get("date"):
                        try:
                            msg_date = datetime.fromisoformat(msg_data["date"].replace("Z", "+00:00"))
                        except:
                            pass
                    
                    new_msg = MLClaimMessage(
                        claim_id=existing_claim.id,
                        ml_message_id=ml_message_id,
                        from_type=msg_data.get("from", "buyer"),
                        message_text=msg_data.get("text", ""),
                        date_created=msg_date or datetime.now(),
                        message_data=msg_data
                    )
                    self.db.add(new_msg)
            
            # Processar evidências
            evidences = claim_data.get("evidences", [])
            for evid_data in evidences:
                ml_evidence_id = str(evid_data.get("id", ""))
                if not ml_evidence_id:
                    continue
                
                existing_evid = self.db.query(MLClaimEvidence).filter(
                    MLClaimEvidence.ml_evidence_id == ml_evidence_id
                ).first()
                
                if not existing_evid and existing_claim:
                    new_evid = MLClaimEvidence(
                        claim_id=existing_claim.id,
                        ml_evidence_id=ml_evidence_id,
                        evidence_type=evid_data.get("type"),
                        evidence_url=evid_data.get("url"),
                        evidence_data=evid_data
                    )
                    self.db.add(new_evid)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao salvar claim: {e}", exc_info=True)
            raise
    
    def accept_claim(self, claim_id: int, company_id: int, user_id: int, message: Optional[str] = None) -> Dict:
        """
        Aceita um claim
        
        Args:
            claim_id: ID do claim no banco local
            company_id: ID da empresa
            user_id: ID do usuário
            message: Mensagem opcional
            
        Returns:
            Dict com resultado
        """
        try:
            claim = self.db.query(MLClaim).filter(
                MLClaim.id == claim_id,
                MLClaim.company_id == company_id
            ).first()
            
            if not claim:
                return {"success": False, "error": "Claim não encontrado"}
            
            # Obter token - usar qualquer token ativo da empresa
            token_manager = TokenManager(self.db)
            access_token = token_manager.get_any_active_token(company_id)
            if not access_token:
                return {"success": False, "error": "Token não encontrado"}
            
            # Aceitar no ML
            success = self.service.accept_claim(claim.ml_claim_id, access_token, message)
            
            if success:
                # Atualizar status local
                claim.status = MLClaimStatus.CLOSED
                claim.date_updated = datetime.now()
                self.db.commit()
                
                return {"success": True, "message": "Claim aceito com sucesso"}
            else:
                return {"success": False, "error": "Erro ao aceitar claim no Mercado Livre"}
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao aceitar claim: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def reject_claim(self, claim_id: int, company_id: int, user_id: int, message: str) -> Dict:
        """
        Rejeita um claim
        
        Args:
            claim_id: ID do claim no banco local
            company_id: ID da empresa
            user_id: ID do usuário
            message: Mensagem obrigatória
            
        Returns:
            Dict com resultado
        """
        try:
            claim = self.db.query(MLClaim).filter(
                MLClaim.id == claim_id,
                MLClaim.company_id == company_id
            ).first()
            
            if not claim:
                return {"success": False, "error": "Claim não encontrado"}
            
            # Obter token - usar qualquer token ativo da empresa
            token_manager = TokenManager(self.db)
            access_token = token_manager.get_any_active_token(company_id)
            if not access_token:
                return {"success": False, "error": "Token não encontrado"}
            
            # Rejeitar no ML
            success = self.service.reject_claim(claim.ml_claim_id, access_token, message)
            
            if success:
                # Atualizar status local
                claim.status = MLClaimStatus.CLOSED
                claim.date_updated = datetime.now()
                self.db.commit()
                
                return {"success": True, "message": "Claim rejeitado com sucesso"}
            else:
                return {"success": False, "error": "Erro ao rejeitar claim no Mercado Livre"}
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao rejeitar claim: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def send_message(self, claim_id: int, company_id: int, user_id: int, message: str) -> Dict:
        """
        Envia mensagem em um claim
        
        Args:
            claim_id: ID do claim no banco local
            company_id: ID da empresa
            user_id: ID do usuário
            message: Texto da mensagem
            
        Returns:
            Dict com resultado
        """
        try:
            claim = self.db.query(MLClaim).filter(
                MLClaim.id == claim_id,
                MLClaim.company_id == company_id
            ).first()
            
            if not claim:
                return {"success": False, "error": "Claim não encontrado"}
            
            # Obter token - usar qualquer token ativo da empresa
            token_manager = TokenManager(self.db)
            access_token = token_manager.get_any_active_token(company_id)
            if not access_token:
                return {"success": False, "error": "Token não encontrado"}
            
            # Enviar mensagem no ML
            success = self.service.send_message(claim.ml_claim_id, access_token, message)
            
            if success:
                # Buscar detalhes atualizados para sincronizar mensagens
                claim_data = self.service.get_claim_details(claim.ml_claim_id, access_token)
                if claim_data:
                    self._save_claim_from_api(claim_data, company_id, claim.ml_account_id)
                
                return {"success": True, "message": "Mensagem enviada com sucesso"}
            else:
                return {"success": False, "error": "Erro ao enviar mensagem no Mercado Livre"}
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

