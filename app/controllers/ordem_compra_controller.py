"""
Controller para Ordens de Compra
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.saas_models import OrdemCompra, OrdemCompraItem, Fornecedor
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

class OrdemCompraController:
    """Controller para operações com ordens de compra"""
    
    def __init__(self):
        pass
    
    def get_ordens_compra(self, company_id: int, db: Session, status: str = None, search: str = None, 
                          date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
        """Buscar ordens de compra da empresa"""
        try:
            query = db.query(OrdemCompra).filter(OrdemCompra.company_id == company_id)
            
            if status:
                query = query.filter(OrdemCompra.status == status)
            
            if search:
                # Buscar por número da ordem ou nome do fornecedor
                query = query.join(Fornecedor, OrdemCompra.fornecedor_id == Fornecedor.id, isouter=True).filter(
                    or_(
                        OrdemCompra.numero_ordem.ilike(f"%{search}%"),
                        Fornecedor.nome.ilike(f"%{search}%")
                    )
                )
            
            if date_from:
                query = query.filter(OrdemCompra.data_ordem >= datetime.strptime(date_from, '%Y-%m-%d').date())
            
            if date_to:
                query = query.filter(OrdemCompra.data_ordem <= datetime.strptime(date_to, '%Y-%m-%d').date())
            
            ordens = query.order_by(OrdemCompra.data_ordem.desc()).all()
            
            return [
                {
                    "id": ordem.id,
                    "numero_ordem": ordem.numero_ordem,
                    "data_ordem": ordem.data_ordem.isoformat() if ordem.data_ordem else None,
                    "data_entrega_prevista": ordem.data_entrega_prevista.isoformat() if ordem.data_entrega_prevista else None,
                    "data_entrega_real": ordem.data_entrega_real.isoformat() if ordem.data_entrega_real else None,
                    "status": ordem.status,
                    "valor_total": float(ordem.valor_total or 0),
                    "desconto": float(ordem.desconto or 0),
                    "valor_final": float(ordem.valor_final or 0),
                    "moeda": ordem.moeda,
                    "cotacao_moeda": float(ordem.cotacao_moeda or 1.0),
                    "tipo_ordem": ordem.tipo_ordem,
                    "comissao_agente": float(ordem.comissao_agente or 0),
                    "percentual_comissao": float(ordem.percentual_comissao or 0),
                    "valor_transporte": float(ordem.valor_transporte or 0),
                    "percentual_importacao": float(ordem.percentual_importacao or 0),
                    "modalidade_importacao": ordem.modalidade_importacao,
                    "valor_impostos": float(ordem.valor_impostos or 0),
                    "fornecedor_nome": ordem.fornecedor.nome if ordem.fornecedor else None,
                    "fornecedor_id": ordem.fornecedor_id,
                    "observacoes": ordem.observacoes,
                    "condicoes_pagamento": ordem.condicoes_pagamento,
                    "prazo_entrega": ordem.prazo_entrega,
                    "created_at": ordem.created_at.isoformat() if ordem.created_at else None,
                    "updated_at": ordem.updated_at.isoformat() if ordem.updated_at else None
                }
                for ordem in ordens
            ]
        except Exception as e:
            logger.error(f"Erro ao buscar ordens de compra: {str(e)}")
            return []
    
    def get_ordem_compra_by_id(self, ordem_id: int, company_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Buscar ordem de compra por ID"""
        try:
            ordem = db.query(OrdemCompra).filter(
                OrdemCompra.id == ordem_id,
                OrdemCompra.company_id == company_id
            ).first()
            
            if not ordem:
                return None
            
            # Buscar itens da ordem
            itens = db.query(OrdemCompraItem).filter(
                OrdemCompraItem.ordem_compra_id == ordem_id
            ).all()
            
            return {
                "id": ordem.id,
                "numero_ordem": ordem.numero_ordem,
                "data_ordem": ordem.data_ordem.isoformat() if ordem.data_ordem else None,
                "data_entrega_prevista": ordem.data_entrega_prevista.isoformat() if ordem.data_entrega_prevista else None,
                "data_entrega_real": ordem.data_entrega_real.isoformat() if ordem.data_entrega_real else None,
                "status": ordem.status,
                "valor_total": float(ordem.valor_total or 0),
                "desconto": float(ordem.desconto or 0),
                "valor_final": float(ordem.valor_final or 0),
                "fornecedor_id": ordem.fornecedor_id,
                "fornecedor_nome": ordem.fornecedor.nome if ordem.fornecedor else None,
                "observacoes": ordem.observacoes,
                "condicoes_pagamento": ordem.condicoes_pagamento,
                "prazo_entrega": ordem.prazo_entrega,
                "itens": [
                    {
                        "id": item.id,
                        "produto_id": item.produto_id,
                        "produto_nome": item.produto_nome,
                        "produto_descricao": item.produto_descricao,
                        "produto_codigo": item.produto_codigo,
                        "quantidade": float(item.quantidade or 0),
                        "valor_unitario": float(item.valor_unitario or 0),
                        "valor_total": float(item.valor_total or 0),
                        "observacoes": item.observacoes
                    }
                    for item in itens
                ],
                "created_at": ordem.created_at.isoformat() if ordem.created_at else None,
                "updated_at": ordem.updated_at.isoformat() if ordem.updated_at else None
            }
        except Exception as e:
            logger.error(f"Erro ao buscar ordem de compra: {str(e)}")
            return None
    
    def create_ordem_compra(self, ordem_data: Dict[str, Any], company_id: int, db: Session) -> Dict[str, Any]:
        """Criar nova ordem de compra"""
        try:
            # Gerar número da ordem se não fornecido
            if not ordem_data.get('numero_ordem'):
                # Buscar último número da empresa
                ultima_ordem = db.query(OrdemCompra).filter(
                    OrdemCompra.company_id == company_id
                ).order_by(OrdemCompra.id.desc()).first()
                
                if ultima_ordem and ultima_ordem.numero_ordem:
                    try:
                        ultimo_numero = int(ultima_ordem.numero_ordem.split('-')[-1])
                        proximo_numero = ultimo_numero + 1
                    except:
                        proximo_numero = 1
                else:
                    proximo_numero = 1
                
                ordem_data['numero_ordem'] = f"OC-{proximo_numero:04d}"
            
            # Calcular valores
            itens = ordem_data.get('itens', [])
            valor_total = sum(float(item.get('valor_total', 0)) for item in itens)
            desconto = float(ordem_data.get('desconto', 0))
            valor_final = valor_total - desconto
            
            # Calcular impostos e comissão para ordens internacionais
            valor_impostos = 0
            valor_comissao = 0
            if ordem_data.get('tipo_ordem') == 'internacional':
                percentual_importacao = float(ordem_data.get('percentual_importacao', 0))
                percentual_comissao = float(ordem_data.get('comissao_agente', 0))
                valor_impostos = valor_total * (percentual_importacao / 100)
                valor_comissao = valor_total * (percentual_comissao / 100)
            
            ordem = OrdemCompra(
                company_id=company_id,
                fornecedor_id=ordem_data.get('fornecedor_id'),
                numero_ordem=ordem_data.get('numero_ordem'),
                data_ordem=datetime.strptime(ordem_data.get('data_ordem'), '%Y-%m-%d').date() if ordem_data.get('data_ordem') else date.today(),
                data_entrega_prevista=datetime.strptime(ordem_data.get('data_entrega_prevista'), '%Y-%m-%d').date() if ordem_data.get('data_entrega_prevista') else None,
                status=ordem_data.get('status', 'pendente'),
                valor_total=valor_total,
                desconto=desconto,
                valor_final=valor_final,
                moeda=ordem_data.get('moeda', 'BRL'),
                cotacao_moeda=float(ordem_data.get('cotacao_moeda', 1.0)),
                tipo_ordem=ordem_data.get('tipo_ordem', 'nacional'),
                comissao_agente=valor_comissao,
                percentual_comissao=float(ordem_data.get('comissao_agente', 0)),
                valor_transporte=float(ordem_data.get('valor_transporte', 0)),
                percentual_importacao=float(ordem_data.get('percentual_importacao', 0)),
                modalidade_importacao=ordem_data.get('modalidade_importacao'),
                valor_impostos=valor_impostos,
                observacoes=ordem_data.get('observacoes'),
                condicoes_pagamento=ordem_data.get('condicoes_pagamento'),
                prazo_entrega=ordem_data.get('prazo_entrega')
            )
            
            db.add(ordem)
            db.flush()  # Para obter o ID
            
            # Criar itens
            for item_data in itens:
                item = OrdemCompraItem(
                    ordem_compra_id=ordem.id,
                    produto_id=item_data.get('produto_id'),
                    produto_nome=item_data.get('produto_nome'),
                    produto_descricao=item_data.get('produto_descricao'),
                    produto_codigo=item_data.get('produto_codigo'),
                    produto_imagem=item_data.get('produto_imagem'),
                    descricao_fornecedor=item_data.get('descricao_fornecedor'),
                    quantidade=item_data.get('quantidade', 0),
                    valor_unitario=item_data.get('valor_unitario', 0),
                    valor_total=item_data.get('valor_total', 0),
                    url=item_data.get('url'),
                    observacoes=item_data.get('observacoes')
                )
                db.add(item)
            
            db.commit()
            db.refresh(ordem)
            
            return {
                "success": True,
                "message": "Ordem de compra criada com sucesso",
                "ordem_id": ordem.id
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao criar ordem de compra: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def update_ordem_compra(self, ordem_id: int, ordem_data: Dict[str, Any], company_id: int, db: Session) -> Dict[str, Any]:
        """Atualizar ordem de compra"""
        try:
            ordem = db.query(OrdemCompra).filter(
                OrdemCompra.id == ordem_id,
                OrdemCompra.company_id == company_id
            ).first()
            
            if not ordem:
                return {"success": False, "error": "Ordem de compra não encontrada"}
            
            # Atualizar dados da ordem
            for field, value in ordem_data.items():
                if field == 'data_ordem' and value:
                    setattr(ordem, field, datetime.strptime(value, '%Y-%m-%d').date())
                elif field == 'data_entrega_prevista' and value:
                    setattr(ordem, field, datetime.strptime(value, '%Y-%m-%d').date())
                elif field == 'data_entrega_real' and value:
                    setattr(ordem, field, datetime.strptime(value, '%Y-%m-%d').date())
                elif field == 'itens':
                    # Atualizar itens (remover existentes e criar novos)
                    db.query(OrdemCompraItem).filter(OrdemCompraItem.ordem_compra_id == ordem_id).delete()
                    
                    for item_data in value:
                        item = OrdemCompraItem(
                            ordem_compra_id=ordem_id,
                            produto_id=item_data.get('produto_id'),
                            produto_nome=item_data.get('produto_nome'),
                            produto_descricao=item_data.get('produto_descricao'),
                            produto_codigo=item_data.get('produto_codigo'),
                            produto_imagem=item_data.get('produto_imagem'),
                            descricao_fornecedor=item_data.get('descricao_fornecedor'),
                            quantidade=item_data.get('quantidade', 0),
                            valor_unitario=item_data.get('valor_unitario', 0),
                            valor_total=item_data.get('valor_total', 0),
                            url=item_data.get('url'),
                            observacoes=item_data.get('observacoes')
                        )
                        db.add(item)
                    
                    # Recalcular valores
                    itens = value
                    valor_total = sum(float(item.get('valor_total', 0)) for item in itens)
                    desconto = float(ordem_data.get('desconto', 0))
                    valor_final = valor_total - desconto
                    
                    ordem.valor_total = valor_total
                    ordem.desconto = desconto
                    ordem.valor_final = valor_final
                elif hasattr(ordem, field):
                    setattr(ordem, field, value)
            
            db.commit()
            
            return {
                "success": True,
                "message": "Ordem de compra atualizada com sucesso"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao atualizar ordem de compra: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def delete_ordem_compra(self, ordem_id: int, company_id: int, db: Session) -> Dict[str, Any]:
        """Deletar ordem de compra"""
        try:
            ordem = db.query(OrdemCompra).filter(
                OrdemCompra.id == ordem_id,
                OrdemCompra.company_id == company_id
            ).first()
            
            if not ordem:
                return {"success": False, "error": "Ordem de compra não encontrada"}
            
            # Deletar itens primeiro (cascade)
            db.query(OrdemCompraItem).filter(OrdemCompraItem.ordem_compra_id == ordem_id).delete()
            
            # Deletar ordem
            db.delete(ordem)
            db.commit()
            
            return {
                "success": True,
                "message": "Ordem de compra excluída com sucesso"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao deletar ordem de compra: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def update_status_ordem(self, ordem_id: int, status: str, company_id: int, db: Session) -> Dict[str, Any]:
        """Atualizar status da ordem de compra"""
        try:
            ordem = db.query(OrdemCompra).filter(
                OrdemCompra.id == ordem_id,
                OrdemCompra.company_id == company_id
            ).first()
            
            if not ordem:
                return {"success": False, "error": "Ordem de compra não encontrada"}
            
            ordem.status = status
            
            # Se status for "entregue", definir data de entrega real
            if status == "entregue" and not ordem.data_entrega_real:
                ordem.data_entrega_real = date.today()
            
            db.commit()
            
            return {
                "success": True,
                "message": f"Status alterado para: {status}",
                "status": status
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao alterar status da ordem: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
