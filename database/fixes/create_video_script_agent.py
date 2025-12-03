#!/usr/bin/env python3
"""
Script para criar agente de scripts de vídeo
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
    """Cria o agente de scripts de vídeo se não existir"""
    try:
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Scripts de Vídeo"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Scripts de Vídeo' já existe.")
            return {"success": True, "message": "Agente já existe"}
        
        agent = OpenAIAssistant(
            name="Scripts de Vídeo",
            description="Agente especializado em criação de scripts para vídeos",
            assistant_id=f"video-script-{uuid.uuid4().hex[:16]}",
            model="gpt-4o",
            instructions="""Você é um especialista em criação de scripts para vídeos, incluindo Reels, TikTok, YouTube e outros formatos.

Sua função é criar scripts completos baseados no briefing de marketing, incluindo:
- Hook inicial (primeiros 3 segundos)
- Estrutura do vídeo (início, meio, fim)
- Diálogos e narrações
- Momentos de pausa e transições
- CTAs (Call to Action) integrados
- Sugestões visuais e de edição

Considere:
- Duração do vídeo (curto para Reels/TikTok, longo para YouTube)
- Público-alvo
- Objetivo do conteúdo
- Estágio do funil
- Linha editorial

Retorne script completo e estruturado para produção do vídeo.""",
            temperature=0.7,
            max_tokens=3000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Scripts de Vídeo",
            provider="openai",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Scripts de Vídeo' criado com sucesso (ID: {agent.id})")
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

