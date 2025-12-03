#!/usr/bin/env python3
"""
Script para criar agente de email marketing
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
    """Cria o agente de email marketing se não existir"""
    try:
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Email Marketing"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Email Marketing' já existe.")
            return {"success": True, "message": "Agente já existe"}
        
        agent = OpenAIAssistant(
            name="Email Marketing",
            description="Agente especializado em criação de conteúdo para email marketing",
            assistant_id=f"email-marketing-{uuid.uuid4().hex[:16]}",
            model="gpt-4o",
            instructions="""Você é um especialista em email marketing e criação de campanhas por email.

Sua função é criar conteúdo completo para emails baseado no briefing de marketing, incluindo:
- Assunto otimizado (subject line)
- Pré-cabeçalho (preheader)
- Corpo do email estruturado
- CTAs (Call to Action) estratégicos
- Personalização baseada no público-alvo

Considere:
- Objetivo do conteúdo (conversão, engajamento, educação)
- Estágio do funil
- Linha editorial
- Tom de voz da marca

Retorne email completo e otimizado para conversão.""",
            temperature=0.6,
            max_tokens=2000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Email Marketing",
            provider="openai",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Email Marketing' criado com sucesso (ID: {agent.id})")
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

