#!/usr/bin/env python3
"""
Script para criar agente de criação de texto usando Anthropic Claude
Execute este script para criar o agente "Criação de Texto" usando Claude
"""
import sys
import os
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import SessionLocal
from app.models.saas_models import OpenAIAssistant, InteractionMode
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run(db):
    """Cria o agente de criação de texto Anthropic se não existir"""
    try:
        # Verificar se já existe
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Criação de Texto"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Criação de Texto' já existe. Nada a fazer.")
            return {"success": True, "message": "Agente já existe"}
        
        # Criar agente
        agent = OpenAIAssistant(
            name="Criação de Texto",
            description="Agente especializado em criação de texto de alta qualidade usando Claude (Anthropic)",
            assistant_id=f"anthropic-text-{uuid.uuid4().hex[:16]}",
            model="claude-3-5-sonnet-20241022",
            instructions="Você é um assistente especializado em criação de texto de alta qualidade. Crie textos claros, persuasivos e bem estruturados. Adapte seu estilo conforme o contexto e objetivo do texto solicitado.",
            temperature=0.7,
            max_tokens=4000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Criação de texto",
            provider="anthropic",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Criação de Texto' criado com sucesso (ID: {agent.id})")
        return {"success": True, "agent_id": agent.id}
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar agente: {e}", exc_info=True)
        db.rollback()
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = run(db)
        if result.get("success"):
            print("✅ Agente criado com sucesso!")
            sys.exit(0)
        else:
            print(f"❌ Erro: {result.get('error')}")
            sys.exit(1)
    finally:
        db.close()

