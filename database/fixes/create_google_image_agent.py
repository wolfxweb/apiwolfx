#!/usr/bin/env python3
"""
Script para criar agente de geração de imagem usando Google Imagen
Execute este script para criar o agente "Geração de Imagem" usando Imagen 3.0
"""
import sys
import os
import json
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import SessionLocal
from app.models.saas_models import OpenAIAssistant, InteractionMode
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run(db):
    """Cria o agente de geração de imagem Google se não existir"""
    try:
        # Verificar se já existe
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Geração de Imagem"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Geração de Imagem' já existe. Nada a fazer.")
            return {"success": True, "message": "Agente já existe"}
        
        # Configurações específicas do Imagen
        api_config = {
            "aspect_ratio": "1:1",
            "safety_filter_level": "block_few"
        }
        
        # Criar agente
        agent = OpenAIAssistant(
            name="Geração de Imagem",
            description="Agente especializado em geração de imagens usando Google Imagen 3.0",
            assistant_id=f"google-image-{uuid.uuid4().hex[:16]}",
            model="imagen-3.0-generate-001",
            instructions="Você é um assistente especializado em geração de imagens. Crie descrições detalhadas e precisas para imagens que serão geradas. Seja específico sobre estilo, composição, cores, iluminação e elementos visuais desejados.",
            temperature=0.7,
            max_tokens=4000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Geração de imagem",
            provider="google",
            api_config=api_config,
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Geração de Imagem' criado com sucesso (ID: {agent.id})")
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

