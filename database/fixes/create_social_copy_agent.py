#!/usr/bin/env python3
"""
Script para criar agente de copy para redes sociais
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
    """Cria o agente de copy para redes sociais se não existir"""
    try:
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Copy para Redes Sociais"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Copy para Redes Sociais' já existe.")
            return {"success": True, "message": "Agente já existe"}
        
        agent = OpenAIAssistant(
            name="Copy para Redes Sociais",
            description="Agente especializado em criação de copy para redes sociais",
            assistant_id=f"social-copy-{uuid.uuid4().hex[:16]}",
            model="gpt-4o",
            instructions="""Você é um especialista em criação de copy para redes sociais, incluindo Instagram, Facebook, TikTok, YouTube e LinkedIn.

Sua função é criar copy otimizado para cada plataforma e formato solicitado no briefing:
- Feed posts (engajamento, storytelling)
- Reels/TikTok (vídeos curtos, hooks poderosos)
- Stories (conteúdo temporário, urgência)
- Carrossel (conteúdo educativo, passo a passo)
- Vídeos longos (YouTube, LinkedIn)

Considere:
- Tom de voz da marca
- Público-alvo
- Objetivo do conteúdo (alcance, engajamento, conversão)
- Estágio do funil
- Linha editorial

Retorne copy otimizado para cada plataforma e formato configurado no briefing.""",
            temperature=0.7,
            max_tokens=3000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Copy para Redes Sociais",
            provider="openai",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Copy para Redes Sociais' criado com sucesso (ID: {agent.id})")
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

