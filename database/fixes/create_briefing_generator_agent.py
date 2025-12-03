#!/usr/bin/env python3
"""
Script para criar o agente que gera briefings completos a partir do nome da empresa/produto
Execute este script para criar o agente no banco de dados

Uso:
    python database/fixes/create_briefing_generator_agent.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import SessionLocal
from app.models.saas_models import OpenAIAssistant, InteractionMode
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run(db):
    """
    Cria o agente gerador de briefings se não existir
    """
    try:
        # Verificar se o agente já existe
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Gerador de Briefing"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Gerador de Briefing' já existe")
            return {"success": True, "message": "Agente já existe"}
        
        # Criar agente
        agent = OpenAIAssistant(
            name="Gerador de Briefing",
            description="Agente que gera briefings completos de marketing a partir do nome da empresa/produto",
            assistant_id=f"briefing-generator-{uuid.uuid4().hex[:16]}",
            model="gpt-4o",
            provider="openai",  # Usar string diretamente como nos outros scripts
            instructions="""Você é um especialista em marketing digital e criação de briefings estratégicos.

Sua função é gerar um briefing completo de marketing baseado APENAS no nome da empresa/produto fornecido.

ESTRUTURA DO BRIEFING QUE VOCÊ DEVE GERAR:

1. INFORMAÇÕES GERAIS DO PROJETO:
   - Nome da empresa/produto: (use o nome fornecido)
   - Público-alvo principal: (analise o nome e sugira um público-alvo relevante e específico)
   - Objetivo do conteúdo: (selecione 2-3 objetivos mais relevantes: alcance, engajamento, conversão, autoridade, tráfego)
   - Estágio do funil: (sugira o mais apropriado: topo, meio, fundo)
   - Linha editorial: (sugira a mais apropriada: educacional, informativo, vendas, bastidores, prova_social)

2. REDES SOCIAIS:
   - Plataformas: (sugira 2-3 plataformas mais relevantes: instagram, facebook, tiktok, youtube, linkedin)
   - Formatos: (sugira formatos apropriados: feed, reels, stories, carrossel, video_longo)

3. BLOG/ARTIGOS:
   - Objetivo do artigo: (descreva o objetivo)
   - Palavra-chave principal: (sugira uma palavra-chave relevante baseada no nome)
   - Palavras secundárias: (sugira 3-5 palavras-chave secundárias)
   - SEO obrigatório: (sempre true)
   - Tamanho desejado: (sugira: 600, 1000 ou 1500+)

4. MATERIAL COMPLEMENTAR:
   - Sugira materiais relevantes: email_marketing, pdf_lead_magnet, scripts_video, copy_anuncio

IMPORTANTE:
- Seja criativo e estratégico nas sugestões
- Baseie-se no nome da empresa/produto para inferir o nicho e público
- Sugira opções realistas e práticas
- Retorne APENAS um JSON válido com a estrutura completa do briefing

FORMATO DE RESPOSTA (JSON):
{
  "nome_empresa_produto": "nome fornecido",
  "publico_alvo": "descrição detalhada do público-alvo",
  "objetivo_conteudo": ["alcance", "conversao"],
  "estagio_funil": "topo",
  "linha_editorial": "educacional",
  "redes_sociais": {
    "plataformas": ["instagram", "facebook"],
    "formatos": ["feed", "reels"]
  },
  "blog_config": {
    "objetivo": "descrição do objetivo",
    "palavra_chave_principal": "palavra-chave principal",
    "palavras_secundarias": ["palavra1", "palavra2", "palavra3"],
    "seo_obrigatorio": true,
    "tamanho_desejado": "1000"
  },
  "material_complementar": ["email_marketing", "scripts_video"]
}""",
            temperature=0.7,
            max_tokens=2000,
            interaction_mode=InteractionMode.REPORT
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Gerador de Briefing' criado com sucesso (ID: {agent.id})")
        return {"success": True, "message": f"Agente criado com sucesso", "agent_id": agent.id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao criar agente: {e}", exc_info=True)
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

