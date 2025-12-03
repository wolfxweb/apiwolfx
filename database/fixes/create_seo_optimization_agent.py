#!/usr/bin/env python3
"""
Script para criar agente de otimização SEO
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
    """Cria o agente de otimização SEO se não existir"""
    try:
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Otimização SEO"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Otimização SEO' já existe.")
            return {"success": True, "message": "Agente já existe"}
        
        agent = OpenAIAssistant(
            name="Otimização SEO",
            description="Agente especializado em otimização SEO de conteúdo",
            assistant_id=f"seo-optimization-{uuid.uuid4().hex[:16]}",
            model="gpt-4o",
            instructions="""Você é um especialista em SEO e otimização de conteúdo para mecanismos de busca.

Sua função é otimizar conteúdo baseado em um briefing de marketing, incluindo:
- Meta título (até 60 caracteres)
- Meta descrição (até 160 caracteres)
- Título H1 otimizado
- Subtítulos H2 e H3 estruturados
- Palavras-chave principais e secundárias integradas naturalmente
- Sugestões de links internos e externos
- CTA (Call to Action) otimizado

Retorne o resultado em formato JSON estruturado com todas as otimizações SEO.""",
            temperature=0.5,
            max_tokens=2000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Otimização SEO",
            provider="openai",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Otimização SEO' criado com sucesso (ID: {agent.id})")
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

