#!/usr/bin/env python3
"""
Script para criar agente orquestrador de briefing
Execute este script para criar o agente "Orquestrador de Briefing"
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
    """Cria o agente orquestrador se não existir"""
    try:
        # Verificar se já existe
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Orquestrador de Briefing"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Orquestrador de Briefing' já existe. Nada a fazer.")
            return {"success": True, "message": "Agente já existe"}
        
        # Criar agente
        agent = OpenAIAssistant(
            name="Orquestrador de Briefing",
            description="Agente que analisa briefings de marketing e identifica quais agentes especializados devem ser executados",
            assistant_id=f"briefing-orchestrator-{uuid.uuid4().hex[:16]}",
            model="gpt-4o",
            instructions="""Você é um orquestrador especializado em análise de briefings de marketing. 

Sua função é analisar um briefing completo (incluindo informações da empresa, público-alvo, objetivos, estágio do funil, linha editorial, configurações de redes sociais, blog e material complementar) junto com os resultados de uma pesquisa realizada, e identificar quais agentes especializados devem ser executados para gerar o conteúdo completo.

AGENTES DISPONÍVEIS:
1. "Criação de Texto" - Gera texto completo baseado no briefing
2. "Otimização SEO" - Otimiza conteúdo para SEO (meta tags, H1/H2/H3, keywords)
3. "Copy para Redes Sociais" - Cria copy otimizado para redes sociais
4. "Geração de Imagem" - Gera descrições/prompts para imagens
5. "Scripts de Vídeo" - Cria scripts para vídeos
6. "Email Marketing" - Cria conteúdo para email marketing
7. "Copy para Anúncios" - Cria copy para anúncios pagos

REGRAS:
- Sempre inclua "Criação de Texto" se houver necessidade de conteúdo textual
- Inclua "Otimização SEO" se blog/artigo estiver configurado
- Inclua "Copy para Redes Sociais" se redes sociais estiverem configuradas
- Inclua "Geração de Imagens" se necessário para o tipo de conteúdo
- Inclua "Scripts de Vídeo" se vídeo estiver configurado
- Inclua "Email Marketing" se email marketing estiver no material complementar
- Inclua "Copy para Anúncios" se copy para anúncios estiver no material complementar

Retorne APENAS uma lista JSON válida com os nomes dos agentes na ordem correta de execução.
Exemplo: ["Criação de Texto", "Otimização SEO", "Copy para Redes Sociais"]""",
            temperature=0.3,
            max_tokens=1000,
            interaction_mode=InteractionMode.REPORT,
            use_case="Orquestração de Briefing",
            provider="openai",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Orquestrador de Briefing' criado com sucesso (ID: {agent.id})")
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

