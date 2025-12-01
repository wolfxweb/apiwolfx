#!/usr/bin/env python3
"""
Script para criar agente de pesquisa usando Perplexity
Execute este script para criar o agente "Pesquisa de Conteúdo" usando Perplexity
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
    """Cria o agente de pesquisa Perplexity se não existir"""
    try:
        # Verificar se já existe
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Pesquisa de Conteúdo"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Pesquisa de Conteúdo' já existe. Nada a fazer.")
            return {"success": True, "message": "Agente já existe"}
        
        # Criar agente
        agent = OpenAIAssistant(
            name="Pesquisa de Conteúdo",
            description="Agente especializado em pesquisa e busca de informações em tempo real usando Perplexity",
            assistant_id=f"perplexity-research-{uuid.uuid4().hex[:16]}",
            model="sonar-pro",
            instructions="Você é um assistente especializado em pesquisa e busca de informações em tempo real. Use a web para encontrar informações atualizadas e precisas. Sempre cite suas fontes e forneça informações verificáveis.",
            temperature=0.7,
            max_tokens=4000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Pesquisa de conteúdo",
            provider="perplexity",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Pesquisa de Conteúdo' criado com sucesso (ID: {agent.id})")
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

