"""
Controller para Fornecedores
"""
from sqlalchemy.orm import Session
from app.models.saas_models import Fornecedor
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FornecedoresController:
    """Controller para operações com fornecedores"""
    
    def __init__(self):
        pass
    
    def get_fornecedores(self, company_id: int, db: Session, ativo: bool = True) -> List[Dict[str, Any]]:
        """Buscar fornecedores da empresa"""
        try:
            query = db.query(Fornecedor).filter(Fornecedor.company_id == company_id)
            
            if ativo is not None:
                query = query.filter(Fornecedor.ativo == ativo)
            
            fornecedores = query.order_by(Fornecedor.nome).all()
            
            return [
                {
                    "id": fornecedor.id,
                    "nome": fornecedor.nome,
                    "nome_fantasia": fornecedor.nome_fantasia,
                    "cnpj": fornecedor.cnpj,
                    "email": fornecedor.email,
                    "telefone": fornecedor.telefone,
                    "celular": fornecedor.celular,
                    "cidade": fornecedor.cidade,
                    "estado": fornecedor.estado,
                    "ativo": fornecedor.ativo,
                    "created_at": fornecedor.created_at.isoformat() if fornecedor.created_at else None,
                    "updated_at": fornecedor.updated_at.isoformat() if fornecedor.updated_at else None
                }
                for fornecedor in fornecedores
            ]
        except Exception as e:
            logger.error(f"Erro ao buscar fornecedores: {str(e)}")
            return []
    
    def get_fornecedor_by_id(self, fornecedor_id: int, company_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Buscar fornecedor por ID"""
        try:
            fornecedor = db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.company_id == company_id
            ).first()
            
            if not fornecedor:
                return None
            
            return {
                "id": fornecedor.id,
                "nome": fornecedor.nome,
                "nome_fantasia": fornecedor.nome_fantasia,
                "cnpj": fornecedor.cnpj,
                "inscricao_estadual": fornecedor.inscricao_estadual,
                "inscricao_municipal": fornecedor.inscricao_municipal,
                "email": fornecedor.email,
                "telefone": fornecedor.telefone,
                "celular": fornecedor.celular,
                "site": fornecedor.site,
                "cep": fornecedor.cep,
                "endereco": fornecedor.endereco,
                "numero": fornecedor.numero,
                "complemento": fornecedor.complemento,
                "bairro": fornecedor.bairro,
                "cidade": fornecedor.cidade,
                "estado": fornecedor.estado,
                "pais": fornecedor.pais,
                "banco": fornecedor.banco,
                "agencia": fornecedor.agencia,
                "conta": fornecedor.conta,
                "tipo_conta": fornecedor.tipo_conta,
                "pix": fornecedor.pix,
                "observacoes": fornecedor.observacoes,
                "ativo": fornecedor.ativo,
                "created_at": fornecedor.created_at.isoformat() if fornecedor.created_at else None,
                "updated_at": fornecedor.updated_at.isoformat() if fornecedor.updated_at else None
            }
        except Exception as e:
            logger.error(f"Erro ao buscar fornecedor: {str(e)}")
            return None
    
    def create_fornecedor(self, fornecedor_data: Dict[str, Any], company_id: int, db: Session) -> Dict[str, Any]:
        """Criar novo fornecedor"""
        try:
            # Verificar se CNPJ já existe (apenas se CNPJ não estiver vazio)
            cnpj = fornecedor_data.get('cnpj', '').strip()
            if cnpj:
                existing = db.query(Fornecedor).filter(
                    Fornecedor.cnpj == cnpj,
                    Fornecedor.company_id == company_id
                ).first()
                if existing:
                    return {"success": False, "error": "CNPJ já cadastrado"}
            
            # Se CNPJ estiver vazio, definir como None para evitar constraint unique
            if not cnpj:
                fornecedor_data['cnpj'] = None
            
            fornecedor = Fornecedor(
                company_id=company_id,
                nome=fornecedor_data.get('nome'),
                nome_fantasia=fornecedor_data.get('nome_fantasia'),
                cnpj=fornecedor_data.get('cnpj'),
                inscricao_estadual=fornecedor_data.get('inscricao_estadual'),
                inscricao_municipal=fornecedor_data.get('inscricao_municipal'),
                email=fornecedor_data.get('email'),
                telefone=fornecedor_data.get('telefone'),
                celular=fornecedor_data.get('celular'),
                site=fornecedor_data.get('site'),
                cep=fornecedor_data.get('cep'),
                endereco=fornecedor_data.get('endereco'),
                numero=fornecedor_data.get('numero'),
                complemento=fornecedor_data.get('complemento'),
                bairro=fornecedor_data.get('bairro'),
                cidade=fornecedor_data.get('cidade'),
                estado=fornecedor_data.get('estado'),
                pais=fornecedor_data.get('pais', 'Brasil'),
                banco=fornecedor_data.get('banco'),
                agencia=fornecedor_data.get('agencia'),
                conta=fornecedor_data.get('conta'),
                tipo_conta=fornecedor_data.get('tipo_conta'),
                pix=fornecedor_data.get('pix'),
                observacoes=fornecedor_data.get('observacoes'),
                ativo=fornecedor_data.get('ativo', True)
            )
            
            db.add(fornecedor)
            db.commit()
            db.refresh(fornecedor)
            
            return {
                "success": True,
                "message": "Fornecedor criado com sucesso",
                "fornecedor_id": fornecedor.id
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao criar fornecedor: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def update_fornecedor(self, fornecedor_id: int, fornecedor_data: Dict[str, Any], company_id: int, db: Session) -> Dict[str, Any]:
        """Atualizar fornecedor"""
        try:
            fornecedor = db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.company_id == company_id
            ).first()
            
            if not fornecedor:
                return {"success": False, "error": "Fornecedor não encontrado"}
            
            # Verificar se CNPJ já existe (se foi alterado)
            cnpj = fornecedor_data.get('cnpj', '').strip()
            if cnpj and cnpj != fornecedor.cnpj:
                existing = db.query(Fornecedor).filter(
                    Fornecedor.cnpj == cnpj,
                    Fornecedor.company_id == company_id,
                    Fornecedor.id != fornecedor_id
                ).first()
                if existing:
                    return {"success": False, "error": "CNPJ já cadastrado"}
            
            # Se CNPJ estiver vazio, definir como None para evitar constraint unique
            if not cnpj:
                fornecedor_data['cnpj'] = None
            
            # Atualizar campos
            for field, value in fornecedor_data.items():
                if hasattr(fornecedor, field):
                    setattr(fornecedor, field, value)
            
            db.commit()
            
            return {
                "success": True,
                "message": "Fornecedor atualizado com sucesso"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao atualizar fornecedor: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def delete_fornecedor(self, fornecedor_id: int, company_id: int, db: Session) -> Dict[str, Any]:
        """Deletar fornecedor (soft delete)"""
        try:
            fornecedor = db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.company_id == company_id
            ).first()
            
            if not fornecedor:
                return {"success": False, "error": "Fornecedor não encontrado"}
            
            # Soft delete - marcar como inativo
            fornecedor.ativo = False
            db.commit()
            
            return {
                "success": True,
                "message": "Fornecedor removido com sucesso"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao deletar fornecedor: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def toggle_fornecedor_status(self, fornecedor_id: int, company_id: int, db: Session) -> Dict[str, Any]:
        """Alternar status ativo/inativo do fornecedor"""
        try:
            fornecedor = db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.company_id == company_id
            ).first()
            
            if not fornecedor:
                return {"success": False, "error": "Fornecedor não encontrado"}
            
            fornecedor.ativo = not fornecedor.ativo
            db.commit()
            
            status = "ativado" if fornecedor.ativo else "desativado"
            return {
                "success": True,
                "message": f"Fornecedor {status} com sucesso",
                "ativo": fornecedor.ativo
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao alterar status do fornecedor: {str(e)}")
            return {"success": False, "error": f"Erro interno: {str(e)}"}
